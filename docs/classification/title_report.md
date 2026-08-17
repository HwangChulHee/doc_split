# TITLE_REPORT 분류·그룹핑 기준서

> **위치**: `docs/classification/title_report.md`
> **성격**: 설계 확정 문서. 구현은 이 문서를 명세로 삼는다.
> **근거 문서**: `docs/domain_knowledge.md`, `docs/analysis/title_standard_analysis.md`
> **선행 문서**: `docs/classification/urla.md` (골격·결합·검증 철학),
> `docs/classification/credit_report.md` (신호 계층 모델·벤더 레이어)
> 이 문서는 TITLE 고유 사항만 규정한다.

---

## 1. 이 유형의 특수성

| 조건 | URLA | CREDIT | **TITLE** |
|---|---|---|---|
| 두 패키지 | 같은 폼 | 같은 벤더 | **다른 폼 · 다른 벤더** |
| 준거 확보 | GSE blank ✅ | 벤더 가이드 ✅ | **폼 계열별로 갈림** — ALTA blank ✅ / CLTA ❌(벤더 가이드 대체) |
| 결정적 universal | 있음 (푸터) | 있음 (3사 동시) | **없음** — 두 폼 공유 고정 문구 부재 (분석 §7-1) |
| 다중 instance | — | — | **있음** (Commitment 두 벌) |
| 텍스트 없는 페이지 | — | — | **있음** (스캔 3장 → VLM 첫 적용) |

핵심 결론: TITLE은 **universal이 약하고 벤더 레이어가 주력**인 첫 유형이다.
CREDIT에서 만든 벤더 레이어 구조가 2블록(first_american, fidelity)으로 확장되며,
같은 유형 안에서 근거 등급이 갈리는 것(ALTA=협회 표준 검증, CLTA=벤더 문서 검증)을
layer 표기로 흡수한다.

---

## 2. 신호 정의

### 2-1. universal — 벤더 독립

**결정적: 없음.** 분석 §7-1이 확정 — ALTA/CLTA가 공유하는 고정 문구가 없다.
따라서 TITLE의 universal은 지지 신호만 갖는다. (이 부재 자체가 문서화 대상:
"결정적 universal을 만들 수 없음이 분석으로 확인됨")

**지지적**

| ID | 신호 | layer | 비고 |
|---|---|---|---|
| T-S1 | Title 어휘 조합 — 다음 중 **3종 이상** 동시: `Title Insurance`, `Schedule A`, `Schedule B`, `estate or interest`, `vested in`, `easement`, `Deed of Trust`, `Legal Description`, `Exceptions`(+`Requirements`) | domain | 분석 §7-2의 공유 어휘 22종에서 식별력 높은 것만 선별. **단독 단어는 신호 아님** — `lien`, `County`, `Company`, `Land`, `recorded` 는 범용어라 제외 |
| T-S2 | 문서 유형 명칭: `PRELIMINARY REPORT` / `Commitment for Title Insurance` | domain | 제목 성격 — 한 문구라도 성립 |

### 2-2. vendor: first_american (ALTA 2021 Commitment 계열)

| 구분 | ID | 신호 | layer | 근거 |
|---|---|---|---|---|
| identity | — | `First American Title` / 주별 버전 조각 `^<State> - 2021 v\.` 패턴 | vendor | 분석 §9-1: `01.00` 부분은 텍스트 레이어에 없음 — 패턴은 `v.` 까지만 |
| 결정적 | FA-D1 | ALTA 고지문 골격: `This page is only a part of a 2021 ALTA Commitment for Title Insurance issued by <발행사>. This Commitment is not valid without the Notice; ...` (발행사 슬롯 와일드카드, 대시 공백 흡수) | **normative** | **협회 표준 검증** — FL OIR 확보 blank와 10/10 일치 (분석 §2). 협회가 라이선스 조건으로 인쇄를 강제하는 문구 |
| 결정적 | FA-D2 | ALTA Copyright 블록: `Copyright 2021 American Land Title Association. All rights reserved.` + 사용 제한 문장 | **normative** | 동일 근거 (분석 §2-4) |
| 지지적 | FA-S1 | Transaction Identification Data 라벨군: `Issuing Agent:`, `Commitment Number:`, `Issuing Office File Number:`, `Loan ID Number:`, `Revision Number:`, `lssuing Office:`(벤더 오타 — 원형 `Issuing Office:`도 병기) | 협회 표준 검증 | 분석 §3-1, 오타는 §3-3 |
| 지지적 | FA-S2 | Schedule B Part I 표준 요건 문장 (`All of the following Requirements must be met:` 등) | 협회 표준 검증 | 분석 §3-1 — Part I은 verbatim. **Part II 예외 문구는 협회 표준이 아니므로 채택하지 않는다** (분석 §3-2) |

**주석 (구현 아님, 확장 방향 기록)**: FA-D1·D2는 실제로는 "ALTA 폼을 쓰는 모든
벤더"에 공통인 폼 계열(form family) 신호다. 다른 ALTA 벤더가 등장하면
`form_families` 레이어로 승격할 수 있으나, 현 시점에는 단순성을 위해 벤더 블록에
둔다 — layer가 normative로 표기되어 있으므로 정보 손실은 없다.

### 2-3. vendor: fidelity (CLTA Preliminary Report 계열)

| 구분 | ID | 신호 | layer | 근거 |
|---|---|---|---|---|
| identity | — | `Fidelity National Title` (표기 2형: 전체 대문자/혼합) / 푸터 코드 조각 `CA-FT-` | vendor | 분석 §4-1 |
| 결정적 | FD-D1 | CLTA 법정 성격 문장 (다음 중 1문장 골격): `It is important to note that this preliminary report is not a written representation as to the condition of title...` / `The exceptions and exclusions are meant to provide you with notice of matters which are not covered...` / `This report (and any supplements or amendments hereto) is issued solely for the purpose of facilitating the issuance...` | vendor | **벤더 문서 검증** — Ticor(FNTG 계열) 가이드 샘플과 문구 일치 (분석 §4-2). 법령 §12340.11은 효력만 규정, 축자 요구 미확인 — 그래서 normative가 아니라 vendor |
| 지지적 | FD-S1 | `CLTA Preliminary Report Form` 푸터 | vendor | 8/9장 반복 |
| 지지적 | FD-S2 | `PRELIM NO.` / `AMENDMENT` | vendor | 6~7/9장 |
| 지지적 | FD-S3 | prelim 도입·Schedule A 문구 골격 (`...hereby reports that it is prepared to issue, or cause to be issued...`, `Title to said estate or interest at the date hereof is vested in:`) | vendor | 분석 §4-2 — 가이드 대조 |

### 2-4. 규칙 미채택 (deployment — 카드 재료)

| 신호 | 배제 근거 | 카드 활용 |
|---|---|---|
| `Page N of 5` / `Page N` (분모 없음) | 조판 산물. **두 폼이 표기 체계도 다름** (분석 §4-1) — 표기 형식을 규칙화하면 폼마다 깨짐 | 경보(중복 감지) + 정렬 |
| `Printed: MM.DD.YY @ HH:MM` | 인쇄 시각 | 그룹핑 보조 (같은 인쇄 배치) |
| 푸터 코드 전체 (`CA-FT-FLVE-`, `-SPS-1-26-`) | 체계 근거 미확보 (분석 §8) | 그룹핑 보조 |
| `Form 50167851 (8-25-22)` 폼 코드 | 벤더 조판 | 그룹핑 보조 |
| 파일번호·Commitment No.·금액 값 | 입력값 | **그룹핑 앵커/분리 재료** |
| `ALTA` 단어 단독 | pkg01에서 상품명 언급으로 3회 등장 (분석 §7-1) — **오발 확인된 단어** | 사용 금지 |

---

## 3. 판정 규칙

결합 규칙·전처리·경합 처리는 CREDIT과 동일 (`decisive_min: 1`, `supportive_min: 2`,
`vendor_decisive_requires_identity: true`).

**단, FA-D1·D2의 identity 전제에 예외를 둔다**: 이 두 신호는 layer가 normative
(협회 강제 문구)이므로 발행사가 누구든 성립한다. 정책에
`identity_exempt: true` 를 표기해 벤더 identity 없이도 결정적으로 인정한다.
(다른 ALTA 벤더의 Commitment가 와도 잡히는 경로 — 이것이 TITLE의 실질적
"universal 결정적" 역할을 한다)

FD-D1은 예외 없음 — 벤더 문서 검증 등급이므로 identity(Fidelity 계열) 전제 유지.

매칭 유의 (분석이 실증한 것들):

- FA-D1은 **줄바꿈 변형 2종** (397/398자) 존재 → 라인 단위가 아니라 전체 텍스트
  이어붙인 뒤 골격 매칭 (기존 substring 경로가 처리)
- `lssuing Office:` 오타 → 오타형·원형 둘 다 phrases에 등록
- 발행사 슬롯 와일드카드: FA-D1 골격을 슬롯 앞/뒤 두 조각으로 나눠 both-substring
  매칭 (엔진에 신규 스펙 `require_all` 로 표현 가능 — 앞조각+뒷조각)

### subtypes

| 벤더 | subtype | 판별 |
|---|---|---|
| first_american | `schedule_a` | Transaction ID Data 라벨군 + `Schedule A` |
| | `legal_description` | `LEGAL DESCRIPTION` 제목 |
| | `schedule_b1` | `SCHEDULE B, PART I` |
| | `schedule_b2` | `SCHEDULE B, PART II` |
| | `conditions` | `COMMITMENT CONDITIONS` (스캔 3장 — VLM 판독 시) |
| fidelity | `cover` | FD-D1 법정 문장 (p0 성격) |
| | `body` | Schedule/Exceptions 본문 |
| | `exhibit` | `EXHIBIT A` / `Legal Description` |
| | `plat_map` | 판별 불가 시 배정하지 않음 — §5 참조 |

**subtype=None은 실패가 아니다 (결정 2).** Part II 예외의 연속장처럼 구분 제목이
없는 페이지가 존재한다. 셔플 입력에서 "앞 장이 Part II였다"는 인접성은 **주어지지
않는 정보**이므로, 그런 페이지에 subtype을 부여하려면 없는 근거를 만들어야 한다.
None이 사실의 반영이며, 순서는 마커(경로 A)가 책임진다.

---

## 4. 그룹핑 (LLM 위임) — 다중 instance 첫 실전

프롬프트: `llm/prompts/group_title.md`

### 4-1. 방침 (확정): 마커 중복 시 분리 + 관계 명시

pkg02 두 벌의 사실 관계 (분석 §6): ID·날짜·파일번호·Revision No. **전부 동일**,
값 차이는 보험금액 1건, 마커 세트(`Page 1..5 of 5`)만 두 벌 완비.

| 기각한 방침 | 이유 |
|---|---|
| ID 동일 → 병합 | `Page 1 of 5` 두 장 = 물리적으로 두 출력물. 병합하면 10장짜리 비문서가 됨 |
| 무조건 분리, 관계 무기록 | "다른 두 거래"라고 단정할 근거도 없음 (앵커 전부 동일) |

**채택**: 마커 세트가 중복 완비되면 **별도 instance로 분리**하되, 공유 앵커와
관계 추정을 evidence에 기록한다 (`related_to` + 상이 필드 명시).

### 4-2. 지시 요지

```text
1. 그룹핑 앵커: 파일번호·Commitment Number 일치 = 같은 거래 계열.
2. ★ 단, 페이지 마커 세트가 중복 완비되면(예: "Page 1 of 5"가 두 장)
   앵커가 전부 동일해도 별도 instance로 분리하라. 물리적 출력 단위가 문서다.
   이때 evidence에 공유 앵커와 벌 간 상이 필드를 기록하고,
   instances 간 related_to 관계를 명시하라.
3. 쌍 맞추기: 마커 N이 같은 페이지들끼리 내용을 대조해 벌을 구성하라
   (분석상 벌 간 차이는 금액 1줄 — 미세하므로 신중히).
4. 벤더 identity가 다르면 무조건 다른 instance.
5. pkg01 p8 성격의 페이지(텍스트 근거 없음)는 인접성만으로 배정하지 말고
   UNRESOLVED로 두라.
6. evidence 필수. 확신 없으면 UNRESOLVED.
```

주의: 이 지시 2번은 URLA/CREDIT의 "ID로 묶어라"와 **반대 방향**이 처음 등장하는
것이다 — "ID가 같아도 분리하는 경우"의 유일한 트리거가 마커 중복이며, 페이지
표기를 경보 전용으로 유지해온 설계가 여기서 실질 역할을 한다.

### 4-2-1. 약관(boilerplate) 페이지의 귀속 — UNRESOLVED (결정 1)

Commitment Conditions처럼 **물건과 무관한 공통 인쇄물**은 어느 벌에 속하는지
가릴 근거가 **원리적으로 없다**. 같은 약관이 두 벌 모두에 동일하게 들어가므로,
값 대조로도 마커로도 구분되지 않는다.

따라서 이 유형의 페이지는:

- **분류(TITLE_REPORT)와 subtype(`conditions`)은 확정한다** — 무슨 문서인지는 안다
- **instance 귀속만 미정으로 둔다** → `unresolved_pages`

"모르는 것을 모른다고 출력하는 것"이 이 경우의 정답이며, 억지 배정은 근거 없는
정보를 만들어내는 것이다. 그룹핑 프롬프트가 이를 지시하고, 검증(T-V4)이 확인한다.

**실제 출력 (통합 실행 결과)**: 약관 3장은 `unresolved_pages` 로 가지 않고
**자기들끼리 한 instance(`title_2`)로 묶였다.** VLM이 회전을 바로잡은 뒤
`Page 2/3/4 of 4` 를 읽어냈기 때문이다 — 분모가 4라 5장짜리 두 벌 중 어느 쪽도
아닌, 그 자체로 완결된 4장짜리 인쇄물임이 드러났다. 이 절이 전제한 "어느 벌에
속하는지 가릴 근거가 없다"는 여전히 맞지만, **어느 벌에도 붙이지 않는 방법이
미배정만은 아니었다.** 두 5장짜리 벌(`title_1`)과는 `related_to` 로 연결했다.
결정 1의 취지(억지 배정 금지)는 지켜졌고, 출력 형태만 달라졌다.

### 4-2-2. 지시가 아니라 절차로 (구현 노트)

초기 구현에서 이 §4-2의 지시를 **서술형**으로 프롬프트에 옮겼더니, 모델이 마커
중복을 evidence·notes에 정확히 서술하고도 `instances` 구조에는 반영하지 않았다
(인지-행동 불일치). 지시를 **출력 전 자가 검증 절차**(마커 나열 → 중복 검사 →
분리 → 재확인)로 바꿔야 출력 구조까지 바뀐다.

### 4-3. 순서 정렬

```text
경로 A (코드): instance 내 마커 1..Y 무결 → 마커 정렬 (pkg02 각 벌: 1..5 완비)
경로 B (코드): 마커 없음 → subtype 순서
   first_american: schedule_a → legal_description → schedule_b1 → schedule_b2 → conditions
   fidelity:       cover → body → exhibit
   ※ conditions는 §4-2-1에 따라 귀속이 UNRESOLVED로 남는 것이 기본이다.
     귀속이 없으면 어느 instance의 순서에도 배정되지 않는다 — 이 항목은
     약관이 특정 벌에 귀속되는 것이 확인된 경우에만 쓰인다.
   (근거: 폼 문서의 구성 나열 순서 — ALTA 쪽은 협회 표준 검증, CLTA 쪽은 벤더 문서 기반)
경로 C: UNRESOLVED
```

pkg01은 `Page N`(분모 없음)이라 경로 A의 "1..Y 무결" 판정이 성립하지 않는다 —
분모 없는 연속 마커(1..N, 겹침 없음)를 경로 A의 변형으로 허용한다
(`marker_no_denominator: true`).

---

## 5. 알려진 한계 (정답 맞추기보다 정직성 우선)

1. **pkg01 p8 (plat map 자리)**: 텍스트 근거가 없다 (공유 어휘 0, 벤더 푸터 0,
   이미지 0). 규칙 NO_SIGNAL → LLM도 `[ Plat map removed... ]` 문구 외 근거 없음.
   **UNRESOLVED가 정당한 출력이다.** GT상 TITLE이지만 이 페이지를 잡으려고 규칙을
   비틀지 않는다. 검증에서도 제외한다 (T-V1).
2. **결정적 universal 부재**: 미등록 벤더 + 미등록 폼 계열의 title 문서는
   T-S1/S2 지지 조합(RULE_MEDIUM) 또는 LLM 경로로만 잡힌다. T-V5가 그 커버리지를
   측정한다.
3. **CLTA 신호의 근거 등급이 낮다**: 협회 폼 미확보로 벤더 문서 검증까지가 상한.
   CLTA P&E Forms Book 확보(유료) 시 승격 가능.
4. **두 벌의 관계는 미확정**: 분리하되 관계를 기록하는 것이 데이터가 허용하는
   최대치다. Revision Number까지 동일하므로 개정/재발행 여부는 판정 불가.
   **실제로는 분리도 되지 않았다** — 최종 실행에서 두 벌이 한 instance(10장)로
   묶였고, 짝을 가를 근거가 신호 카드에 실리지 않은 것이 원인이다
   (`known_limits.md` §3, 검증 T-V4 실패로 남김).
5. **Part II 예외 문구는 주별/벤더별 변형**: 신호로 채택하지 않았다.
6. **분모 없는 마커(`Page N`)는 중복 경보에 쓸 수 없다 (결정 3)**: 본문의 등기
   참조(`Book 577, Page 401` 등)가 같은 형태로 추출되어 오탐이 섞인다. 따라서
   §4-1의 "마커 세트 중복 → 분리" 규칙은 **분모 있는 마커에만** 적용한다.
   결과적으로 CLTA 계열처럼 분모 없는 폼이 두 벌 들어오면 이 규칙이 작동하지
   않으며, 내용 기반 분리 또는 UNRESOLVED로 흘러야 한다. (현 데이터셋에는
   해당 사례가 없다 — pkg01은 1벌)
7. **CLTA 신호가 RULE_MEDIUM에 머무는 것은 정합적이다 (결정 4)**: FD-D1은 벤더
   문서 검증 등급이라 identity 전제를 유지하며, 그 결과 pkg01은 표지 1장을 뺀
   나머지가 RULE_MEDIUM으로 판정된다. **근거 등급이 낮으면 판정 등급도 낮은 것이
   맞다** — 등급을 올리려면 준거를 올려야 한다(§5-3). 현행 유지.

---

## 6. 검증

| # | 검증 | 기준 |
|---|---|---|
| T-V1 | pkg01 TITLE 8p (**p8 제외**) + pkg02 텍스트 10p 전부 RULE_HIGH/MEDIUM | 18/18 |
| T-V2 | 비-TITLE에서 결정적(FA-D1/D2, FD-D1) 오발 | 0 |
| T-V3 | 비-TITLE에서 지지 ≥2 동시 성립 | 0 |
| T-V4 | 그룹핑: pkg01 1 instance / pkg02 **2 instance 분리 + related_to 기록** | 충족 |
| T-V5 | universal만 커버리지 측정 (벤더 레이어 오프) | 측정만 — TITLE은 낮게 나올 것이 예상되는 유형 |
| T-V6 | VLM: 스캔 3장(p10/25/39)이 TITLE로 분류 | 3/3 (§7) |

p8은 T-V1에서 제외하고, 그 처리 결과(UNRESOLVED 또는 LLM 판정)를 리포트에
별도 기록한다.

---

## 7. VLM 경로 (이번 구현에서 첫 가동)

대상: DEFER_VLM 페이지 (현재 pkg02 p10/25/39).

```text
렌더링: PyMuPDF pixmap (dpi 150) — 저장된 /Rotate 를 무시하고 정방향으로 렌더
프롬프트: llm/prompts/classify_page_vision.md (스텁 → 실물화)
모델: 동일 (gpt-5.4-mini, 비전 입력)
지시: 텍스트 분류와 동일 원칙 — 5유형 중 판정, 이미지에서 읽은 문구를
      evidence로 인용, 확신 없으면 UNRESOLVED
출력: classify_page와 동일 스키마 + grade=VLM
```

VLM 판정 페이지는 신호 카드가 빈약하므로, 그룹핑 입력에는 VLM이 읽어낸
텍스트 요지(마커, 폼 코드 등)를 카드 필드로 넘긴다.

**회전에 대한 정정 (구현 후)**: 위 렌더링 줄은 처음에 "페이지 회전은 렌더링이
자동 반영"이라고 적혀 있었다. 사실이 아니었다 — 이 3장은 `/Rotate` 값이 스캔
내용과 달라서, 값을 적용해 그리면 오히려 뒤집히거나 눕는다. 첫 가동에서 p10이
`OTHER`로 판정된 원인이 이것이었고, 저장값을 무시하고 그리도록 바꾼 뒤 3장 모두
마커·폼 코드·벤더명까지 판독됐다. 다만 지금 구현은 회전을 판별하는 것이 아니라
**항상 0으로 강제**하므로, `/Rotate` 가 내용과 맞는 PDF에서는 반대로 어긋난다
(`known_limits.md` §5).

비용 유의: 이미지 3장 × 1회 — 캐싱 대상.

---

## 8. 정책 파일 스키마 차분 (CREDIT 대비 신규 요소만)

```yaml
type: TITLE_REPORT

universal:
  # decisive 없음 — 분석 §7-1로 확정된 부재. 섹션 자체를 생략하지 말고
  # 빈 상태로 두고 주석으로 부재 사유를 남긴다.
  supportive:
    T-S1: {layer: domain, min_matches: 3, phrases: [...]}
    T-S2: {layer: domain, phrases: ["PRELIMINARY REPORT", "Commitment for Title Insurance"]}

vendors:
  first_american:
    identity: {layer: vendor, phrases: [...], patterns: ['^\w[\w ]* - 2021 v\.']}
    decisive:
      FA-D1:
        layer: normative
        identity_exempt: true        # ★ 신규 스펙 — 협회 강제 문구라 발행사 불문 성립
        require_all: ["This page is only a part of a 2021 ALTA Commitment for Title Insurance issued by",
                      "This Commitment is not valid without the Notice"]
      FA-D2:
        layer: normative
        identity_exempt: true
        phrases: ["Copyright 2021 American Land Title Association. All rights reserved."]
    supportive: {FA-S1: ..., FA-S2: ...}
    subtypes: {...}
  fidelity:
    identity: {...}
    decisive:
      FD-D1: {layer: vendor, phrases: [3문장 골격]}   # identity 전제 유지
    supportive: {...}
    subtypes: {...}

ordering:
  marker_no_denominator: true   # ★ 신규 — pkg01의 "Page N" (분모 없음) 대응
  per_vendor_subtype_order:
    first_american: [schedule_a, legal_description, schedule_b1, schedule_b2, conditions]
    fidelity: [cover, body, exhibit]
```

엔진 신규 요구: `identity_exempt`, `marker_no_denominator`,
벤더별 subtype_order. 이외는 CREDIT 엔진 그대로.
