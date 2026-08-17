# URLA_1003 분류·그룹핑 기준서 (v2 — 확정)

> **위치**: `docs/classification/urla.md`
> **성격**: 설계 확정 문서. 구현은 이 문서를 명세로 삼는다.
> **근거 문서**: `docs/domain_knowledge.md`, `docs/analysis/urla_standard_analysis.md`
> **v1 대비 변경**: 정책/프롬프트 분리 구조 반영, 그룹핑·정렬을 단계 분리
> (신호 카드 방식), 페이지 표기를 그룹핑 근거에서 경보로 강등, LLM 확정(GPT-5.4 mini)

---

## 1. 설계 원칙

1. **결정론적 규칙에는 표준 검증 신호만.** 신호의 성립 근거에 공식 표준 문서
   (양 GSE blank)가 있는 것만 규칙화한다. 데이터셋 관찰에서만 확인된 신호는
   규칙화하지 않는다.
2. **관찰 기반 판단은 LLM에 위임.** 그룹핑·정렬의 신호(이름 값, ID 값, 페이지
   표기, 렌더러 코드)는 렌더러 산물이거나 입력값이다. 코드에 형태를 고정하지
   않고, LLM에 "활용 방법"을 지시한다.
3. **매칭은 느슨하게.** 정규화 후 비교, 철자·조판 변형 허용.
   (근거: 바이트 일치는 발행처 간에도 깨짐 — 표준 대조 §7, §10)
4. **부재는 감점이 아니다.** 표준 문구도 렌더러가 생략할 수 있음이 실증됨.
5. **점수를 발명하지 않는다.** 임의 가중치 대신 신호 등급 + 단순 결합 규칙.
6. **확신 없으면 넘긴다.** 규칙 → LLM → UNRESOLVED의 단방향 에스컬레이션.
7. **정책·프롬프트는 코드와 분리한다.** 신호 문구, 등급, 결합 규칙, 패턴은
   정책 파일(`rules/policies/urla.yaml`)로, LLM 지시는 프롬프트 파일(`llm/prompts/*.md`)로.
   엔진 코드는 이를 읽어 실행만 한다. 유형 추가 = 정책·프롬프트 추가, 엔진 무수정.

---

## 2. 파이프라인과 책임 분담

```text
페이지 텍스트 (파싱 완료 상태)
  ↓
[1] URLA 판정 .............. 코드 + policies/urla.yaml
  ↓ (URLA 판정 페이지만)
[2] 신호 카드 생성 ......... 코드 (regex + AcroForm 폼필드)
  ↓
[3] 그룹핑 ................. LLM (llm/prompts/group_urla.md)
  ↓ (instance별)
[4] 순서 정렬 .............. 코드 우선 → 폴백 LLM
```

| 단계 | 질문 | 주체 | 산출물 |
|---|---|---|---|
| [1] | 이 페이지가 URLA인가? 어느 컴포넌트인가? | 코드 | 페이지별 판정 + subtype + 매칭 근거 |
| [2] | 그룹핑에 쓸 신호는 무엇인가? | 코드 | 페이지별 신호 카드 (JSON) |
| [3] | 몇 개의 URLA instance인가? | LLM | instance 배정 + evidence |
| [4] | instance 내 페이지 순서는? | 코드/LLM | 순서 + evidence |

---

## 3. [1] 판정 — 신호 정의와 결합 규칙

### 3-1. 결정적 신호 (decisive) — 단독 확정

| ID | 신호 (정규화 기준) | 위치 | 근거 |
|---|---|---|---|
| D1 | `Uniform Residential Loan Application` (+컴포넌트 접미 변형) | 푸터 | 양 GSE blank 전 페이지 |
| D2 | `Freddie Mac Form 65 [·•] Fannie Mae Form 1003` | 푸터 | 양 GSE blank 전 페이지 |

등급 근거: 타 유형 문서 본문에 이 전체 문구가 등장할 도메인적 이유 없음.
(부분 문구 언급과의 구분은 V2 검증에서 확인)

### 3-2. 지지적 신호 (supportive) — 조합 판정

| ID | 신호 | 위치 | 비고 |
|---|---|---|---|
| S1 | `Effective M/YYYY` 패턴 (현행 1/2021) | 푸터 | 버전 개정 대비 패턴 매칭 |
| S2 | 상단 식별 블록 (`To be completed by the Lender:` + `Lender Loan No./Universal Loan Identifier` + `Agency Case No.`) | 상단 | SCIF와 공유 → 단독 확정 불가 |
| S3 | `Section 1:`~`Section 9:` + 표준 제목 문구 | 본문 | 철자 변형 허용 (`Acknowledg(e)ments`) |
| S4 | `L1.`~`L4.` + 표준 제목 문구 | 본문 | Lender Loan Info |
| S5 | `1a. Personal Information` 등 번호+표준 라벨 세트 | 본문 | 번호 토큰 단독은 신호 아님 |

### 3-3. 결합 규칙 (임계값은 조정 대상 아님)

```text
D ≥ 1                    → URLA 확정        [RULE_HIGH]
S ≥ 2 (서로 다른 ID)      → URLA 판정        [RULE_MEDIUM]
S = 1                    → LLM 이관         [DEFER_LLM]
신호 0                    → 타 유형과 경합    [NO_SIGNAL]
텍스트 없음               → VLM 이관         [DEFER_VLM]
인접 문서 문구 성립        → 유형 배제        [EXCLUDED_ADJACENT]
```

같은 ID 반복(예: S5 라벨 3개)은 1개로 센다.

### 3-4. 매칭 전처리

```text
NFKC → 가운뎃점류 통일 → dash류 통일 → 공백 축약 → 소문자화
정확 일치 → 부분문자열(줄바꿈 재조합) → 근사(0.90) 순
```

### 3-5. 컴포넌트 판별 (subtype)

푸터 접미: 없음=본체 / `— Additional Borrower` / `— Unmarried Addendum` /
`— Continuation Sheet` / `— Lender Loan Information`.
보조: S3→본체, S4→Lender Info. 충돌 시 LLM 이관.
출력 유형은 `URLA_1003` 통합, subtype은 내부 기록 (추출 단계 확장 대비).

### 3-6. 인접 문서 오분류 방지

`Supplemental Consumer Information Form` 또는 `Form 1103` 존재 시 SCIF로 식별
(URLA 아님. 라벨링 정책은 등장 시 결정. 데이터셋 미존재 확인됨).

이 경우 등급은 **`EXCLUDED_ADJACENT`** 이며 `flags.excluded_as` 에 어떤 인접 문서로
배제됐는지 기록한다 (v2에서 확정). `NO_SIGNAL`("신호가 없다")과 "인접 문서로 판별되어
이 유형에서 배제됐다"는 서로 다른 사실이므로 등급을 구분한다.

### 3-7. 규칙화 금지 신호 (명시)

| 신호 | 배제 근거 | 행선지 |
|---|---|---|
| 페이지 표기 `N of Y` | blank에 없음, 분모 가변 실증 | 신호 카드 → 경보용 |
| 인쇄 코드 `GURLA20S` 계열 | 렌더러 고유 (Calyx 반례) | 신호 카드 → 보강용 |
| 차주명·ULI·대출번호 값 | 입력값 | 신호 카드 → 주력/앵커 |
| CA Civil Code 고지 | 주별 삽입물 | 사용 안 함 |

---

## 4. [2] 신호 카드 — 추출 명세

**철학: 추출기는 확정하지 않고 후보를 수집한다.** 오탐 포함 수집,
판단은 [3]의 몫. 렌더러가 바뀌어 신호가 안 잡히면 카드가 빈약해지고,
[3]이 원문 기반 경로로 자연히 전환된다.

페이지당 카드 스키마:

```json
{
  "page": 37,
  "subtype": "본체",
  "name_candidates": ["..."],
  "id_candidates": {"loan_number": ["<9자리>"], "uli": ["<20–35자 영숫자>"]},
  "page_marker_candidates": [{"n": 2, "y": 11, "raw": "2 of 11"}],
  "sections_found": ["Section 2"],
  "printed_codes": ["GURLA20S", "(POD)"]
}
```

추출 경로:

| 필드 | 방법 | 비고 |
|---|---|---|
| name_candidates | ① AcroForm 폼필드 (`page.widgets()`, 필드명에 name/borrower 포함) ② 폼필드 없으면 라벨 앵커 (`Borrower Name:` 표준 문구 탐지 후 주변 후보 수집) | 폼필드 텍스트 흐트러짐 때문에 "라벨 다음 줄" 보장 불가 → 후보 복수 수집 |
| id_candidates | regex: 9자리 숫자 후보 + 20–35자 영숫자(ULI) 후보. 상단 식별 블록 라벨 근처 출현 시 신뢰 표시 | |
| page_marker_candidates | regex: `(page )?N of Y` 변형 | 본문 오탐(`1 of 2 units`) 포함 수집 허용 |
| sections_found | [1]의 S3/S4 매칭 결과 재사용 | 추가 스캔 없음 |
| printed_codes | 리터럴 존재 확인 | 분류 규칙 아님 — 재료 수집 |

**신호 커버리지 사실** (설계 전제, 관찰 기준):
- 이름: 대부분 페이지에서 1개 이상 형태로 존재. 단 본체 첫 장은 푸터 라벨
  없음(본문 1a에 존재), Lender Info 페이지는 확인 필요 — "전 페이지 보장" 아님
- ID: 상단 식별 블록 있는 페이지만 (~4/11) — 드문 앵커
- 페이지 표기: 이 렌더러는 전 페이지 (타 렌더러 보장 없음)

---

## 5. [3] 그룹핑 — LLM 위임 명세

- 모델: GPT-5.4 mini (구조화 출력)
- 입력: 신호 카드 목록. 신호 빈약 페이지(이름·ID·표기 모두 공백)만 원문 동봉
- 프롬프트: `llm/prompts/group_urla.md` (아래 지시 요지 포함)

지시 요지:

```text
1. 기대값: URLA는 통상 패키지당 1부다. 이름이 단일하고 페이지 표기가
   단일 세트로 맞아떨어지면 1개 instance로 확정하라.
2. 신호 역할:
   - 이름 일치 = 주력 그룹핑 근거
   - ULI/대출번호 일치 = 앵커 (등장 페이지에서 확정력 최고)
   - 페이지 표기 = 경보 전용: 같은 번호가 중복되면(예: "3 of 11" 두 장)
     다중 instance를 의심하라. 표기 자체를 그룹핑 근거로 쓰지 마라.
   - 위 신호 부족 시에만 동봉 원문으로 내용 기반 판단
3. 같은 이름의 다중 instance 가능성(재제출본)을 배제하지 마라.
   분리 근거: 번호 중복, ULI 상이, 서명 타임스탬프 상이.
4. 모든 판단에 evidence(신호와 페이지) 필수. 확신 없으면 UNRESOLVED.
```

출력 스키마:

```json
{
  "instances": [{"instance_id": "urla_1", "pages": [...], "evidence": [...]}],
  "unresolved_pages": [],
  "notes": "..."
}
```

## 6. [4] 순서 정렬

```text
경로 A (코드): instance의 page_marker가 1..Y 무결(겹침·공백 없음) → 그대로 정렬
경로 B (코드): 불완전/부재 → 표준 섹션 순서로 정렬
              Section 1→9 → 부속(Addendum·Continuation) → L1→L4
              (이 폴백은 GSE 양식 구조가 보장 — 표준 근거 있는 폴백)
경로 C: 섹션 신호도 없는 페이지 → 순서 UNRESOLVED
```

경로 A 채택 시에도 evidence에 "page_marker 무결로 코드 정렬" 기록.

**경로 B는 코드가 수행한다** (v2에서 확정). 섹션 순서는 표준이 고정한 결정론적
순서이므로 LLM 추론이 불필요하며, 순서 정렬용 프롬프트는 만들지 않는다.
섹션 신호가 없는 페이지만 경로 C로 넘긴다.

## 7. 검증 절차 (튜닝 금지)

pkg01 GT는 검산용. 숫자 조정 없음.

| # | 검증 | 기준 | 실패 시 |
|---|---|---|---|
| V1 | URLA 21p (pkg01 11 + pkg02 10) 전부 RULE_HIGH/MEDIUM 도달 | 21/21 | 정규화 버그 vs 신호 설계 누락 구분 보고 |
| V2 | 비-URLA에서 D 신호 오발 | 0 | 해당 문구 D→S 강등, 사유 기록 |
| V3 | 비-URLA에서 S≥2 동시 성립 | 0 | 조합 분석, "다른 ID" 조건 보강 검토 |
| V4 | 그룹핑: pkg01 URLA가 1 instance로 묶이고 순서가 GT의 source_page와 일치 | 일치 | evidence 검토 → 프롬프트 수정 (수정 이력 기록) |

## 8. 알려진 한계

1. 2021 개정 전 구버전·번역판 미지원 (신호 세트 상이)
2. 푸터·섹션 전면 생략 렌더러 → NO_SIGNAL → LLM 흐름이 수용 (설계된 경로)
3. 그룹핑 신호의 렌더러 의존 — LLM 위임으로 완화, 신호 전무 시 UNRESOLVED 상승
4. Additional Borrower·SCIF는 미관찰 대비 설계 — 실물 검증 안 됨
5. 같은 차주 2부가 표기·ULI·타임스탬프까지 동일하면 분리 불가 → UNRESOLVED가 정답

## 9. 다른 유형 적용 틀

```text
① 도메인 이해 → ② 준거 문서 확인 → ③ 신호 추출·근거 등급화
→ ④ 결정적/지지적 → ⑤ 단순 결합 → ⑥ GT 검산 (튜닝 금지)
→ ⑦ 규칙 밖은 LLM (evidence + UNRESOLVED)
```

| 유형 | 준거 상황 | 예상 조정 |
|---|---|---|
| CREDIT | 레이아웃 표준 없음 | 결정적 신호를 도메인 논리에서 도출 |
| TITLE | ALTA/CLTA는 라이선스 자료 | 데이터 내 약관 전문 + 도메인 논리 |
| INCOME | IRS 계열만 공개 표준 | IRS 샘플 확보 + LLM 의존도 상향 |