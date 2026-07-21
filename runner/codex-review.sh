#!/usr/bin/env bash
# =============================================================================
# codex-review.sh — Codex adversarial review 표준 래퍼 (harness v2 설계 §8.3, P0.5)
# =============================================================================
# 배경: codex exec 는 non-TTY 파이프 stdin 에서 무한 블록되는 문서화된 결함이 있다
#   (openai/codex #20919, #27019 — "Reading additional input from stdin" deadlock).
#   우리 실측: 32min 0출력 hang (LOG 2026-06-09 PROJ-570~574) → 이후 codex=skip 관행화.
# 보장 4가지:
#   a. stdin 봉인   — 모든 호출에 < /dev/null (deadlock 원천 차단)
#   b. 출력 파일화  — stdout pipe 캡처 금지 (1.2MB 급 출력의 pipe 버퍼 데드락 차단)
#   c. 이중 타임박스 — hard timeout(기본 900s) + 무진행 watchdog(기본 180s 출력 불변 시 kill)
#   d. 호출 계측    — .claude/runtime/codex-invocations.log 에 1줄/호출 (hang 빈도 최초 계측)
# 폴백 계약: exit 42 = 타임아웃/무진행/실행 실패 → 호출측(오케스트레이터)은 즉시
#   Claude adversarial workflow(opus skeptic 레인)로 대체하고 verdict 에 codex=fallback(<사유>) 기록.
# ★ 2026-07-20 2차 하드닝 (첫 실계측 리뷰의 Codex 자기지적 4건 반영):
#   ① kill 을 프로세스 트리 단위로 (Windows: taskkill //T //F — Node launcher→codex.exe orphan 방지)
#   ② sleep 후 생존 재확인 — 완주 직후 wake 를 TIMEOUT 으로 오판하는 race 제거
#   ③ 기본 출력 파일명에 PID 포함 — 같은 초 이중 호출 truncate 충돌 방지
#   ④ prompt 미존재도 log_line 기록 (호출당 1줄 계약 준수)
#
# 사용:
#   scripts/codex-review.sh <prompt-file> [출력파일]
#   env: CODEX_TIMEOUT(기본 900) CODEX_STALL(기본 180) CODEX_ARGS(기본 "exec")
# =============================================================================
set -u

PROMPT_FILE="${1:?usage: codex-review.sh <prompt-file> [out-file]}"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
RUNTIME="$ROOT/.claude/runtime"
mkdir -p "$RUNTIME"

TS=$(date +%Y%m%d-%H%M%S)
OUT="${2:-$RUNTIME/codex-review-$TS-$$.out}"
LOGF="$RUNTIME/codex-invocations.log"
HARD_TIMEOUT="${CODEX_TIMEOUT:-900}"
STALL_LIMIT="${CODEX_STALL:-180}"
CODEX_ARGS="${CODEX_ARGS:-exec}"

log_line() { # status elapsed bytes note
  printf '[%s] status=%s elapsed=%ss out_bytes=%s prompt=%s note=%s\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "$2" "$3" "$PROMPT_FILE" "${4:-}" >> "$LOGF"
}

if [[ ! -f "$PROMPT_FILE" ]]; then
  log_line PROMPT_MISSING 0 0 "prompt file not found"
  echo "[codex-review] prompt file not found: $PROMPT_FILE" >&2
  exit 42
fi

# ① 프로세스 트리 kill — Windows Git Bash 는 kill 이 자식(codex.exe)을 못 죽인다.
#    ⚠ 실측(2026-07-21 TIMEOUT 강제 테스트): taskkill //T 도 재부모화된 codex.exe 를 놓침 →
#    spawn 전 스냅샷 대비 '새로 생긴 codex.exe' 를 diff kill (래퍼는 슬롯 직렬화 전제라 안전).
CODEX_PIDS_BEFORE=""
snapshot_codex() {
  CODEX_PIDS_BEFORE=$(tasklist.exe 2>/dev/null | grep -i 'codex' | awk '{print $2}' | sort | tr '\n' ' ')
}
kill_tree() {
  local pid=$1
  if command -v taskkill.exe >/dev/null 2>&1; then
    local winpid
    winpid=$(ps -p "$pid" -o winpid= 2>/dev/null | tr -d ' ')
    taskkill.exe //PID "${winpid:-$pid}" //T //F >/dev/null 2>&1
    # 재부모화 orphan 회수: 스냅샷에 없던 codex.exe 전부 kill
    for cpid in $(tasklist.exe 2>/dev/null | grep -i 'codex' | awk '{print $2}'); do
      case " $CODEX_PIDS_BEFORE " in
        *" $cpid "*) ;;                                  # 기존 프로세스 — 보존
        *) taskkill.exe //PID "$cpid" //T //F >/dev/null 2>&1 ;;
      esac
    done
  fi
  kill "$pid" 2>/dev/null; sleep 2; kill -9 "$pid" 2>/dev/null
}

START=$(date +%s)
snapshot_codex

# a. stdin 봉인(< /dev/null) + b. 출력 파일화 — pipe 캡처 절대 금지
# shellcheck disable=SC2086
codex $CODEX_ARGS "$(cat "$PROMPT_FILE")" < /dev/null > "$OUT" 2>&1 &
PID=$!

LAST_SIZE=0
STALL=0
while kill -0 "$PID" 2>/dev/null; do
  sleep 10
  # ② sleep 중 정상 완주했으면 timeout/stall 판정 없이 즉시 회수
  kill -0 "$PID" 2>/dev/null || break
  NOW=$(date +%s); ELAPSED=$((NOW - START))
  SIZE=$(wc -c < "$OUT" 2>/dev/null || echo 0)
  if [[ "$SIZE" -gt "$LAST_SIZE" ]]; then
    LAST_SIZE=$SIZE; STALL=0
  else
    STALL=$((STALL + 10))
  fi
  if [[ "$ELAPSED" -ge "$HARD_TIMEOUT" ]]; then
    kill_tree "$PID"
    log_line TIMEOUT "$ELAPSED" "$SIZE" "hard-timeout(${HARD_TIMEOUT}s) — fallback: opus skeptic workflow"
    echo "[codex-review] TIMEOUT after ${ELAPSED}s → exit 42 (fallback to Claude adversarial)" >&2
    exit 42
  fi
  if [[ "$STALL" -ge "$STALL_LIMIT" ]]; then
    kill_tree "$PID"
    log_line STALLED "$ELAPSED" "$SIZE" "no-output-progress(${STALL_LIMIT}s) — stdin-deadlock 의심(#20919) — fallback"
    echo "[codex-review] STALLED (no output ${STALL_LIMIT}s) → exit 42 (fallback to Claude adversarial)" >&2
    exit 42
  fi
done

wait "$PID"; RC=$?
NOW=$(date +%s); ELAPSED=$((NOW - START))
SIZE=$(wc -c < "$OUT" 2>/dev/null || echo 0)

if [[ "$RC" -ne 0 ]]; then
  log_line "EXIT_$RC" "$ELAPSED" "$SIZE" "non-zero-exit — fallback: opus skeptic workflow"
  echo "[codex-review] codex exited $RC → exit 42 (fallback)" >&2
  exit 42
fi

log_line OK "$ELAPSED" "$SIZE" "-"
echo "$OUT"
exit 0
