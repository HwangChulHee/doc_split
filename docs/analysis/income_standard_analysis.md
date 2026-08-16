# INCOME_DOC 준거 문서 ↔ 데이터셋 대조 분석

작성일: 2026-08-17. 페이지 번호는 전부 **0-based**.
대조 raw 결과: `outputs/income_standard_diff/` (데이터셋 원문 포함 — 커밋 금지 영역).
대조 스크립트: `scripts/observe_income_diff.py`.
확보 문서·출처·커밋 정책: `data/reference/income/SOURCES.md`.

> **과최적화 경계 — 이 분석의 전제.**
> INCOME 표본은 **7페이지**다 (pkg01 P&L 1장 + pkg02 6장). 이 표본에 맞춘 신호는
> 반드시 깨진다. 그래서 이 문서는 확인된 문구마다 **"데이터셋 밖의 같은 하위군
> 문서에도 있을 근거"** 를 같이 적는다. 근거가 없으면 분류 신호 후보에서 빼고
> deployment(그룹핑 재료)로 내린다.
>
> | 등급 | 뜻 | 이 문서에서의 예 |
> |---|---|---|
> | **정부 표준** | IRS가 제정·발행 | 양식 blank의 OMB 번호·제목 |
> | **제3자 전재** | 협회가 IRS 산출물을 전재 | transcript 샘플 (NASFAA) |
> | **업계 규범** | GSE 인수 지침 | Fannie B3-3.7-04 |
> | **벤더 문서** | 벤더 제품 샘플 | Xactus TWN Indicator |
> | **관찰만** | 준거 없음 | Corelogic 페이지 |

이 문서는 사실 기록이다. 분류 전략 판단은 포함하지 않는다.
개인정보 값·고용주명·금액·고객사 고유명은 기록하지 않는다(범주·역할로만 서술).

---

## 1. 확보 목록과 등급

| 대상 | 결과 | 확보물 |
|---|---|---|
| IRS Transcript 샘플 | ✅ | NASFAA Tax Transcript Decoder 23p — **Tax Return Transcript(p8–12)와 Wage & Income Transcript(p16) 두 종을 전재** |
| IRS transcript 종류 안내 | ✅ | irs.gov 공식 페이지 — 5종 명칭 확정 |
| IRS 양식 blank | ✅ 5종 | W-2, 1040, 4506-C, 1099-MISC, 1099-NEC |
| P&L 형식 근거 | ✅ | Fannie Selling Guide B3-3.7-04 |
| TWN 샘플 | ✅ (기확보 재사용) | `data/reference/credit/xactus/twn_indicator_sample.pdf` |
| Customer File Number 도입 근거 | ❌ | irs.gov FAQ 페이지 `HTTP 503` (점검 중) |
| Fannie Form 1005 (VOE) | ❌ | 다운로드 링크 `HTTP 403` — VOE 어휘 미수집 |
| Corelogic 4506-C 서비스 안내 | ❌ | 공개 제품 문서 미확인 |

Account Transcript·Record of Account 샘플은 **별도로 확보하지 않았다** — 아래 §2가
보이듯 종류가 달라도 골격이 같아, 두 종 샘플로 골격 확정이 가능했다.

---

## 2. transcript 가족의 공통 골격 (확정)

### 2-1. 종류 로스터 (irs.gov)

`Tax Return Transcript` / `Tax Account Transcript` / `Record of Account Transcript` /
`Wage and Income Transcript` / `Verification of Non-filing Letter` — **5종**.
데이터셋에 있는 것은 `Wage and Income Transcript` 하나(2장)다.

### 2-2. 종류가 달라도 같은 것 — 골격

Tax Return Transcript 샘플과 Wage & Income Transcript 샘플 **양쪽 모두**에서 확인:

| 문구 | TRT 샘플 | W&I 샘플 | 성격 |
|---|---|---|---|
| `This Product Contains Sensitive Taxpayer Data` | ✅ | ✅ | **가족 공통 고지** |
| `Internal Revenue Service` | ✅ | ✅ | 발행 기관 |
| `United States Department of the Treasury` | ✅ | ✅ | 발행 기관 |
| `Request Date:` | ✅ | ✅ | 공통 필드 |
| `Response Date:` | ✅ | ✅ | 공통 필드 |
| `Tracking Number:` | ✅ | ✅ | 공통 필드 |
| `<종류명> Transcript` | ✅ | ✅ | 제목 |
| `SSN Provided:` | ✅ | ✅ | 공통 필드 |
| `Tax Period Ending:` | ✅ | ✅ | 공통 필드 |

즉 **transcript는 종류가 달라도 헤더 6요소가 동일**하다. 종류를 가르는 것은
제목 한 줄뿐이다.

### 2-3. 샌드위치 — **문서 단위로 사실, 페이지 단위로는 아님**

| 대상 | 위치 |
|---|---|
| TRT 샘플 첫 장(p8) | 82줄 중 **16번째** → 상단 |
| TRT 샘플 마지막 장(p12) | 16줄 중 **15번째** → 하단 |
| W&I 샘플(1장짜리, p16) | 54줄 중 3번째 → 상단 |

**고지문은 문서의 맨 앞과 맨 뒤에 한 번씩 온다.** 여러 장짜리 문서의 중간 장에는
없을 수 있다. 데이터셋도 같다:

| 페이지 | 마커 | 고지문 위치 |
|---|---|---|
| pkg02 p11 | `PAGE 1 OF 2` | 59줄 중 3번째 (상단) |
| pkg02 p26 | `PAGE 1 OF 2` | 60줄 중 3번째 (상단) |
| pkg02 p30 | `PAGE 2 OF 2` | 46줄 중 26번째 |
| pkg02 p38 | `PAGE 2 OF 2` | 6줄 중 1번째 |

p30이 "중간"으로 집계되는 것은 **추출 순서 아티팩트**다 — 이 렌더링은 라벨을 먼저
쏟고 값을 뒤에 몰아 내보내므로, 라벨 줄만 보면 고지문이 마지막이다(그 뒤 20줄은
전부 값). 즉 4장 모두 "문서 시작 또는 끝"에 고지문이 있다.

**결론**: `This Product Contains Sensitive Taxpayer Data`는 종류 불문·페이지 위치
불문 **transcript 가족 전체를 관통하는 단 하나의 문구**이며, 이 데이터셋의
transcript 계열 4장 전부(p38 껍데기 포함)에 존재한다.

### 2-4. 종류가 달라도 같지만 — **판(version)에 따라 라벨이 다르다**

준거(2018 과세연도 샘플)와 데이터셋(2024·2025 과세연도)의 라벨이 갈린다:

| 준거(2019년 전재) | 데이터셋 | 판정 |
|---|---|---|
| `SSN Provided:` | `TIN Provided:` | **표기 교체** |
| `Tax Period Ending:` | `Tax Period Requested:` | **표기 교체** |
| (없음) | `Customer File Number:` | **신설 필드** |

`Customer File Number`는 2018년 이후 IRS가 도입한 마스킹 transcript의 제3자
식별용 필드로 알려져 있으나, **IRS 문서로 확인하지 못했다**(§1 확보 실패) → §10.

같은 방향의 증거가 W-2 블록에도 있다. 준거 샘플에 **없고** 데이터셋에 있는 라벨:
`Third Party Sick Pay Indicator:`, `Retirement Plan Indicator:`,
`Statutory Employee:`, `W2 Submission Type:`, `W2 WHC SSN Validation Code:`.
반대로 준거에만 있는 것: `Social Security Tips:`, `Allocated Tips:`,
`Dependent Care Benefits:`, `Code "Q" Nontaxable Combat Pay:` 등.

**즉 transcript 라벨 집합은 판마다 증감한다.** 고정된 것은 §2-2의 골격뿐이다.

---

## 3. 데이터셋 대조 — 벤더 오버레이 분리

### 3-1. IRS 산출물이 아닌 것 (확정)

| 라벨 | IRS 준거 | 데이터셋 | 판정 |
|---|---|---|---|
| `Ref:` | **없음** (샘플·blank 5종 전부) | 5p (p11, p26, p30, p35, p38) | **벤더 스탬프** |
| `Report ID:` | **없음** (IRS 쪽) / TWN 샘플에는 있음 | 6p (전 페이지) | **벤더 스탬프** |
| `File Number:` | **없음** | 2p (p11, p26) | **벤더 스탬프** |
| `PREPARED FOR:` / `PREPARED BY:` | **없음** | 1p (p35) | 검증 벤더 표기 |
| `IRS Form Types:` / `Years:` / `Income Summary` / `Completed:` | **없음** | 1p (p35) | 검증 벤더 표기 |

**`Ref:` 와 `Report ID:` 는 IRS 표준이 아니다.** 이 둘은 CREDIT 분석에서 Xactus
벤더 신호로 이미 확인된 라벨이며(`credit_vendor_analysis.md` §3), 여기서는
IRS 산출물 위에 덧찍혀 있다. 계층은 **deployment**이고, 분류 신호가 아니라
**그룹핑 재료**다.

### 3-2. 10자 토큰 2종 — 주문 단위 식별자

영숫자 혼합 10자 토큰 2종이 **INCOME 계열 5장 전부**(transcript 4장 + Corelogic
1장)를 관통한다. TWN 페이지(p31)에는 없다.

- transcript 두 벌을 **가르지 못한다** (두 벌 모두에 같은 토큰)
- Corelogic 페이지와 transcript를 **잇는다** → 같은 주문의 산출물이라는 재료
- 값은 기록하지 않는다 (deployment 계층)

### 3-3. 페이지별 라인 분류

| 페이지 | IRS_STANDARD | VENDOR_OVERLAY | FILLED | UNCERTAIN |
|---|---|---|---|---|
| pkg02 p11 (W&I 1/2) | 19 | 3 | 16 | 21 |
| pkg02 p26 (W&I 1/2) | 18 | 4 | 17 | 21 |
| pkg02 p30 (W&I 2/2) | 13 | 3 | 11 | 19 |
| pkg02 p38 (W&I 2/2 껍데기) | **1** | 2 | 0 | 3 |
| pkg02 p31 (TWN 계열) | 0 | 2 | 3 | 19 |
| pkg02 p35 (Corelogic) | 2 | 10 | 8 | 12 |
| pkg01 P&L | **0** | 0 | 18 | 5 |

UNCERTAIN이 큰 이유는 §2-4의 판 차이(준거에 없는 신설 라벨)와 값 라인 때문이다.

### 3-4. 매칭 방법론에서 드러난 것 두 가지

준거 대조 중 **문구가 같은데 매칭이 실패**하는 사례를 두 건 확인했다. 둘 다
데이터의 문제가 아니라 정규화의 한계다.

1. **곡선 아포스트로피**: 준거는 `Employee’s Social Security Number:`(U+2019),
   데이터셋은 `Employee's`(U+0027). `normalize()`의 NFKC는 이 둘을 통일하지 않아
   준거 매칭이 0건으로 나온다. 현행 정규화가 불릿·대시는 통일하면서 인용부호는
   통일하지 않는 데서 오는 공백이다.
2. **준거 원문의 오타**: 준거 샘플이 `Deferred Compenensation:`으로 인쇄되어 있다
   (IRS 출력의 오타를 NASFAA가 그대로 전재). 데이터셋의 정상 표기
   `Deferred Compensation:`과 매칭되지 않는다.

---

## 4. p38 — 최소 신호 페이지 전수

99자, 6줄. **전부 나열하면 이것이 전부다**:

| # | 라인 | 분류 |
|---|---|---|
| 1 | `This Product Contains Sensitive Taxpayer Data` | **IRS_STANDARD** |
| 2 | `Ref:` (값 없음) | VENDOR_OVERLAY |
| 3 | `Report ID:` (값 없음) | VENDOR_OVERLAY |
| 4 | `PAGE 2 OF 2` | 페이지 마커 |
| 5–6 | 10자 토큰 2종 | deployment |

**유형을 지시하는 신호는 1번 한 줄뿐**이다. 고용주·금액·과세연도·EIN이 전부 없다.
이 페이지가 판별 가능한 것은 오직 §2-3에서 확정한 "가족 관통 고지문" 덕분이다.

---

## 5. 두 벌 짝 맞추기 재료

transcript 4장은 `PAGE 1 OF 2` 2장(p11, p26) + `PAGE 2 OF 2` 2장(p30, p38)이다.
값을 출력하지 않고 **일치 여부만** 비교한 결과:

| 쌍 | 과세연도 | EIN | 고용주 라인 | 금액 | 판정 |
|---|---|---|---|---|---|
| p11 ↔ p26 | 다름 | 다름 | 다름 | 다름 | 서로 다른 벌의 1쪽 |
| **p26 ↔ p30** | — | **일치** | **일치** | 다름 | **짝 성립** |
| p11 ↔ p30 | — | 다름 | 다름 | 다름 | 아님 |
| p11 ↔ p38 | — | (p38에 없음) | (없음) | (없음) | **판정 불가** |
| p26 ↔ p38 | — | (없음) | (없음) | (없음) | 판정 불가 |

**정리**:

- **p26 + p30**: EIN 마스크와 고용주 라인이 일치해 짝이 성립한다. 근거 있는 유일한 쌍.
- **p11 + p38**: p38에 대조 가능한 필드가 하나도 없다. 짝은 **소거법으로만** 남고
  직접 근거는 **없다**.
- p11과 p26은 `Tax Period Requested` 값이 서로 달라 **두 벌이 서로 다른 과세연도**임이
  확인된다 (연도 값 자체는 기록하지 않음).
- 10자 토큰 2종과 `Request Date`/`Response Date`는 **두 벌이 동일**하다 → 같은 날
  한 주문으로 두 연도를 함께 조회한 산출물로 보이며, 벌 구분에는 쓸 수 없다.

---

## 6. TWN 페이지 (p31) — 이전 세션 판정의 정정

### 6-1. 라벨 세트는 벤더 샘플과 일치한다 (12종)

`Client Name:` `Ordered:` `Address:` `Address 2:` `City, State, Zip:` `Report ID:`
`Loan Number:` `Borrower:` `Co-Borrower:` `SSN:` `Requested By:` `End of Report`
— **전부 TWN Indicator 샘플에 존재**한다. 이전 세션이 8종 일치로 보고한 것을
전수 대조해 12종으로 확정했다.

### 6-2. 그러나 결정적 표기 3건이 어긋난다 ★

| 항목 | 벤더 샘플 | 데이터셋 p31 | 의미 |
|---|---|---|---|
| 제품명 | `THE WORK NUMBER®` (고지문 안) | **0건** | 데이터셋 페이지에 제품명이 없다 |
| 결과 라벨 | `Record Available: NO` | `Employment Record Available: NO` | 표기 상이 |
| 발행 CRA | (샘플은 벤더 테스트 계정) | `consumer reporting agency Experian Background Data` | **다른 회사** |

The Work Number는 **Equifax** 제품이다(`domain_knowledge.md` §4-4). 그런데 이
페이지가 자신을 발행했다고 밝히는 주체는 **Experian Background Data**다.

**따라서 "이 페이지 = The Work Number 조회 결과"라는 이전 세션의 동정은 확정으로
볼 수 없다.** 확정할 수 있는 사실은 이것뿐이다:

- 같은 벤더(주문 시스템)의 **고용 이력 조회 결과 표시 페이지** 레이아웃이다 (라벨 12종 일치)
- 조회 결과는 "기록 없음"이다
- 발행 CRA로 명시된 것은 Experian 계열이다

제품 동정은 §10 UNCERTAIN으로 내린다.

---

## 7. Corelogic 페이지 (p35) — 준거 없음, 관찰만

외부 근거 탐색 실패(§1). 관찰된 구조만 기록한다.

- **역할 표기**: `PREPARED FOR:` (LOS 벤더) / `PREPARED BY:` (검증 벤더)
  → 이 페이지는 **누가 누구에게** 발행했는지를 문서 자체가 밝힌다
- **처리 이력**: `Received:` / `Completed:` (각 1일 간격)
- **주문 명세**: `Account:`, `IRS Form Types:`(값 `W-2`), `Years:`(두 개 연도)
- **결과부**: `Income Summary`, `Output - W2`, `Tax Period:`, 그리고
  `Wages, Tips and Other Compensation:` — **transcript와 같은 라벨을 재사용**한다
- 10자 토큰 2종이 transcript 4장과 공유된다 (§3-2)

즉 이 페이지는 **transcript 조회를 대행한 벤더의 요약본**이며, 원본 IRS 산출물의
라벨을 일부 인용한다. `Wages, Tips and Other Compensation:`이 IRS 라벨로 잡히는
2건이 여기서 나온다(§3-3의 IRS_STANDARD 2).

---

## 8. P&L 페이지 — 어휘 프로브 결과

### 8-1. 프로브 32종, **적중 0건**

Fannie B3-3.7-04("Schedule C와 유사한 형식")을 근거로 만든 프로브 32종
(`Profit and Loss`, `Revenue`, `Expenses`, `Net Income`, `YTD`, Schedule C 항목명
`Advertising`/`Rent`/`Supplies`/`Depreciation`/`Commissions and fees` 등)이
이 페이지에서 **하나도 걸리지 않는다.**

### 8-2. 실제로 있는 것 전수 (23줄, 250자)

| 범주 | 개수 | 비고 |
|---|---|---|
| 이름 + 직함 | 1줄 | 차주와 직업 |
| 금액 라인 | **18줄** | 라벨 없는 숫자만 |
| 작성자명 | 2줄 | 반복 |
| `CTEC #` + 등록번호 | 1줄 | 캘리포니아 세무대리인 등록번호 |
| 차주 서명명 | 1줄 | |
| 날짜 | 1줄 | |

**라벨이 하나도 없다.** 금액 18줄이 무엇의 금액인지 텍스트만으로는 알 수 없다.
이 페이지는 이미지 5개를 갖고 있어, 항목명이 이미지 레이어에 있을 가능성이 있다
(판독은 이번 범위 밖 — §10).

### 8-3. 이 결과의 의미

"전형 P&L이라면 걸렸을 어휘 32종 중 0종" — 이는 **P&L 문서의 형식 표준 부재**
(§SOURCES 3: GSE도 "유사한 형식"이라고만 서술)가 실제 데이터에서 어떻게 나타나는지의
정량 사례다. 이 표본에서 텍스트로 확인되는 유일한 문서-성격 신호는
`CTEC #`(세무대리인 등록번호) 하나이며, 그것도 **캘리포니아 한정 제도**다.

---

## 9. 교차 오염 측정

INCOME 후보 어휘가 **다른 유형 페이지**에서 얼마나 걸리는가 (모집단 83p,
pkg01은 GT·pkg02는 기대 페이지 설정 기준):

| 어휘 | INCOME | URLA_1003 | CREDIT_REPORT | TITLE | 판정 |
|---|---|---|---|---|---|
| `Wages` | 4p | 0 | 0 | 0 | **INCOME 전용** |
| `W-2` | 3p | 0 | 0 | 0 | **INCOME 전용** |
| `Medicare` | 3p | 0 | 0 | 0 | **INCOME 전용** |
| `Withheld` | 3p | 0 | 0 | 0 | **INCOME 전용** |
| `Tax Period` | 3p | 0 | 0 | 0 | **INCOME 전용** |
| `Taxpayer` | 4p | **2p** | 0 | 0 | 오염 |
| `Income` | 4p | **6p** | 0 | 0 | **오염 큼** |
| `Employer` | 3p | **7p** | **2p** | 0 | **오염 가장 큼** |
| `Employment` | 1p | **4p** | **2p** | 0 | 오염 |
| `Employee` | 3p | 0 | **1p** | **1p** | 오염 |
| `Social Security` | 3p | **2p** | **4p** | 0 | **오염 큼** |
| `Overtime` / `Bonus` | 0 | **2p** | 0 | 0 | **URLA 전용** |
| `Tax Return` | 0 | **2p** | 0 | 0 | **URLA 전용** |
| `Salary` / `Gross Income` / `Self Employed` / `Base Income` | 0 | 0 | 0 | 0 | 데이터셋 미등장 |

**충돌 지점 확정**: URLA의 고용·소득 섹션 페이지(pkg01 p5 / pkg02 p19가 대표)가
`Income`·`Employer`·`Employment`·`Social Security`·`Overtime`·`Bonus`·`Taxpayer`를
한 페이지에 몰아 갖는다. `Overtime`·`Bonus`·`Tax Return`은 **INCOME이 아니라 URLA에만**
등장한다는 점이 특히 역설적이다 — 소득 어휘가 소득 문서보다 신청서에 더 많다.

CREDIT 쪽 충돌은 `Employer`(2p)·`Employment`(2p)·`Social Security`(4p)로,
tradeline의 고용 정보·SSN 표기에서 온다.

---

## 10. 미관찰 하위군 어휘 (수집만 — 대조 대상 아님)

다음 패키지에 W-2 원본·1040·1099가 들어올 때를 대비해 blank에서 뽑은 식별자다.
전부 **정부 표준** 등급이다.

| 양식 | OMB 번호 | Catalog | 대표 문구 |
|---|---|---|---|
| W-2 | `OMB No. 1545-0029` | `Cat. No. 10134D` | (blank는 안내문 중심 — 아래 주의) |
| 1040 | `OMB No. 1545-0074` | `Cat. No. 11320B` | `U.S. Individual Income Tax Return`, `Department of the Treasury—Internal Revenue Service` |
| 4506-C | — | `Catalog Number 72627P` | `IVES Request for Transcript of Tax Return`, `Form 4506-C (Rev. 10-2022)` |
| 1099-MISC | `OMB No. 1545-0115` | `Cat. No. 14425J` | (안내문 중심) |
| 1099-NEC | `OMB No. 1545-0116` | `Cat. No. 72590N` | (안내문 중심) |

**주의 — blank 자체가 대조 준거로 약하다**: W-2·1099 blank의 1쪽은 실제 양식이
아니라 `Attention: ... Copy A ... for informational purposes only` 류 **안내문**이다.
실제 양식 문구는 뒤쪽 페이지에 있고, 그마저 **인쇄용 스캔 이미지**라 텍스트 추출이
제한된다. 즉 이 어휘 목록은 **참고 자료이지 검증된 신호가 아니다.**

VOE(Form 1005) 어휘는 확보 실패로 빠져 있다(§1).

---

## 11. UNCERTAIN

- **`Customer File Number` 도입 경위**: IRS FAQ 페이지 접속 실패(503)로 공식 확인
  불가. 데이터셋에 있고 2019년 전재 샘플에 없다는 관찰만 확정.
- **transcript 페이지의 `Internal Revenue Service` / `United States Department of
  the Treasury` 부재**: 준거 양쪽에 있으나 데이터셋 4장 모두 0건이다. p11·p26이
  이미지 2개씩을 갖고 있어 **이미지 레이어에 있을 가능성**이 있으나 판독하지 않았다
  (VLM 범위 밖). 제거된 것인지 이미지인지 미확정.
- **p31의 제품 동정**: §6-2 — 라벨은 TWN 샘플과 일치하나 제품명이 없고 발행 CRA가
  Experian 계열이다. The Work Number(Equifax) 여부 미확정.
- **p11 ↔ p38 짝**: 소거법 외 근거 없음 (§5).
- **P&L 페이지의 이미지 5개**: 항목명이 이미지에 있는지 미확인 (§8-2).
- **Corelogic 페이지의 벤더 준거**: 공개 제품 문서 미확인 (§7).
- **`Ref:` 라벨의 소속**: IRS가 아닌 것은 확정이나, Xactus 고유인지 IVES 참여
  벤더 공통 관행인지는 벤더 1곳 자료만으로 확정 불가.

---

## 12. 산출물

| 산출물 | 위치 | 커밋 |
|---|---|---|
| 이 보고서 | `docs/analysis/income_standard_analysis.md` | ✅ |
| 대조 스크립트 | `scripts/observe_income_diff.py` | ✅ |
| 출처·커밋 정책 | `data/reference/income/SOURCES.md` | ✅ |
| IRS 양식 blank 5종 + irs.gov 페이지 | `data/reference/income/irs/` | ✅ (미국 정부 저작물) |
| NASFAA transcript decoder | `data/reference/income/irs/transcripts/` | ❌ gitignore (© NASFAA) |
| Fannie Selling Guide 발췌 | `data/reference/income/vendors/` | ❌ gitignore (© Fannie Mae) |
| 대조 raw (9종 + 페이지별 7종) | `outputs/income_standard_diff/` | ❌ gitignore |
