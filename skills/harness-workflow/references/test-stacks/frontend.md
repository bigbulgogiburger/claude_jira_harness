# Frontend (Vue/React/Angular) 테스트 패턴

## 명령어 감지

package.json의 `scripts` 섹션에서 실제 명령어를 확인합니다.

| 카테고리 | 일반적인 명령 | 대안 |
|----------|-------------|------|
| Lint | `npm run lint` | `npx eslint .` |
| Test | `npm test` | `npm run test:unit`, `npx vitest run`, `npx jest` |
| Build | `npm run build` | `npx vite build`, `npx next build` |

## CLAUDE.md 우선

프로젝트의 CLAUDE.md에 정의된 명령어가 있으면 해당 명령어를 우선 사용합니다.

## 테스트 구조 확인

```
src/**/__tests__/        # Vue/React 컴포넌트 테스트
src/**/*.spec.ts         # Vitest/Jest 스펙 파일
src/**/*.test.ts         # Jest 테스트 파일
tests/                   # E2E 테스트 (Playwright, Cypress)
```

## 주의사항

- `--legacy-peer-deps`가 필요한 프로젝트인지 확인
- TypeScript 프로젝트에서 `import type` 사용 제한이 있을 수 있음 (CLAUDE.md 확인)
- E2E 테스트는 개발 서버가 실행 중이어야 할 수 있음
