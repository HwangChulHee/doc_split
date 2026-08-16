# INCOME_DOC 분류·그룹핑 기준서

> **위치**: `docs/classification/income_doc.md`
> **성격**: 설계 확정 문서. 구현은 이 문서를 명세로 삼는다.
> **근거 문서**: `docs/domain_knowledge.md`, `docs/analysis/income_standard_analysis.md`
> **선행 문서**: urla.md (골격), credit_report.md (계층·벤더 레이어), title_report.md
> 이 문서는 INCOME 고유 사항만 규정한다.

---

## 1. 이 유형의 특수성

INCOME_DOC는 단일 문서가 아니라 **"소득 증빙 기능"의 열린 카테고리**다.
데이터셋 표본이 극단적으로 적고(7페이지), 하위군 간 생김새 격차가 4개 유형 중
가장 크다.

| 하위군 | 데이터셋 | 신호 밀도 | 준거 |
|---|---|---|---|
| IRS Transcript | 4p (2벌) | 높음 (정부 표준 출력) | ✅ IRS 샘플·공식 안내 |
| 고용검증 조회 결과 | 1p | 중간 (벤더 템플릿) | ✅ 벤더 샘플 (단, 제품 동정 UNCERTAIN) |
| 검증 대행 리포트 (Corelogic) | 1p | 낮음 (준거 미확보) | ❌ |
| P&L | 1p | **0 (어휘 프로브 32종 전멸)** | 형식 표준 부재가 공식 확인됨 (Fannie B3-3.7-04) |
| W-2·1040·1099·Paystub·VOE 등 | **0p (미관찰)** | — | IRS blank 확보 (어휘만 수집) |

**설계 결론 세 줄:**

1. 규칙은 **하위군별로** 세운다 — "INCOME 공통 신호"는 존재하지 않음이 측정으로
   확인됐다 (교차 오염: 소득 어휘가 URLA에 더 많음).
2. 미관찰 하위군은 **준거에서 수집한 어휘로 대비**하되 데이터셋 검증이 불가함을
   명시한다 (합격 기준 없는 대비 신호).
3. **P&L류(무표준 개인 작성물)는 규칙의 영역 밖**이다 — LLM 의미 판단이 유일한
   경로임이 정량(32종 0건)과 공식 문서(GSE가 형식을 요구하지 않음)로 뒷받침된다.
   이는 실패가 아니라 이 하위군의 본질이다.

---

## 2. 신호 정의

### 2-1. universal — 하위군별 (계층 병기)

**결정적**

| ID | 신호 | layer | 근거 |
|---|---|---|---|
| I-D1 | IRS transcript 헤더 조합: `This Product Contains Sensitive Taxpayer Data` **AND** (`Internal Revenue Service` OR `United States Department of the Treasury`) | **normative** | IRS 산출물 공통 골격 — 준거 2종 샘플 + irs.gov 공식 안내로 확정. 정부 표준 출력 |
| I-D2 | transcript 제목: `Wage and Income Transcript` / `Tax Return Transcript` / `Account Transcript` / `Record of Account` / `Verification of Non-filing` | normative | irs.gov 공식 5종 명칭. 제목 자체가 유형+하위군 동시 지시 |

- I-D1을 고지문 **단독이 아니라 기관명과 AND 조합**으로 한 이유: p38 같은
  껍데기 페이지는 고지문만 있고 기관명이 없다 — 단독 결정은 과하다.
  고지문 단독은 지지(I-S1)로 별도 등록해 p38이 DEFER_LLM으로 흐르게 한다.

**지지적**

| ID | 신호 | layer | 근거·비고 |
|---|---|---|---|
| I-S1 | `This Product Contains Sensitive Taxpayer Data` 단독 | normative | I-D1 미성립 시(껍데기 페이지)의 잔여 신호 |
| I-S2 | transcript 필드 라벨 조합 — 다음 중 **2종 이상**: `Request Date:`, `Response Date:`, `Tracking Number:`, `Tax Period Requested:`/`Tax Period Ending:`, `TIN Provided:`/`SSN Provided:`, `Customer File Number:` | normative | **판마다 라벨이 다름이 확인됨** (SSN↔TIN 등) — 그래서 변형 병기 + 조합 조건. 단독 라벨은 신호 아님 |
| I-S3 | 세무 특이어 조합 — 다음 중 **3종 이상**: `Wages, Tips and Other Compensation`, `Federal Income Tax Withheld`, `Medicare Wages`, `Social Security Wages`, `Employer Identification Number`/`EIN`, `Form W-2 Wage and Tax Statement` | domain | 교차 오염 측정에서 INCOME 전용으로 확인된 어휘만 선별. **`Income`·`Employer` 단독은 금지** (URLA 오염 6~7p) |
| I-S4 | 손익 어휘 조합 (미관찰 P&L 대비) — 다음 중 **2종 이상**: `Profit and Loss`, `Net Income`, `Gross Revenue`/`Gross Receipts`, `Total Expenses`, `Year-to-Date`/`YTD` | domain | Fannie B3-3.7-04 내용 3요소 기반. **데이터셋 표본에는 0건 — 검증 불가한 대비 신호**임을 명시 |
| I-S5 | 미관찰 IRS 양식 신호 (대비) — `Form W-2` blank 제목·OMB 번호, `Form 1040`, `Form 4506-C` 등 blank에서 수집한 식별 문구 | normative | IRS blank 5종에서 수집. 데이터셋 검증 불가 |

### 2-2. vendor: xactus (CREDIT 블록 재사용 + 확장)

INCOME 전용 벤더 블록을 새로 만들지 않는다. CREDIT의 xactus 블록에
**고용검증 subtype 신호**를 추가한다 (같은 벤더가 신용·고용검증 산출물을 함께
배달하는 구조가 확인됐으므로):

| ID | 신호 | layer | 비고 |
|---|---|---|---|
| X-EV1 | 고용검증 라벨 조합 — `Employment Record Available:` AND (`Employer Name`/`Employment Status`/`Verification Type` 등 샘플 일치 라벨 중 1+) | vendor | **제품 동정은 UNCERTAIN** (분석 §7: TWN 제품명 부재, Experian Background Data 명시) — 신호명을 제품 중립적으로 `employment_verification` 으로 명명. "TWN" 명칭 사용 금지 |

이 신호는 **INCOME_DOC 유형 판정에 기여**한다 (CREDIT이 아니라). 즉 xactus
블록이 두 유형에 걸치게 되며, 정책 표현은 §7 스키마 참조.

### 2-3. 준거 미확보 하위군 — Corelogic 검증 리포트

`PREPARED FOR:`/`PREPARED BY:` + `IRS Form Types:` + `Years:` 라벨 구조는
관찰뿐이고 외부 근거가 없다. **§0 과최적화 지침에 따라 분류 신호로 채택하지
않는다.** 이 페이지(p35)는:

- I-S3(세무 특이어)나 10자 토큰 동반 여부에 따라 지지 신호가 일부 걸릴 수 있고
- 부족하면 DEFER_LLM — LLM이 "IRS Form Types: W-2, Years: ..."의 의미로 판단

이것이 옳은 흐름이다. 관찰 1장짜리 라벨을 규칙화하는 것보다 LLM 위임이
과최적화를 막는다.

### 2-4. 규칙 미채택 (deployment)

| 신호 | 성격 | 활용 |
|---|---|---|
| `Ref:` / `Report ID:` / `File Number:` (transcript 위) | 전달 벤더 스탬프 — IRS 준거 부재 확정 | 그룹핑 |
| 10자 토큰 2종 | 주문 단위 식별자 (transcript 4p + Corelogic 관통, **두 벌 구분 불가**) | 그룹핑 — "같은 주문 묶음" 앵커 |
| `CTEC #` | 캘리포니아 한정 제도 | 그룹핑 보조. **분류 신호 금지** (지역 한정 과최적화) |
| `PAGE N OF M` | 마커 | 경보·정렬 |

---

## 3. 판정 규칙

결합·전처리·경합은 기존과 동일. 추가 사항:

### 3-1. normalize 수정 (분석이 발견한 방법론 결함)

- **곡선 인용부호 통일 추가**: `'`(U+2019) 등 → `'`. 준거의 `Employee's` ↔
  데이터셋 `Employee's` 매칭 실패 사례. 기존 대조 결과에 영향 없는지 회귀 확인
- 준거 자체 오타(`Compenensation`)는 정책에 반영하지 않는다 (준거의 결함)

### 3-2. 유형 경합 — 첫 실전 (설계된 시나리오)

INCOME 정책 등장으로 다음 경합이 **의도적으로** 발생한다:

| 페이지 | 경합 | 기대 동작 |
|---|---|---|
| transcript 4장 | INCOME I-D1 (RULE_HIGH) vs CREDIT X-S1 (`Report ID:` 1개 → 미달) | 경합 아님 — INCOME 단독 확정. **p26 오분류가 규칙 수준에서 해소** |
| 고용검증 p31 | INCOME X-EV1 vs CREDIT X-S1+X-S3 (RULE_MEDIUM) | **type_conflict → LLM**. 프롬프트의 "기능 기준" 지침이 판정 |

`classify_page.md` 프롬프트에 추가할 지침:

```text
발행·전달 경로와 문서의 기능이 다를 수 있다. 신용조회 벤더가 배달한 문서라도
내용이 고용·소득의 확인이면 INCOME_DOC다. 유형은 문서의 기능을 따른다.
```

### 3-3. subtypes

| subtype | 판별 | 비고 |
|---|---|---|
| `irs_transcript` | I-D1/I-D2 | 제목으로 세부종류(w2_income/tax_return/...)까지 기록 가능하면 기록 |
| `employment_verification` | X-EV1 | 제품 동정 UNCERTAIN — 중립 명칭 |
| `verification_report` | (규칙 없음 — LLM 판정 시 LLM이 부여) | Corelogic류 |
| `pnl` | (규칙 없음 — LLM 판정 시) | P&L류 |
| None | 판별 불가 | 허용 (TITLE 결정 2와 동일) |

---

## 4. 그룹핑 (LLM 위임)

프롬프트: `prompts/group_income.md`

INCOME 그룹핑의 특수성: **하위군이 곧 문서 경계에 가깝다** (transcript 2벌,
검증 리포트 1장, P&L 1장 — 서로 묶일 일이 없는 낱개들).

지시 요지:

```text
1. INCOME은 성격이 다른 낱개 문서들의 집합일 수 있다. 억지로 큰 덩어리로
   묶지 마라. 1~2장짜리 instance가 정상이다.
2. 앵커: 과세연도(Tax Period), 고용주/EIN, Tracking Number 일치 = 같은 문서.
   10자 토큰류(Ref/Report ID 값)는 "같은 주문 묶음"일 뿐 같은 문서의 근거가
   아니다 — instance를 가르지도 묶지도 마라 (evidence 참고로만).
3. 마커(PAGE 1 OF 2 / 2 OF 2)가 이어지고 내용 앵커(EIN·연도)가 일치하면
   같은 instance. 마커 중복(1 OF 2가 두 장)이면 벌 분리 — TITLE과 동일 규칙.
4. 내용 앵커가 전무한 페이지(껍데기)는 마커+토큰만으로 억지 배정하지 말고,
   배정 근거를 못 세우면 unresolved. 단 소거법이 성립하면(남는 자리가 하나뿐)
   그 논리를 evidence에 쓰고 배정해도 된다.
5. evidence 필수, UNRESOLVED 허용.
```

4번의 소거법 허용은 p38을 위한 것이다 — p11+p38 짝은 "p26+p30이 EIN으로
확정된 뒤 남는 조합"이라는 소거 논리만 성립한다 (분석 §7). 소거는 근거가
서술 가능하므로 허용하되, LLM이 그 서술을 evidence에 남겨야 한다.

순서: 마커 경로 A로 충분 (2장짜리). subtype 순서 폴백 불필요.

---

## 5. 검증

| # | 검증 | 기준 |
|---|---|---|
| I-V1 | 기대 INCOME 페이지가 규칙 또는 **의도된 DEFER 경로**에 도달 — transcript 3장(p11·26·30) RULE_HIGH, p38 DEFER_LLM→LLM 판정, p31 type_conflict→LLM, p35 DEFER_LLM→LLM, pkg01 P&L DEFER_LLM 또는 NO_SIGNAL→LLM | 경로별 명세 일치 |
| I-V2 | 비-INCOME에서 결정적(I-D1/D2) 오발 | 0 |
| I-V3 | 비-INCOME에서 지지 ≥2 동시 성립 — **특히 URLA 고용·소득 페이지(오염 측정 지점)** | 0 |
| I-V4 | 그룹핑: transcript 2벌 분리(p26+30 앵커, p11+38 소거) + 낱개들 각자 instance | 충족 |
| I-V5 | universal만 커버리지 (측정) | 기록 |
| I-V6 | **p26 오분류 해소 확인**: INCOME 정책 활성 후 p26이 CREDIT으로 가지 않음 | 해소 |

I-V1이 기존 V1과 다름에 주의: "전부 RULE_HIGH/MEDIUM"이 아니라 **페이지별로
의도된 경로가 다르다.** P&L·Corelogic이 LLM으로 가는 것은 실패가 아니라 명세다.

## 6. 알려진 한계

1. **P&L류는 규칙 커버 불가** — 본질 (정량·공식 근거 확보됨). LLM 오답 시
   잡을 안전망 없음.
2. **미관찰 하위군 신호(I-S4/S5)는 검증 불가** — 대비용. 실물 등장 시 검증 필요.
3. **Corelogic류는 규칙 미채택** — 관찰 1장 과최적화 방지가 우선. LLM 의존.
4. **고용검증 신호는 벤더(xactus 배달분) 한정** — 다른 벤더의 VOE는 미대비
   (Form 1005 확보 실패). I-S3 일부 또는 LLM으로 흐른다.
5. **p38급 껍데기는 소거법 의존** — 소거가 안 서는 구성에서는 UNRESOLVED.

## 7. 정책 스키마 차분

```yaml
# policies/income_doc.yaml
type: INCOME_DOC
universal:
  decisive:
    I-D1: {layer: normative, require_all_any: ...}   # 고지문 AND (IRS|Treasury)
    I-D2: {layer: normative, phrases: [5종 제목]}
  supportive:
    I-S1: {layer: normative, phrases: [고지문]}
    I-S2: {layer: normative, min_matches: 2, phrases: [...변형 병기]}
    I-S3: {layer: domain, min_matches: 3, phrases: [...]}
    I-S4: {layer: domain, min_matches: 2, phrases: [...], note: "미관찰 대비 — 데이터셋 검증 불가"}
    I-S5: {layer: normative, phrases: [...], note: "미관찰 대비"}

# policies/credit_report.yaml 의 xactus 블록에 추가:
#   cross_type_signals:
#     X-EV1: {contributes_to: INCOME_DOC, layer: vendor,
#             require_all_any: [...], subtype: employment_verification}
```

엔진 신규 요구: `cross_type_signals` — 한 벤더 블록의 신호가 다른 유형 판정에
기여하는 표현. 구현이 복잡하면 대안: income_doc.yaml에 xactus identity 참조를
중복 등록하고 주석으로 출처 명시 (단순성 우선 — 구현 판단에 맡김, 단 어느 쪽이든
"같은 벤더 identity 문구를 두 곳에 복붙"하게 되면 그 사실을 주석으로 남길 것).
```
