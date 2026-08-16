# CREDIT_REPORT 벤더 문서 ↔ 데이터셋 대조 분석

작성일: 2026-08-16. 페이지 번호는 전부 **0-based**.
대조 raw 결과: `outputs/credit_vendor_diff/` (데이터셋 원문 포함 — 커밋 금지 영역).
대조 스크립트: `scripts/observe_credit_diff.py`.
확보 문서·출처: `data/reference/credit/xactus/SOURCES.md`.

> **근거 등급 주의**: 이 분석의 준거는 벤더(Xactus)의 **제품 문서**이지 규범 표준이 아니다.
> URLA 대조(`urla_standard_analysis.md`)의 근거는 양 GSE가 발행한 blank 양식으로
> "모든 URLA가 이래야 한다"는 규범이었으나, 벤더 가이드는 "우리 리포트는 이렇게 생겼다"는
> 제품 설명이다. 따라서 본 문서에서 확인된 항목은 **VENDOR_DOC(벤더 문서 검증)** 등급이며
> 표준 검증과 동일하게 취급하지 않는다.

이 문서는 사실 기록이다. 분류 전략 판단은 포함하지 않는다.
개인정보 값과 고객사 고유명은 기록하지 않는다(범주·역할로만 서술).

---

## 1. 확보한 문서

Reference Guide 3종(Form 1/2/3) + 파생 문서 6종, 총 **9개 전부 확보 성공, 실패 0**.
전부 정상 오픈·텍스트 추출 확인. 상세 URL·페이지 수·일자는 SOURCES.md 참조.

가이드 3종은 모두 **번호 범례(legend) 형식**이다 — 샘플 리포트 이미지 위에 번호를 얹고,
번호별로 해당 영역이 무엇인지 설명하는 구성. 따라서 "필드가 어디에 있는가"와
"필드명이 무엇인가"를 동시에 알려준다.

| 가이드 | 범례 항목 수 | 특징 |
|---|---|---|
| Form 1 | 1–14 (+ Credit History 하위 a–u) | **tradeline 필드 상세 범례 보유** (ECOA 코드, Account Type 코드, Manner of Payment 코드) |
| Form 2 | 1–18 | Credit Score Disclosure(17)·Risk based pricing(18) 항목 포함 |
| Form 3 | 1–17 | Collections·Disputed Account·Footnotes 항목 보유, tradeline 범례는 간략 |

세 가이드는 **항목 1–5(헤더)가 완전히 동일**하다: ① Company Name and Address
② Customer Code, Requested By, Loan Number ③ Date Ordered/Released·Completed/Reissued
④ Report ID number, Repositories, Price ⑤ Order Verifications.

## 2. Form 판별 결과

**결론: Form 1이 최적합이나, 어느 가이드와도 정확히 일치하지 않는다 (혼재).**

가이드 3종에 걸쳐 배타적으로 등장하는 지표만 골라 데이터셋 존재 여부를 확인:

| 지표 | 배타 소속 | 데이터셋 | 판정 |
|---|---|---|---|
| `Credit Summary` | **Form 1 전용** | ✅ pkg01 p0, pkg02 p13 | Form 1 지지 |
| `Manner of Payment` | **Form 1 전용** | ✅ 16개 페이지 | Form 1 지지 |
| `File Summary` | Form 2 전용 | ❌ 0건 | Form 2 반증 |
| `Whose` (tradeline 열) | Form 2·3 | ❌ 0건 | Form 2/3 반증 |
| `Report Summary` | Form 3 전용 | ❌ 0건 | Form 3 반증 |
| `Extensive borrower information` | Form 3 전용 | ❌ 0건 | Form 3 반증 |
| `Footnotes` / `Open Date` | Form 3 전용 | ❌ 0건 | Form 3 반증 |
| `Repository Files Returned` | **Form 2 전용** | ✅ pkg01 p10, pkg02 p9 | **혼재** |
| `Disputed Account` | **Form 3 전용** | ✅ pkg01 p1, pkg02 p7 | **혼재** |

**근거 요약:**

1. 요약 섹션 명칭이 결정적이다. 세 가이드는 같은 영역을 각각 `Credit Summary`(F1) /
   `File Summary`(F2) / `Report Summary`(F3)로 부르는데, 데이터셋은 **`Credit Summary`만** 갖는다.
2. tradeline 상세 필드 범례(a–u)는 Form 1 가이드에만 있고, 그 필드명 대부분이
   데이터셋 본문 페이지에서 실제로 추출된다(§6).
3. 그러나 Form 2 전용 `Repository Files Returned`와 Form 3 전용 `Disputed Account`가
   데이터셋에 존재한다 → **단일 Form으로 환원되지 않는다.**
4. Form 1 가이드에 있으나 데이터셋에 없는 것도 있다: `FICO Scores`(항목 7 제목),
   `Red Asterisk`(항목 t). 단 `FICO` 단어 자체는 데이터셋에 존재.

가이드 발행 시점(2022–2023)과 데이터셋 리포트 시점(2026) 차이를 고려하면
제품 개정에 따른 차이로 볼 여지가 있다 — 실제로 가이드 이후 추가된 기능이 데이터셋에 있다(§9).

## 3. VENDOR_DOC — 헤더 요소와 가이드 항목 매핑

관찰 보고서에서 확인된 헤더 요소를 가이드 범례 항목에 대응시킨 결과.
"가이드 문구 존재"는 가이드 텍스트에 해당 표기가 실제로 있는지를 뜻한다.

| 데이터셋 표기 | 가이드 항목 | 가이드 문구 존재 | pkg01 등장 | pkg02 등장 |
|---|---|---|---|---|
| `Report ID:` | 항목 4 (Report ID number) | ✅ Form 1 | 18/18 전 페이지 | 15/15 |
| `Repositories:` (+`TUC/EXP/EQX`) | 항목 4 (Repositories) | ✅ 3종 전부 | 12p (본 리포트) | 10p |
| `Order Verifications` | 항목 5 | ✅ 3종 전부 | 12p | 10p |
| `Requested By:` | 항목 2 (Requested By) | ✅ 3종 전부 | 12p | 11p |
| `Price:` | 항목 4 (Price) | 개념만 (콜론 라벨형 없음) | 12p | 10p |
| `Loan Number:` | 항목 2 (Loan Number) | 개념만 | 14p | 13p |
| `Client Code:` | 항목 2 (**Customer Code**) | ⚠️ **표기 상이** | 12p | 10p |
| `Ordered:` | 항목 3 (Date Ordered) | ⚠️ 표기 상이 | 12p | 11p |
| `Released:` | 항목 3 (Date Released/Completed) | ⚠️ 표기 상이 | 12p | 10p |
| `Reissued:` | 항목 3 (Date Reissued) | ⚠️ 표기 상이 | 12p | 10p |
| `Originally Requested By:` | — | ❌ **가이드 미언급** | 12p | 10p |
| 벤더 주소·전화 라인 | 항목 1 (Company Name and Address) | 개념만 (샘플은 타사 주소) | 12p | 10p |
| `Page N of   Y` | — | ❌ **가이드 미언급** (3종 모두 유사 표기 없음) | 11p | — |

**표기 상이 정리**: 가이드는 서술형 명칭(`Customer Code`, `Date Ordered`, `Date Released/Completed`)을
쓰고, 실제 리포트는 축약 라벨(`Client Code:`, `Ordered:`, `Released:`)을 인쇄한다.
가이드 원문 표기(`Customer Code`/`Date Ordered`/`Date Released`)는 데이터셋에 **0건**이다.

## 4. CLIENT / FILLED 범주

**CLIENT (렌더·브로커 관련 고정값 — 값 자체는 기록하지 않음)**

| 범주 | 성격 | 등장 |
|---|---|---|
| 렌더사명 + 주소 3줄 | 조회를 주문한 렌더. 가이드 항목 2/1의 채움값 | pkg01 14p, pkg02 다수 |
| 브로커사명 (`Originally Requested By:`의 값) | 최초 조회 주체. **패키지마다 다름** (pkg01·pkg02 서로 다른 회사) | 각 12p / 10p |
| Client Code 값 | 벤더가 렌더에 부여한 고객 코드 | 12p / 10p |
| Requested By 값 | 주문 담당 계정명 | 12p / 11p |

**FILLED (개별 조회 값 — 값 기록하지 않음)**

차주 성명, 주소, SSN, 3사 점수 3개, Report ID 값(8자리), Loan Number 값(9자리),
Ordered/Released/Reissued 날짜, tradeline 데이터(채권자명, 계좌번호, 금액, 개설·보고 일자),
inquiry 이력, 청구 금액.

## 5. 법정·준표준 고지문 목록

Form 1 가이드가 명세하는 고지문과 데이터셋 존재 여부:

| 고지문 | 가이드 | 데이터셋 pkg01 | pkg02 |
|---|---|---|---|
| Patriot Act §326 / OFAC 조회 고지 | ✅ Form 1 (항목 13 Fraud Messages 영역) | ❌ **부재** | ❌ 부재 |
| `Office of Foreign Asset Control` 명시 | ✅ Form 1 | ❌ 부재 | ❌ 부재 |
| MMCR 인증문 (`Merged Mortgage Credit Report`) | ✅ Form 1·2 | ❌ **부재** | ❌ 부재 |
| FACT Act / `Legislative Cost Recovery Fees` | ✅ Form 1 | ❌ 부재 | ❌ 부재 |
| `THE REPORTING BUREAU CERTIFIES THAT` (public records 인증) | ✅ Form 1 | ✅ p9 | ✅ p5 |
| `Consumer Financial Protection Bureau` 언급 | ✅ Form 1·2 | ✅ p13 | ✅ p3 |
| `Notice to Home Loan Applicant` (점수 고지) | ✅ 3종 전부 | ✅ p12 | ✅ p1 |
| `End of Report` | ✅ Form 1 | ✅ p11 | ✅ p9, p31 |
| Credit Repositories 연락처 블록 (3사 주소·전화) | ✅ Form 1 | ✅ p11 | ✅ p9 |

**주목**: 가이드가 명세하는 법정 고지문 중 **OFAC/Patriot Act·MMCR·FACT Act 문단이
데이터셋에는 전혀 없다**. 익명화 과정에서 제거된 흔적(`[ ... removed ... ]` 류)도 없으므로,
추출 실패나 마스킹이 아니라 이 리포트 구성에 애초에 포함되지 않았을 가능성이 있다.
(단정 불가 — §8 UNCERTAIN)

한편 pkg02에는 가이드에 없는 다른 법정 성격 문구가 있다:
`FACTA: ADDRESS DISCREPANCY` 계열 경고 2종 (p9, p13).

## 6. tradeline 필드명 추출 가능성

Form 1 가이드 항목 10(a–u)이 명세하는 tradeline 필드명이 데이터셋 본문 페이지에서
실제로 추출되는지 확인한 결과 — **대부분 추출된다.**

| 필드명 | 가이드 | pkg01 등장 페이지 | pkg02 등장 페이지 |
|---|---|---|---|
| `Manner of Payment` | F1 전용 | 1–9 (9p) | 5, 20, 27, 33, 37, 40, 43 |
| `Months Reviewed` | F1·F2 | 1–9, 15 | 동 7p |
| `30-59 Days Late` ~ `150+ Days Late` (5종) | F1 전용 | 1–9 | 동 7p |
| `Collateral` | F1 전용 | 1–9 | 동 7p |
| `Last Activity` / `Closed` | F1 전용 | 1–9 | 동 7p |
| `Comment` | F1 전용 | 4–10, 15 | 5, 9, 13, 20, 27, 33, 40, 43 |
| `Account Number` / `ECOA` / `Account Type` / `Terms` | 3종 또는 F1·F2 | 1–9 | 동 7p |
| `Credit Limit` / `High Credit` / `Past Due` / `Payment` / `Balance` | 3종 | 1–9 (+요약 페이지) | 다수 |
| `Reported On` | F1·F2 | 1–9 등 | 다수 |

**즉, "신호가 빈약할 것으로 예상되던 본문 중간 페이지(tradeline 표)"에 오히려
가이드 명세 필드명이 페이지당 20종 내외로 조밀하게 존재한다.**
pkg01 p1–9(9페이지), pkg02 7페이지가 이에 해당한다.

## 7. pkg01 ↔ pkg02 교차 확인

**같은 Form, 같은 헤더 세트다.**

- 본 리포트 페이지(벤더 헤더 보유): pkg01 12p(p0–11), pkg02 10p(p5,7,9,13,20,27,33,37,40,43)
- 두 패키지의 **반복 라인(≥80% 페이지) 중 라벨·문구 성격은 전부 일치** —
  `report id:`, `repositories: tuc/exp/eqx`, `price:`, `client code:`, `loan number:`,
  `ordered:`, `released:`, `reissued:`, `requested by:`, `originally requested by:`,
  `order verifications`, 벤더 주소·전화, tradeline 필드명 전체, `trended data`,
  `scheduled`, `actual`, 월 약어 12종 — **차이 0**
- 차이나는 반복 라인은 **전부 값**: 금액, 날짜, ID 값, 차주명, 브로커사명,
  bureau suffix 조합(pkg01 `EXP-B1` 단독 반복 vs pkg02 `TUC-B1, EXP-B1,` 조합), 채권자명

## 8. UNCERTAIN

- **OFAC/MMCR/FACT Act 문단 부재의 원인**: 리포트 구성에서 원래 빠진 것인지, 데이터 가공 과정에서
  제거된 것인지 데이터만으로는 확정 불가. (제거 표식은 없음)
- **`Collections`**: Form 1·3 양쪽에 등장하는 단어라 배타 지표가 못 됨. 데이터셋에서는
  요약 표의 항목명으로 보이나 섹션 제목인지 표 라벨인지 라인 단위로는 불확정.
- **`Individual` / `Joint`**: ECOA 코드 설명(가이드 항목 b)의 값 명칭이면서 tradeline 표의
  출력값이기도 함 — 라벨인지 값인지 구분 불가.
- **`Reported`**: 가이드 항목 f(보고 일자)와 요약 표의 다른 용례가 혼재.
- **`Payment (Min.)`**: 가이드 미수록. `Payment`(항목 o)의 변형 표기로 보이나 확정 불가.

## 9. 가이드에 없는데 데이터셋에 있는 고정 문구 (강조)

값이 아니라 **고정 문구/구조**인데 가이드 3종 어디에도 없는 것들:

| 항목 | 데이터셋 등장 | 비고 |
|---|---|---|
| **Trended Data 블록** — `Trended Data` + `Scheduled` + `Actual` + 월 약어 `JAN`~`DEC` | pkg01 p1–9, pkg02 4p | 가이드 3종 전부 미수록. **별도 how-to 문서가 2025-07자로 존재**(`how_to_view_trended_data.pdf`) → 가이드 발행(2022–23) 이후 추가된 기능으로 보임 |
| **bureau suffix `B1`** (`EQX-B1`, `EXP-B1`, `TUC-B1`) | pkg01 다수, pkg02 다수 | 가이드는 `A1 = borrower, C1 = Co-borrower`만 설명하고 샘플도 `A1`만 사용. **`B1`은 미설명** |
| `Originally Requested By:` | pkg01 12p, pkg02 10p | 재발행(reissue) 경로 표기. 가이드 항목 2에 없음 |
| `Invoice` / `Reissue(Cross-customer)` / `Secondary Use Reissue` | pkg01 p11 | 청구 내역 블록. 가이드 미수록 |
| `Page N of   Y` (푸터) | pkg01 p1–11 | 가이드 3종에 페이지 표기 언급 자체가 없음 |
| `Payment (Min.)` | pkg01 p2, p3 | §8 참조 |

**추가 발견 — pkg02 p31의 정체**: 관찰 보고서에서 "주문 요약형 낱장"으로 기록했던 페이지가
`twn_indicator_sample.pdf`(The Work Number Indicator 샘플)와 라벨 구성이 일치한다.
공통 라벨 8종(`Client Name:`, `Ordered:`, `Address:`, `Address 2:`, `City, State, Zip:`,
`Report ID:`, `Loan Number:`, `End of Report`)이 동일하고, 데이터셋 쪽에는
`Employment Record Available: NO`가 있다. 즉 이 페이지는 신용 리포트가 아니라
**고용 검증(The Work Number) 조회 결과 표시 페이지**로 보인다. 핸드오프가 제시한
"크레딧 계열 페이지" 목록에 포함되어 있던 페이지다.
