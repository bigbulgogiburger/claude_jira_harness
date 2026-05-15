# 테스트 작성 가이드

## 개요

CS-Back 프로젝트의 테스트 커버리지를 체계적으로 개선하기 위한 가이드입니다.
Given-When-Then 패턴과 `@DisplayName`을 활용한 명확한 테스트 작성을 지향합니다.

## 중요: 성공과 실패 케이스 모두 작성

**테스트는 성공 케이스와 실패 케이스를 모두 포함해야 합니다.**

- **성공 케이스 (Happy Path):** 정상적인 흐름 검증
- **실패 케이스 (Failure Path):** 예외 상황, 에러 처리, 비즈니스 규칙 위반 검증

### 실패 케이스가 중요한 이유

1. **버그 예방:** 예외 상황에서의 동작을 명확히 정의
2. **안전한 리팩토링:** 에러 처리가 깨지지 않았는지 확인
3. **문서화:** 어떤 상황에서 어떤 예외가 발생하는지 명시
4. **운영 안정성:** 실제 운영 환경의 다양한 상황 대비

### 일반적인 실패 케이스 유형

```
- 존재하지 않는 데이터 접근 → NotFoundException
- 중복 데이터 생성 시도 → DuplicateException
- 비즈니스 규칙 위반 → BusinessRuleException
- 권한 부족 → UnauthorizedException
- 잘못된 입력값 → ValidationException
- 상태 전환 오류 → InvalidStateException
- 제약 조건 위반 → DataIntegrityViolationException
```

**원칙:** 각 메서드마다 최소 1개 이상의 실패 케이스를 작성하세요.

## 테스트 계층

### 1. Controller Test (Controller 계층 테스트)
- **대상:** Controller 계층 (요청/응답 처리)
- **도구:** @WebMvcTest, MockMvc
- **어노테이션:** `@WebMvcTest(ControllerClassName.class)`
- **특징:** Controller만 로드하고 Service는 @MockBean으로 주입

### 2. Service Test (Service 계층 단위 테스트)
- **대상:** Service 계층 비즈니스 로직
- **도구:** @ExtendWith(MockitoExtension.class)
- **어노테이션:** `@ExtendWith(MockitoExtension.class)`
- **특징:** 의존성을 @Mock으로 대체하여 격리된 테스트

### 3. Repository Test (데이터 접근 테스트)
- **대상:** Custom Repository 구현체
- **도구:** @DataJpaTest, H2
- **어노테이션:** `@DataJpaTest`
- **특징:** 실제 DB와 유사한 환경에서 쿼리 검증

### 4. Integration Test (통합 테스트)
- **대상:** Controller → Service → Repository 전체 흐름
- **도구:** @SpringBootTest, MockMvc
- **어노테이션:** `@SpringBootTest`
- **특징:** 전체 애플리케이션 컨텍스트 로드

## Service Layer 테스트

### 기본 구조 (Mockito)

```java
@ExtendWith(MockitoExtension.class)
@DisplayName("RepairRequestWriteService 테스트")
class RepairRequestWriteServiceTest {

    @Mock
    private HARepairRequestRepository repository;

    @Mock
    private RepairRequestReadService readService;

    @Mock
    private CustomerRepository customerRepository;

    @Mock
    private SequenceService sequenceService;

    @Mock
    private RepairTimelineService timelineService;

    @InjectMocks
    private RepairRequestWriteService service;

    // 테스트 메서드들...
}
```

### 패턴 1: 성공 케이스

```java
@DisplayName("수리 요청 생성 시 시퀀스 ID가 생성되고 저장되어야 한다")
@Test
void createRepairRequest_success() {
    // Given
    String customerId = "C001";
    String generatedId = "REQ20250130001";

    CreateRequestCommand command = CreateRequestCommand.builder()
        .customerId(customerId)
        .productId("P001")
        .requestedDate(LocalDate.now())
        .build();

    Customer mockCustomer = Customer.builder()
        .id(customerId)
        .name("홍길동")
        .build();

    HomeAppliancesRepairRequest savedRequest = HomeAppliancesRepairRequest.builder()
        .id(generatedId)
        .customer(mockCustomer)
        .status(RequestStatus.PENDING)
        .build();

    given(customerRepository.findById(customerId))
        .willReturn(Optional.of(mockCustomer));
    given(sequenceService.generateId("REQ"))
        .willReturn(generatedId);
    given(readService.existsByCustomerIdAndStatus(customerId, RequestStatus.PENDING))
        .willReturn(false);
    given(repository.save(any(HomeAppliancesRepairRequest.class)))
        .willReturn(savedRequest);

    // When
    String requestId = service.createRepairRequest(command);

    // Then
    assertThat(requestId).isEqualTo(generatedId);
    verify(repository).save(any(HomeAppliancesRepairRequest.class));
    verify(timelineService).createTimeline(eq(generatedId), anyString(), anyString());
}
```

### 패턴 2: 실패 케이스 (예외 발생)

```java
@DisplayName("존재하지 않는 고객으로 수리 요청 생성 시 예외가 발생해야 한다")
@Test
void createRepairRequest_customerNotFound_shouldThrowException() {
    // Given
    String invalidCustomerId = "INVALID";
    CreateRequestCommand command = CreateRequestCommand.builder()
        .customerId(invalidCustomerId)
        .productId("P001")
        .build();

    given(customerRepository.findById(invalidCustomerId))
        .willReturn(Optional.empty());

    // When & Then
    assertThatThrownBy(() -> service.createRepairRequest(command))
        .isInstanceOf(CommonException.class)
        .hasFieldOrPropertyWithValue("errorCode", ErrorCode.CUSTOMER_NOT_FOUND);

    verify(repository, never()).save(any());
}

@DisplayName("중복된 PENDING 요청이 있을 때 생성 시 예외가 발생해야 한다")
@Test
void createRepairRequest_duplicatePending_shouldThrowException() {
    // Given
    String customerId = "C001";
    CreateRequestCommand command = CreateRequestCommand.builder()
        .customerId(customerId)
        .productId("P001")
        .build();

    Customer mockCustomer = Customer.builder().id(customerId).build();

    given(customerRepository.findById(customerId))
        .willReturn(Optional.of(mockCustomer));
    given(readService.existsByCustomerIdAndStatus(customerId, RequestStatus.PENDING))
        .willReturn(true);  // 이미 PENDING 요청 존재

    // When & Then
    assertThatThrownBy(() -> service.createRepairRequest(command))
        .isInstanceOf(CommonException.class)
        .hasFieldOrPropertyWithValue("errorCode", ErrorCode.DUPLICATE_REQUEST);

    verify(repository, never()).save(any());
}
```

### 패턴 3: 상태 변경 로직

```java
@DisplayName("PENDING → ASSIGNED 상태 변경이 성공해야 한다")
@Test
void updateStatus_pendingToAssigned_success() {
    // Given
    String requestId = "REQ001";
    RequestStatus newStatus = RequestStatus.ASSIGNED;

    HomeAppliancesRepairRequest mockRequest = HomeAppliancesRepairRequest.builder()
        .id(requestId)
        .status(RequestStatus.PENDING)
        .build();

    given(readService.getEntityById(requestId))
        .willReturn(mockRequest);

    // When
    service.updateStatus(requestId, newStatus);

    // Then
    assertThat(mockRequest.getStatus()).isEqualTo(RequestStatus.ASSIGNED);
    verify(timelineService).createTimeline(
        eq(requestId),
        eq("상태 변경"),
        contains("PENDING → ASSIGNED")
    );
}

@DisplayName("잘못된 상태 전환 시 예외가 발생해야 한다")
@Test
void updateStatus_invalidTransition_shouldThrowException() {
    // Given
    String requestId = "REQ001";

    HomeAppliancesRepairRequest mockRequest = HomeAppliancesRepairRequest.builder()
        .id(requestId)
        .status(RequestStatus.PENDING)
        .build();

    given(readService.getEntityById(requestId))
        .willReturn(mockRequest);

    // When & Then
    assertThatThrownBy(() -> service.updateStatus(requestId, RequestStatus.COMPLETED))
        .isInstanceOf(CommonException.class)
        .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_STATUS_TRANSITION);
}
```

### 패턴 4: 비즈니스 규칙 위반 (실패)

```java
@DisplayName("잘못된 날짜로 수리 요청 생성 시 예외가 발생해야 한다")
@Test
void createRepairRequest_invalidDate_shouldThrowException() {
    // Given
    LocalDate pastDate = LocalDate.now().minusDays(10);
    CreateRequestCommand command = CreateRequestCommand.builder()
        .customerId("C001")
        .productId("P001")
        .requestedDate(pastDate)  // 과거 날짜
        .build();

    Customer mockCustomer = Customer.builder().id("C001").build();

    given(customerRepository.findById("C001"))
        .willReturn(Optional.of(mockCustomer));

    // When & Then
    assertThatThrownBy(() -> service.createRepairRequest(command))
        .isInstanceOf(CommonException.class)
        .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_DATE)
        .hasMessageContaining("과거 날짜");

    verify(repository, never()).save(any());
}

@DisplayName("필수 필드 누락 시 예외가 발생해야 한다")
@Test
void createRepairRequest_missingRequiredField_shouldThrowException() {
    // Given
    CreateRequestCommand command = CreateRequestCommand.builder()
        .customerId("C001")
        // productId 누락
        .requestedDate(LocalDate.now())
        .build();

    // When & Then
    assertThatThrownBy(() -> service.createRepairRequest(command))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("productId");

    verify(repository, never()).save(any());
}
```

### 패턴 5: 권한 검증 실패

```java
@DisplayName("권한이 없는 사용자의 요청 수정 시도 시 예외가 발생해야 한다")
@Test
void updateRequest_unauthorized_shouldThrowException() {
    // Given
    String requestId = "REQ001";
    String unauthorizedUserId = "USER999";
    UpdateRequestCommand command = UpdateRequestCommand.builder()
        .userId(unauthorizedUserId)
        .description("변경 내용")
        .build();

    HomeAppliancesRepairRequest mockRequest = HomeAppliancesRepairRequest.builder()
        .id(requestId)
        .createdBy("USER001")  // 다른 사용자가 생성
        .build();

    given(readService.getEntityById(requestId))
        .willReturn(mockRequest);

    // When & Then
    assertThatThrownBy(() -> service.updateRequest(requestId, command))
        .isInstanceOf(CommonException.class)
        .hasFieldOrPropertyWithValue("errorCode", ErrorCode.UNAUTHORIZED);

    verify(repository, never()).save(any());
}
```

### 패턴 6: ArgumentCaptor 활용 (성공)

```java
@DisplayName("수리 요청 생성 시 올바른 엔티티가 저장되어야 한다")
@Test
void createRepairRequest_shouldSaveCorrectEntity() {
    // Given
    CreateRequestCommand command = CreateRequestCommand.builder()
        .customerId("C001")
        .productId("P001")
        .requestedDate(LocalDate.of(2025, 1, 30))
        .build();

    Customer mockCustomer = Customer.builder().id("C001").build();

    given(customerRepository.findById("C001"))
        .willReturn(Optional.of(mockCustomer));
    given(sequenceService.generateId("REQ"))
        .willReturn("REQ20250130001");
    given(readService.existsByCustomerIdAndStatus(anyString(), any()))
        .willReturn(false);

    ArgumentCaptor<HomeAppliancesRepairRequest> captor =
        ArgumentCaptor.forClass(HomeAppliancesRepairRequest.class);

    // When
    service.createRepairRequest(command);

    // Then
    verify(repository).save(captor.capture());

    HomeAppliancesRepairRequest savedEntity = captor.getValue();
    assertThat(savedEntity.getId()).isEqualTo("REQ20250130001");
    assertThat(savedEntity.getCustomer().getId()).isEqualTo("C001");
    assertThat(savedEntity.getProductId()).isEqualTo("P001");
    assertThat(savedEntity.getRequestedDate()).isEqualTo(LocalDate.of(2025, 1, 30));
    assertThat(savedEntity.getStatus()).isEqualTo(RequestStatus.PENDING);
}
```

## Repository Layer 테스트

### 기본 구조 (@DataJpaTest)

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@DisplayName("HARepairRequestRepository 커스텀 쿼리 테스트")
class HARepairRequestRepositoryTest {

    @Autowired
    private HARepairRequestRepository repository;

    @Autowired
    private CustomerRepository customerRepository;

    @Autowired
    private TestEntityManager entityManager;

    private Customer testCustomer;
    private HomeAppliancesRepairRequest testRequest;

    @BeforeEach
    void setUp() {
        // 공통 테스트 데이터 설정
        testCustomer = Customer.builder()
            .id("C001")
            .name("홍길동")
            .phoneNumber(new PhoneNumber("010-1234-5678"))
            .build();

        customerRepository.save(testCustomer);

        testRequest = HomeAppliancesRepairRequest.builder()
            .id("REQ001")
            .customer(testCustomer)
            .status(RequestStatus.PENDING)
            .requestedDate(LocalDate.now())
            .build();

        repository.save(testRequest);
        entityManager.flush();
        entityManager.clear();  // 영속성 컨텍스트 초기화
    }

    // 테스트 메서드들...
}
```

### 패턴 1: N+1 방지 검증

```java
@DisplayName("관계 엔티티와 함께 조회 시 N+1 문제가 발생하지 않아야 한다")
@Test
void findByIdWithRelations_shouldNotCauseNPlusOne() {
    // Given
    Partner partner = Partner.builder()
        .id("P001")
        .name("파트너사")
        .build();
    entityManager.persist(partner);

    testCustomer.assignPartner(partner);
    entityManager.flush();
    entityManager.clear();

    // When
    Optional<HomeAppliancesRepairRequest> result =
        repository.findByIdWithRelations(testRequest.getId());

    // Then
    assertThat(result).isPresent();

    HomeAppliancesRepairRequest request = result.get();

    // Lazy Loading 없이 즉시 접근 가능
    assertThat(request.getCustomer()).isNotNull();
    assertThat(request.getCustomer().getName()).isEqualTo("홍길동");

    // Partner도 fetch join으로 로드됨
    assertThat(request.getCustomer().getPartner()).isNotNull();
    assertThat(request.getCustomer().getPartner().getName()).isEqualTo("파트너사");
}
```

### 패턴 2: 검색 조건 테스트

```java
@DisplayName("상태로 검색 시 해당 상태의 요청만 반환해야 한다")
@Test
void searchByStatus_shouldReturnOnlyMatchingStatus() {
    // Given
    HomeAppliancesRepairRequest assignedRequest = HomeAppliancesRepairRequest.builder()
        .id("REQ002")
        .customer(testCustomer)
        .status(RequestStatus.ASSIGNED)
        .requestedDate(LocalDate.now())
        .build();
    repository.save(assignedRequest);

    HomeAppliancesRepairRequest completedRequest = HomeAppliancesRepairRequest.builder()
        .id("REQ003")
        .customer(testCustomer)
        .status(RequestStatus.COMPLETED)
        .requestedDate(LocalDate.now())
        .build();
    repository.save(completedRequest);

    entityManager.flush();
    entityManager.clear();

    // When
    List<HomeAppliancesRepairRequest> pendingRequests =
        repository.findByStatus(RequestStatus.PENDING);
    List<HomeAppliancesRepairRequest> assignedRequests =
        repository.findByStatus(RequestStatus.ASSIGNED);

    // Then
    assertThat(pendingRequests)
        .hasSize(1)
        .extracting(HomeAppliancesRepairRequest::getId)
        .containsExactly("REQ001");

    assertThat(assignedRequests)
        .hasSize(1)
        .extracting(HomeAppliancesRepairRequest::getId)
        .containsExactly("REQ002");
}
```

### 패턴 3: Soft Delete 검증

```java
@DisplayName("삭제된 요청은 조회되지 않아야 한다")
@Test
void findById_deletedRequest_shouldReturnEmpty() {
    // Given
    testRequest.softDelete();
    repository.save(testRequest);
    entityManager.flush();
    entityManager.clear();

    // When
    Optional<HomeAppliancesRepairRequest> result =
        repository.findById(testRequest.getId());

    // Then
    // 기본 findById는 delete_yn 체크 안함
    assertThat(result).isPresent();

    // 커스텀 메서드는 delete_yn 체크
    Optional<HomeAppliancesRepairRequest> customResult =
        repository.findByIdExcludingDeleted(testRequest.getId());
    assertThat(customResult).isEmpty();
}
```

### 패턴 4: 페이징 테스트 (성공)

```java
@DisplayName("페이징 조회 시 올바른 페이지와 전체 개수를 반환해야 한다")
@Test
void searchWithPaging_shouldReturnCorrectPageAndTotal() {
    // Given
    for (int i = 2; i <= 10; i++) {
        HomeAppliancesRepairRequest request = HomeAppliancesRepairRequest.builder()
            .id("REQ" + String.format("%03d", i))
            .customer(testCustomer)
            .status(RequestStatus.PENDING)
            .requestedDate(LocalDate.now())
            .build();
        repository.save(request);
    }
    entityManager.flush();
    entityManager.clear();

    SearchCondition condition = SearchCondition.builder()
        .status(RequestStatus.PENDING)
        .build();

    Pageable pageable = PageRequest.of(0, 5, Sort.by("createdDate").descending());

    // When
    Page<HomeAppliancesRepairRequest> result =
        repository.searchWithPaging(condition, pageable);

    // Then
    assertThat(result.getTotalElements()).isEqualTo(10);
    assertThat(result.getTotalPages()).isEqualTo(2);
    assertThat(result.getContent()).hasSize(5);
    assertThat(result.getNumber()).isEqualTo(0);
    assertThat(result.isFirst()).isTrue();
    assertThat(result.hasNext()).isTrue();
}
```

### 패턴 5: 존재하지 않는 데이터 조회 (실패)

```java
@DisplayName("존재하지 않는 ID로 조회 시 빈 Optional을 반환해야 한다")
@Test
void findById_notFound_shouldReturnEmpty() {
    // Given
    String nonExistentId = "REQ999";

    // When
    Optional<HomeAppliancesRepairRequest> result =
        repository.findById(nonExistentId);

    // Then
    assertThat(result).isEmpty();
}

@DisplayName("존재하지 않는 상태로 검색 시 빈 리스트를 반환해야 한다")
@Test
void searchByStatus_noResults_shouldReturnEmptyList() {
    // Given
    // 모든 데이터는 PENDING 상태

    // When
    List<HomeAppliancesRepairRequest> results =
        repository.findByStatus(RequestStatus.COMPLETED);

    // Then
    assertThat(results).isEmpty();
}
```

### 패턴 6: 잘못된 조건 검증 (실패)

```java
@DisplayName("잘못된 날짜 범위로 검색 시 빈 결과를 반환해야 한다")
@Test
void searchByDateRange_invalidRange_shouldReturnEmpty() {
    // Given
    LocalDate startDate = LocalDate.now().plusDays(10);
    LocalDate endDate = LocalDate.now().minusDays(10);  // 시작일보다 이른 종료일

    SearchCondition condition = SearchCondition.builder()
        .startDate(startDate)
        .endDate(endDate)
        .build();

    // When
    List<HomeAppliancesRepairRequest> results =
        repository.searchByDateRange(condition);

    // Then
    assertThat(results).isEmpty();
}

@DisplayName("제약 조건 위반 시 예외가 발생해야 한다")
@Test
void save_uniqueConstraintViolation_shouldThrowException() {
    // Given
    HomeAppliancesRepairRequest duplicateRequest = HomeAppliancesRepairRequest.builder()
        .id("REQ001")  // 이미 존재하는 ID
        .customer(testCustomer)
        .status(RequestStatus.PENDING)
        .requestedDate(LocalDate.now())
        .build();

    // When & Then
    assertThatThrownBy(() -> {
        repository.save(duplicateRequest);
        entityManager.flush();
    }).isInstanceOf(DataIntegrityViolationException.class);
}
```

## Controller Layer 테스트 (@WebMvcTest)

### 기본 구조

**중요:** Controller 테스트에는 `@WebMvcTest`를 사용하며, Service는 `@MockBean`으로 주입합니다.

```java
@WebMvcTest(RepairRequestController.class)
@DisplayName("RepairRequestController 테스트")
class RepairRequestControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private RepairRequestReadService readService;

    @MockBean
    private RepairRequestWriteService writeService;

    // Security 설정이 있는 경우 필요
    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    // 테스트 메서드들...
}
```

### 패턴 1: POST 요청

```java
@DisplayName("수리 요청 생성 API 성공 케이스")
@Test
void createRepairRequest_success() throws Exception {
    // Given
    CreateRequest request = CreateRequest.builder()
        .customerId("C001")
        .productId("P001")
        .requestedDate(LocalDate.of(2025, 1, 30))
        .build();

    String generatedId = "REQ20250130001";

    given(writeService.createRepairRequest(any()))
        .willReturn(generatedId);

    RepairRequestDto dto = RepairRequestDto.builder()
        .id(generatedId)
        .customerName("홍길동")
        .status(RequestStatus.PENDING)
        .build();

    given(readService.getRepairRequest(generatedId))
        .willReturn(dto);

    // When & Then
    mockMvc.perform(post("/repair-requests")
            .contentType(MediaType.APPLICATION_JSON)
            .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value(generatedId))
        .andExpect(jsonPath("$.customerName").value("홍길동"))
        .andExpect(jsonPath("$.status").value("PENDING"));

    verify(writeService).createRepairRequest(any());
    verify(readService).getRepairRequest(generatedId);
}
```

### 패턴 2: GET 요청

```java
@DisplayName("수리 요청 상세 조회 API 성공 케이스")
@Test
void getRepairRequest_success() throws Exception {
    // Given
    String requestId = "REQ001";

    RepairRequestDto dto = RepairRequestDto.builder()
        .id(requestId)
        .customerName("홍길동")
        .productName("냉장고")
        .status(RequestStatus.PENDING)
        .build();

    given(readService.getRepairRequest(requestId))
        .willReturn(dto);

    // When & Then
    mockMvc.perform(get("/repair-requests/{id}", requestId))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value(requestId))
        .andExpect(jsonPath("$.customerName").value("홍길동"))
        .andExpect(jsonPath("$.productName").value("냉장고"));

    verify(readService).getRepairRequest(requestId);
}

@DisplayName("존재하지 않는 요청 조회 시 404 반환")
@Test
void getRepairRequest_notFound() throws Exception {
    // Given
    String invalidId = "INVALID";

    given(readService.getRepairRequest(invalidId))
        .willThrow(new CommonException(ErrorCode.NOT_FOUND));

    // When & Then
    mockMvc.perform(get("/repair-requests/{id}", invalidId))
        .andExpect(status().isNotFound());
}
```

### 패턴 3: PUT 요청 (성공)

```java
@DisplayName("상태 업데이트 API 성공 케이스")
@Test
void updateStatus_success() throws Exception {
    // Given
    String requestId = "REQ001";
    UpdateStatusRequest request = new UpdateStatusRequest(RequestStatus.ASSIGNED);

    doNothing().when(writeService).updateStatus(requestId, RequestStatus.ASSIGNED);

    // When & Then
    mockMvc.perform(put("/repair-requests/{id}/status", requestId)
            .contentType(MediaType.APPLICATION_JSON)
            .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isOk());

    verify(writeService).updateStatus(requestId, RequestStatus.ASSIGNED);
}
```

### 패턴 4: 잘못된 요청 (실패 - 400 Bad Request)

```java
@DisplayName("필수 필드 누락 시 400 에러 반환")
@Test
void createRepairRequest_missingRequiredField_shouldReturnBadRequest() throws Exception {
    // Given
    String invalidJson = """
        {
            "customerId": "C001"
            // productId 누락
        }
        """;

    // When & Then
    mockMvc.perform(post("/repair-requests")
            .contentType(MediaType.APPLICATION_JSON)
            .content(invalidJson))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.message").value(containsString("productId")));

    verify(writeService, never()).createRepairRequest(any());
}

@DisplayName("잘못된 JSON 형식으로 요청 시 400 에러 반환")
@Test
void createRepairRequest_invalidJson_shouldReturnBadRequest() throws Exception {
    // Given
    String malformedJson = "{ invalid json }";

    // When & Then
    mockMvc.perform(post("/repair-requests")
            .contentType(MediaType.APPLICATION_JSON)
            .content(malformedJson))
        .andExpect(status().isBadRequest());

    verify(writeService, never()).createRepairRequest(any());
}
```

### 패턴 5: 비즈니스 규칙 위반 (실패 - 422 Unprocessable Entity)

```java
@DisplayName("잘못된 상태 전환 시도 시 422 에러 반환")
@Test
void updateStatus_invalidTransition_shouldReturnUnprocessableEntity() throws Exception {
    // Given
    String requestId = "REQ001";
    UpdateStatusRequest request = new UpdateStatusRequest(RequestStatus.COMPLETED);

    doThrow(new CommonException(ErrorCode.INVALID_STATUS_TRANSITION))
        .when(writeService).updateStatus(requestId, RequestStatus.COMPLETED);

    // When & Then
    mockMvc.perform(put("/repair-requests/{id}/status", requestId)
            .contentType(MediaType.APPLICATION_JSON)
            .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.errorCode").value("INVALID_STATUS_TRANSITION"))
        .andExpect(jsonPath("$.message").exists());
}

@DisplayName("중복 요청 생성 시도 시 409 에러 반환")
@Test
void createRepairRequest_duplicate_shouldReturnConflict() throws Exception {
    // Given
    CreateRequest request = CreateRequest.builder()
        .customerId("C001")
        .productId("P001")
        .requestedDate(LocalDate.now())
        .build();

    given(writeService.createRepairRequest(any()))
        .willThrow(new CommonException(ErrorCode.DUPLICATE_REQUEST));

    // When & Then
    mockMvc.perform(post("/repair-requests")
            .contentType(MediaType.APPLICATION_JSON)
            .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.errorCode").value("DUPLICATE_REQUEST"));
}
```

### 패턴 6: 권한 없음 (실패 - 403 Forbidden)

```java
@DisplayName("권한 없는 사용자의 수정 시도 시 403 에러 반환")
@Test
void updateRequest_unauthorized_shouldReturnForbidden() throws Exception {
    // Given
    String requestId = "REQ001";
    UpdateRequest request = UpdateRequest.builder()
        .description("변경 내용")
        .build();

    doThrow(new CommonException(ErrorCode.UNAUTHORIZED))
        .when(writeService).updateRequest(eq(requestId), any());

    // When & Then
    mockMvc.perform(put("/repair-requests/{id}", requestId)
            .contentType(MediaType.APPLICATION_JSON)
            .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isForbidden())
        .andExpect(jsonPath("$.errorCode").value("UNAUTHORIZED"));
}
```

### 패턴 7: 서버 에러 (실패 - 500 Internal Server Error)

```java
@DisplayName("예상치 못한 서버 에러 발생 시 500 에러 반환")
@Test
void createRepairRequest_unexpectedError_shouldReturnInternalServerError() throws Exception {
    // Given
    CreateRequest request = CreateRequest.builder()
        .customerId("C001")
        .productId("P001")
        .requestedDate(LocalDate.now())
        .build();

    given(writeService.createRepairRequest(any()))
        .willThrow(new RuntimeException("Database connection failed"));

    // When & Then
    mockMvc.perform(post("/repair-requests")
            .contentType(MediaType.APPLICATION_JSON)
            .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isInternalServerError());
}
```

## Integration Test (@SpringBootTest)

**언제 사용:** 전체 애플리케이션 컨텍스트가 필요한 통합 테스트 (실제 DB 포함)

### 기본 구조

```java
@SpringBootTest
@AutoConfigureMockMvc
@Transactional  // 각 테스트 후 자동 롤백
@DisplayName("RepairRequest 전체 플로우 통합 테스트")
class RepairRequestIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private HARepairRequestRepository repository;

    @Autowired
    private CustomerRepository customerRepository;

    private Customer testCustomer;

    @BeforeEach
    void setUp() {
        // 실제 DB에 데이터 삽입
        testCustomer = Customer.builder()
            .id("C001")
            .name("홍길동")
            .phoneNumber(new PhoneNumber("010-1234-5678"))
            .build();
        customerRepository.save(testCustomer);
    }

    @DisplayName("수리 요청 생성부터 완료까지 전체 플로우 테스트")
    @Test
    void completeRepairFlow_success() throws Exception {
        // 1. 수리 요청 생성
        CreateRequest createRequest = CreateRequest.builder()
            .customerId("C001")
            .productId("P001")
            .requestedDate(LocalDate.now())
            .build();

        String responseBody = mockMvc.perform(post("/repair-requests")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createRequest)))
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();

        String requestId = objectMapper.readTree(responseBody).get("id").asText();

        // 2. 생성된 요청 조회
        mockMvc.perform(get("/repair-requests/{id}", requestId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("PENDING"));

        // 3. 상태 업데이트
        UpdateStatusRequest updateRequest = new UpdateStatusRequest(RequestStatus.ASSIGNED);

        mockMvc.perform(put("/repair-requests/{id}/status", requestId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updateRequest)))
            .andExpect(status().isOk());

        // 4. 업데이트된 상태 확인
        mockMvc.perform(get("/repair-requests/{id}", requestId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ASSIGNED"));

        // 5. DB에 실제 저장 확인
        HomeAppliancesRepairRequest savedRequest = repository.findById(requestId)
            .orElseThrow();
        assertThat(savedRequest.getStatus()).isEqualTo(RequestStatus.ASSIGNED);
    }

    @DisplayName("존재하지 않는 고객으로 수리 요청 생성 시 실패해야 한다")
    @Test
    void createRepairRequest_customerNotFound_shouldFail() throws Exception {
        // Given
        CreateRequest createRequest = CreateRequest.builder()
            .customerId("INVALID_CUSTOMER")  // 존재하지 않는 고객
            .productId("P001")
            .requestedDate(LocalDate.now())
            .build();

        // When & Then
        mockMvc.perform(post("/repair-requests")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createRequest)))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.errorCode").value("CUSTOMER_NOT_FOUND"));

        // DB에 저장되지 않았는지 확인
        long count = repository.count();
        assertThat(count).isEqualTo(0);
    }

    @DisplayName("잘못된 상태 전환 시도 시 롤백되어야 한다")
    @Test
    void updateStatus_invalidTransition_shouldRollback() throws Exception {
        // Given
        // 1. 먼저 수리 요청 생성
        HomeAppliancesRepairRequest request = HomeAppliancesRepairRequest.builder()
            .id("REQ001")
            .customer(testCustomer)
            .status(RequestStatus.PENDING)
            .requestedDate(LocalDate.now())
            .build();
        repository.save(request);

        // 2. PENDING에서 COMPLETED로 바로 전환 시도 (잘못된 전환)
        UpdateStatusRequest updateRequest = new UpdateStatusRequest(RequestStatus.COMPLETED);

        // When & Then
        mockMvc.perform(put("/repair-requests/{id}/status", "REQ001")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updateRequest)))
            .andExpect(status().isUnprocessableEntity());

        // 상태가 변경되지 않았는지 확인 (여전히 PENDING)
        HomeAppliancesRepairRequest savedRequest = repository.findById("REQ001")
            .orElseThrow();
        assertThat(savedRequest.getStatus()).isEqualTo(RequestStatus.PENDING);
    }

    @DisplayName("트랜잭션 롤백 테스트 - 중간 실패 시 전체 롤백")
    @Test
    void transactionRollback_shouldRevertAllChanges() throws Exception {
        // Given
        CreateRequest createRequest = CreateRequest.builder()
            .customerId("C001")
            .productId("P001")
            .requestedDate(LocalDate.now())
            .build();

        // Mock을 사용하여 중간에 실패하도록 설정
        // (실제로는 Service 계층에서 예외 발생 시나리오)

        long initialCount = repository.count();

        // When & Then
        // 생성 후 타임라인 생성 실패 등의 시나리오
        // (실제 구현은 프로젝트 구조에 따라 다를 수 있음)

        // 실패 후 데이터가 롤백되었는지 확인
        long finalCount = repository.count();
        assertThat(finalCount).isEqualTo(initialCount);
    }
}
```

## 테스트 작성 우선순위

### 1순위: 핵심 비즈니스 로직 (Service Write)

```java
// 성공 케이스
// - WriteService의 create, update, delete 메서드
// - 정상 플로우 검증

// 실패 케이스 (필수)
// - 존재하지 않는 데이터 접근
// - 비즈니스 규칙 위반
// - 중복 데이터 생성 시도
// - 권한 부족
// - 잘못된 상태 전환
```

### 2순위: Repository 커스텀 쿼리

```java
// 성공 케이스
// - QueryDSL Custom Implementation
// - 복잡한 조인 쿼리
// - N+1 방지 로직

// 실패 케이스 (필수)
// - 존재하지 않는 데이터 조회
// - 빈 결과 반환
// - 제약 조건 위반
// - 잘못된 검색 조건
```

### 3순위: Controller API 테스트

```java
// 성공 케이스
// - 주요 API 엔드포인트
// - 요청/응답 검증

// 실패 케이스 (필수)
// - 400 Bad Request (잘못된 요청)
// - 401 Unauthorized (인증 실패)
// - 403 Forbidden (권한 없음)
// - 404 Not Found (리소스 없음)
// - 409 Conflict (중복)
// - 422 Unprocessable Entity (비즈니스 규칙 위반)
// - 500 Internal Server Error (서버 에러)
```

### 4순위: Integration 테스트

```java
// 성공 케이스
// - 전체 플로우 검증
// - 트랜잭션 커밋 확인

// 실패 케이스
// - 중간 단계 실패 시 롤백
// - 데이터 무결성 검증
```

## 테스트 작성 체크리스트

### Controller 테스트 (@WebMvcTest)
- [ ] `@WebMvcTest(ControllerClass.class)` 사용
- [ ] Service를 `@MockBean`으로 주입
- [ ] Given-When-Then 패턴으로 작성
- [ ] `@DisplayName`으로 테스트 의도 명확히 설명
- [ ] MockMvc로 HTTP 요청/응답 검증
- [ ] JSON 응답 필드 검증
- [ ] HTTP 상태 코드 검증
- [ ] **성공 케이스:** 정상 요청 처리
- [ ] **실패 케이스:** 400 (잘못된 요청), 404 (리소스 없음), 403 (권한 없음), 409 (중복), 422 (비즈니스 규칙 위반), 500 (서버 에러)
- [ ] `verify(service, never())` 로 실패 시 서비스 호출 안됨 확인

### Service 테스트 (@ExtendWith(MockitoExtension.class))
- [ ] `@ExtendWith(MockitoExtension.class)` 사용
- [ ] 의존성을 `@Mock`으로 주입, Service는 `@InjectMocks`
- [ ] Given-When-Then 패턴으로 작성
- [ ] `@DisplayName`으로 테스트 의도 명확히 설명
- [ ] **성공 케이스:** 정상 플로우 검증
- [ ] **실패 케이스:** 존재하지 않는 데이터, 중복 데이터, 비즈니스 규칙 위반, 권한 부족, 잘못된 상태 전환
- [ ] `assertThatThrownBy()` 로 예외 타입과 메시지 검증
- [ ] Mock 설정이 적절한지 확인
- [ ] ArgumentCaptor로 저장 데이터 검증 (필요시)
- [ ] `verify(repository, never()).save()` 로 실패 시 저장 안됨 확인

### Repository 테스트 (@DataJpaTest)
- [ ] `@DataJpaTest` 사용
- [ ] `@BeforeEach`로 공통 데이터 설정
- [ ] `entityManager.clear()`로 영속성 컨텍스트 초기화
- [ ] **성공 케이스:** 정상 조회, N+1 방지, 페이징
- [ ] **실패 케이스:** 존재하지 않는 데이터 (빈 Optional), 빈 리스트 반환, 제약 조건 위반 (DataIntegrityViolationException)
- [ ] `assertThat(result).isEmpty()` 로 빈 결과 검증
- [ ] Soft delete 체크 검증
- [ ] 페이징 로직 검증 (전체 개수, 페이지 수)

### Integration 테스트 (@SpringBootTest)
- [ ] `@SpringBootTest` + `@AutoConfigureMockMvc` 사용
- [ ] `@Transactional`로 각 테스트 후 자동 롤백
- [ ] **성공 케이스:** 전체 플로우 검증 (생성 → 조회 → 수정 → 삭제)
- [ ] **실패 케이스:** 존재하지 않는 데이터 접근, 잘못된 상태 전환, 트랜잭션 롤백
- [ ] 실제 DB에 데이터 저장 확인
- [ ] 실패 후 롤백 확인 (데이터 개수 동일)
- [ ] 외부 연동 테스트 (필요시)

## 실행 방법

```bash
# 전체 테스트
./gradlew.bat test

# 특정 클래스
./gradlew.bat test --tests "RepairRequestWriteServiceTest"

# 특정 메서드
./gradlew.bat test --tests "RepairRequestWriteServiceTest.createRepairRequest_success"

# 테스트 리포트
./gradlew.bat test jacocoTestReport
# → build/reports/jacoco/test/html/index.html
```
