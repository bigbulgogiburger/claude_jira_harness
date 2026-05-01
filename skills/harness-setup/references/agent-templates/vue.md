# Vue 3 Agent Templates

## compile-check.sh (Vue 3)

```bash
#!/usr/bin/env bash
HARNESS_MODE="${HARNESS_MODE:-suggest}"
[[ "$HARNESS_MODE" == "off" ]] && exit 0
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | grep -oE '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)".*/\1/' 2>/dev/null || echo "")
if [[ -n "$FILE_PATH" ]] && echo "$FILE_PATH" | grep -qiE "\.(vue|ts|tsx)$"; then
  mkdir -p .claude/runtime
  echo "$FILE_PATH" >> .claude/runtime/changed-files.txt
  sort -u .claude/runtime/changed-files.txt -o .claude/runtime/changed-files.txt
fi
exit 0
```

## 핵심 에이전트 (4종) — spring-boot.md와 동일 구조, 스택 차이만

- `{prefix}-explorer`: 동일
- `{prefix}-security-reviewer`: XSS, CORS, CSP 중심으로 description 조정
- `{prefix}-test-writer`: Vitest, @vue/test-utils 패턴 가이드
- `{prefix}-build-resolver`: vite/vue-tsc 빌드 에러 해결

## 도메인 에이전트 (조건부)

### {prefix}-component-reviewer (.vue 파일 존재 시)

```markdown
---
name: {prefix}-component-reviewer
description: "Use PROACTIVELY after .vue file modification. Reviews Composition API patterns, props/emits design, component structure. Never modifies code."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-component-reviewer — Vue 컴포넌트 리뷰 에이전트
## 역할
Composition API 패턴, props/emits 설계, 컴포넌트 구조를 분석하고 개선점을 제안한다.
## 판단 기준
1. Composition API 올바른 사용 (setup, ref, reactive, computed)
2. Props/Emits 타입 안전성
3. 컴포넌트 단일 책임 원칙
4. v-model 패턴
5. slot 활용
```

### {prefix}-design-verifier (스타일 파일 존재 시)

```markdown
---
name: {prefix}-design-verifier
description: "Use after UI component styling changes. Verifies design system compliance, spacing, color tokens."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-design-verifier — 디자인 시스템 검증 에이전트
## 판단 기준
1. 디자인 토큰 사용 (하드코딩된 색상/크기 금지)
2. 반응형 브레이크포인트 일관성
3. 컴포넌트 간 간격 규칙
```

### {prefix}-i18n-checker (locales/ 존재 시)

```markdown
---
name: {prefix}-i18n-checker
description: "Use after locale file or template changes. Checks i18n key coverage, missing translations, unused keys."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-i18n-checker — 다국어 검증 에이전트
## 판단 기준
1. 하드코딩된 문자열 (t() 미사용)
2. locale 파일 간 키 불일치
3. 사용되지 않는 번역 키
```

### {prefix}-state-reviewer (stores/ 존재 시)

```markdown
---
name: {prefix}-state-reviewer
description: "Use after Pinia store modification. Reviews state design, action patterns, getter efficiency."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-state-reviewer — 상태 관리 리뷰 에이전트
## 판단 기준
1. Store 단일 책임
2. Action 내 부수효과 관리
3. Getter 계산 효율성
4. Store 간 의존성
```

## 스택별 CLAUDE.md 디스패치 규칙

```
- *.vue 변경 → {prefix}-component-reviewer 우선 디스패치
- locales/ 변경 → {prefix}-i18n-checker
- stores/ 변경 → {prefix}-state-reviewer
- 빌드 실패 → {prefix}-build-resolver
```
