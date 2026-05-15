# N+1 문제 해결 가이드

## N+1 문제란?

연관된 엔티티를 조회할 때 발생하는 성능 문제로, 1번의 쿼리로 N개의 엔티티를 조회한 후, 각 엔티티의 연관 데이터를 가져오기 위해 N번의 추가 쿼리가 실행되는 현상입니다.

### 문제 예시

```java
// 1번의 쿼리로 100개의 Customer 조회
List<Customer> customers = customerRepository.findAll();

// 각 Customer의 Partner를 조회하기 위해 100번의 추가 쿼리 실행
for (Customer customer : customers) {
    String partnerName = customer.getPartner().getName();  // Lazy Loading 발생
}

// 총 101번의 쿼리 (1 + 100)
```

**실행되는 SQL:**
```sql
-- 1. Customer 조회
SELECT * FROM customer;

-- 2. 각 Customer마다 Partner 조회 (N번)
SELECT * FROM partner WHERE id = 1;
SELECT * FROM partner WHERE id = 2;
SELECT * FROM partner WHERE id = 3;
...
SELECT * FROM partner WHERE id = 100;
```

## 해결 전략

CS-Back 프로젝트에서는 3가지 전략을 상황에 따라 사용합니다:

1. **Fetch Join** (QueryDSL) - 가장 권장
2. **@EntityGraph** (Spring Data JPA)
3. **Batch Fetching** (이미 글로벌 설정됨)

### 전략 1: Fetch Join (QueryDSL) ⭐ 권장

**장점:**
- 1번의 쿼리로 모든 연관 데이터 조회
- 타입 안전성
- 복잡한 조인 조건 처리 가능
- 프로젝션과 조합 가능

**단점:**
- 커스텀 Repository 구현 필요
- 페이징 시 주의 필요 (컬렉션 fetch join)

#### 기본 사용법

```java
// CustomRepositoryImpl
@RequiredArgsConstructor
public class HARepairRequestRepositoryCustomImpl
    implements HARepairRequestRepositoryCustom {

    private final JPAQueryFactory queryFactory;

    @Override
    public Optional<HomeAppliancesRepairRequest> findByIdWithRelations(String id) {
        QHomeAppliancesRepairRequest request = QHomeAppliancesRepairRequest.homeAppliancesRepairRequest;
        QCustomer customer = QCustomer.customer;
        QPartner partner = QPartner.partner;
        QHomeAppliancesProduct product = QHomeAppliancesProduct.homeAppliancesProduct;

        HomeAppliancesRepairRequest result = queryFactory
            .select(request)
            .from(request)
            .leftJoin(request.customer, customer).fetchJoin()
            .leftJoin(customer.partner, partner).fetchJoin()
            .leftJoin(request.product, product).fetchJoin()
            .where(request.id.eq(id)
                .and(request.deleteYn.deleteYn.ne("Y")))
            .fetchOne();

        return Optional.ofNullable(result);
    }
}
```

**실행되는 SQL (1번의 쿼리):**
```sql
SELECT
    r.*,
    c.*,
    p.*,
    pr.*
FROM home_appliances_repair_request r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN partner p ON c.partner_id = p.id
LEFT JOIN home_appliances_product pr ON r.product_id = pr.id
WHERE r.id = ?
  AND r.delete_yn != 'Y';
```

#### 조건부 Fetch Join

```java
public List<HomeAppliancesRepairRequest> searchWithDynamicFetch(
    SearchCondition condition,
    boolean includeCustomer,
    boolean includeProduct) {

    QHomeAppliancesRepairRequest request = QHomeAppliancesRepairRequest.homeAppliancesRepairRequest;
    QCustomer customer = QCustomer.customer;
    QHomeAppliancesProduct product = QHomeAppliancesProduct.homeAppliancesProduct;

    JPAQuery<HomeAppliancesRepairRequest> query = queryFactory
        .select(request)
        .from(request)
        .where(buildSearchPredicate(condition));

    // 조건부 fetch join
    if (includeCustomer) {
        query.leftJoin(request.customer, customer).fetchJoin();
    }

    if (includeProduct) {
        query.leftJoin(request.product, product).fetchJoin();
    }

    return query.fetch();
}
```

#### 컬렉션 Fetch Join (OneToMany)

**주의:** 컬렉션 fetch join은 페이징과 함께 사용 시 메모리 문제 발생 가능

```java
// ❌ 잘못된 예: 페이징 + 컬렉션 fetch join
public Page<HomeAppliancesRepairRequest> findAllWithActions(Pageable pageable) {
    // 경고: 모든 데이터를 메모리에 로드 후 페이징 처리
    List<HomeAppliancesRepairRequest> results = queryFactory
        .select(request)
        .from(request)
        .leftJoin(request.actions).fetchJoin()  // OneToMany
        .offset(pageable.getOffset())
        .limit(pageable.getPageSize())
        .fetch();

    // 실제로는 limit/offset이 적용되지 않고, 모든 row를 가져옴
}

// ✅ 올바른 예 1: 별도 쿼리로 분리
public HomeAppliancesRepairRequest findByIdWithActions(String id) {
    // 1. 부모 엔티티만 조회
    HomeAppliancesRepairRequest request = queryFactory
        .select(QHomeAppliancesRepairRequest.homeAppliancesRepairRequest)
        .from(QHomeAppliancesRepairRequest.homeAppliancesRepairRequest)
        .where(QHomeAppliancesRepairRequest.homeAppliancesRepairRequest.id.eq(id))
        .fetchOne();

    // 2. 컬렉션은 별도 조회 (Batch Fetching으로 최적화됨)
    List<HomeAppliancesRepairAction> actions = queryFactory
        .select(QHomeAppliancesRepairAction.homeAppliancesRepairAction)
        .from(QHomeAppliancesRepairAction.homeAppliancesRepairAction)
        .where(QHomeAppliancesRepairAction.homeAppliancesRepairAction.repairRequest.id.eq(id))
        .fetch();

    return request;
}

// ✅ 올바른 예 2: Batch Fetching 활용 (권장)
public List<HomeAppliancesRepairRequest> findAllWithActions() {
    // 부모만 조회 (Batch Fetching이 컬렉션 자동 로드)
    return queryFactory
        .select(request)
        .from(request)
        .fetch();
    // actions에 접근하면 Batch Fetching으로 최적화된 쿼리 실행
}
```

#### Distinct 사용 (컬렉션 조인 시 중복 제거)

```java
public List<HomeAppliancesRepairRequest> findAllWithTimelines() {
    return queryFactory
        .select(request).distinct()  // 중복 제거
        .from(request)
        .leftJoin(request.timelines, timeline).fetchJoin()
        .fetch();
}
```

### 전략 2: @EntityGraph (Spring Data JPA)

**장점:**
- 간단한 선언으로 사용 가능
- Repository 인터페이스만 수정

**단점:**
- 복잡한 조인 조건 처리 어려움
- 동적 fetch 전략 적용 불가

#### 기본 사용법

```java
public interface HARepairRequestRepository
    extends JpaRepository<HomeAppliancesRepairRequest, String>,
            HARepairRequestRepositoryCustom {

    // 단일 경로
    @EntityGraph(attributePaths = {"customer"})
    Optional<HomeAppliancesRepairRequest> findWithCustomerById(String id);

    // 다중 경로
    @EntityGraph(attributePaths = {"customer", "product"})
    Optional<HomeAppliancesRepairRequest> findWithCustomerAndProductById(String id);

    // 중첩 경로
    @EntityGraph(attributePaths = {"customer", "customer.partner", "product"})
    Optional<HomeAppliancesRepairRequest> findWithAllRelationsById(String id);

    // 컬렉션 포함
    @EntityGraph(attributePaths = {"customer", "timelines"})
    Optional<HomeAppliancesRepairRequest> findWithCustomerAndTimelinesById(String id);
}
```

#### Named EntityGraph

```java
// Entity에 정의
@Entity
@NamedEntityGraph(
    name = "RepairRequest.withAllRelations",
    attributeNodes = {
        @NamedAttributeNode("customer"),
        @NamedAttributeNode("product"),
        @NamedAttributeNode(value = "customer", subgraph = "customer.partner")
    },
    subgraphs = {
        @NamedSubgraph(
            name = "customer.partner",
            attributeNodes = @NamedAttributeNode("partner")
        )
    }
)
public class HomeAppliancesRepairRequest extends Base {
    // ...
}

// Repository에서 사용
@EntityGraph("RepairRequest.withAllRelations")
Optional<HomeAppliancesRepairRequest> findById(String id);
```

### 전략 3: Batch Fetching (글로벌 설정)

CS-Back 프로젝트는 이미 Batch Fetching이 설정되어 있습니다:

```yaml
# application.yml
spring:
  jpa:
    properties:
      hibernate:
        default_batch_fetch_size: 1000
```

**동작 원리:**
```java
// 100개의 Customer 조회
List<Customer> customers = customerRepository.findAll();

// 각 Customer의 Partner 접근
for (Customer customer : customers) {
    customer.getPartner().getName();
}

// 실행되는 SQL:
// 1. SELECT * FROM customer;
// 2. SELECT * FROM partner WHERE id IN (1, 2, 3, ..., 1000);  -- 1번의 IN 쿼리로 최적화
//    (1000개씩 묶어서 조회)
```

**장점:**
- 설정만으로 자동 적용
- 코드 수정 불필요

**단점:**
- 여전히 2번 이상의 쿼리 실행 (Fetch Join보다는 느림)
- 대량 데이터 시 IN 절이 매우 길어질 수 있음

## 실전 패턴

### 패턴 1: 상세 조회 (단일 엔티티)

**시나리오:** ID로 수리 요청 1건 조회, 모든 연관 데이터 포함

**권장:** Fetch Join

```java
@Override
public Optional<HomeAppliancesRepairRequest> findByIdWithAllRelations(String id) {
    QHomeAppliancesRepairRequest request = QHomeAppliancesRepairRequest.homeAppliancesRepairRequest;
    QCustomer customer = QCustomer.customer;
    QPartner partner = QPartner.partner;
    QHomeAppliancesProduct product = QHomeAppliancesProduct.homeAppliancesProduct;
    QArea area = QArea.area;

    return Optional.ofNullable(
        queryFactory
            .select(request)
            .from(request)
            .leftJoin(request.customer, customer).fetchJoin()
            .leftJoin(customer.partner, partner).fetchJoin()
            .leftJoin(request.product, product).fetchJoin()
            .leftJoin(request.area, area).fetchJoin()
            .where(request.id.eq(id)
                .and(request.deleteYn.deleteYn.ne("Y")))
            .fetchOne()
    );
}
```

### 패턴 2: 목록 조회 (페이징)

**시나리오:** 수리 요청 목록 페이징 조회, 고객/제품 정보 포함

**권장:** Fetch Join (페이징은 부모 엔티티 기준)

```java
@Override
public Page<HomeAppliancesRepairRequest> searchWithPaging(
    SearchCondition condition,
    Pageable pageable) {

    QHomeAppliancesRepairRequest request = QHomeAppliancesRepairRequest.homeAppliancesRepairRequest;
    QCustomer customer = QCustomer.customer;
    QHomeAppliancesProduct product = QHomeAppliancesProduct.homeAppliancesProduct;

    // 1. Count 쿼리 (fetch join 없이)
    long total = queryFactory
        .select(request.count())
        .from(request)
        .where(buildSearchPredicate(condition))
        .fetchOne();

    // 2. 데이터 쿼리 (fetch join 포함)
    List<HomeAppliancesRepairRequest> content = queryFactory
        .select(request)
        .from(request)
        .leftJoin(request.customer, customer).fetchJoin()
        .leftJoin(request.product, product).fetchJoin()
        .where(buildSearchPredicate(condition))
        .offset(pageable.getOffset())
        .limit(pageable.getPageSize())
        .orderBy(request.createdDate.desc())
        .fetch();

    return new PageImpl<>(content, pageable, total);
}
```

### 패턴 3: 통계 조회 (집계)

**시나리오:** 상태별 수리 요청 건수 조회

**권장:** 집계 쿼리 (fetch join 불필요)

```java
@Override
public Map<RequestStatus, Long> countByStatus() {
    QHomeAppliancesRepairRequest request = QHomeAppliancesRepairRequest.homeAppliancesRepairRequest;

    List<Tuple> results = queryFactory
        .select(request.status, request.count())
        .from(request)
        .where(request.deleteYn.deleteYn.ne("Y"))
        .groupBy(request.status)
        .fetch();

    return results.stream()
        .collect(Collectors.toMap(
            tuple -> tuple.get(request.status),
            tuple -> tuple.get(request.count())
        ));
}
```

### 패턴 4: DTO 프로젝션

**시나리오:** 화면 표시용 DTO만 조회 (엔티티 불필요)

**권장:** DTO 직접 조회

```java
@Override
public List<RepairRequestListDto> searchForList(SearchCondition condition) {
    QHomeAppliancesRepairRequest request = QHomeAppliancesRepairRequest.homeAppliancesRepairRequest;
    QCustomer customer = QCustomer.customer;
    QHomeAppliancesProduct product = QHomeAppliancesProduct.homeAppliancesProduct;

    return queryFactory
        .select(Projections.constructor(RepairRequestListDto.class,
            request.id,
            customer.name,
            customer.phoneNumber.value,
            product.modelName,
            request.status,
            request.requestedDate,
            request.createdDate
        ))
        .from(request)
        .leftJoin(request.customer, customer)
        .leftJoin(request.product, product)
        .where(buildSearchPredicate(condition)
            .and(request.deleteYn.deleteYn.ne("Y")))
        .fetch();
}

// DTO
public record RepairRequestListDto(
    String id,
    String customerName,
    String phoneNumber,
    String productModel,
    RequestStatus status,
    LocalDate requestedDate,
    LocalDateTime createdDate
) {}
```

## N+1 감지 방법

### 방법 1: SQL 로깅 확인

```yaml
# application-local.yml
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.type.descriptor.sql.BasicBinder: TRACE
```

**반복되는 SELECT 패턴 확인:**
```
SELECT * FROM repair_request WHERE ...
SELECT * FROM customer WHERE id = ?
SELECT * FROM customer WHERE id = ?
SELECT * FROM customer WHERE id = ?
...
```

### 방법 2: P6Spy 활용 (이미 설정됨)

CS-Back 프로젝트는 P6Spy가 이미 설정되어 있어 포맷팅된 SQL이 출력됩니다.

**로그 예시:**
```
#1 | took 3ms | statement | connection 0 | url jdbc:mariadb://...
SELECT ...
```

### 방법 3: 테스트 코드로 검증

```java
@Test
@DisplayName("N+1 문제 발생하지 않아야 함")
void findByIdWithRelations_shouldNotCauseNPlusOne() {
    // Given
    String id = "REQ001";

    // When
    // 쿼리 카운터 시작
    long queryCountBefore = getQueryCount();

    Optional<HomeAppliancesRepairRequest> result =
        repository.findByIdWithAllRelations(id);

    long queryCountAfter = getQueryCount();

    // Then
    assertThat(result).isPresent();
    assertThat(queryCountAfter - queryCountBefore).isEqualTo(1);  // 1번의 쿼리만 실행

    // Lazy Loading이 발생하지 않는지 확인
    assertThat(result.get().getCustomer()).isNotNull();
    assertThat(result.get().getCustomer().getPartner()).isNotNull();
    assertThat(result.get().getProduct()).isNotNull();
}
```

## 체크리스트

리팩토링 시 다음 항목을 확인하세요:

### Repository 메서드 검토
- [ ] `findById` 메서드에 fetch join 또는 @EntityGraph 적용 여부
- [ ] `findAll` 계열 메서드에서 연관 엔티티 접근 여부
- [ ] 커스텀 쿼리에서 leftJoin 사용 시 fetchJoin() 호출 여부
- [ ] 페이징 쿼리에서 컬렉션 fetch join 사용 여부 (금지)

### Service 메서드 검토
- [ ] for문 안에서 연관 엔티티 접근 (`entity.getRelation()`) 여부
- [ ] 조회 결과를 DTO 변환 시 연관 데이터 필요 여부
- [ ] Lazy Loading Exception 발생 가능성

### 테스트 검증
- [ ] 쿼리 횟수 검증 테스트 작성
- [ ] 로그에서 반복 SELECT 패턴 확인
- [ ] 성능 테스트 (대량 데이터)

## 참고 사항

### Soft Delete 필수 체크

모든 QueryDSL 쿼리에서 soft delete 체크를 포함해야 합니다:

```java
.where(request.id.eq(id)
    .and(request.deleteYn.deleteYn.ne("Y")))  // 필수
```

### 복합키 (Composite Key) 처리

```java
// Area 엔티티는 복합키 사용
QArea area = QArea.area;

queryFactory
    .select(request)
    .from(request)
    .leftJoin(request.area, area).fetchJoin()
    .where(request.area.areaCode.eq("SEOUL")
        .and(request.area.subAreaCode.eq("GANGNAM")))
    .fetch();
```
