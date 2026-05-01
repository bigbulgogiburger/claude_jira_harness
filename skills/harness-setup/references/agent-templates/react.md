# React Agent Templates

## compile-check.sh (React)

```bash
#!/usr/bin/env bash
HARNESS_MODE="${HARNESS_MODE:-suggest}"
[[ "$HARNESS_MODE" == "off" ]] && exit 0
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | grep -oE '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)".*/\1/' 2>/dev/null || echo "")
if [[ -n "$FILE_PATH" ]] && echo "$FILE_PATH" | grep -qiE "\.(tsx|jsx|ts)$"; then
  mkdir -p .claude/runtime
  echo "$FILE_PATH" >> .claude/runtime/changed-files.txt
  sort -u .claude/runtime/changed-files.txt -o .claude/runtime/changed-files.txt
fi
exit 0
```

## 핵심 에이전트 (4종) — spring-boot.md와 동일 구조

- `{prefix}-explorer`: 동일
- `{prefix}-security-reviewer`: XSS, CORS, CSP, dangerouslySetInnerHTML 중심
- `{prefix}-test-writer`: Jest, React Testing Library, @testing-library/hooks 패턴
- `{prefix}-build-resolver`: webpack/vite/tsc 빌드 에러 해결

## 도메인 에이전트 (조건부)

### {prefix}-component-reviewer (.tsx 파일 존재 시)

```markdown
---
name: {prefix}-component-reviewer
description: "Use PROACTIVELY after .tsx/.jsx file modification. Reviews React patterns, hooks, memo, context usage. Never modifies code."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-component-reviewer — React 컴포넌트 리뷰 에이전트
## 판단 기준
1. Hook 규칙 (조건부 호출 금지, 최상위에서만)
2. useMemo/useCallback 적절한 사용
3. key prop 안정성
4. 컴포넌트 합성 패턴
5. prop drilling vs context
```

### {prefix}-hook-auditor (hooks/ 존재 시)

```markdown
---
name: {prefix}-hook-auditor
description: "Use after custom hook creation/modification. Reviews hook design, dependency arrays, cleanup patterns."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-hook-auditor — Custom Hook 리뷰 에이전트
## 판단 기준
1. useEffect dependency array 정확성
2. cleanup 함수 필요 여부
3. hook 재사용성
4. 불필요한 리렌더링 유발 여부
```

### {prefix}-performance-reviewer (.tsx 파일 존재 시)

```markdown
---
name: {prefix}-performance-reviewer
description: "Use when performance issues suspected. Reviews re-render patterns, bundle size, lazy loading."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-performance-reviewer — 성능 리뷰 에이전트
## 판단 기준
1. 불필요한 리렌더링 (React.memo, useMemo 누락)
2. 번들 사이즈 (dynamic import, code splitting)
3. 이미지/미디어 최적화
4. 가상화 필요 여부 (긴 리스트)
```

### {prefix}-state-reviewer (store/context 존재 시)

```markdown
---
name: {prefix}-state-reviewer
description: "Use after state management changes. Reviews Redux/Zustand/Context patterns, selector efficiency."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-state-reviewer — 상태 관리 리뷰 에이전트
## 판단 기준
1. 전역 vs 지역 상태 적절한 구분
2. Selector 메모이제이션
3. 상태 정규화
4. 불변성 패턴
```

## 스택별 CLAUDE.md 디스패치 규칙

```
- *.tsx/*.jsx 변경 → {prefix}-component-reviewer 우선 디스패치
- hooks/ 변경 → {prefix}-hook-auditor
- store/context 변경 → {prefix}-state-reviewer
- 빌드 실패 → {prefix}-build-resolver
```
