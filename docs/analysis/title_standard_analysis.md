# TITLE_REPORT 준거 문서 ↔ 데이터셋 대조 분석

작성일: 2026-08-16. 페이지 번호는 전부 **0-based**.
대조 raw 결과: `outputs/title_standard_diff/` (데이터셋 원문 포함 — 커밋 금지 영역).
대조 스크립트: `scripts/observe_title_diff.py`.
확보 문서·출처: `data/reference/title/SOURCES.md` (**폼 원본은 gitignore — §1 참조**).

> **근거 등급 주의 — 이번엔 한 유형 안에서 등급이 갈린다.**
> URLA는 양 GSE의 blank(규범), CREDIT은 벤더 제품 문서(벤더 문서 검증)로 단일했으나,
> TITLE은 두 패키지가 서로 다른 폼이라 근거도 둘로 갈린다.
>
> | | pkg01 (CLTA Preliminary Report) | pkg02 (2021 ALTA Commitment) |
> |---|---|---|
> | 준거 | ❌ 협회 폼 확보 실패 | ✅ 협회 blank 확보 |
> | 대체 근거 | 벤더 가이드(FNTG 계열) + 주 법령 | — |
> | 등급 | **벤더 문서 검증 + 법령 정황** | **협회 표준 검증** |
>
> 즉 pkg02 쪽 확인은 URLA와 같은 수준이고, pkg01 쪽은 CREDIT과 같은 수준이다.

이 문서는 사실 기록이다. 분류 전략 판단은 포함하지 않는다.
개인정보 값·고객사 고유명·금액·문서번호 값은 기록하지 않는다(범주·역할로만 서술).

---

## 1. 확보 결과

| 대상 | 결과 | 확보물 |
|---|---|---|
| **ALTA** (pkg02) | ✅ **성공** | 2021 ALTA Commitment blank 6p (미기입, 선택 구간 `[...]` 유지) |
| **CLTA** (pkg01) | ❌ **실패** (3경로 전부) | — (대신 CA Ins. Code §12340.11 법령 원문 확보) |
| **벤더 자료** | ✅ 2종 | Ticor Title(FNTG 계열) `How to Read a Preliminary Report` 2023, First American 소비자 안내 |

**ALTA 확보 경로가 협회 사이트가 아니다.** `alta.org`는 이 작업 시간 내내 오리진 장애였다
(`policy-forms/` 페이지·`downloadSub?formSubID=2159` 링크 모두 Cloudflare `HTTP 520`/`526`,
재시도 5회 동일). 대신 **플로리다 주 보험규제청(FL OIR)이 공개하는 title insurance 2021 폼
라이브러리**에서 동일 폼을 받았다. 개별 거래 문서가 아니라 주 규제기관이 게시한 협회 폼
원본이며, 문서 내부 표기(`BLANK TITLE INSURANCE COMPANY`, `[2021 v. 01.00 (07-01-2021)]`,
`Copyright 2021 American Land Title Association`)로 진본성을 확인했다.

**CLTA 실패 경로 3종** (상세는 SOURCES.md §2):
① CLTA 공식 — 유료 구독 포털 뒤 / ② CDI — 공개되는 건 **접수 목록**뿐, 폼 본문 미공개 /
③ 언더라이터 폼 라이브러리(Stewart Virtual Underwriter) — 항목은 존재하나 본문 로그인 벽.

**저작권 취급이 앞선 둘과 다르다.** ALTA 폼에는 "The use of this Form ... is restricted to
ALTA licensees ... All other uses are prohibited." 표기가 붙어 있다. 참조 목적의 로컬 보관은
문제없으나 공개 저장소에 재배포하지 않기로 하고, `data/reference/title/` 전체를 gitignore에
추가한 뒤 `SOURCES.md`만 커밋했다.

---

## 2. ★ "This page is only a part of a 2021 ALTA Commitment..." 고지 (최우선 확인)

### 2-1. 반복 범위 — **pkg02 텍스트 10장 전부 (10/10)**

스캔 3장(p10, p25, p39)은 텍스트가 없어 판정 대상에서 제외했다.
pkg01에는 **0장** — CLTA 문서에는 이 고지가 존재하지 않는다.

### 2-2. 폼과의 일치 — **정확히 일치한다 (조건 2개 명시)**

협회 blank의 고지문은 **선택 구간 3개를 대괄호로 표시**하고 있다:

```
This page is only a part of a 2021 ALTA Commitment for Title Insurance[ issued by ________].
This Commitment is not valid without the Notice; the Commitment to Issue Policy; the
Commitment Conditions; Schedule A; Schedule B, Part I—Requirements;[ and] Schedule B,
Part II—Exceptions[; and a counter-signature by the Company or its issuing agent that
may be in electronic form].
```

8가지 조합(2³) 전개 후 대조한 결과, 데이터셋 10장 전부가 **`[K-K]` 조합**과 일치한다 —
① 발행사 구간 **유지**(공란에 발행사명 기입) ② `[ and]` **생략** ③ 반대서명 구간 **유지**.

단, 정규화만으로는 일치하지 않고 **두 단계 보정이 필요했다**:

| 단계 | 처리 | 일치 |
|---|---|---|
| ① 정규화 원문 그대로 | — | ❌ 10/10 실패 |
| ② 대시 주변 공백 흡수 | 폼이 `Part II—`⏎`Exceptions`로 줄바꿈되어 `part ii- exceptions`가 됨 | ❌ 여전히 실패 |
| ③ + 발행사 공란(`________`)을 임의 문자열로 허용 | 폼의 fill-in 슬롯 | ✅ **10/10 `[K-K]` 일치** |

즉 **문장 골격은 협회 폼과 완전히 동일**하고, 차이는 (a) 채워 넣는 슬롯 1개와
(b) 줄바꿈 위치뿐이다.

### 2-3. 데이터셋 내부의 줄바꿈 변형 2종

같은 고지가 페이지마다 두 가지로 끊긴다 — 정규화 후 길이가 397자와 398자로 갈린다:

| 변형 | 끊기는 위치 | 페이지 |
|---|---|---|
| A (398자) | `... is not valid` ⏎ `without the notice; ... part ii-` ⏎ `exceptions; and a counter-signature ...` | 0, 2, 4, 21, 32 |
| B (397자) | `... is not` ⏎ `valid without the notice; ... part` ⏎ `ii-exceptions; and a counter-signature ...` | 6, 8, 14, 16, 41 |

**라인 단위 매칭으로는 두 변형이 서로 다른 문자열이다.** 전체 텍스트를 이어붙인 뒤 봐야
동일해진다. (URLA 대조에서 확인한 loose matching 필요성과 같은 성격의 현상)

### 2-4. Copyright 블록 — **10/10, 3줄 전부 폼과 일치**

`Copyright 2021 American Land Title Association. All rights reserved.` /
`The use of this Form (or any derivative thereof) is restricted to ALTA licensees and` /
`ALTA members in good standing as of the date of use. All other uses are prohibited.` /
`Reprinted under license from the American Land Title Association.`

고지문과 같은 10장에 함께 등장한다. pkg01에는 0장.

---

## 3. ALTA 폼 고정 텍스트가 발행본에 얼마나 남는가

blank의 라벨·문장을 하나씩 대조했다 (`outputs/title_standard_diff/structure_terms.txt`).

### 3-1. 그대로 살아남은 것

| 블록 | 항목 | 데이터셋 |
|---|---|---|
| Transaction Identification Data | 도입문 + `Commitment Condition 5.e.` | p2, p16 |
| 동 라벨 8종 | `Issuing Agent:` `Issuing Office’s ALTA® Registry ID:` `Loan ID Number:` `Commitment Number:` `Issuing Office File Number:` `Property Address:` `Revision Number:` (+ 아래 §3-3) | p2, p16 |
| Schedule A | `Commitment Date:` `Policy to be issued:` `Proposed Insured:` `Proposed Amount of Insurance:` `The estate or interest to be insured:` `The Title is, at the Commitment Date, vested in:` `The Land is described as follows:` | p2, p16 |
| Schedule B Part I | 도입문 `All of the following Requirements must be met:` + 표준 요건 1~4 전문 | p8, p32 |
| Schedule B Part II | Discriminatory Covenants 문단 2문장 | p14, p21 |
| 서명란 | `Authorized Signatory` | p2, p16 |

Schedule B Part I의 표준 요건 4개는 **문장 단위로 verbatim**이다
(`Pay the agreed amount for the estate or interest to be insured.` 등).

### 3-2. 폼에는 있으나 발행본에 없거나 바뀐 것 — 4건

| 폼 문구 | 데이터셋 | 성격 |
|---|---|---|
| `and, as disclosed in the Public Records, has been since (Date)` | **없음** | 항목 4의 후반부를 생략 |
| `The Policy will not insure against loss or damage resulting from the terms and **conditions** of any lease or easement...` | `...terms and **provisions** of any lease or easement...` | **한 단어 상이** |
| `Any defect, lien, encumbrance, adverse claim, or other matter that appears for the first time in the Public Records or is created, attaches, or is disclosed between...` | `Defects, liens, encumbrances, adverse claims or other matters, if any, created, first appearing in the public records...` | 구판 계열 표현으로 교체 |
| `2021 ALTA® Owner’s Policy` | `(a) ALTA® Homeowner’s Policy` / `(b) 2021 ALTA® Loan Policy` | 발행 상품 구성이 다름 |

즉 **Schedule B Part II의 예외 문구는 협회 표준 그대로가 아니다.** 반면 고지문·Copyright·
Transaction Identification Data·Schedule A 라벨·Part I 요건은 그대로다.

### 3-3. ★ 벤더 템플릿의 오타 — `lssuing Office:`

폼은 `Issuing Office:` (대문자 I)인데 **데이터셋은 소문자 L로 시작하는 `lssuing Office:`를
인쇄한다.** p2, p16 두 장 모두 동일하다.

- `Issuing Office:` 로는 **정확 일치 0건** (0.90 유사도 fuzzy로만 걸린다)
- `lssuing Office:` 로는 **정확 일치 2건**

같은 블록의 다른 라벨 7종은 전부 정확 일치하므로 추출 오류가 아니라 **벤더 템플릿에 박힌
오타**로 보인다. (엄밀 일치를 전제한 문구 대조가 어떻게 깨지는지 보여주는 사례)

---

## 4. pkg01 (CLTA) — 협회 폼 없이 확인한 것

### 4-1. 전 페이지 반복 문구

9장 중 p8(plat map 제거 페이지)을 제외한 **8장**에 아래가 반복된다:

| 반복 라인 | 등장 | 분류 |
|---|---|---|
| `CLTA Preliminary Report Form (MM/DD/YYYY)` | 8/9 | VENDOR (폼 버전 푸터) |
| `Printed:  MM.DD.YY @ HH:MM PM` | 8/9 | VENDOR (인쇄 시각) |
| `CA-FT-<4글자>-` | 8/9 | VENDOR (푸터 코드 앞부분) |
| `-SPS-<n>-<n>-` | 8/9 | VENDOR (푸터 코드 뒷부분) |
| 파일번호 2종 (`####-#######`, `#####.######`) | 8/9 | FILLED |
| `Page N` (**분모 없음**) | 8/9 | VENDOR |
| `FIDELITY NATIONAL TITLE COMPANY` | 7/9 | VENDOR (벤더명) |
| `AMENDMENT N` | 7/9 | VENDOR |
| `PRELIM NO.` | 6/9 | VENDOR |
| `PRELIMINARY REPORT` | p0~p7 (8장, 헤더/푸터 아님) | 문서 유형 명칭 |

**푸터 코드 구조**: 데이터셋은 `CA-FT-FLVE-`와 `-SPS-1-26-`이 **두 라인으로 쪼개져** 추출된다
(사이에 파일번호가 들어가는 형태). 앞부분은 `CA`(주) + `FT`(회사 약어) + 사무소/상품 코드로
읽히나, 코드 체계의 근거 문서는 확보하지 못했다 → §8 UNCERTAIN.

**페이지 표기가 ALTA와 다르다**: pkg01은 `Page 1`처럼 **분모가 없고**, pkg02는 `Page 1 of 5`로
분모가 있다.

### 4-2. 법정 성격 문장 3종 — 벤더 가이드와 대조

Ticor(FNTG 계열) 가이드는 CLTA prelim 샘플에 주석을 달면서 아래 문장들에
*"This statement is required by California Law"* / *"required by California law"* 라고
표기한다. 세 문장 전부 **데이터셋 pkg01 p0에 존재하고, 가이드 샘플과 문구가 일치**한다.
pkg02에는 **0건**.

| 문장(앞부분) | 가이드 | pkg01 | pkg02 |
|---|---|---|---|
| `It is important to note that this preliminary report is not a written representation as to the condition of title...` | ✅ | p0 | ❌ |
| `The exceptions and exclusions are meant to provide you with notice of matters which are not covered...` | ✅ | p0 | ❌ |
| `This report (and any supplements or amendments hereto) is issued solely for the purpose of facilitating the issuance...` | ✅ | p0 | ❌ |

또한 prelim 본문 도입 문단(`...hereby reports that it is prepared to issue, or cause to be
issued, as of the date hereof, a policy or policies of title insurance describing the land and
the estate or interest therein hereinafter set forth...`)도 가이드 샘플과 문장 골격이 일치한다.
Schedule A 항목 문구(`The estate or interest in the land hereinafter described or referred to
covered by this report is:`, `Title to said estate or interest at the date hereof is vested in:`)도 마찬가지다.

**법령과의 관계는 부분적이다.** 확보한 CA Ins. Code §12340.11은 preliminary report가
"shall not be construed as, nor constitute, a representation as to the condition of title to
real property"라고 **효력**을 규정하지만, 위 인쇄 문장을 **축자적으로 요구하는 조문은
찾지 못했다.** 따라서 "법이 이 문장을 그대로 쓰라고 했다"가 아니라 "법이 규정한 효력을
CLTA 표준 문안이 이렇게 표현했고, 벤더 가이드가 이를 법정 요구로 설명한다"까지가 확인된
사실이다 → §8 UNCERTAIN.

### 4-3. p8 — 유일한 신호 공백 페이지 (재확인)

| 항목 | 값 |
|---|---|
| 텍스트 | 83자 (`[ Plat map removed in anonymized sample ]` 2회) |
| 이미지 | **0개** (스캔본이 아니라 내용이 제거된 자리) |
| 크기 | 612 × 946pt — **다른 8장(612×792)과 세로 길이가 다르다** |
| 회전 | 0 |
| 벤더 푸터 | **없음** (8/9 반복 문구가 이 페이지에만 부재) |
| 분류 결과 | UNCERTAIN 2줄, 그 외 0 |

**Title 어휘 프로브 30종 중 이 페이지에 걸리는 것이 하나도 없다.** 앞뒤 페이지와의 인접성
외에는 텍스트 근거가 존재하지 않는 페이지다.

---

## 5. 텍스트 4분류 결과

`ASSOC_STANDARD`(협회 표준) / `VENDOR`(벤더 조판·고정 요소) / `FILLED`(개별 값) /
`UNCERTAIN`(구분 불가). 추가로 순수 목록 번호(`1.`, `a.`)는 어느 쪽 근거도 아니므로
**`ENUM`**으로 따로 뺐다. ASSOC_STANDARD는 근거 출처를 접미사로 구분했다
(`(notice)` 고지문 골격, `~` 폼 텍스트 부분일치, `(clta-ref)` 벤더 가이드/법령 대조).

| 페이지 | ASSOC_STANDARD 계열 | VENDOR | FILLED | ENUM | UNCERTAIN |
|---|---|---|---|---|---|
| pkg01 p0 | 12 | 13 | 7 | 0 | 33 |
| pkg01 p1 | 2 | 8 | 3 | 3 | 8 |
| pkg01 p2 | 1 | 5 | 3 | 0 | 11 |
| pkg01 p3 | 2 | 8 | 3 | 8 | 41 |
| pkg01 p4 | 0 | 8 | 10 | 0 | 24 |
| pkg01 p5 | 1 | 8 | 3 | 2 | 12 |
| pkg01 p6 | 3 | 8 | 13 | 8 | 38 |
| pkg01 p7 | 0 | 11 | 3 | 2 | 20 |
| pkg01 p8 | 0 | 0 | 0 | 0 | 2 |
| pkg02 p0 / p41 | 10 / 10 | 3 / 3 | 4 / 4 | 0 / 0 | 10 / 10 |
| pkg02 p2 / p16 | 25 / 25 | 3 / 3 | 6 / 6 | 5 / 5 | 32 / 32 |
| pkg02 p4 / p6 | 8 / 8 | 3 / 3 | 3 / 3 | 0 / 2 | 18 / 19 |
| pkg02 p8 / p32 | 17 / 17 | 3 / 3 | 4 / 3 | 8 / 8 | 25 / 26 |
| pkg02 p14 / p21 | 16 / 15 | 3 / 3 | 6 / 6 | 10 / 9 | 32 / 33 |

읽는 법:

- **pkg02는 어느 장을 펴도 협회 표준 텍스트가 8줄 이상** 있다 (최소 p4/p6의 8줄).
  고지문 4~5줄 + Copyright 3~4줄이 바닥을 깔아준다.
- **pkg01은 p0에 몰려 있고 p4·p7·p8은 0이다.** 대신 p8을 뺀 전 장에 벤더 푸터가 8줄씩 있다.
- **UNCERTAIN이 pkg01에서 특히 크다** — 대부분 Schedule B 예외 항목의 본문
  (등기 사항, 세금 항목, 지역권 서술)으로, 개별 물건에 따라 달라지는 서술문이라
  표준 문구인지 값인지 라인 단위로는 가릴 수 없다.
- pkg02의 UNCERTAIN도 같은 성격 + **주별 표준 예외 문구**다(§3-2 참조).

---

## 6. ★ pkg02 Commitment 두 벌 대조

### 6-1. 쌍 대응 — 페이지 마커로 재확인

각 장이 `Page N of 5` 마커를 갖고 있어 쌍이 결정된다. **핸드오프가 제시한 대응과 일치**한다.

| 마커 | 페이지 | 내용 |
|---|---|---|
| Page 1 of 5 | **2 ↔ 16** | Transaction Identification Data + Schedule A |
| Page 2 of 5 | **0 ↔ 41** | LEGAL DESCRIPTION |
| Page 3 of 5 | **8 ↔ 32** | SCHEDULE B, PART I—Requirements |
| Page 4 of 5 | **14 ↔ 21** | SCHEDULE B, PART II—Exceptions |
| Page 5 of 5 | **4 ↔ 6** | Exceptions 계속 |

### 6-2. 벌 간 차이 — **값 차이는 단 한 곳이다**

라인 집합 비교로는 쌍마다 6~16줄이 달라 보이지만, 그 대부분이 **줄바꿈 차이**였다.
전체 텍스트를 단어 단위로 비교한 결과:

| 쌍 | 단어 일치율 | 실제 차이 |
|---|---|---|
| 2 ↔ 16 | 0.9905 | ① 고지문 줄바꿈 ② 서명란 이름 2개가 **중복 출력**(`이름이름` 형태) ③ **Schedule A `Proposed Amount of Insurance` 두 번째 값** |
| 0 ↔ 41 | 0.9925 | 고지문 줄바꿈뿐 |
| 8 ↔ 32 | 0.9961 | 고지문 줄바꿈뿐 |
| 14 ↔ 21 | 0.9977 | 고지문 줄바꿈뿐 |
| 4 ↔ 6 | 0.9960 | 고지문 줄바꿈뿐 |

**어느 필드가 다른가 (§4-3-6 답):**

- **`Proposed Amount of Insurance` — (b) 대출 정책 쪽 금액 1건.** 이것이 유일한 값 차이다.
- (a) Homeowner's Policy 쪽 금액은 **동일**하다.
- `Commitment Date:` / `Commitment Number:` / `Issuing Office File Number:` /
  `Loan ID Number:` / `Revision Number:` / `Property Address:` / 소유권 이전 이력 / 등기
  Book·Page 번호 / 세금 항목 — **전부 동일**.

> **핸드오프 전제 정정**: 핸드오프 §4-3-6은 "금액, 날짜, 파일번호, Commitment No. 등"이
> 다를 것으로 보고 목록화를 요청했으나, 실제로 다른 것은 **금액 1건뿐**이고 날짜·파일번호·
> Commitment No.는 두 벌이 같다. 나머지 차이는 전부 렌더링 아티팩트(줄바꿈, 서명란 중복
> 출력)다.

두 벌은 "다른 거래"가 아니라 **같은 Commitment의 두 출력본이며 보험금액 한 줄만 다른 관계**로
보인다. 다만 그 차이가 개정(revision)인지 다른 목적의 재발행인지는 `Revision Number:` 값이
두 벌 모두 동일하므로 데이터만으로는 확정할 수 없다 → §8 UNCERTAIN.

---

## 7. 교차 확인

### 7-1. ALTA 고정 문구가 pkg01에 나타나는가 → **거의 전무**

| 프로브 | pkg01 | pkg02 |
|---|---|---|
| `This page is only a part of a 2021 ALTA Commitment` | **0장** | 10장 |
| `Copyright 2021 American Land Title Association` | **0장** | 10장 |
| `American Land Title Association` (기관명) | **0장** | 10장 |
| `Commitment Conditions` / `Commitment to Issue Policy` / `Schedule B, Part I—Requirements` | **0장** | 각 10장 |
| `Proposed Insured` | **0장** | 6장 |
| `ALTA` (약어 단독) | 3장 (p0, p1, p6) | 10장 |
| `Amount of Insurance` | 1장 (p0) | 2장 |
| `Public Records` | 1장 (p3) | 4장 |

pkg01의 `ALTA` 등장은 **협회 문구가 아니라 상품명 언급**이다 — `ALTA Loan Policy 2021`(발행
예정 정책), `ALTA Endorsement Form 9`, `CLTA/ALTA Homeowner's Policy`. 즉 CLTA 문서가 ALTA
상품을 참조하는 것이지 ALTA 폼 문구를 쓰는 것이 아니다.

역방향(§4-2의 CLTA 법정 문장 3종)도 pkg02에 **0건**이다.

**두 폼이 공유하는 고정 문구는 확인되지 않았다.**

### 7-2. 두 패키지 공유 어휘

30종 프로브 중 **양쪽에 모두 나타난 것 22종**:

| 어휘 | pkg01 | pkg02 |
|---|---|---|
| `Company` | 7장 | 10장 |
| `Land` | 5장 | 10장 |
| `Title Insurance` | 4장 | 10장 |
| `Requirements` | 4장 | 10장 |
| `Exceptions` | 3장 | 10장 |
| `recorded` | 3장 | 10장 |
| `County` | 3장 | 8장 |
| `Deed of Trust`, `Trustee` | 3장, 2장 | 2장, 4장 |
| `estate or interest` | 2장 | 6장 |
| `lien` | 2장 | 2장 |
| `Schedule A` | 1장 | 10장 |
| `assessments` | 1장 | 4장 |
| `easement` | 1장 | 4장 |
| `Legal Description` | 1장 | 2장 |
| `vested in`, `Parcel`, `encumbrance`, `covenants, conditions`, `Amount of Insurance` | 각 1장 | 2장 |

한쪽에만 있는 것:

- **pkg01 전용**: `Beneficiary`, `Recording Date`, `Official Records`, `APN`,
  `Property taxes`, `policy of title insurance`, `arbitration`
- **pkg02 전용**: `Proposed Insured`

`Official Records`(CA 등기 표현) ↔ `land records of Fairfax County`(VA 표현)처럼
**같은 개념을 주별로 다르게 부르는 사례**가 있다. `APN`(CA) ↔ `Tax ID`(VA)도 같은 관계다.

주의: **p8(plat map 제거 페이지)은 22종 공유 어휘 중 어느 것에도 걸리지 않는다.**

---

## 8. UNCERTAIN

- **CLTA 인쇄 문장의 법적 근거**: 벤더 가이드는 "California law가 요구한다"고 설명하나,
  확보한 §12340.11에는 그 문장이 축자적으로 없다. 다른 조문·규정 근거인지 CLTA 표준 문안
  자체인지 미확정 (§4-2).
- **pkg01 푸터 코드 체계**: `CA-FT-FLVE-` / `-SPS-1-26-`의 각 자리 의미. 주·회사 약어까지는
  읽히나 근거 문서 없음.
- **두 벌의 관계**: 금액 한 줄만 다른 두 출력본. 개정인지 재발행인지 `Revision Number:`가
  동일해 확정 불가 (§6-2).
- **Schedule B Part II 예외 문구의 출처**: 협회 blank와 다르다(§3-2). 버지니아 주 표준
  예외인지 벤더 표준 문안인지 구분할 준거를 확보하지 못했다.
- **스캔 3장의 내용**: p10·p25·p39는 텍스트 0자·이미지 1개다. 이전 세션에서 사람이
  Commitment Conditions 약관으로 판독한 사실은 유지하되, 이번 대조에서는 **판독 불가로
  두고 텍스트 페이지만 대조**했다 (VLM 미사용).
- **`Form 50167851 (8-25-22)`**: 텍스트 10장의 폼 코드는 8자리 `50167851`이다.
  이전 세션의 스캔본 육안 판독은 7자리 `5016785`였다 — 같은 코드의 판독 차이인지 스캔
  3장이 실제로 다른 코드를 갖는지는 스캔을 읽지 않는 한 확정 불가.

---

## 9. 예상 밖 발견

1. **`Virginia - 2021 v. 01.00 (07-01-2021)` 중 버전 번호 `01.00`이 텍스트 레이어에 없다.**
   추출되는 것은 `Virginia - 2021 v. ` 와 ` (07-01-2021) ` 두 조각뿐이고, **10장 전부
   동일**하다. 핸드오프 §4-3-5가 패턴 일반화를 요청한 그 문자열이 실제로는 온전히 존재하지
   않는다. 텍스트만으로 잡을 수 있는 것은 `^<주 이름> - 2021 v\.$` 까지다.
2. **벤더 템플릿 오타 `lssuing Office:`** (§3-3). 대문자 I가 소문자 L이다.
3. **두 벌의 차이가 금액 한 줄뿐이었다** (§6-2). 핸드오프 전제와 다르다.
4. **같은 고지문이 페이지마다 다르게 줄바꿈된다** (§2-3). 라인 단위 비교로는 두 문자열이다.
5. **협회 표준 텍스트를 가장 많이 담은 페이지는 본문이 아니라 고지·저작권 블록이다.**
   pkg02에서 내용이 가장 적은 LEGAL DESCRIPTION 장(p0/p41, 27줄)조차 협회 표준 10줄을 갖는다.
6. **Schedule B Part II의 예외 문구는 협회 표준이 아니다** (§3-2). 같은 문서 안에서
   Part I은 verbatim인데 Part II는 다른 계열 문안이다.
7. **pkg01 p8은 스캔본이 아니다** — 이미지 0개, 크기만 다른 빈 페이지다(§4-3).
   "plat map은 스캔으로 들어온다"는 일반론과 달리 이 데이터셋에서는 내용이 제거된 자리다.

---

## 10. 산출물

| 산출물 | 위치 | 커밋 |
|---|---|---|
| 이 보고서 | `docs/analysis/title_standard_analysis.md` | ✅ |
| 대조 스크립트 | `scripts/observe_title_diff.py` | ✅ |
| 출처 기록 | `data/reference/title/SOURCES.md` | ✅ |
| 대조 raw (8종 + 페이지별 19종) | `outputs/title_standard_diff/` | ❌ gitignore |
| 확보한 폼·가이드 원본 | `data/reference/title/{alta,clta,vendors}/` | ❌ gitignore (§1) |
