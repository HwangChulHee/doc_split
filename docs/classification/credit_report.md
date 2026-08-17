# CREDIT_REPORT 분류·그룹핑 기준서

> **위치**: `docs/classification/credit_report.md`
> **성격**: 설계 확정 문서. 구현은 이 문서를 명세로 삼는다.
> **근거 문서**: `docs/domain_knowledge.md`, `docs/analysis/credit_vendor_analysis.md`
> **선행 문서**: `docs/classification/urla.md` — 파이프라인 골격·결합 규칙·검증 철학은
> URLA 기준서를 따른다. 이 문서는 CREDIT 고유 사항만 규정한다.

---

## 1. 이 유형의 특수성 (URLA와 무엇이 다른가)

| | URLA | CREDIT |
|---|---|---|
| 준거 문서 | GSE blank = **규범** ("이래야 한다") | 벤더 Reference Guide = **제품 설명서** ("우리 건 이렇다") |
| 근거 등급 | 표준 검증 | **벤더 문서 검증** (한 단계 약함) |
| 신호 분포 | 푸터 1세트가 전 페이지 커버 | **페이지 부위별로 신호가 다름** |
| 문구 일치 | blank 문구를 그대로 채택 가능 | 가이드는 서술형 명칭, 실물은 축약 라벨 → 그대로 못 씀 |

분석에서 확인된 사실 세 가지가 설계를 규정한다:

1. **실물은 커스터마이즈 결과다.** 데이터셋 리포트는 가이드의 Form 1/2/3 어느
   하나와도 일치하지 않고 요소가 혼재한다. → 특정 Form의 문구 세트를 통짜로
   규칙화할 수 없다. **개별 문구 단위 가점**만 허용.
2. **준거 문서가 실물보다 낡을 수 있다.** Trended Data 관련 문구는 가이드
   3종 어디에도 없으나 실물 13페이지에 존재(가이드 2022–23 발행, 해당 기능
   2025 문서에 별도 수록). → 가이드 부재는 신호 배제 사유가 아니다.
3. **가이드는 완전하지 않다.** bureau suffix `B1`은 실물 전반에 쓰이나 가이드는
   `A1`/`C1`만 설명한다. → 가이드를 신호의 상한으로 두지 않는다.

---

## 2. 신호 계층 모델 (이 문서가 도입, 이후 유형에 공통 적용)

모든 신호는 **출처 계층**을 갖는다. 계층은 신호의 수명과 적용 범위를 규정한다.

| 계층 | 정의 | 수명·범위 | 규칙 채택 |
|---|---|---|---|
| **normative** | 법·정부기관·표준협회가 요구 | 매우 김. 벤더·고객사 불문 | ✅ |
| **domain** | 업계 구조상 필연 | 김. 업계 불변 동안 | ✅ |
| **vendor** | 특정 벤더 제품 명세 | 벤더 단위 | ✅ **단, 분리 레이어** |
| **deployment** | 고객사 설정·조판·인쇄 | 없음 | ❌ 그룹핑 재료로만 |

**설계 규칙**

- 계층 1–3만 분류 규칙에 채택한다.
- 계층 3(vendor)은 정책 파일에서 **물리적으로 분리**한다. 벤더 추가 =
  블록 추가이며 엔진과 universal 섹션은 수정하지 않는다.
- 계층 4(deployment)는 규칙에 넣지 않는다. 신호 카드에만 담아 그룹핑에 쓴다.
- 모든 신호 정의에 `layer` 를 명시한다. "왜 이 규칙인가"의 답이 여기 있다.

---

## 3. 신호 정의

### 3-1. universal — 벤더 독립 (계층 normative/domain)

**결정적**

| ID | 신호 | layer | 근거 |
|---|---|---|---|
| U-D1 | bureau 3사 정식명 동시 등장 (Equifax + Experian + TransUnion) | domain | 3사를 나란히 언급하는 문서는 tri-merge 신용보고서뿐. 벤더 자체 설명("3사 리포트를 제공하며 자체 DB는 없음")이 방증 |

**지지적**

| ID | 신호 | layer | 근거 |
|---|---|---|---|
| U-S1 | 법정 고지문: `Notice to Home Loan Applicant`, `Consumer Financial Protection Bureau`, `THE REPORTING BUREAU CERTIFIES THAT` | normative | FCRA 계열 요구 고지. 가이드 명세 + 데이터셋 존재 확인. **벤더 독립성이 가장 높은 신호군** |
| U-S2 | 신용 어휘: `FICO`, `Credit Score`, `Credit Report`, `Credit Summary` | domain | 업계 통용 |
| U-S3 | Trended Data 계열: `Trended Data` + (`Scheduled` / `Actual`) | domain | bureau 제공 업계 표준 데이터 상품. 가이드 미수록이나 업계 통용 |
| U-S4 | bureau 약어 조합: `TUC` + `EXP` + `EQX` (접미 무시) | domain | 접미(`-B1` 등)는 조판이므로 약어만 매칭 |

### 3-2. vendors — 벤더별 레이어 (계층 vendor)

각 벤더 블록은 `identity`(이 벤더 산출물임을 증명) + `decisive` + `supportive`
+ `subtypes`(그 벤더의 패키지 구성)로 구성한다.

**vendor: xactus**

| 구분 | ID | 신호 | 근거 |
|---|---|---|---|
| identity | — | `XACTUS`, 벤더 주소 라인 | 이 벤더는 신용조회 산출물만 발행 |
| 결정적 | X-D1 | tradeline 필드명 **3종 이상** 동시: `Manner of Payment`, `Months Reviewed`, `30-59 Days Late`(및 60-89/90-119/120-149/150+ 계열), `ECOA`, `High Credit`, `Credit Limit`, `Past Due`, `Reported On`, `Last Activity`, `Account Type`, `Collateral` | Form 1 가이드 명세 필드. **단독 단어는 타 문서에도 출현하므로 조합 조건 필수** |
| 지지적 | X-S1 | `Report ID:` | 가이드 항목 4 명세 |
| 지지적 | X-S2 | `Repositories:` 라인 | 가이드 항목 4 명세 |
| 지지적 | X-S3 | `Order Verifications`, `Requested By:` | 가이드 명세 |

**표기 주의**: 가이드는 서술형(`Customer Code`, `Date Ordered`), 실물은 축약
(`Client Code:`, `Ordered:`)을 인쇄한다. **실물 표기를 채택**하되 근거란에
가이드 대응 항목을 병기한다.

### 3-3. subtypes (패키지 구성 판별)

벤더 패키지 구성은 벤더 블록에 둔다. xactus 기준:

| subtype | 판별 신호 | 비고 |
|---|---|---|
| `main_report` | X-D1 성립 (tradeline 조밀) 또는 U-D1 + 헤더 세트 | 본체 |
| `score_disclosure` | `Credit Score Disclosure` 제목 | **렌더 레터헤드**임에 유의 — 발행 주체가 벤더가 아님 |
| `consumer_letter` | `Dear Consumer:` + 벤더 identity | 소비자 안내 |
| `order_summary` | 주문 요약 라벨군 (`Client Name:`, `Ordered:` 중심, tradeline 부재) | pkg02에서만 관찰 |

출력 유형은 `CREDIT_REPORT` 로 통합, subtype은 내부 기록.

### 3-4. 규칙 미채택 신호 (계층 deployment — 카드 재료)

| 신호 | 배제 근거 |
|---|---|
| `Page N of   Y` | 가이드 미명세. 조판 산물 (URLA와 동일 결론) |
| `Originally Requested By:` | 가이드 미명세. 벤더 조판 |
| 고객사명, 브로커사명, `Client Code` 값 | 배포 고유 |
| `Report ID` **값**, `Loan Number` 값 | 입력값 — 단, 그룹핑 앵커로 최우선 |

---

## 4. 판정 규칙

### 4-1. 결합 (URLA와 동일 임계값 — 조정 대상 아님)

```text
universal.decisive ≥ 1                            → RULE_HIGH
벤더 identity 성립 AND 해당 벤더 decisive ≥ 1        → RULE_HIGH
서로 다른 supportive ID ≥ 2 (universal + 벤더 합산)  → RULE_MEDIUM
서로 다른 supportive ID = 1                        → DEFER_LLM
신호 0                                            → NO_SIGNAL
텍스트 없음                                        → DEFER_VLM
```

- 같은 ID 반복은 1개로 센다.
- 벤더 decisive는 **identity 성립을 전제**한다. identity 없이 tradeline
  필드명만 있는 경우는 supportive 1개로 취급한다 (다른 벤더 리포트일 수 있으므로
  DEFER_LLM 경로가 옳다).
- 매칭 전처리는 URLA와 동일 (NFKC → 특수문자 통일 → 공백 축약 → 소문자화,
  정확→부분문자열→근사 0.90).

### 4-2. 유형 간 경합

CREDIT 신호와 타 유형 신호가 동시 성립하는 페이지가 나올 수 있다
(예: URLA Lender Loan Info에 신용 관련 어휘). 처리 원칙:

1. 각 유형 정책을 독립 평가한다.
2. 두 유형 모두 RULE_HIGH → **경합으로 표시하고 LLM에 이관**한다. 임의 우선순위를
   두지 않는다.
3. 한쪽만 RULE_HIGH → 그쪽으로 확정.

### 4-3. 라벨링 정책 (확정)

부속 문서 3종(`score_disclosure`, `consumer_letter`, `order_summary`)은
모두 `CREDIT_REPORT` 로 라벨한다.

근거: 벤더 Reference Guide가 이 문서들을 신용조회 산출물 패키지의 구성으로
명세한다. 즉 한 파일에 함께 있던 것은 우연이 아니라 제품 구성이다.
`score_disclosure`가 렌더 레터헤드를 쓰는 것은 법정 고지 의무 주체가 렌더이기
때문이며, 문서의 소속을 바꾸지 않는다.

**보류 항목**: pkg02 p31은 The Work Number(고용 검증) 조회 결과로 판명되었다.
기능 기준으로는 INCOME_DOC 후보다. **INCOME 설계 시 결정**하며, 그때까지
CREDIT 규칙은 이 페이지를 강제로 잡지 않는다 (벤더 identity로 걸릴 수 있으므로
subtype 판별에서 tradeline·고지문 부재를 확인해 `order_summary` 로 오분류하지
않도록 주의).

---

## 5. 신호 카드 (그룹핑 재료)

URLA와 동일 철학: **추출기는 확정하지 않고 후보를 수집한다.**

CREDIT 카드 스키마 (URLA 카드에 더해):

| 필드 | 내용 | 비고 |
|---|---|---|
| `report_id_candidates` | `Report ID:` 값 | **최강 앵커** — 관찰상 18/18 전 페이지 존재 |
| `loan_number_candidates` | 대출번호 | 패키지 관통 신호 |
| `client_code_candidates` | Client Code 값 | 배포 계층이나 그룹핑엔 유효 |
| `date_candidates` | Ordered / Released / Reissued / 편지 날짜 | 재조회 구분 재료 |
| `page_marker_candidates` | `Page N of Y` | 경보 전용 (URLA와 동일) |
| `vendor_identity` | 매칭된 벤더 키 | 다중 벤더 혼입 시 분리 근거 |
| `subtype` | 판별 결과 | |
| `name_candidates` | Applicant 표기 | 페이지별 존재 편차 큼 |

---

## 6. 그룹핑·순서 (LLM 위임)

프롬프트: `llm/prompts/group_credit.md`

### 6-1. 그룹핑 지시 요지

```text
1. 기대값: 신용조회 1건당 산출물 패키지 1세트. 단, 재조회(Refresh/LQI)나
   Supplement로 같은 유형이 복수 존재할 수 있다.
2. 신호 역할:
   - Report ID 값 일치 = 주력 그룹핑 근거 (URLA에서 이름이 하던 역할)
   - 대출번호·Client Code = 보조 앵커
   - 날짜(Ordered/Released/Reissued) 상이 = 재조회 분리 근거
   - 벤더 identity 상이 = 다른 조회건
   - 페이지 표기 = 경보 전용 (같은 번호 중복 시 다중 instance 의심)
3. 부속 문서(disclosure/letter/order_summary)는 본체와 같은 instance로 묶되,
   Report ID가 다르면 분리하라.
4. evidence 필수. 확신 없으면 UNRESOLVED.
```

### 6-2. 순서 정렬

```text
경로 A (코드): page_marker가 1..Y 무결 → 정렬
경로 B (코드): 마커 불완전 → subtype 순서로 정렬
               main_report → score_disclosure → consumer_letter → order_summary
               (근거: 데이터셋 관찰 순서 및 패키지 논리. **관찰 기반 폴백이며
                URLA의 섹션 순서 폴백과 달리 표준 보장이 없음** — 문서화 필수)
경로 C: 판별 불가 → 순서 UNRESOLVED
```

**주의**: main_report 내부의 페이지 순서는 마커 없이는 복원이 어렵다.
`End of Report` 는 마지막 페이지 힌트로만 쓴다.

---

## 7. 검증 (튜닝 금지 — URLA §7과 동일 철학)

pkg01 GT 기준. 실패 시 임계값 조정이 아니라 **등급 재판정 또는 사실 보고**.

| # | 검증 | 기준 |
|---|---|---|
| C-V1 | pkg01 CREDIT 18p 전부 RULE_HIGH/MEDIUM 도달 | 18/18 |
| C-V2 | 비-CREDIT 페이지에서 결정적 신호(U-D1, X-D1) 오발 | 0 |
| C-V3 | 비-CREDIT 페이지에서 supportive ≥ 2 동시 성립 | 0 |
| C-V4 | pkg01 CREDIT이 1 instance로 묶이고 GT source_page 순서와 일치 | 일치 |
| C-V5 | **universal만으로** pkg01 CREDIT 몇 페이지가 잡히는가 (벤더 레이어 제외) | 측정만 — 벤더 독립 커버리지 지표. 합격 기준 없음 |

C-V5는 통과/실패가 아니라 **측정 항목**이다. "다른 벤더 리포트가 왔을 때
최소 몇 %가 규칙으로 잡히는가"의 대리 지표이며, 결과를 리포트에 기록한다.

---

## 8. 알려진 한계

1. **벤더 레이어는 xactus만 등록됨.** 다른 벤더(CoreLogic Credco, Factual Data
   등) 리포트는 universal 신호로만 판정되며 커버리지가 낮아질 수 있다.
   C-V5가 그 정도를 측정한다.
2. **가이드 미명세 신호 존재.** Trended Data, `B1` suffix 등. 가이드를 신호의
   상한으로 두지 않았으나, 반대로 가이드에 있는데 실물에 없는 항목
   (Patriot Act/OFAC 고지, MMCR 인증문 등)의 부재 원인은 미상(UNCERTAIN)이다.
   커스터마이즈·익명화·조건부 출력 중 어느 것인지 확정하지 못했다.
3. **subtype 순서 폴백은 표준 근거가 없다.** URLA의 섹션 순서와 등급이 다르다.
4. **본체 내부 순서는 마커 의존.** 마커 없는 렌더링에서는 순서 UNRESOLVED가
   대량 발생할 수 있다.
5. **TWN 페이지 소속 미결.** §4-3 보류 항목.

---

## 9. 정책 파일 스키마 (구현 지침)

```yaml
type: CREDIT_REPORT

universal:
  decisive:
    U-D1:
      layer: domain
      require_all: ["Equifax", "Experian", "TransUnion"]
  supportive:
    U-S1: {layer: normative, phrases: [...]}
    U-S2: {layer: domain, phrases: [...]}
    U-S3: {layer: domain, require_all_any: [...]}   # Trended Data + (Scheduled|Actual)
    U-S4: {layer: domain, require_all: ["TUC", "EXP", "EQX"]}

vendors:
  xactus:
    identity: {layer: vendor, phrases: ["XACTUS", "..."]}
    decisive:
      X-D1: {layer: vendor, min_matches: 3, phrases: [...]}
    supportive:
      X-S1: {...}
    subtypes:
      score_disclosure: {phrases: ["Credit Score Disclosure"]}
      consumer_letter:  {phrases: ["Dear Consumer:"]}
      order_summary:    {phrases: [...], require_absent: [...]}
      main_report:      {via: X-D1}

combine:
  decisive_min: 1
  supportive_min: 2
  vendor_decisive_requires_identity: true

cards:
  report_id_pattern: '...'
  # ... (§5)

ordering:
  subtype_order: [main_report, score_disclosure, consumer_letter, order_summary]
```

엔진 요구사항:

- `universal` → `vendors` 순회 → 결합. 벤더 블록 추가만으로 신규 벤더 지원.
- 신호 매칭 결과에 `layer` 를 함께 기록한다 (리포트에서 계층별 기여도 확인용).
- URLA 정책은 이 스키마로 **마이그레이션하지 않는다** — 단일 벤더 개념이 없는
  유형이므로 `universal` 만 갖는 형태로 호환되면 충분하다. 엔진은 `vendors`
  섹션 부재를 정상으로 처리해야 한다.
