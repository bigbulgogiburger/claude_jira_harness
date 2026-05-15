# 프레임워크별 딥 스캔 + 매핑

> 참조 시점: Phase 1-3 (실제 코드 분석) + Phase 1-4 (스캔 결과 → reference 문서 매핑) 수행 시
> 갱신 트리거: 새 프레임워크 지원, 기존 프레임워크의 표준 패턴 변경

## 사용 방법

1. Phase 1-2 에서 감지된 프레임워크 / 언어 조합을 확인
2. 본 문서에서 해당 섹션만 읽고 스캔 — 다른 섹션은 무시
3. 스캔 결과를 해당 섹션의 "매핑" 테이블에 따라 reference 문서로 분류

## 프레임워크 + 언어 감지 우선순위

빌드 파일 감지 순서: `package.json` → `build.gradle(.kts)` → `pom.xml` → `pubspec.yaml` → `go.mod` → `Cargo.toml` → `requirements.txt` / `pyproject.toml` → `Makefile` → `nx.json` / `turbo.json` → `Dockerfile`

**JVM 프로젝트는 Java vs Kotlin 필수 구분:**
- `src/main/kotlin/` 디렉토리 존재
- `*.kt` 파일 비율
- `build.gradle.kts` 사용 + `kotlin("jvm")` 플러그인
- 잘못 감지하면 Lombok ↔ data class 혼용 → 컴파일 실패

**복수 스택 감지:** → Monorepo 로 분기. `references/monorepo.md` 참조.

---

## Vue / Nuxt

### 스캔 영역

- `package.json` → 버전, 의존성, 스크립트, 프로파일
- `vue.config.js` / `nuxt.config.ts` → 빌드/프록시/환경 설정
- `src/views/` → 도메인 디렉토리 목록 (= 도메인 모듈)
- `src/components/` → atoms / common / layouts / mobile 구조
- `src/composables/` → 목록 + 영속화 패턴
- `src/store/` (Vuex) + `src/stores/` (Pinia) → 공존 여부 + 책임 분담
- `src/router/` → 모듈 + 가드 + meta 필드 스키마
- `src/api/` → axios 인스턴스 + 인터셉터 + 커스텀 플래그 (`_skipAuth` 등)
- `src/locales/` → 네임스페이스 구조 + 다국어 동기
- `src/assets/css/` → 변수 / 토큰 / 브레이크포인트
- 그리드 라이브러리: `ag-grid-vue`, `@primevue/datatable`, `vxe-table` 등 버전
- `window.open` 팝업 패턴 사용 빈도
- `keep-alive` 캐시 + dirty 패턴
- Composition API vs Options API 비율: `grep -rc "<script setup>" src/` vs `grep -rc "export default {" src/`
- vue-i18n Legacy 모드 vs Composition 모드: `createI18n({ legacy: ... })`

### 스캔 결과 → reference 매핑

| 스캔 항목 | 기록 위치 |
|-----------|----------|
| package.json 의존성, 빌드 설정 | `build-config.md` |
| Vue 버전, Composition vs Options 비율 | `architecture.md` |
| views/ 구조 → 도메인 목록 | `CLAUDE.md` Architecture + `domain-*.md` |
| components/ 구조 | `component-library.md` |
| composables/ 목록 | 각 해당 reference 에 분산 기재 |
| store/ + stores/ → 상태관리 | `state-management.md` |
| router/ → 모듈 + 가드 + meta | `routing.md` |
| api/ → 인스턴스 + 인터셉터 | `api-layer.md` + `auth-flow.md` |
| 인증 인터셉터 + 라우터 가드 + 토큰 | `auth-flow.md` |
| locales/ → 네임스페이스 구조 | `i18n.md` |
| assets/css/ → 변수 + 브레이크포인트 | `css-system.md` + `responsive-layout.md` |
| 그리드 라이브러리 설정 | `grid-library.md` |
| 에러 핸들링 유틸 + Toast | `error-handling.md` |
| 폼 검증 패턴 | `form-patterns.md` |
| 팝업 패턴 (window.open) | `component-library.md` |
| keep-alive 캐시 관리 | `routing.md` |
| PrimeVue/Element/Vuetify 설정 | `component-library.md` |

### Vue-only NEVER 후보

- **NEVER** composable 바깥에서 `ref()`를 직접 export — 반응성 소실
- **NEVER** `<script setup>` 없이 Composition API 사용 — SFC 컨벤션 위반
- **NEVER** keep-alive 페이지에서 `mounted()` 만 사용 — `activated()` + dirty 패턴 필수
- **NEVER** AxiosResponse 객체를 도메인 객체에 merge — `response.data` 만 사용

---

## Spring Boot (Java)

### 스캔 영역

- `build.gradle` → 버전, 의존성, profile, Flyway, QueryDSL plugin
- `src/main/java/<pkg>/` → 패키지 구조 (domain / common / config / external)
- `application.yml` + profile yml → 프로파일별 설정
- Entity: `@Entity` 어노테이션 검색 + Base 클래스 상속 (감사필드)
- Repository: `JpaRepository` 상속 + `*RepositoryCustom` + `*RepositoryImpl` (QueryDSL CustomImpl 패턴)
- Service: CQRS 분리 여부 (`*ReadService` vs `*WriteService` 또는 단일)
- Controller: Swagger 어노테이션 (`@Tag`, `@Operation`, `@ApiResponses`) + AccessChecker 패턴
- Security: `SecurityConfig` 개수 + JwtAuthenticationFilter + UserType enum
- Scheduling: `@Scheduled` + `@SchedulerLock` (ShedLock) + `@Async`
- 외부연동: `FeignClient` / `WebClient` / Resilience4j
- 캐시: Redis (`RedisTemplate` / `@Cacheable`) / Caffeine
- 암호화: `@Encrypted` + Hibernate listener / `AttributeConverter`

### 스캔 결과 → reference 매핑

| 스캔 항목 | 기록 위치 |
|-----------|----------|
| build.gradle 의존성, 프로파일 | `build-config.md` |
| 패키지 구조 → 도메인 모듈 | `CLAUDE.md` Architecture + `domain-*.md` |
| Entity + 상속 + 감사필드 | `data-access.md` |
| Repository + QueryDSL | `data-access.md` |
| Service CQRS 분리 여부 | `architecture.md` |
| Controller + Swagger | `api-layer.md` |
| Security + JWT | `security.md` |
| application.yml 프로파일 | `build-config.md` |
| 스케줄러 + 외부연동 | `async-scheduling.md` |
| 테스트 설정 | `testing.md` |
| 캐시 (Redis/Caffeine) | `caching.md` |
| 암호화 (@Encrypted) | `security.md` |
| Flyway 마이그레이션 | `build-config.md` + `data-access.md` |

### Spring Boot (Java) NEVER 후보

- **NEVER** Entity 수정 후 `clean build` 생략 — Q-class 재생성 필수
- **NEVER** 쿼리에서 소프트삭제 조건 누락 — 표준 predicate 사용
- **NEVER** `@OneToMany` fetch join 사용 — 페이지네이션 깨짐, batch_fetch_size 사용
- **NEVER** Entity 를 그대로 Controller 응답에 노출 — DTO 매핑 또는 Projection 사용

---

## Spring Boot (Kotlin)

Java 와 동일하나 **언어 차이**로 인한 패턴 다름:

### 추가 스캔 영역
- `build.gradle.kts` + `kotlin("jvm")` / `kotlin("plugin.spring")` / `kotlin("plugin.jpa")` 플러그인
- `src/main/kotlin/` 디렉토리
- data class 사용 빈도 (JPA Entity 에는 금지)
- `suspend fun` + coroutine 사용
- Spring Boot allopen 플러그인 적용 여부

### Kotlin 전용 NEVER 후보

- **NEVER** Entity 에 data class 사용 — JPA 프록시와 충돌, 일반 class + copy 함수로 대체
- **NEVER** suspend fun 없이 코루틴 서비스 작성 — blocking 코드 혼입 방지
- **NEVER** `lateinit var` 를 Bean 주입 외에 사용 — null safety 무력화
- **NEVER** Lombok 사용 — Kotlin 의 data class / 프로퍼티가 대체

### 추가 매핑

| 스캔 항목 | 기록 위치 |
|-----------|----------|
| Kotlin 컨벤션 + data class 금지 영역 | `kotlin-patterns.md` |
| 코루틴 적용 영역 | `kotlin-patterns.md` 또는 `async-scheduling.md` |

---

## React / Next.js

### 스캔 영역

- `package.json` → React 버전, Next.js 버전 (App Router vs Pages Router 결정), 의존성
- `next.config.js` / `next.config.mjs` → middleware, SSR/SSG 설정, env
- App Router: `src/app/` 디렉토리 + `page.tsx` / `layout.tsx` / `loading.tsx` / `route.ts`
- Pages Router: `src/pages/` 디렉토리 + `getStaticProps` / `getServerSideProps`
- 상태관리: Zustand / Redux Toolkit / Jotai / Recoil / Context API
- 데이터 fetch: TanStack Query (React Query) / SWR / 직접 fetch
- 커스텀 hooks: `src/hooks/`
- 스타일: Tailwind / CSS Modules / styled-components / vanilla-extract
- 폼: react-hook-form / formik + zod / yup
- 인증: NextAuth.js / Clerk / Auth0 / 자체 JWT

### 스캔 결과 → reference 매핑

| 스캔 항목 | 기록 위치 |
|-----------|----------|
| Next.js 버전 + Router 종류 | `architecture.md` |
| 의존성, 빌드 설정 | `build-config.md` |
| app/ 또는 pages/ 구조 | `routing.md` |
| 상태관리 | `state-management.md` |
| 데이터 fetch (Query/SWR) | `api-layer.md` |
| 커스텀 hooks | 각 reference 에 분산 |
| 스타일 시스템 | `css-system.md` |
| 폼 검증 | `form-patterns.md` |
| 인증 (NextAuth/Clerk/자체) | `auth-flow.md` |
| middleware / SSR / SSG | `routing.md` |

### React/Next.js NEVER 후보

- **NEVER** Server Component 에서 useState/useEffect — 'use client' 누락
- **NEVER** `getServerSideProps` + App Router 혼용 — Router 1개 선택
- **NEVER** key 누락 list 렌더링 — 리렌더링 깨짐

---

## Flutter (Dart)

### 스캔 영역

- `pubspec.yaml` → Flutter 버전, Dart SDK, 의존성, assets
- `lib/` → 디렉토리 구조 (features / shared / core 등)
- 상태관리: BLoC (bloc/flutter_bloc) / Provider / Riverpod / GetX
- 코드 생성: freezed / json_serializable / build_runner / injectable
- 라우팅: go_router / auto_route / Navigator 1.0
- 플랫폼 채널: `platform/android/`, `platform/ios/`, `platform/web/`
- 테스트: `test/` + `integration_test/`

### 스캔 결과 → reference 매핑

| 스캔 항목 | 기록 위치 |
|-----------|----------|
| Flutter / Dart 버전 + 의존성 | `architecture.md` + `build-config.md` |
| lib/ 구조 + 상태관리 | `architecture.md` + `state-management.md` |
| BLoC/Provider/Riverpod | `state-management.md` |
| freezed / json_serializable | `data-layer.md` |
| 라우팅 | `navigation.md` |
| 플랫폼 채널 | `build-config.md` (플랫폼별) |
| 테스트 + integration_test | `testing.md` |

### Flutter NEVER 후보

- **NEVER** build() 안에서 비동기 호출 — initState 또는 상태관리 레이어에서
- **NEVER** StatefulWidget 남용 — 상태관리 패키지로 분리
- **NEVER** freezed 클래스 수정 후 build_runner 생략 — 생성 코드 stale

---

## NestJS

### 스캔 영역
- `package.json` → NestJS 버전 + 의존성
- `src/` → 모듈 / DI 구조 + decorator 사용
- ORM: TypeORM / Prisma / Mongoose
- Guards / Pipes / Interceptors / Filters
- 큐: BullMQ / Bull / RabbitMQ / Kafka
- 이벤트: EventEmitter / CQRS pattern

### 매핑

| 스캔 항목 | 기록 위치 |
|-----------|----------|
| 모듈 + DI 구조 | `architecture.md` |
| ORM | `data-access.md` |
| Guards/Pipes/Interceptors | `api-layer.md` + `auth-flow.md` |
| 큐 + 이벤트 | `async-scheduling.md` |

---

## FastAPI / Django / Go — 공통 패턴

특수 매핑 없이 일반 카테고리 적용:

| 스캔 범주 | 기록 위치 |
|-----------|----------|
| 빌드/환경 설정 | `build-config.md` |
| 앱 구조/모듈/레이어 | `architecture.md` |
| ORM/데이터 접근 | `data-access.md` |
| 인증/미들웨어/가드 | `auth-flow.md` |
| API 스키마/직렬화/컨트롤러 | `api-layer.md` |
| 상태관리 | `state-management.md` |
| 테스트 구조 | `testing.md` |
| 도메인별 코드 | `domain-[name].md` |

### FastAPI 추가 스캔
- `app/main.py` + `app/api/` 라우터 구조
- Pydantic 모델 (request/response 분리)
- Dependency injection: `Depends(...)`
- SQLAlchemy / SQLModel / Tortoise ORM

### Django 추가 스캔
- `settings.py` + 환경별 분리 (settings/base.py, prod.py)
- `apps/<name>/models.py` / `views.py` / `urls.py`
- DRF (Django REST framework) viewsets / serializers
- 미들웨어 chain

### Go 추가 스캔
- `go.mod` + 모듈 경로
- `cmd/` / `internal/` / `pkg/` 표준 구조
- 라우터: gin / echo / chi / standard library
- ORM: GORM / sqlc / standard library

---

## git diff 기반 역매핑 (Phase 1-1 과 연동)

변경 파일에서 영향받는 reference 를 빠르게 판별:

| 변경 파일 패턴 (단일 프로젝트) | 영향받는 reference |
|---------------|------------------|
| `src/api/domain/*.js` | `api-layer.md` + `domain-[name].md` |
| `src/api/*.js` (interceptors / instance) | `api-layer.md` + `auth-flow.md` |
| `src/store/**`, `src/stores/**` | `state-management.md` |
| `src/router/**` | `routing.md` |
| `src/views/[domain]/**` | `domain-[name].md` |
| `src/locales/*.json` | `i18n.md` |
| `src/assets/css/**` | `css-system.md` |
| `vue.config.js`, `.env*` | `build-config.md` |
| `src/components/common/**` | `component-library.md` |
| `src/utils/**` | `error-handling.md` |
| `package.json` | `build-config.md` (+ 버전 변경 시 해당 reference) |
| `**/security/**`, `**/config/Security*` | `security.md` |
| `**/exception/**`, `**/ErrorResponse*` | `api-layer.md` (BE) |
| `**/repository/**`, `**/entity/**` | `data-access.md` |
| `src/main/resources/db/migration/V*.sql` | `data-access.md` + `build-config.md` |

**Monorepo 의 경우** — 모든 패턴 앞에 `<sub>/` prefix 추가 + sub 별 reference 디렉토리로 매핑. `references/monorepo.md § 7` 참조.
