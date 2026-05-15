# CQRS 패턴 상세 가이드

## 개요

CQRS (Command Query Responsibility Segregation)는 읽기와 쓰기 책임을 분리하는 패턴입니다.
CS-Back 프로젝트에서는 Service 계층에서 이 패턴을 적용합니다.

## 분리 기준

### Read Service (Query)
- **목적:** 데이터 조회만 수행
- **트랜잭션:** `@Transactional(readOnly = true)` 클래스 레벨
- **메서드 네이밍:** `get*`, `find*`, `search*`, `list*`, `count*`, `exists*`
- **반환값:** DTO 또는 Entity (읽기 전용)
- **의존성:** Repository, 다른 ReadService

### Write Service (Command)
- **목적:** 데이터 변경(생성/수정/삭제) 수행
- **트랜잭션:** `@Transactional` 클래스 레벨
- **메서드 네이밍:** `create*`, `update*`, `delete*`, `save*`, `modify*`, `register*`
- **반환값:** ID 또는 void (변경 결과)
- **의존성:** Repository, ReadService, 다른 WriteService

## 실전 예시

### 예시 1: RepairRequest 도메인

**Before (단일 Service)**
```java
@Service
@RequiredArgsConstructor
public class RepairRequestService {

    private final HARepairRequestRepository repository;
    private final CustomerRepository customerRepository;
    private final SequenceService sequenceService;

    public RepairRequestDto getRepairRequest(String id) {
        HomeAppliancesRepairRequest request = repository.findById(id)
            .orElseThrow(() -> new CommonException(ErrorCode.NOT_FOUND));
        return RepairRequestDto.from(request);
    }

    public List<RepairRequestDto> searchRepairRequests(SearchCondition condition) {
        return repository.searchByCondition(condition).stream()
            .map(RepairRequestDto::from)
            .toList();
    }

    public String createRepairRequest(CreateRequestCommand command) {
        Customer customer = customerRepository.findById(command.customerId())
            .orElseThrow(() -> new CommonException(ErrorCode.CUSTOMER_NOT_FOUND));

        String requestId = sequenceService.generateId("REQ");

        HomeAppliancesRepairRequest request = HomeAppliancesRepairRequest.builder()
            .id(requestId)
            .customer(customer)
            .productId(command.productId())
            .requestedDate(command.requestedDate())
            .status(RequestStatus.PENDING)
            .build();

        repository.save(request);
        return requestId;
    }

    public void updateStatus(String id, RequestStatus newStatus) {
        HomeAppliancesRepairRequest request = repository.findById(id)
            .orElseThrow(() -> new CommonException(ErrorCode.NOT_FOUND));

        request.updateStatus(newStatus);
        repository.save(request);
    }
}
```

**After (CQRS 분리)**

```java
// Read Service
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class RepairRequestReadService {

    private final HARepairRequestRepository repository;

    public RepairRequestDto getRepairRequest(String id) {
        HomeAppliancesRepairRequest request = repository.findByIdWithRelations(id)
            .orElseThrow(() -> new CommonException(ErrorCode.NOT_FOUND));
        return RepairRequestDto.from(request);
    }

    public RepairRequestDetailDto getRepairRequestDetail(String id) {
        HomeAppliancesRepairRequest request = repository.findByIdWithAllRelations(id)
            .orElseThrow(() -> new CommonException(ErrorCode.NOT_FOUND));
        return RepairRequestDetailDto.from(request);
    }

    public List<RepairRequestDto> searchRepairRequests(SearchCondition condition) {
        return repository.searchByCondition(condition).stream()
            .map(RepairRequestDto::from)
            .toList();
    }

    public long countByStatus(RequestStatus status) {
        return repository.countByStatus(status);
    }

    public boolean existsByCustomerIdAndStatus(String customerId, RequestStatus status) {
        return repository.existsByCustomerIdAndStatus(customerId, status);
    }

    // 내부 조회용 메서드 (Write Service에서 사용)
    HomeAppliancesRepairRequest getEntityById(String id) {
        return repository.findById(id)
            .orElseThrow(() -> new CommonException(ErrorCode.NOT_FOUND));
    }
}

// Write Service
@Service
@RequiredArgsConstructor
@Transactional
public class RepairRequestWriteService {

    private final HARepairRequestRepository repository;
    private final RepairRequestReadService readService;
    private final CustomerRepository customerRepository;
    private final SequenceService sequenceService;
    private final RepairTimelineService timelineService;

    public String createRepairRequest(CreateRequestCommand command) {
        // 고객 존재 확인
        Customer customer = customerRepository.findById(command.customerId())
            .orElseThrow(() -> new CommonException(ErrorCode.CUSTOMER_NOT_FOUND));

        // 중복 요청 확인
        if (readService.existsByCustomerIdAndStatus(
                command.customerId(), RequestStatus.PENDING)) {
            throw new CommonException(ErrorCode.DUPLICATE_REQUEST);
        }

        // ID 생성
        String requestId = sequenceService.generateId("REQ");

        // 엔티티 생성
        HomeAppliancesRepairRequest request = HomeAppliancesRepairRequest.builder()
            .id(requestId)
            .customer(customer)
            .productId(command.productId())
            .requestedDate(command.requestedDate())
            .status(RequestStatus.PENDING)
            .build();

        // 저장
        repository.save(request);

        // 타임라인 기록
        timelineService.createTimeline(requestId, "요청 생성", "고객 요청 접수");

        return requestId;
    }

    public void updateStatus(String id, RequestStatus newStatus) {
        HomeAppliancesRepairRequest request = readService.getEntityById(id);

        // 비즈니스 규칙 검증
        validateStatusTransition(request.getStatus(), newStatus);

        // 상태 변경
        request.updateStatus(newStatus);

        // 타임라인 기록
        timelineService.createTimeline(id, "상태 변경",
            String.format("%s → %s", request.getStatus(), newStatus));
    }

    public void assignStaff(String id, String staffId) {
        HomeAppliancesRepairRequest request = readService.getEntityById(id);

        if (request.getStatus() != RequestStatus.PENDING) {
            throw new CommonException(ErrorCode.INVALID_STATUS);
        }

        request.assignStaff(staffId);
        request.updateStatus(RequestStatus.ASSIGNED);

        timelineService.createTimeline(id, "기술자 배정", "기술자: " + staffId);
    }

    public void deleteRepairRequest(String id) {
        HomeAppliancesRepairRequest request = readService.getEntityById(id);
        request.softDelete();  // deleteYn = 'Y'
    }

    private void validateStatusTransition(RequestStatus current, RequestStatus target) {
        // 상태 전환 규칙 검증 로직
        if (!isValidTransition(current, target)) {
            throw new CommonException(ErrorCode.INVALID_STATUS_TRANSITION);
        }
    }

    private boolean isValidTransition(RequestStatus current, RequestStatus target) {
        // PENDING → ASSIGNED → VISIT_PROPOSED → ... 순서 검증
        return switch (current) {
            case PENDING -> target == RequestStatus.ASSIGNED;
            case ASSIGNED -> target == RequestStatus.VISIT_PROPOSED;
            // ...
            default -> false;
        };
    }
}
```

### 예시 2: Notification 도메인

**Before**
```java
@Service
public class NotificationService {

    public NotificationDto getNotification(String id) { ... }

    public void sendNotification(SendCommand command) { ... }

    public void sendBulkNotifications(List<SendCommand> commands) { ... }
}
```

**After**
```java
// Read Service
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class NotificationReadService {

    private final NotificationRepository repository;

    public NotificationDto getNotification(String id) {
        return repository.findById(id)
            .map(NotificationDto::from)
            .orElseThrow(() -> new CommonException(ErrorCode.NOT_FOUND));
    }

    public List<NotificationDto> getNotificationsByUser(String userId) {
        return repository.findByUserId(userId).stream()
            .map(NotificationDto::from)
            .toList();
    }

    public List<NotificationDto> getUnreadNotifications(String userId) {
        return repository.findByUserIdAndReadYn(userId, "N").stream()
            .map(NotificationDto::from)
            .toList();
    }
}

// Write Service
@Service
@RequiredArgsConstructor
@Transactional
public class NotificationWriteService {

    private final NotificationRepository repository;
    private final BizMsgClient bizMsgClient;
    private final FirebaseCloudMessageService fcmService;

    public void sendNotification(SendCommand command) {
        // 알림 엔티티 생성
        Notification notification = Notification.builder()
            .userId(command.userId())
            .message(command.message())
            .type(command.type())
            .readYn("N")
            .build();

        repository.save(notification);

        // 외부 발송
        sendExternalNotification(command);
    }

    public void sendBulkNotifications(List<SendCommand> commands) {
        List<Notification> notifications = commands.stream()
            .map(cmd -> Notification.builder()
                .userId(cmd.userId())
                .message(cmd.message())
                .type(cmd.type())
                .readYn("N")
                .build())
            .toList();

        repository.saveAll(notifications);

        // 배치 발송
        commands.forEach(this::sendExternalNotification);
    }

    public void markAsRead(String id) {
        Notification notification = repository.findById(id)
            .orElseThrow(() -> new CommonException(ErrorCode.NOT_FOUND));

        notification.markAsRead();
    }

    private void sendExternalNotification(SendCommand command) {
        switch (command.channel()) {
            case KAKAO -> bizMsgClient.sendAlimTalk(command);
            case PUSH -> fcmService.sendMessage(command);
            case EMAIL -> emailService.send(command);
        }
    }
}
```

## Controller에서의 사용

### 패턴 1: 단일 Service 주입

```java
@RestController
@RequestMapping("/repair-requests")
@RequiredArgsConstructor
public class RepairRequestController {

    // 조회만 필요한 엔드포인트
    private final RepairRequestReadService readService;

    @GetMapping("/{id}")
    public ResponseEntity<RepairRequestResponse> getRepairRequest(
        @PathVariable String id) {

        RepairRequestDto dto = readService.getRepairRequest(id);
        return ResponseEntity.ok(RepairRequestResponse.from(dto));
    }

    @GetMapping
    public ResponseEntity<List<RepairRequestResponse>> searchRepairRequests(
        @ModelAttribute SearchCondition condition) {

        List<RepairRequestDto> results = readService.searchRepairRequests(condition);
        return ResponseEntity.ok(
            results.stream()
                .map(RepairRequestResponse::from)
                .toList()
        );
    }
}

@RestController
@RequestMapping("/repair-requests")
@RequiredArgsConstructor
public class RepairRequestCommandController {

    // 변경 작업만 필요한 엔드포인트
    private final RepairRequestWriteService writeService;

    @PostMapping
    public ResponseEntity<CreateResponse> createRepairRequest(
        @RequestBody CreateRequest request) {

        String requestId = writeService.createRepairRequest(request.toCommand());
        return ResponseEntity.ok(new CreateResponse(requestId));
    }

    @PutMapping("/{id}/status")
    public ResponseEntity<Void> updateStatus(
        @PathVariable String id,
        @RequestBody UpdateStatusRequest request) {

        writeService.updateStatus(id, request.status());
        return ResponseEntity.ok().build();
    }
}
```

### 패턴 2: Read/Write Service 모두 주입

```java
@RestController
@RequestMapping("/repair-requests")
@RequiredArgsConstructor
public class RepairRequestController {

    private final RepairRequestReadService readService;
    private final RepairRequestWriteService writeService;

    // 조회
    @GetMapping("/{id}")
    public ResponseEntity<RepairRequestResponse> get(@PathVariable String id) {
        RepairRequestDto dto = readService.getRepairRequest(id);
        return ResponseEntity.ok(RepairRequestResponse.from(dto));
    }

    // 생성 후 즉시 조회
    @PostMapping
    public ResponseEntity<RepairRequestResponse> create(
        @RequestBody CreateRequest request) {

        String requestId = writeService.createRepairRequest(request.toCommand());

        // 생성 후 바로 조회하여 응답
        RepairRequestDto dto = readService.getRepairRequest(requestId);
        return ResponseEntity.ok(RepairRequestResponse.from(dto));
    }

    // 업데이트 후 조회
    @PutMapping("/{id}")
    public ResponseEntity<RepairRequestResponse> update(
        @PathVariable String id,
        @RequestBody UpdateRequest request) {

        writeService.updateStatus(id, request.status());

        // 업데이트 후 최신 데이터 조회
        RepairRequestDto dto = readService.getRepairRequest(id);
        return ResponseEntity.ok(RepairRequestResponse.from(dto));
    }
}
```

## 의존성 규칙

```
Controller
  ├─ ReadService (O)
  ├─ WriteService (O)
  └─ ReadService + WriteService (O)

WriteService
  ├─ ReadService (O) - 조회 로직 재사용
  ├─ Repository (O)
  ├─ 다른 WriteService (O)
  └─ 다른 ReadService (O)

ReadService
  ├─ Repository (O)
  ├─ 다른 ReadService (O)
  └─ WriteService (X) - 절대 의존 금지
```

## 자주 묻는 질문

### Q1: ReadService에서 Entity를 반환해도 되나요?

A: 내부 메서드(package-private 또는 default)로 제한하고, WriteService에서만 사용하세요.

```java
@Transactional(readOnly = true)
public class RepairRequestReadService {

    // 외부 노출용 - DTO 반환
    public RepairRequestDto getRepairRequest(String id) {
        return RepairRequestDto.from(getEntityById(id));
    }

    // 내부 전용 - Entity 반환 (WriteService에서 사용)
    HomeAppliancesRepairRequest getEntityById(String id) {
        return repository.findById(id)
            .orElseThrow(() -> new CommonException(ErrorCode.NOT_FOUND));
    }
}
```

### Q2: WriteService에서 조회 로직이 필요할 때는?

A: ReadService를 주입받아 사용하세요.

```java
@Transactional
public class RepairRequestWriteService {

    private final RepairRequestReadService readService;

    public void updateStatus(String id, RequestStatus newStatus) {
        // ReadService 활용
        HomeAppliancesRepairRequest request = readService.getEntityById(id);
        request.updateStatus(newStatus);
    }
}
```

### Q3: 간단한 CRUD만 있는 도메인도 분리해야 하나요?

A: 네. 일관성을 위해 모든 Service는 분리합니다. 나중에 비즈니스 로직이 추가될 때 유연하게 대응할 수 있습니다.

```java
// 간단한 도메인도 분리
@Service
@Transactional(readOnly = true)
public class CodeReadService {
    public List<CodeDto> getAllCodes() { ... }
}

@Service
@Transactional
public class CodeWriteService {
    public void createCode(CreateCodeCommand command) { ... }
}
```

### Q4: 트랜잭션 전파는 어떻게 되나요?

A: WriteService에서 ReadService 호출 시, ReadService의 `readOnly=true`는 무시되고 WriteService의 트랜잭션이 전파됩니다.

```java
@Transactional  // 쓰기 트랜잭션
public class WriteService {

    @Transactional(readOnly = true)
    private final ReadService readService;

    public void update(String id) {
        // readService의 메서드도 쓰기 트랜잭션 내에서 실행됨
        Entity entity = readService.getEntityById(id);
        entity.update();  // 정상 동작
    }
}
```

## 마이그레이션 체크리스트

### 기존 Service 분리 시

- [ ] Service 클래스의 모든 메서드 목록 작성
- [ ] Read/Write 분류
- [ ] ReadService 클래스 생성 (`@Transactional(readOnly = true)`)
- [ ] WriteService 클래스 생성 (`@Transactional`)
- [ ] 메서드 이동
- [ ] WriteService에서 ReadService 주입
- [ ] Controller 수정 (Service 주입 변경)
- [ ] 테스트 코드 수정
- [ ] 빌드 및 테스트 실행
- [ ] 기존 Service 클래스 삭제
