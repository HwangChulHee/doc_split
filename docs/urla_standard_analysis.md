# URLA 표준 양식 ↔ 데이터셋 대조 분석

작성일: 2026-08-15. 페이지 번호는 전부 0-based.
대조 raw 결과: `outputs/urla_standard_diff/` (데이터셋 원문 포함 — 커밋 금지 영역).
대조 스크립트: `scripts/observe_urla_diff.py` (라인 정규화: NFKC, `•`→`·`, em/en dash→`-`, 공백 축약, 소문자).

이 문서는 사실 기록이다. 분류 전략에 대한 판단은 포함하지 않는다.
차주 개인정보 값은 포함하지 않는다 (라벨/고정 문구만 인용).

---

## 1. 확보한 공식 양식

출처: Freddie Mac ULAD 페이지 (Fannie Mae는 Cloudflare 403으로 접근 불가 → 핸드오프 명시 대안 사용).
상세 URL·일자: `data/reference/urla/SOURCES.md`.

| 파일 | 컴포넌트 | 페이지 | 버전 표기 (푸터) |
|---|---|---|---|
| `urla_borrower_information_blank.pdf` | URLA 본체 (Section 1–9) | 9p | `Freddie Mac Form 65  •  Fannie Mae Form 1003` + `Effective 1/2021` |
| `urla_additional_borrower_blank.pdf` | Additional Borrower | 4p | 동일 |
| `urla_unmarried_addendum_blank.pdf` | Unmarried Addendum | 1p | 동일 |
| `urla_lender_loan_information_blank.pdf` | Lender Loan Information (L1–L4) | 2p | 동일 |
| `urla_continuation_sheet_blank.pdf` | Continuation Sheet | 1p | 동일 |
| `urla_instructions.pdf` | 작성 지침 (참고) | 15p | `Effective 1/2021` |
| `scif_form_1103_blank.pdf` | SCIF Form 1103 (참고) | 1p | `Fannie Mae/Freddie Mac Form 1103` + `5/2022` |

무결성: 7개 전부 정상 오픈·텍스트 추출 가능. URLA 컴포넌트 5종 모두 `Effective 1/2021` 확인 — 데이터셋과 동일 버전.

## 2. 데이터셋 페이지 ↔ 공식 컴포넌트 매핑

| pkg01 원본 p | pkg02 shuffled p | 공식 컴포넌트 | blank 페이지 | 내용 |
|---|---|---|---|---|
| 0 | 19 | Borrower Information | p0–1 | Section 1 (차주 정보) |
| 1 | 34 | Borrower Information | p2 | Section 2 (자산/부채) |
| 2 | 12 | Borrower Information | p3 + p4 | Section 3 + 4 (부동산/대출) |
| 3 | 15 | Borrower Information | p5 | Section 5 (Declarations) |
| 4 | 42 | Borrower Information | p6 | Section 6 (Acknowledgments) |
| 5 | 17 | Borrower Information | p7 | Section 7 + 8 (군복무/인구통계) |
| 6 | 22 | Borrower Information | p8 | Section 9 (Loan Originator) |
| 7 | 28 | Unmarried Addendum | p0 | 전체 |
| 8 | (없음) | Continuation Sheet | p0 | 전체 (pkg02에는 이 컴포넌트 없음) |
| 9 | 24 | Lender Loan Information | p0 | L1–L3 |
| 10 | 36 | Lender Loan Information | p1 | L4 |

- **페이지 분할이 다르다**: 공식 blank 본체는 9페이지 구성이지만 데이터셋 렌더러는 7페이지로 압축 (Section 1을 1페이지로, Section 3+4를 한 페이지로). 페이지 경계는 렌더러 재량임이 실증됨.
- Additional Borrower 컴포넌트는 두 패키지 모두 미사용 (단일 차주).
- pkg02 URLA에는 Continuation Sheet가 없어 총 10페이지 (`N of 10`), pkg01은 11페이지 (`N of 11`).

## 3. STANDARD로 확인된 문구 (공식 blank에 존재 + 데이터셋에 존재)

라인 수 기준, 데이터셋 URLA 21페이지 텍스트의 대다수(페이지당 STANDARD+STANDARD~ 비율 약 70–95%)가 표준 문구였다. 핵심만 발췌:

**푸터 (본체·모든 컴포넌트 공통, blank에서도 하단 위치 확인):**

| 문구 | 공식 위치 |
|---|---|
| `Uniform Residential Loan Application` | 전 컴포넌트 푸터 (컴포넌트별 접미: `— Unmarried Addendum`, `— Continuation Sheet`, `— Lender Loan Information`, `— Additional Borrower`) |
| `Freddie Mac Form 65  •  Fannie Mae Form 1003` | 전 컴포넌트 푸터 (표기 차이는 §7 참조) |
| `Effective 1/2021` | 전 컴포넌트 푸터 |
| `Borrower Name:` | 본체 p1–8 푸터 (blank도 하단 y≈718/792) |

**상단 식별 블록 (본체 p0, Unmarried Addendum, Lender Loan Info, SCIF 공통):**
`To be completed by the Lender:` / `Lender Loan No./Universal Loan Identifier` / `Agency Case No.` — 데이터셋과 완전 일치.

**섹션 제목 (본체, 본문 위치):** `Section 1: Borrower Information.` ~ `Section 9: Loan Originator Information.` 및 각 제목 뒤 설명 문장, 하위 항목 라벨(`1a. Personal Information`, `1b. Current Employment/Self-Employment and Income` 등) — 데이터셋과 일치 (Section 6 철자 예외는 §8 참조).

**Lender Loan Information 섹션 제목:** `L1. Property and Loan Information`, `L2. Title Information`, `L3. Mortgage Loan Information`, `L4. Qualifying the Borrower – Minimum Required Funds …` — 데이터셋 해당 페이지(pkg01 p9–10)와 일치.

**고정 안내문:** Section 6의 법적 고지 본문(데이터셋에서 43라인이 줄바꿈 위치만 다른 STANDARD~로 매칭), Section 7/8의 선택지 라벨(`Currently serving on active duty …` 등), Continuation Sheet의 `Use this continuation sheet if you need more space …` 등.

## 4. RENDERER로 판정된 항목

| 항목 | 등장 | 근거 |
|---|---|---|
| `GURLA20S`, `GURLA20_S`, `(POD)`, `0718` | 데이터셋 URLA 전 21페이지 푸터 | 공식 blank 어디에도 없음. 값 아님 (인쇄/폼 코드) |
| 페이지 번호 `N of 11` / `N of 10` | 데이터셋 전 페이지 푸터 | **공식 blank에는 페이지 번호 표기가 아예 없음.** 분모는 패키지 구성(Continuation Sheet 유무)에 따라 11/10으로 변동 — 렌더러가 조립 후 부여 |
| 페이지 분할 (본체 9p→7p) | 전체 | blank와 데이터셋의 섹션↔페이지 대응이 다름 (§2) |
| California Civil Code 1812.30(j) 고지 문구 | pkg01 p8 (Continuation Sheet) | GSE blank에 없는 주(州)별 고정 문구. 입력값이 아닌 템플릿 삽입 텍스트 |

참고(외부 사례, 핸드오프 제공 정보): 타 렌더러(Calyx)는 같은 자리에 `Calyx Form - URLA_1.frm (04/2020)` 형태의 자체 코드를 찍는다. 본 데이터셋의 `GURLA20S` 계열이 그 자리에 해당.

## 5. FILLED 항목 (범주만)

- 차주 성명 (전 페이지 푸터 `Borrower Name:` 값 + 서명란) — 페이지당 1회 이상
- 주소 요소: 도시/주/우편번호/카운티 라인, 거리 주소 (패키지당 4~8건)
- 연락처: 전화번호, 이메일 (패키지당 각 1~3건)
- 고용주명·직위·근무 시작일, 고용주 주소
- 금액·비율 값: 자산/부채 금액, Note Rate, Loan Term 등
- 채권자/기관 약칭 (자산·부채 표의 기관명 다수)
- 서명 타임스탬프: `MM/DD/YYYY H:MM AM/PM TZ` 형식 (차주 서명, originator 서명)
- ULI(30자 영숫자, 끝 9자리가 대출번호와 중복) 및 대출번호
- Loan Originator 조직/개인 정보 (조직명, NMLS류 번호, 주소, 이메일, 전화)

## 6. UNCERTAIN 목록

- **라벨+값 융합 라인**: `Loan Term360`, `Note Rate 6.250`, `Position or Title …` 등 — 라벨은 STANDARD, 값은 FILLED이나 추출 라인 단위에서는 분리 불가 (렌더러의 텍스트 레이어 구성 산물)
- **슬래시 결합 라벨**: `Balloon / Balloon Term`, `Interest Only / Interest Only Term`, `Prepayment Penalty / Prepayment Penalty Term`, `Temporary Interest Rate Buydown / Initial Buydown Rate` (pkg01 p9, pkg02 p24) — blank에서는 다른 라인 구성으로 존재. 표준 라벨의 렌더러별 조판 차이로 보이나 라인 단위 매칭 불가
- `Country US`, `Housing`, `Revolving`, `Retained`, `Funds`, `Checking Account`, `Cash Gift`, `Relative`, `Other (specify)` 등 — blank의 선택지/열거값과 대응하는 것으로 보이는 짧은 라인. 선택지(표준 어휘)인지 입력값인지 라인만으로는 확정 불가
- `Date` 단독 라인 (서명란 인근) — blank는 `Date (mm/dd/yyyy)` 형식. 렌더러 생략인지 값 라벨인지 불확정

## 7. 렌더러 간 표기 차이 (같은 표준 문구의 다른 표기)

| 항목 | 공식 blank | 데이터셋 |
|---|---|---|
| Form 65/1003 구분자 | `Freddie Mac Form 65  •  Fannie Mae Form 1003` — U+2022 BULLET, 앞뒤 공백 2칸 | `Freddie Mac Form 65 · Fannie Mae Form 1003` — U+00B7 MIDDLE DOT, 공백 1칸 |
| Section 6 제목 철자 | 본체 blank: `Acknowledgments` / Additional Borrower blank: `Acknowledgements` | `Acknowledgements` (e 포함) |
| 줄바꿈 위치 | Section 6 법적 고지 등 장문 단락 | 동일 문장이 다른 위치에서 줄바꿈 (데이터셋 21페이지에서 STANDARD~ 판정 총 170라인 — 줄바꿈 재조합·근사 일치 포함) |
| 라벨 조판 | `Home Phone (___) …` 처럼 괄호가 라벨 라인에 포함 | `Home Phone` + 값 별도 라인 |
| 선택지 안내 목록 | Section 1e에 income source 열거 목록(`· Alimony` ~ `· VA Compensation` 16종), Section 2에 liability 유형 목록 존재 | **해당 안내 목록 텍스트가 데이터셋에 없음** (렌더러가 생략하거나 다른 방식으로 렌더) |

## 8. 데이터셋과 공식 양식 간 불일치 표준 문구 (강조)

1. **Section 6 제목 철자 불일치**: 데이터셋(`Acknowledgements`)은 본체 blank(`Acknowledgments`)와 다르다. 단, **GSE 공식 문서끼리도 철자가 갈린다** (Additional Borrower blank는 `Acknowledgements`). 즉 이 제목은 표준 문서 안에서도 표기가 안정적이지 않다.
2. **blank에만 있는 표준 안내문**: Section 1e/2c의 선택지 열거 목록, `(e.g., Pension, IRA)` 등 예시 문구, `NOTE: Reveal alimony, child support…` 안내문이 데이터셋 렌더링에는 없다 (48개 미출현 표준 라인 중 Additional Borrower 고유분 제외 시 대부분이 이 부류 + 라벨 조판 차이). 상세: `outputs/urla_standard_diff/standard_lines_not_seen.txt`.
3. **데이터셋에만 있는 비표준 고정 문구**: California Civil Code 1812.30(j) 고지 (pkg01 p8). GSE 표준 텍스트가 아니다.
4. 푸터 핵심 3종(`Uniform Residential Loan Application`(+접미), `Form 65/1003` 라인, `Effective 1/2021`)과 섹션 제목·상단 식별 블록은 표기 차이(§7) 외 **내용 불일치 없음**.

## 9. SCIF (Form 1103) 참고 노트 — 데이터셋에는 없음

향후 등장 대비 식별 문구 (blank 1페이지에서 추출):

- 상단: `To be completed by the Lender:` + `Lender Loan No./Universal Loan Identifier` + `Agency Case No.` (URLA와 동일 블록)
- 제목: `Supplemental Consumer Information Form`
- 본문 첫 문장: `The purpose of the Supplemental Consumer Information Form (SCIF) is to collect information on homeownership education and housing counseling and/or language preference…`
- 푸터: `Supplemental Consumer Information Form` / `Fannie Mae/Freddie Mac Form 1103` / `5/2022`
- 주요 섹션: Homeownership Education and Housing Counseling, Language Preference

**pkg01 원본 4종·pkg02 44페이지 어디에도 SCIF 텍스트는 등장하지 않는다** (Form 1103, Supplemental Consumer 등 문구 검색 기준).
