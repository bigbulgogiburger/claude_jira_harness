# Frontend (Vue/React/Angular) DoD 체크리스트

## 필수 검증 항목

### 코드 품질
- [ ] ESLint 오류 0개 (`npm run lint`)
- [ ] 빌드 성공 (`npm run build`)
- [ ] `console.log`, `console.warn`, `console.error` 디버그 출력 없음
- [ ] `alert()`, `confirm()`, `prompt()` 사용 없음
- [ ] 하드코딩된 시크릿 없음
- [ ] 사용하지 않는 import 없음

### 반응형
- [ ] 모바일 (< 768px) 대응 확인
- [ ] 태블릿 (768-1023px) 대응 확인
- [ ] 데스크톱 (>= 1024px) 대응 확인
- [ ] 오버플로우 없음

### UX
- [ ] 로딩 상태 처리
- [ ] 에러 상태 처리 (try/catch, 사용자 피드백)
- [ ] 빈 데이터 상태 처리

### 보안
- [ ] XSS 방지 (v-html / dangerouslySetInnerHTML 사용 시 sanitize)
- [ ] 사용자 입력 검증
- [ ] API 키 등 민감 정보 미포함

### i18n (다국어 프로젝트인 경우)
- [ ] 하드코딩된 문자열 없음 (i18n 키 사용)
