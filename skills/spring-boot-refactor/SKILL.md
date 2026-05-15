---
name: spring-boot-refactor
description: Spring Boot 프로젝트의 아키텍처 개선 및 리팩토링 skill. DDD 패턴 강화, CQRS 패턴 적용, Service 계층 분리(Read/Write), 테스트 커버리지 개선, N+1 문제 해결, 코드 품질 향상 등을 자동으로 분석하고 제안합니다. 'CS-Back 프로젝트를 리팩토링해줘', '서비스 계층을 CQRS로 분리해줘', '테스트 커버리지를 개선해줘', 'N+1 문제를 찾아서 수정해줘' 등의 요청에 사용됩니다.
---

# Spring Boot Refactor Skill

이 skill은 Spring Boot 3.x + JPA + QueryDSL 기반 프로젝트의 체계적인 리팩토링을 지원합니다.

## 핵심 리팩토링 영역

### 1. CQRS 패턴 적용 (Service 계층 분리)

Service 계층을 Read/Write로 분리하여 관심사를 명확히 구분합니다.

**분리 기준:**
- `XyzReadService`: 모든 조회 로직 (`@Transactional(readOnly = true)`)
- `XyzWriteService`: 모든 변경 로직 (`@Transactional`)

**분석 절차:**

1. 기존 Service 클래스 식별
   ```java
   // Before: 단일 Service
   @Service
   public class RepairRequestService {
       public RepairRequestDto getRequest(String id) { ... }
       public void updateRequest(String id, UpdateDto dto) { ... }
   }
   ```

2. 메서드별 성격 분류
   - Read: `get*`, `find*`, `search*`, `list*`, `count*`, `exists*`
   - Write: `create*`, `update*`, `delete*`, `save*`, `modify*`

3. 분리 후 구조
   ```java
   // After: CQRS 분리
   @Service
   @RequiredArgsConstructor
   @Transactional(readOnly = true)
   public class RepairRequestReadService {
       private final HARepairRequestRepository repository;

       public RepairRequestDto getRequest(String id) { ... }
       public List<RepairRequestDto> searchRequests(...) { ... }
   }

   @Service
   @RequiredArgsConstructor
   @Transactional
   public class RepairRequestWriteService {
       private final HARepairRequestRepository repository;
       private final RepairRequestReadService readService;

       public void updateRequest(String id, UpdateDto dto) { ... }
       public String createRequest(CreateDto dto) { ... }
   }
   ```

**주의사항:**
- Write Service는 Read Service를 의존할 수 있음 (역은 불가)
- Controller는 필요에 따라 양쪽 Service를 모두 주입받을 수 있음
- 트랜잭션 범위가 명확해져야 함

### 2. N+1 문제 감지 및 해결

**감지 방법:**

1. 코드에서 Lazy Loading 패턴 찾기
   ```java
   // N+1 발생 위험
   List<Customer> customers = repository.findAll();
   for (Customer c : customers) {
       c.getPartner().getName();  // 각 Customer마다 Partner 조회
   }
   ```

2. Repository 메서드에서 fetch join 누락 확인
   ```java
   // 문제: fetch join 없음
   @Query("SELECT r FROM HomeAppliancesRepairRequest r WHERE r.id = :id")
   Optional<HomeAppliancesRepairRequest> findById(@Param("id") String id);
   ```

**해결 전략:**

**전략 1: Fetch Join (QueryDSL)**
```java
// CustomRepositoryImpl
@Override
public Optional<HomeAppliancesRepairRequest> findByIdWithRelations(String id) {
    return Optional.ofNullable(
        queryFactory
            .select(qHomeAppliancesRepairRequest)
            .from(qHomeAppliancesRepairRequest)
            .leftJoin(qHomeAppliancesRepairRequest.customer, qCustomer).fetchJoin()
            .leftJoin(qCustomer.partner, qPartner).fetchJoin()
            .leftJoin(qHomeAppliancesRepairRequest.product, qProduct).fetchJoin()
            .where(qHomeAppliancesRepairRequest.id.eq(id))
            .fetchOne()
    );
}
```

**전략 2: @EntityGraph**
```java
@EntityGraph(attributePaths = {"customer", "customer.partner", "product"})
@Query("SELECT r FROM HomeAppliancesRepairRequest r WHERE r.id = :id")
Optional<HomeAppliancesRepairRequest> findByIdWithGraph(@Param("id") String id);
```

**전략 3: Batch Fetching (이미 설정됨)**
```yaml
spring.jpa.properties.hibernate.default_batch_fetch_size: 1000
```

**우선순위:**
1. 단일 엔티티 조회: Fetch Join 또는 @EntityGraph
2. 리스트 조회: Batch Fetching (이미 적용됨)
3. 복잡한 조회: QueryDSL Custom Repository

### 3. 테스트 커버리지 개선

**테스트 작성 우선순위:**

1. **핵심 비즈니스 로직** (최우선)
   - Service Write 메서드 (상태 변경, 유효성 검증)
   - 복잡한 계산 로직
   - 도메인 규칙 검증

2. **Repository 커스텀 쿼리**
   - QueryDSL Custom Implementation
   - 복잡한 조인이나 서브쿼리

3. **통합 시나리오**
   - API 엔드포인트 (Controller → Service → Repository)

**테스트 템플릿:**

**Service 테스트 (Mockito)**
```java
@ExtendWith(MockitoExtension.class)
@DisplayName("RepairRequestWriteService 테스트")
class RepairRequestWriteServiceTest {

    @Mock
    private HARepairRequestRepository repository;

    @Mock
    private RepairRequestReadService readService;

    @InjectMocks
    private RepairRequestWriteService service;

    @DisplayName("수리 요청 생성 시 시퀀스 ID가 생성되어야 한다")
    @Test
    void createRequest_shouldGenerateSequenceId() {
        // Given
        CreateRequestDto dto = CreateRequestDto.builder()
            .customerId("C001")
            .productId("P001")
            .build();

        given(repository.save(any())).willReturn(mockEntity);

        // When
        String requestId = service.createRequest(dto);

        // Then
        assertThat(requestId).isNotNull();
        verify(repository).save(any(HomeAppliancesRepairRequest.class));
    }

    @DisplayName("존재하지 않는 요청 업데이트 시 예외가 발생해야 한다")
    @Test
    void updateRequest_notFound_shouldThrowException() {
        // Given
        String invalidId = "INVALID";
        given(readService.getRequest(invalidId))
            .willThrow(new CommonException(ErrorCode.NOT_FOUND));

        // When & Then
        assertThatThrownBy(() -> service.updateRequest(invalidId, updateDto))
            .isInstanceOf(CommonException.class)
            .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_FOUND);
    }
}
```

**Repository 테스트 (@DataJpaTest)**
```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@DisplayName("HARepairRequestRepository 커스텀 쿼리 테스트")
class HARepairRequestRepositoryTest {

    @Autowired
    private HARepairRequestRepository repository;

    @Autowired
    private TestEntityManager entityManager;

    @DisplayName("관계 엔티티와 함께 조회 시 N+1 문제가 발생하지 않아야 한다")
    @Test
    void findByIdWithRelations_shouldNotCauseNPlusOne() {
        // Given
        Customer customer = createCustomer();
        entityManager.persist(customer);

        HomeAppliancesRepairRequest request = createRequest(customer);
        entityManager.persistAndFlush(request);
        entityManager.clear();

        // When
        Optional<HomeAppliancesRepairRequest> result =
            repository.findByIdWithRelations(request.getId());

        // Then
        assertThat(result).isPresent();
        assertThat(result.get().getCustomer()).isNotNull();
        // Lazy loading이 일어나지 않음을 확인
        assertThat(result.get().getCustomer().getPartner()).isNotNull();
    }
}
```

### 4. 아키텍처 패턴 강화

**DDD 임베디드 밸류 객체 활용:**

```java
// Before: Primitive Obsession
@Entity
public class Customer {
    private String phoneNumber;
    private String zipCode;
    private String address;
}

// After: Value Object 패턴
@Entity
public class Customer {
    @Embedded
    private PhoneNumber phoneNumber;

    @Embedded
    private Address address;
}

@Embeddable
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PhoneNumber {
    private String value;

    public PhoneNumber(String value) {
        validate(value);
        this.value = value;
    }

    private void validate(String value) {
        if (!value.matches("^01[0-9]-[0-9]{4}-[0-9]{4}$")) {
            throw new IllegalArgumentException("Invalid phone number format");
        }
    }
}
```

**계층간 DTO 변환 명확화:**

```java
// Controller Layer
public class RepairRequestController {

    @PostMapping
    public ResponseEntity<RepairRequestResponse> create(
        @RequestBody RepairRequestCreateRequest request) {

        // Request → Command DTO
        CreateRequestCommand command = request.toCommand();

        // Service 호출
        String requestId = writeService.createRequest(command);

        // Response 생성
        RepairRequestDto dto = readService.getRequest(requestId);
        return ResponseEntity.ok(RepairRequestResponse.from(dto));
    }
}

// Service Layer - Command/Query DTO 분리
public record CreateRequestCommand(
    String customerId,
    String productId,
    LocalDate requestedDate
) {}

public record RepairRequestDto(
    String id,
    String customerName,
    String productName,
    String status,
    LocalDateTime createdDate
) {}
```

## 리팩토링 워크플로우

### 자동 분석 및 제안 프로세스

1. **코드베이스 스캔**
   - Service 클래스 식별 (CQRS 미적용 대상)
   - Repository 메서드에서 Fetch Join 누락 확인
   - 테스트 파일 존재 여부 확인

2. **우선순위 결정**
   - 높음: N+1 문제로 성능 이슈 발생 가능한 코드
   - 중간: CQRS 미적용 Service 클래스
   - 낮음: 테스트 누락

3. **개선안 제시**
   - 구체적인 코드 변경 예시 제공
   - Before/After 비교
   - 예상 효과 설명

4. **사용자 확인 후 실행**
   - 변경 범위 승인 요청
   - 단계별 리팩토링 수행
   - 테스트 실행으로 검증

### 단계별 실행 가이드

**Step 1: 현황 분석**
```
1. Service 클래스 목록 및 CQRS 적용 여부 확인
2. Repository에서 N+1 위험 메서드 식별
3. 테스트 커버리지 측정
```

**Step 2: 리팩토링 계획 수립**
```
1. 우선순위별 작업 목록 생성
2. 각 작업의 예상 영향도 평가
3. 순차적 실행 계획 (의존성 고려)
```

**Step 3: 실행**
```
1. CQRS 분리: Service → ReadService + WriteService
2. N+1 해결: Fetch Join 또는 @EntityGraph 추가
3. 테스트 작성: 핵심 비즈니스 로직 우선
4. 빌드 및 테스트 실행으로 검증
```

**Step 4: 검증**
```
./gradlew.bat clean build
./gradlew.bat test
```

## 프로젝트별 규칙 준수

### CS-Back 프로젝트 컨벤션

1. **Service 네이밍:**
   - `XyzReadService` / `XyzWriteService` 패턴 필수

2. **Transaction 관리:**
   - Read Service: `@Transactional(readOnly = true)` 클래스 레벨
   - Write Service: `@Transactional` 클래스 레벨

3. **Soft Delete 체크:**
   - 모든 QueryDSL 쿼리에 `.where(qEntity.deleteYn.deleteYn.ne("Y"))` 포함

4. **Entity ID 생성:**
   - `SequenceService` 사용 (DB auto-increment 사용 안 함)

5. **테스트 네이밍:**
   - `@DisplayName`으로 Given-When-Then 패턴 설명

## 참고 자료

프로젝트 아키텍처 및 규칙은 `CLAUDE.md` 파일을 참고합니다.

- Service 계층 분리 패턴: CLAUDE.md "Architecture Overview" 섹션
- QueryDSL 사용법: CLAUDE.md "Data Access Patterns" 섹션
- 테스트 패턴: CLAUDE.md "Repository Testing Pattern" 및 "Service Testing Pattern" 섹션
- 캐싱 전략: CLAUDE.md "Caching Strategy" 섹션
