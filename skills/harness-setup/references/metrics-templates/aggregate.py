#!/usr/bin/env python3
"""Harness Metrics Aggregator.

모든 aggregate-verdict.md (active + archive)를 순회하여 scorecard.md를 집계.
사용: python3 aggregate.py  (환경변수 REPO_ROOT 필수)
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime


def main():
    repo = Path(os.environ.get("REPO_ROOT", "."))
    runtime = repo / ".claude" / "runtime"
    metrics = runtime / "harness-metrics"
    scorecard = metrics / "scorecard.md"

    if not runtime.exists():
        print("[aggregate] .claude/runtime not found — skipping.", file=sys.stderr)
        return 0

    # Collect verdict files
    verdicts = []
    active = runtime / "aggregate-verdict.md"
    if active.exists():
        verdicts.append(active)
    archive = runtime / "archive"
    if archive.exists():
        for f in archive.rglob("aggregate-verdict.md"):
            verdicts.append(f)

    if not verdicts:
        print("[aggregate] No verdict files found — scorecard unchanged.", file=sys.stderr)
        return 0

    rows = []
    stats = {
        "b_valid": 0, "b_invalid": 0, "b_uncertain": 0,
        "a_actioned": 0, "a_ignored": 0,
        "shadow": 0, "scored": 0,
    }

    for path in verdicts:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[warn] read failed: {path}: {e}", file=sys.stderr)
            continue

        def grab(pattern, default="—"):
            m = re.search(pattern, text)
            return m.group(1).strip() if m else default

        issue = grab(r"\*\*Issue\*\*:\s*([^\n]+)")
        phase = grab(r"\*\*Phase\*\*:\s*([^\n]+)")
        verdict = grab(r"\*\*Verdict\*\*:\s*([A-Z|]+)")
        iteration = grab(r"\*\*Iteration\*\*:\s*([^\n]+)")
        duration = grab(r"\*\*Duration\*\*:\s*([^\n]+)")
        tokens = grab(r"\*\*Tokens.*?\*\*:\s*([^\n]+)")
        shadow = grab(r"\*\*Shadow Run\*\*:\s*([YN])")
        if shadow == "Y":
            stats["shadow"] += 1

        pm_match = re.search(r"## Post-merge Scoring(.+?)(?=\n##|\Z)", text, re.DOTALL)
        scored = False
        if pm_match:
            pm = pm_match.group(1)
            if "VALID" in pm or "INVALID" in pm:
                scored = True
                stats["scored"] += 1
            stats["b_valid"] += pm.count("| VALID |")
            stats["b_invalid"] += pm.count("| INVALID |")
            stats["b_uncertain"] += pm.count("| UNCERTAIN |")
            stats["a_actioned"] += pm.count("| ACTIONED |")
            stats["a_ignored"] += pm.count("| IGNORED |")

        rows.append({
            "issue": issue, "phase": phase, "verdict": verdict,
            "iter": iteration, "duration": duration, "tokens": tokens,
            "shadow": shadow, "scored": "✅" if scored else "⏳",
        })

    n = len(rows)
    total_b = stats["b_valid"] + stats["b_invalid"] + stats["b_uncertain"]
    catch = (stats["b_valid"] / total_b * 100) if total_b else 0
    fp = (stats["b_invalid"] / total_b * 100) if total_b else 0

    def pct(v):
        return f"{v:.1f}%" if total_b else "—"

    cond_met = sum([
        n >= 5,
        total_b > 0 and catch >= 60,
        total_b > 0 and fp <= 40,
        stats["shadow"] >= 1,
        stats["scored"] >= 3,
    ])

    lines = []
    lines.append(f"# Harness Metrics Scorecard — {repo.name}")
    lines.append("")
    lines.append(f"> 자동 생성: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"> 생성기: `.claude/runtime/harness-metrics/aggregate.py`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| 지표 | 값 | 합격선 | 상태 |")
    lines.append("|------|-----|-------|------|")
    lines.append(f"| **Total runs (n)** | {n} | ≥ 5 | {'✅' if n >= 5 else '⏳'} |")
    lines.append(f"| **Scored runs** | {stats['scored']} | ≥ 3 | {'✅' if stats['scored'] >= 3 else '⏳'} |")
    lines.append(f"| **Catch rate** | {pct(catch)} | ≥ 60% | {'✅' if total_b and catch >= 60 else '⏳' if not total_b else '❌'} |")
    lines.append(f"| **FP rate** | {pct(fp)} | ≤ 40% | {'✅' if total_b and fp <= 40 else '⏳' if not total_b else '❌'} |")
    lines.append(f"| **Shadow runs** | {stats['shadow']} | ≥ 1 | {'✅' if stats['shadow'] >= 1 else '⏳'} |")
    lines.append(f"| **Blockers V/I/U** | {stats['b_valid']}/{stats['b_invalid']}/{stats['b_uncertain']} | — | — |")
    lines.append(f"| **Advisory A/I** | {stats['a_actioned']}/{stats['a_ignored']} | — | — |")
    lines.append("")
    lines.append("## 누적 데이터 (Per Issue)")
    lines.append("")
    lines.append("| Issue | Phase | Verdict | Iter | Duration | Tokens | Shadow | Scored |")
    lines.append("|-------|-------|---------|------|----------|--------|--------|--------|")
    for r in rows:
        lines.append(f"| {r['issue']} | {r['phase']} | {r['verdict']} | {r['iter']} | {r['duration']} | {r['tokens']} | {r['shadow']} | {r['scored']} |")
    lines.append("")
    lines.append("## 판정 매트릭스")
    lines.append("")
    lines.append(f"- **충족 조건 수**: {cond_met}/5")
    if cond_met >= 4:
        lines.append("- **판정**: 🟢 **Tier 2 진입 + HARNESS_MODE=auto 권장**")
    elif cond_met >= 3:
        lines.append("- **판정**: 🟡 **Suggest 유지, 에이전트 반감 검토**")
    elif n >= 5:
        lines.append("- **판정**: 🔴 **Harness 폐기 검토** (측정 결과 미달)")
    else:
        lines.append("- **판정**: ⏳ **데이터 부족 (n<5) — 결정 유보**")
    lines.append("")
    lines.append("## 다음 행동")
    if n < 5:
        lines.append(f"- n={n}. 실전 이슈 {5 - n}개 더 투입 필요")
    if stats["shadow"] < 1:
        lines.append("- Shadow run 0회 — /harness-shadow 1회 이상 필요")
    if stats["scored"] < 3 and n >= 3:
        lines.append(f"- Scored={stats['scored']}. 머지 7일+ 경과 이슈에 /harness-score 실행")
    lines.append("")

    scorecard.parent.mkdir(parents=True, exist_ok=True)
    scorecard.write_text("\n".join(lines), encoding="utf-8")
    print(f"[aggregate] Wrote {scorecard}")
    print(f"[aggregate] n={n}, catch={pct(catch)}, fp={pct(fp)}, shadow={stats['shadow']}, scored={stats['scored']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
