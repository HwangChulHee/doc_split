# Handoff — CREDIT_REPORT 벤더 문서 확보 + 대조 분석 (완료 보고)

> 이 문서는 완료된 세션의 결과를 다음 세션에 전달하는 핸드오프다.
> 이 세션의 범위는 "자료 확보 + 대조 + 사실 보고"까지였다.
> **CREDIT 분류/그룹핑 로직과 정책 파일은 미작성이고, 전략도 미결정 상태다** —
> 이 문서에도 전략 판단은 없다.

## 0. 전제 상태 (이 세션 이전)

- 파싱 파이프라인: `uv run python -m docsplit.parse --data-dir data --out-dir outputs`
- URLA 파이프라인 구현 완료 (`docsplit.urla_pipeline`, V1–V4 전부 통과) — CREDIT은 미착수
- 선행 분석: `docs/analysis/urla_standard_analysis.md`, 관찰 보고서 `outputs/observation_report.md`(미커밋)
- 도메인 지식: `docs/domain_knowledge.md` — CREDIT 절에 벤더 사슬(bureau 3사 → reseller → 렌더)과
  조회 1건이 낳는 산출물 4종(본 리포트 / Score Disclosure / 소비자 편지 / 주문 요약)이 정리돼 있음

## 1. 이 세션에서 한 것

1. Xactus 공식 문서 9종 확보 (Reference Guide Form 1/2/3 + 파생 문서 6종)
2. 데이터셋 크레딧 계열 33페이지(pkg01 원본 18p + pkg02 15p)와 가이드 대조
   → VENDOR_DOC / CLIENT / FILLED / UNCERTAIN 4분류
3. Form 1/2/3 중 어느 레이아웃인지 판별
4. pkg01 ↔ pkg02 교차 확인

## 2. 준거 문서의 성격 — URLA와 결정적으로 다른 점 ★

| | URLA | CREDIT |
|---|---|---|
| 준거 | 양 GSE 발행 blank 양식 | 벤더(Xactus) 제품 문서 |
| 규범성 | "모든 URLA는 이래야 한다" (규범) | "우리 리포트는 이렇게 생겼다" (제품 설명) |
| 근거 등급 | **표준 검증** | **벤더 문서 검증** (한 단계 낮음) |
| 벤더 교체 시 | 문구 유지 기대 가능 | 보장 없음 |

이 구분은 분석 보고서에도 명시해 두었다. 두 등급을 같게 취급하면 안 된다.

## 3. 산출물 위치

| 산출물 | 위치 | 커밋 |
|---|---|---|
| 분석 보고서 (핵심) | `docs/analysis/credit_vendor_analysis.md` | ✅ |
| 확보 문서 + 출처 | `data/reference/credit/xactus/` (9 PDF + SOURCES.md) | ✅ |
| 대조 스크립트 | `scripts/observe_credit_diff.py` | ✅ |
| 대조 raw 결과 | `outputs/credit_vendor_diff/` | ❌ (데이터셋 원문 포함) |

커밋된 문서·스크립트에는 고객사명·차주 개인정보·대출번호가 **0건**임을 검사로 확인했다
(스크립트는 파일명 하드코딩 대신 glob 탐색 사용 — `urla_pipeline.py`와 같은 관례).

## 4. 핵심 사실

### 4-1. Form 판별 — Form 1 최적합, 단 단일 Form으로 환원 불가

배타 지표(가이드 3종 중 한 곳에만 등장하는 문구)로 판정:

| 지표 | 배타 소속 | 데이터셋 | 판정 |
|---|---|---|---|
| `Credit Summary` | Form 1 | ✅ | F1 지지 |
| `Manner of Payment` | Form 1 | ✅ 16p | F1 지지 |
| `File Summary` | Form 2 | ❌ | F2 반증 |
| `Report Summary` / `Footnotes` / `Open Date` | Form 3 | ❌ | F3 반증 |
| `Repository Files Returned` | Form 2 | ✅ | **혼재** |
| `Disputed Account` | Form 3 | ✅ | **혼재** |

요약 섹션 명칭이 결정적 근거다 — 세 가이드가 같은 영역을 각각 `Credit Summary` /
`File Summary` / `Report Summary`로 부르는데 데이터셋은 `Credit Summary`만 갖는다.
가이드 발행(2022–2023) 이후 제품이 개정됐을 가능성이 있다 (4-4 참조).

### 4-2. 헤더 요소 ↔ 가이드 항목 매핑

가이드 3종은 **항목 1–5(헤더)가 완전히 동일**하다. 데이터셋 헤더 요소의 대응:

- 가이드 문구 그대로 존재: `Report ID:`(항목 4), `Repositories:`(4), `Order Verifications`(5), `Requested By:`(2)
- 개념만 명세, 라벨 표기 상이: `Price:`(4), `Loan Number:`(2)
- **표기 자체가 다름**: `Client Code:` ↔ 가이드 `Customer Code` /
  `Ordered:` `Released:` `Reissued:` ↔ 가이드 `Date Ordered` `Date Released/Completed` `Date Reissued`
  → 가이드 원문 표기는 데이터셋에 **0건**
- **가이드 미언급**: `Originally Requested By:`, 푸터 `Page N of   Y`

### 4-3. tradeline 필드명이 본문 중간 페이지에 조밀하다

"신호 빈약 예상 지점"이던 tradeline 표 페이지에 Form 1 범례(항목 10, a–u) 필드명이
페이지당 20종 내외로 존재한다 — pkg01 p1–9(9p), pkg02 7p.
(`Manner of Payment`, `Months Reviewed`, `30-59`~`150+ Days Late` 5종, `Collateral`,
`Last Activity`, `Closed`, `Comment`, `Account Number`, `ECOA`, `Account Type`, `Terms` 등)

### 4-4. 가이드에 없는데 데이터셋에 있는 고정 문구

- **Trended Data 블록** (`Trended Data`+`Scheduled`+`Actual`+월 약어 `JAN`~`DEC`) — 13페이지.
  가이드 3종 미수록이나 **별도 how-to 문서가 2025-07자로 존재** → 가이드 이후 추가 기능으로 보임
- **bureau suffix `B1`** (`EQX-B1`/`EXP-B1`/`TUC-B1`) — 데이터셋은 전부 B1인데
  가이드는 `A1 = borrower, C1 = Co-borrower`만 설명하고 샘플도 A1만 사용
- `Originally Requested By:`, `Invoice` / `Reissue(Cross-customer)` / `Secondary Use Reissue`, `Payment (Min.)`

### 4-5. 법정 고지문 — 가이드 명세분 중 상당수가 데이터셋에 없음

| 고지문 | 가이드 | 데이터셋 |
|---|---|---|
| `THE REPORTING BUREAU CERTIFIES THAT` | ✅ F1 | ✅ pkg01 p9 / pkg02 p5 |
| `Consumer Financial Protection Bureau` | ✅ F1·F2 | ✅ p13 / p3 |
| `Notice to Home Loan Applicant` | ✅ 3종 | ✅ p12 / p1 |
| `End of Report` + Credit Repositories 3사 연락처 블록 | ✅ F1 | ✅ |
| Patriot Act §326 / OFAC 고지 | ✅ F1 | ❌ **양 패키지 0건** |
| MMCR 인증문 | ✅ F1·F2 | ❌ 0건 |
| FACT Act / Legislative Cost Recovery Fees | ✅ F1 | ❌ 0건 |

부재 원인은 확정 불가(제거 표식 없음) — UNCERTAIN으로 기록했다.
별건으로 pkg02엔 가이드에 없는 `FACTA: ADDRESS DISCREPANCY` 경고 2종이 있다(p9, p13).

### 4-6. pkg01 ↔ pkg02 교차

같은 Form, **헤더/푸터 라벨 세트 완전 동일(차이 0)**. 반복 라인 중 차이나는 것은
전부 값(금액·날짜·ID·차주명·브로커사명·채권자명·bureau suffix 조합)이다.

## 5. 관찰 보고서 정정 사항 ★

**pkg02 p31은 신용 리포트가 아니라 고용 검증(The Work Number) 조회 결과 페이지로 보인다.**
`twn_indicator_sample.pdf`(벤더 공식 샘플)와 라벨 구성이 일치한다 — 공통 라벨 8종
(`Client Name:`, `Ordered:`, `Address:`, `Address 2:`, `City, State, Zip:`, `Report ID:`,
`Loan Number:`, `End of Report`) + 데이터셋 쪽 `Employment Record Available: NO`.

기존 관찰 보고서(`outputs/observation_report.md`)는 이 페이지를 "주문 요약형 낱장"으로
기록했고, 이번 핸드오프의 대조 대상 페이지 목록에도 크레딧 계열로 포함돼 있었다.
**이 페이지의 유형 귀속은 재검토 대상이다** (INCOME 계열과 연결될 수 있음 —
도메인 문서 §4 "④ 제3자 검증"의 The Work Number 항목 참조).

## 6. 다음 세션 참고사항

- CREDIT 분류 정책(`policies/credit.yaml`)·프롬프트: **미작성**. 이번 범위 밖이었다
- 신호의 근거 등급을 URLA와 구분해 기록할 필요가 있다 (§2)
- 확보해 둔 파생 문서(Rescore·Supplement 팁, Consumer Copy·Adverse Action 안내)는
  도메인 문서가 예고한 "데이터셋에 없는 CREDIT 계열 문서" 확장 대비 자료다 — 이번엔 대조에 미사용
- 재현: `uv run python scripts/observe_credit_diff.py --out-dir outputs/credit_vendor_diff`
- 상세 근거: `docs/analysis/credit_vendor_analysis.md` (§1~§9) → `outputs/credit_vendor_diff/` (raw)
