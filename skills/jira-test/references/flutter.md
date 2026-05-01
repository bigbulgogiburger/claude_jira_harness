# Flutter 테스트 패턴

## 명령어

| 카테고리 | 명령어 |
|----------|--------|
| Analyze | `flutter analyze` |
| Test | `flutter test` |
| Build (Android) | `flutter build apk --debug` |
| Build (iOS) | `flutter build ios --no-codesign` (macOS만 가능) |

## 테스트 구조 확인

```
test/                    # 단위/위젯 테스트
integration_test/        # 통합 테스트
```

## 주의사항

- `pubspec.yaml`에서 테스트 의존성 확인 (`flutter_test`, `mockito` 등)
- Riverpod 사용 시 `ProviderScope` 감싸기 필요
- 위젯 테스트에서 `pumpWidget` + `pumpAndSettle` 패턴 사용
- 플랫폼별 빌드 제약 (iOS 빌드는 macOS에서만 가능)
- `flutter pub get` 실행 후 테스트 수행
