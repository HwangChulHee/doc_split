# Handoff — CREDIT_REPORT 파이프라인 구현 (완료 보고)

> 이 문서는 완료된 세션의 결과를 다음 세션에 전달하는 핸드오프다.
> 범위는 엔진 일반화 + CREDIT 파이프라인 + 검증 + URLA 잔여 정리였다.
> **TITLE_REPORT / INCOME_DOC / OTHER 로직과 VLM(이미지 페이지)은 미구현이다.**
> 검증 실패 2건은 지시대로 **튜닝하지 않고 원인만 기록**했다 — §5 참조.

## 0. 전제 상태 (이 세션 이전)

- URLA 파이프라인 구현 완료 (V1–V4 통과), 파싱·GT 빌더·LLM 캐싱 기반 존재
- 선행 분석: `docs/analysis/urla_standard_analysis.md`, `docs/analysis/credit_vendor_analysis.md`
- 설계 문서: `docs/classification/urla.md`, `docs/classification/credit_report.md`

## 1. 이 세션에서 한 것

1. **엔진 일반화** — 신호 계층(layer), 벤더 레이어, 신호 스펙 확장, 유형 간 경합
2. **CREDIT 정책·프롬프트** 작성 및 파이프라인 연결
3. **검증 C-V1~C-V5** 구현·실행
4. **URLA 잔여 6항목** 정리 + `tests/` 신설

## 2. 구조 변경 — 다음 유형을 붙일 때 알아야 할 것 ★

### 2-1. 파이프라인은 하나다

`src/docsplit/pipeline.py` 가 [1]판정 → [2]카드 → [3]그룹핑 → [4]정렬 + 검증을 모두
수행하고, `urla_pipeline.py` / `credit_pipeline.py` 는 정책만 바인딩하는 얇은 엔트리다.

```python
run(policy_name="credit_report", out_subdir="credit", check_prefix="C-", args=args)
```

**새 유형 추가 = 정책 yaml + 프롬프트 + 3줄짜리 엔트리.** 엔진은 수정하지 않는다.

### 2-2. 정책 스키마 (설계 credit_report.md §9)

```yaml
universal:                    # 벤더 독립
  decisive:   {ID: {layer: ..., <match spec>}}
  supportive: {...}
vendors:                      # 선택 — 없으면 정상 동작 (URLA가 그 경우)
  <key>:
    identity:   {...}         # 이 벤더 산출물임을 증명
    decisive:   {...}         # identity 성립이 전제 (아니면 supportive 1개로 강등)
    supportive: {...}
    subtypes:   {name: {<match spec> | via: <signal id>}}
```

- 최상위에 `decisive`/`supportive` 를 두는 구형(URLA)도 `universal` 로 읽힌다 — 마이그레이션 불필요
- 매치 스펙 키: `phrases`, `patterns`, `min_matches`, `require_all`, `require_all_any`, `require_absent`
- **모든 신호에 `layer` 필수** (`normative` > `domain` > `vendor` > `deployment`).
  테스트가 이를 강제한다 (`test_shipped_policy_signals_declare_layer`)
- 카드 추출·순서 폴백·그룹핑 프롬프트명도 전부 정책에서 온다
  (`cards.id_patterns`, `ordering.subtype_order`, `prompts.group`)

### 2-3. 유형 간 경합

페이지마다 모든 정책을 독립 평가한다. **둘 이상이 RULE_HIGH면** `flags.type_conflict`
를 달고 DEFER_LLM으로 넘긴다 (임의 우선순위 없음). 이번 데이터셋에서는 0건.

### 2-4. 등급

`RULE_HIGH` / `RULE_MEDIUM` / `DEFER_LLM` / `NO_SIGNAL` / `DEFER_VLM` /
`EXCLUDED_ADJACENT`(인접 문서로 배제 — 이번에 신설) / `LLM` / `LLM_UNRESOLVED`

## 3. 실행

```bash
uv run python -m docsplit.credit_pipeline --data-dir data --out-dir outputs
uv run python -m docsplit.urla_pipeline   --data-dir data --out-dir outputs
# 옵션: --no-llm, --package {01,02,both}
uv run pytest tests/ -q     # 25 passed
```

산출물: `outputs/{credit,urla}/{classification.jsonl,cards.jsonl,grouping.json,ordering.json,report.md}`
(전부 gitignore — 데이터셋 파생물)

## 4. 검증 결과

| # | 기준 | 결과 |
|---|---|---|
| C-V1 | 기대 CREDIT 페이지 전부 RULE_HIGH/MEDIUM | ❌ 30/32 (pkg01 17/18, pkg02 13/14) |
| C-V2 | 비-CREDIT 50p 결정적 신호 오발 | ✅ 0 |
| C-V3 | 비-CREDIT 50p supportive≥2 | ✅ 0 |
| C-V4 | pkg01 1 instance + GT 순서 일치 | ❌ 그룹핑 정확(18/18), **순서만 불일치** |
| C-V5 | universal만으로 커버 (측정) | **15/18 (83%)** |
| URLA V1–V4 | 회귀 확인 | ✅ 전부 통과 (21/21) |

**계층별 기여도** (CREDIT 판정 34p): vendor 34p / domain 29p / normative 6p.
**벤더 신호만으로 잡힌 페이지 5p** — 나머지는 universal 신호가 함께 잡는다.

**subtype**: main_report 20 / score_disclosure 2 / consumer_letter 2 / None 9 (양 패키지 합)

## 5. 검증 실패 2건 — 원인과 성격 (튜닝하지 않음) ★

### C-V1: 짧은 편지 페이지 2장이 규칙 등급에 못 미침

pkg01 shuffled p2(= Credit 원본 p17, 275자)와 pkg02 p23(554자). 둘 다 XACTUS
반송·안내 편지의 마지막 장으로, 가진 신호가 **벤더 identity + `Report ID:` 단 1개**다.
법정 고지문(U-S1)·신용 어휘(U-S2)·tradeline이 전무하다.

- **정규화 버그 아님** — 페이지 원문에 실제로 다른 신호가 없다
- 규칙 설계의 신호 공백이며, LLM 단계에서는 CREDIT으로 확정된다
  (C-V1은 규칙 등급만 인정하므로 실패로 남김)

### C-V4: 순서 정렬 (그룹핑은 정확)

그룹핑은 18/18 정확히 1 instance, unresolved 0. 실패는 **순서뿐**이다.
페이지 마커가 원본 p1–11에만 있고 p0·p12–17에는 없어 경로 A(1..Y 무결)가 성립하지
않고 경로 B(subtype 순서)로 떨어져 main_report 11장 내부 순서가 복원되지 않았다.

**설계 §8-4가 예고한 한계**("본체 내부 순서는 마커 의존")가 그대로 재현된 것이다.

## 6. 결정이 필요한 열린 항목 ★

1. **TWN 페이지(pkg02 p31)가 규칙에 잡힌다.** 설계 §4-3은 "CREDIT 규칙이 이 페이지를
   강제로 잡지 않는다"고 했으나, `Report ID:`(X-S1) + `Requested By:`(X-S3) 두 벤더
   supportive로 **RULE_MEDIUM**에 도달한다. subtype 가드는 작동해 `order_summary`
   오분류는 막았다(subtype=None). 배제하려면 임계값·문구를 건드려야 해서 손대지 않았다.
2. **pkg02 p26(IRS Wage and Income Transcript)이 LLM 단계에서 CREDIT으로 확정됐다.**
   규칙은 `Report ID:` 하나만 잡아 DEFER_LLM으로 넘겼고(IRS 문서도 같은 라벨을 인쇄)
   LLM이 CREDIT_REPORT로 답했다. 그룹핑은 별도 instance로 분리하며 "앵커 없음"을 기록했다.
   **INCOME 설계 시 이 페이지와 p31의 귀속을 함께 결정해야 한다.**
3. **C-V1 검증 범위**: 설계 §7 표는 pkg01만 명시하나 URLA V1은 양 패키지를 봤다.
   양쪽 검증하되 패키지별로 나눠 보고하도록 구현했다 (판정은 어느 해석이든 FAIL).
4. **pkg02 기대 페이지에서 p31 제외**: `config/expected_pages.yaml` 에 `undecided: [31]`
   로 분리해 기대값·반례 양쪽에서 뺐다 (설계 §4-3 보류 지시에 따름).

## 7. URLA 잔여 정리 (완료)

| # | 항목 | 조치 |
|---|---|---|
| 1 | 기대 페이지 하드코딩 | `config/expected_pages.yaml` 로 이관. **라벨 불일치 시 경고 출력** (조용한 빈 목록 방지) |
| 2 | `llm_usage.json` 누적 | `this_run` / `cumulative` 분리. 리포트는 이번 실행분 표기 |
| 3 | 설계 §6 경로 B | "(LLM)" → **코드(섹션 순서)** 로 수정. 순서 정렬 프롬프트는 만들지 않음 |
| 4 | SCIF 등급 | `NO_SIGNAL` → **`EXCLUDED_ADJACENT`** 신설 (설계 문서 반영) |
| 5 | `--package both` | URLA·CREDIT 양쪽 실행 완료 (pkg02 결과 산출됨) |
| 6 | 테스트 | `tests/test_classify.py` — 결합 규칙·벤더 identity 전제·순서 경로 A/B/C·정책 layer 강제, **25 passed** |

구현 중 잡은 버그 하나: score_disclosure는 설계상 **렌더 레터헤드**라 벤더 identity가
없는데 초기 코드가 identity를 전제로 해 미판별됐다. 설계 §3-3에 맞춰 identity 없이도
subtype을 평가하도록 수정했다.

## 8. 다음 세션 참고

- TITLE_REPORT / INCOME_DOC 정책은 **0줄**. 붙일 때는 §2-2 스키마만 따르면 엔진 수정 불필요
- TITLE은 pkg01(CLTA/Fidelity)과 pkg02(ALTA/First American)가 **다른 폼·다른 벤더**다 —
  벤더 레이어를 2개 등록하는 첫 사례가 될 것 (`docs/domain_knowledge.md` §3 참조)
- INCOME은 §6-2의 두 페이지(p26, p31) 귀속 결정이 선행되어야 한다
- 검증 철학은 동일하다: GT는 검산용, **실패 시 튜닝 금지·사실 기록**
