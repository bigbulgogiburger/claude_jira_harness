#!/usr/bin/env python3
"""
harness-execute.py — headless step 러너 (harness v2 설계 §4.2, P2)

핵심 계약: **모델은 코드만 쓴다.** 검증(AC·probe·diff 범위·FORBID)과 commit 권한은
전부 이 러너가 가진다 — hook 비의존 결정론 게이트 (headless hook 발화가 문서상
미보장이므로 러너가 게이트의 1차 책임자).

사용:
  python scripts/harness-execute.py phases/STD-N [--max-retries 3] [--step N]
                                    [--dry-run] [--timeout 1800]

index.json 스키마 (§4.1 — /jira-compile 산출물):
  {
    "issue": "STD-N", "branch": "feat/STD-N",
    "contract": ".claude/runtime/sprint-contract/STD-N.md",
    "always_context": ["phases/_always.md"],
    "forbid": ["git push", "-Pqa", ...],          # loop.yaml safety 미러 (operation-anchor)
    "steps": [{
      "step": 0, "name": "entity-layer", "status": "pending",
      "model": "opus", "max_turns": 40, "timeout": 1800,
      "prompt_file": "phases/STD-N/step0-entity-layer.md",
      "ac": ["cd backend && JAVA_HOME=... ./gradlew.bat compileJava"],
      "probe": [{"kind": "grep", "cmd": "...", "expect": "<regex>"}],
      "context_refs": ["docs/08-decision-log.md#ADR-090", "docs/STD-M-dev-guide.md"],
      "touched_files": ["backend/src/main/java/com/example/domain/**"],
      "summary": null, "error_message": null, "cost_usd": null, "attempts": 0
    }]
  }
status: pending | completed | error | blocked
  - blocked = FORBID 히트 또는 인간 게이트(Flyway QA·W13·prod) — 인간만 해제 가능
  - error   = AC/probe/diff 게이트 3회 연속 실패 — 인간이 원인 해소 후 pending 복귀
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

# Windows 콘솔 cp949 가 한글/em-dash 출력에서 UnicodeEncodeError — UTF-8 강제 (실측)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# ── 예방층: step 세션의 per-invocation deny (§4.2 — 검출층인 FORBID 재매칭과 2층 구조)
DISALLOWED_TOOLS = ",".join([
    "Bash(git commit*)", "Bash(git push*)", "Bash(git merge*)",
    "Bash(rm -rf*)", "Bash(*-Pqa*)", "Bash(*-Pprod*)",
    "Bash(*std_cs_app*)", "Bash(*DROP TABLE*)", "Bash(*DROP COLUMN*)",
])

# 러너 산출물/상태 경로는 diff 범위 검사에서 항상 허용
ALWAYS_ALLOWED_GLOBS = ["phases/**", ".claude/runtime/**"]

DEFAULT_FORBID = [
    "git push", "push --force", "push -f", "git merge", "gh pr merge",
    "rm -rf", "-Pqa", "-Penv=qa", "profiles.active=qa", "std_cs_app",
    "-Pprod", "-Penv=prod", "profiles.active=prod",
    "DROP TABLE", "DROP COLUMN",
]


def log(msg: str) -> None:
    print(f"[harness-execute {_dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


# ─────────────────────────────────────────────────────────────── index io ──
def load_index(phase_dir: str) -> dict:
    with open(os.path.join(phase_dir, "index.json"), encoding="utf-8") as f:
        return json.load(f)


def save_index(phase_dir: str, idx: dict) -> None:
    """atomic write — 중단 시에도 index.json 파손 없음 (재개 SSoT 보호)."""
    path = os.path.join(phase_dir, "index.json")
    fd, tmp = tempfile.mkstemp(dir=phase_dir, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def first_pending(idx: dict) -> dict | None:
    for s in idx["steps"]:
        if s.get("status") == "pending":
            return s
    return None


# ──────────────────────────────────────────────── context_refs 선별 주입 ──
SECTION_CAP = 120_000  # 파일 통주입 상한 (bytes) — 초과 시 경고 + 앞부분 절단


def extract_context(ref: str, root: str = None) -> str:
    """'path#ANCHOR' → 해당 `## ANCHOR ...` 헤더부터 다음 `## ` 전까지.
    앵커 없으면 파일 전문 (SECTION_CAP 절단). W1 헤더 정규화(`## ADR-NNN — 제목`)가 전제."""
    root = root or ROOT
    path, _, anchor = ref.partition("#")
    full = os.path.join(root, path)
    if not os.path.isfile(full):
        return f"[context_refs 경고] 파일 없음: {path}"
    with open(full, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if not anchor:
        if len(text.encode("utf-8")) > SECTION_CAP:
            return text[:SECTION_CAP] + f"\n\n[... {path} 절단 — {SECTION_CAP} bytes 상한]"
        return text
    # 앵커: '## ADR-090' / '## 3. 구현 계획' 류 — 헤더 라인 prefix 매칭
    lines = text.split("\n")
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"^#{{1,4}}\s*{re.escape(anchor)}(\s|—|:|$)", ln):
            start = i
            break
    if start is None:
        return f"[context_refs 경고] 앵커 미발견: {ref} — 파일 헤더 정규화(W1) 확인 필요"
    start_depth = len(lines[start]) - len(lines[start].lstrip("#"))
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = re.match(r"^(#{1,4})\s", lines[j])
        if m and len(m.group(1)) <= start_depth:
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def build_prompt(idx: dict, step: dict, prev_error: str | None, root: str = None) -> str:
    root = root or ROOT
    parts: list[str] = []
    for p in idx.get("always_context", []):
        parts.append(extract_context(p, root))
    if step.get("context_refs"):
        parts.append("## 선별 가드레일 (INDEX cross-ref — 이 이슈에 관련된 결정만)")
        for ref in step["context_refs"]:
            parts.append(f"### {ref}\n{extract_context(ref, root)}")
    done = [s for s in idx["steps"] if s.get("status") == "completed" and s.get("summary")]
    if done:
        parts.append("## 완료된 step 요약 (누적 컨텍스트)")
        parts.extend(f"- step{s['step']} {s['name']}: {s['summary']}" for s in done)
    pf = os.path.join(root, step["prompt_file"])
    with open(pf, encoding="utf-8") as f:
        parts.append("## 이번 step 작업 지시 (자기완결)\n" + f.read())
    if prev_error:
        parts.append(
            "## ⚠ 직전 시도 실패 — 아래 에러를 해소하라 (fresh 세션, 이전 대화 없음)\n"
            + prev_error[-8000:]
        )
    parts.append(
        "## 러너 계약 (준수 필수)\n"
        "- 코드 작성/수정만 하라. **git commit/push/merge 를 실행하지 마라** — 검증과 커밋은 러너가 한다.\n"
        f"- 선언된 touched_files 범위 밖 파일을 수정하지 마라: {step.get('touched_files', [])}\n"
        "- 마지막 메시지에 1줄 요약을 `SUMMARY: <내용>` 형식으로 남겨라."
    )
    return "\n\n---\n\n".join(parts)


# ──────────────────────────────────────────────────────── claude 호출 ──
def _claude_cmd() -> list[str]:
    """claude CLI 실체 해석 — 파일럿 실측 함정: PATH 의 claude.cmd 가 삭제된 구 설치
    (nodejs 전역 cli.js)를 가리키는 stale 런처라 즉시 MODULE_NOT_FOUND 로 죽었다.
    네이티브 bin/claude.exe 를 우선 탐색 (cmd.exe 레이어 quoting 문제도 함께 제거)."""
    import glob as _glob
    cand = os.environ.get("HARNESS_CLAUDE_EXE")
    if cand and os.path.isfile(cand):
        return [cand]
    home = os.path.expanduser("~")
    patterns = [
        os.path.join(home, r"AppData\Roaming\nvm\*\node_modules\@anthropic-ai\claude-code\bin\claude.exe"),
        os.path.join(home, r"AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"),
    ]
    for pat in patterns:
        hits = sorted(_glob.glob(pat))
        if hits:
            return [hits[-1]]
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("claude CLI 미발견 (PATH/HARNESS_CLAUDE_EXE 확인)")
    if exe.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/d", "/c", exe]
    return [exe]


def run_claude(prompt: str, step: dict, timeout: int) -> dict:
    """claude -p fresh 세션. stdin 으로 프롬프트 전달(Windows argv 32K 한계 회피).
    반환: {"result": str, "cost_usd": float|None, "is_error": bool, "raw": str}"""
    cmd = _claude_cmd() + [
        "-p", "--output-format", "json",
        "--max-turns", str(step.get("max_turns", 40)),
        "--dangerously-skip-permissions",
        "--disallowedTools", DISALLOWED_TOOLS,
    ]
    if step.get("model"):
        cmd += ["--model", step["model"]]
    try:
        proc = subprocess.run(
            cmd, input=prompt.encode("utf-8"), capture_output=True,
            timeout=timeout, cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return {"result": "", "cost_usd": None, "is_error": True,
                "raw": f"[runner] step hard-timeout {timeout}s"}
    out = proc.stdout.decode("utf-8", errors="replace")
    parsed = parse_claude_json(out)
    if proc.returncode != 0 and not parsed.get("result"):
        parsed["is_error"] = True
        parsed["raw"] += f"\n[exit={proc.returncode}] stderr: " + proc.stderr.decode("utf-8", errors="replace")[-2000:]
    return parsed


def parse_claude_json(out: str) -> dict:
    """--output-format json 의 마지막 JSON 오브젝트에서 result/total_cost_usd 추출."""
    try:
        data = json.loads(out.strip().split("\n")[-1]) if out.strip() else {}
    except json.JSONDecodeError:
        # stdout 에 JSON 외 잡음 — 마지막 '{' 부터 재시도
        i = out.rfind("\n{")
        try:
            data = json.loads(out[i:]) if i != -1 else {}
        except json.JSONDecodeError:
            data = {}
    return {
        "result": data.get("result", ""),
        "cost_usd": data.get("total_cost_usd"),
        "is_error": bool(data.get("is_error", False)) or not data,
        "raw": out,
    }


# ───────────────────────────────────────────── 러너 게이트 (4중 검증) ──
def _bash_path() -> str:
    """Git Bash 를 명시 해석 — Windows 에서 bare 'bash' 는 System32\\bash.exe(WSL)로
    떨어져 'Linux용 Windows 하위 시스템 배포 없음' 으로 죽는다 (러너 테스트 실측)."""
    cand = os.environ.get("HARNESS_BASH")
    if cand and os.path.isfile(cand):
        return cand
    for c in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if os.path.isfile(c):
            return c
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    return "bash"


def sh(cmd: str, timeout: int = 900) -> tuple[int, str]:
    """Git Bash 로 실행 — AC/probe 커맨드는 bash 문법(&&, JAVA_HOME=... 등) 전제."""
    try:
        p = subprocess.run([_bash_path(), "-lc", cmd], capture_output=True, timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return 124, f"[runner] gate-timeout {timeout}s: {cmd}"
    out = p.stdout.decode("utf-8", errors="replace") + p.stderr.decode("utf-8", errors="replace")
    # CRLF 정규화 — 파일럿 실측: Windows stdout \r\n 이 probe 의 `$` anchor 를 깨서
    # 정상 출력이 expect 불일치로 오발 (재시도 1회 낭비). 게이트 비교는 \n 기준으로 통일.
    return p.returncode, out.replace("\r\n", "\n")


def gate_ac(step: dict) -> str | None:
    """a. AC 커맨드를 러너가 직접 재실행 (모델 자기보고 불신). 실패 시 에러 문자열."""
    for cmd in step.get("ac", []):
        rc, out = sh(cmd)
        if rc != 0:
            return f"AC 실패 (exit={rc}): {cmd}\n{out[-4000:]}"
    return None


def gate_probe(step: dict) -> str | None:
    """b. probe 실행 + expect 정규식 매칭 (anti-gaming — 정적 GREEN 만으로 completed 금지)."""
    for pr in step.get("probe", []):
        rc, out = sh(pr["cmd"])
        if rc != 0:
            return f"probe 실행 실패 (exit={rc}): {pr['cmd']}\n{out[-2000:]}"
        if pr.get("expect") and not re.search(pr["expect"], out, re.MULTILINE):
            return f"probe expect 불일치: {pr['cmd']}\n  expect~=/{pr['expect']}/\n  실측: {out[-2000:]}"
    return None


def changed_paths() -> list[str]:
    rc, out = sh("git status --porcelain")
    paths = []
    for ln in out.splitlines():
        if not ln.strip():
            continue
        p = ln[3:].strip().strip('"')
        if " -> " in p:
            p = p.split(" -> ")[-1]
        paths.append(p.replace("\\", "/"))
    return paths


def gate_diff_scope(step: dict, paths: list[str] | None = None,
                    baseline: set[str] | None = None) -> str | None:
    """c. touched-files 선언 범위 밖 변경 검출 → error (auto-revert 하지 않음 — 인간 판단).
    baseline = step 시작 전부터 dirty 였던 경로 (동시 세션/수작업 변경) — 게이트 대상에서 제외.
    (벤치마크 실측 결함 수정: 전체 status 를 보면 타 세션 변경이 오발·오커밋됨)"""
    globs = list(step.get("touched_files", [])) + ALWAYS_ALLOWED_GLOBS
    paths = changed_paths() if paths is None else paths
    if baseline:
        paths = [p for p in paths if p not in baseline]
    out_of_scope = [
        p for p in paths
        if not any(fnmatch.fnmatch(p, g) or fnmatch.fnmatch(p, g.rstrip("/") + "/*") for g in globs)
    ]
    if out_of_scope:
        return "선언 범위 밖 변경 검출: " + ", ".join(out_of_scope[:20])
    return None


def baseline_conflict(step: dict, baseline: set[str]) -> str | None:
    """사전 dirty 경로가 이 step 의 touched_files 와 겹치면 실행 거부 — 동시 작업 충돌 방지."""
    globs = step.get("touched_files", [])
    hits = [p for p in baseline
            if any(fnmatch.fnmatch(p, g) or fnmatch.fnmatch(p, g.rstrip("/") + "/*") for g in globs)]
    if hits:
        return ("step touched_files 와 겹치는 사전 미커밋 변경 존재(동시 세션 충돌 위험): "
                + ", ".join(hits[:10]) + " — 해당 변경 커밋/정리 후 재실행")
    return None


def gate_forbid(idx: dict, session_text: str, diff_text: str) -> str | None:
    """d. FORBID 재매칭 (loop.yaml safety 미러, operation-anchor 규율) — 히트 시 blocked.
    diff 는 **추가된 라인만** 검사 (기존 문서의 산문 인용이 오발하지 않도록 — 2026-06-30 driver 자폭 교훈)."""
    added = "\n".join(
        ln[1:] for ln in diff_text.splitlines()
        if ln.startswith("+") and not ln.startswith("+++")
    )
    for pat in idx.get("forbid", DEFAULT_FORBID):
        for label, text in (("session", session_text), ("diff+", added)):
            if pat in text:
                return f"FORBID 히트 [{label}]: '{pat}'"
    return None


# ─────────────────────────────────────────────────────────── commit ──
def runner_commit(idx: dict, step: dict, baseline: set[str] | None = None) -> str | None:
    """통과 시에만 러너가 commit — 모델에게 commit 을 시키지 않는다.
    baseline(사전 dirty) 경로는 절대 staging 하지 않는다 — 타 세션 변경 오커밋 방지."""
    paths = [p for p in changed_paths() if not (baseline and p in baseline)]
    if not paths:
        return None  # 변경 없음(문서/조사 step) — commit 생략은 정상
    rc, out = sh("git add -A -- " + " ".join(f"'{p}'" for p in paths))
    if rc != 0:
        return None if "nothing" in out else out
    msg = f"feat({idx['issue']}): step{step['step']} {step['name']} [harness-execute]"
    rc, out = sh(f"git commit -m \"{msg}\"")
    if rc != 0:
        log(f"commit 실패: {out[-500:]}")
        return None
    rc, sha = sh("git rev-parse --short HEAD")
    return sha.strip() if rc == 0 else None


# ─────────────────────────────────────────────────────────── main ──
def extract_summary(result_text: str) -> str:
    m = re.search(r"^SUMMARY:\s*(.+)$", result_text, re.MULTILINE)
    return (m.group(1) if m else result_text.strip().split("\n")[-1])[:300]


def execute_step(idx: dict, step: dict, phase_dir: str, args) -> str:
    """한 step 실행. 반환: completed | error | blocked"""
    prev_error = None
    baseline = set(changed_paths())  # 사전 dirty 스냅샷 — 게이트/commit 대상에서 격리
    conflict = baseline_conflict(step, baseline)
    if conflict:
        step["status"] = "blocked"
        step["error_message"] = conflict
        save_index(phase_dir, idx)
        return "blocked"
    for attempt in range(1, args.max_retries + 1):
        step["attempts"] = step.get("attempts", 0) + 1
        log(f"step{step['step']} {step['name']} — 시도 {attempt}/{args.max_retries} (model={step.get('model', 'inherit')})")
        prompt = build_prompt(idx, step, prev_error)
        if args.dry_run:
            print(prompt)
            return "pending"
        res = run_claude(prompt, step, step.get("timeout", args.timeout))
        if res.get("cost_usd"):
            # 실패 시도 포함 누적 — 파일럿 실측: 마지막 시도만 기록하면 재시도 비용이 유실됨
            step["cost_usd"] = round((step.get("cost_usd") or 0) + res["cost_usd"], 6)
        if res["is_error"] and not res["result"]:
            prev_error = f"claude 세션 에러: {res['raw'][-3000:]}"
            step["error_message"] = prev_error[:1500]  # 재시도 소진 시에도 원인 보존 (파일럿 실측 결함)
            save_index(phase_dir, idx)
            log(f"  세션 에러 → 재시도 (API null/timeout 계열): {res['raw'][-200:]}")
            continue
        # 러너 게이트 — hook 비의존 4중 검증
        _, diff_text = sh("git diff; git diff --cached")
        err = gate_forbid(idx, res["result"], diff_text)
        if err:
            step["status"] = "blocked"
            step["error_message"] = err + " — 인간만 해제 가능 (사유 해소 후 status=pending 복귀)"
            save_index(phase_dir, idx)
            return "blocked"
        err = gate_diff_scope(step, baseline=baseline) or gate_ac(step) or gate_probe(step)
        if err is None:
            sha = runner_commit(idx, step, baseline=baseline)
            step["status"] = "completed"
            step["summary"] = extract_summary(res["result"])
            step["error_message"] = None
            step["commit"] = sha
            step["completed_at"] = _dt.datetime.now().isoformat(timespec="seconds")
            save_index(phase_dir, idx)
            log(f"  ✅ completed (commit={sha}, cost=${res['cost_usd']})")
            return "completed"
        prev_error = err
        step["error_message"] = err
        save_index(phase_dir, idx)
        log(f"  게이트 실패 → 에러 주입 fresh 재시도: {err[:200]}")
    step["status"] = "error"
    save_index(phase_dir, idx)
    return "error"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="프로젝트 headless step runner (harness v2 §4.2)")
    ap.add_argument("phase_dir", help="예: phases/STD-N")
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800, help="step 당 hard timeout (초)")
    ap.add_argument("--step", type=int, default=None, help="특정 step 만 실행")
    ap.add_argument("--dry-run", action="store_true", help="프롬프트만 출력, 미실행")
    args = ap.parse_args(argv)

    idx = load_index(args.phase_dir)
    # 브랜치 가드: index 선언 브랜치 위에서만 실행
    rc, cur = sh("git rev-parse --abbrev-ref HEAD")
    cur = cur.strip()
    if idx.get("branch") and cur != idx["branch"]:
        log(f"⛔ 현재 브랜치 {cur} ≠ index 선언 {idx['branch']} — 중단")
        return 2

    while True:
        step = None
        if args.step is not None:
            step = next((s for s in idx["steps"] if s["step"] == args.step), None)
            if step and step["status"] != "pending":
                log(f"step{args.step} status={step['status']} — pending 아님, 중단")
                return 2
        else:
            step = first_pending(idx)
        if step is None:
            log("전 step completed — review 단계로 (harness-workflow ⑦)")
            return 0
        outcome = execute_step(idx, step, args.phase_dir, args)
        if outcome in ("blocked", "error"):
            log(f"⛔ step{step['step']} {outcome}: {(step.get('error_message') or '')[:300]}")
            return 1
        if outcome == "pending":  # dry-run
            return 0
        if args.step is not None:
            return 0


if __name__ == "__main__":
    sys.exit(main())
