# parallel-modes — 실무 병렬 모드 2개 (fan-out 표준 = dynamic Workflow)

> 2026-07-20 확정 (harness v2 설계 §7, 구 parallel-fanout.md·Agent Teams 서술 supersede).
> **Agent Teams 신규 사용 금지** — 실측 결함 4건: 시퀀스 해석 결함(4 worktree 전원 게이트 무시, LOG 632) / worker hang(LOG 228) / 모델 오버라이드 미적용 전원-fable 상속(CHANGELOG 235) / 동일 함정 재발 긴급 중단(CHANGELOG 116). `--subtasks` 정식 모드(ADR-070)는 실무에서 매번 일반 모드로 폴백됐으므로 문서 표면에서 제거 — 병렬은 아래 2모드로만.

## 모드 ① 단일 이슈 2레인 (기본)

한 이슈가 BE+FE 에 걸칠 때. 같은 워킹트리·같은 브랜치에서 dynamic **Workflow** 로 레인 분리:

```
Workflow script:
  phase('Implement')
  parallel([
    () => agent(<BE 레인 prompt>, {model:'opus',   phase:'Implement', label:'BE'}),
    () => agent(<FE 레인 prompt>, {model:'sonnet', phase:'Implement', label:'FE'}),
  ])
  → 메인(fable)이 크로스레인 seam(DTO 계약·URL·i18n) 직접 대조 후 통합
```

- 선례: PROJ-803/804/805(15 agents)·PROJ-815/820/821/822/824/826-827 전부 이 패턴으로 완주.
- 크로스레인 갭(예: RepairRequestDetailResponse 필드 누락)은 레인에 재위임하지 말고 **메인이 직접 해소**.

## 모드 ② 다중부모 fan-out (부모 이슈 N개 병렬)

독립 부모 이슈 N개를 동시에 진행할 때. **worktree 격리 + 클러스터링 레인**:

1. touched-files 충돌 매트릭스 사전 산출 — 겹치는 이슈는 같은 레인으로 클러스터링(직렬), disjoint 만 병렬.
2. `git worktree add ../<repo>-<KEY> feat/<KEY>` 레인별 격리 (운영 함정: 데몬 경합·node_modules — 운영 실측. vitest 는 절대경로/--exclude 필수 — 운영 실측).
3. dynamic Workflow 로 레인별 `agent(..., {isolation:'worktree'})` 또는 명시 cwd. 하이브리드 wave: 병렬 구현 → 순차 머지 → 횡단(cross-cutting) 변경은 머지 후 직렬 (운영 실측).
4. 머지는 인간 게이트 원칙 (레인 브랜치 → 검증 → 사용자/메인 판단).

## 공통 운용 규칙 — 모델 티어링 (메인=fable 세션)

| 역할 | 모델 |
|------|------|
| orchestration·verify/adversarial·크로스레인 seam | **fable (메인 직접)** |
| 난이도 상 구현·설계·보안 리뷰 | **opus 4.8** |
| FE 구현·recon·기계적 변환·리뷰 다수 축 | **sonnet 5** |

1. workflow script 의 **모든 `agent()` 호출에 `opts.model` 명시** (미지정 = fable 상속 함정). `meta.phases[].model` 에도 표기.
2. 웨이브 시작 시 **모델 스모크 프로브 1회** — 첫 agent 에게 자기 모델 식별 보고시켜 오버라이드 실적용 확인 후 본 fan-out.
3. fable 구현 레인은 **명시 사유 1줄 필수** (원장 불변식·동시성·상태머신 재설계급 한정, 레인 1개까지).
4. Codex adversarial 은 `scripts/codex-review.sh` 래퍼 경유 필수 — exit 42 시 opus skeptic workflow 폴백 + verdict 에 `codex=fallback(<사유>)`.
