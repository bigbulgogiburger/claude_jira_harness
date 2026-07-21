# Flutter DoD (Definition of Done) 체크리스트

## 필수 검증 항목

### 코드 품질
- [ ] `flutter analyze` 경고/오류 없음
- [ ] `flutter test` 통과
- [ ] `print()`, `debugPrint()` 디버그 출력 없음 (Logger 사용)
- [ ] 하드코딩된 시크릿 없음
- [ ] 사용하지 않는 import 없음

### 아키텍처
- [ ] 상태 관리 패턴 일관성 (Riverpod/Bloc/Provider 등)
- [ ] UI와 비즈니스 로직 분리
- [ ] 모델 클래스에 `fromJson`/`toJson` 구현 (API 통신 시)
- [ ] 에러 처리 적절 (try/catch, 사용자 피드백)

### UI/UX
- [ ] 로딩 상태 표시 (CircularProgressIndicator 등)
- [ ] 에러 상태 표시
- [ ] 빈 데이터 상태 표시
- [ ] 키보드 오버플로우 방지 (SingleChildScrollView, resizeToAvoidBottomInset)
- [ ] 다양한 화면 크기 대응 (MediaQuery, LayoutBuilder)

### 보안
- [ ] API 키는 환경 변수 또는 secure storage 사용
- [ ] 사용자 입력 검증
- [ ] 민감 데이터 로깅 없음

### 다국어 (easy_localization 등 사용 시)
- [ ] 하드코딩된 문자열 없음 (번역 키 사용)
