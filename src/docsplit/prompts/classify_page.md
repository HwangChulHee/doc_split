<!--
목적: 규칙 판정이 LLM으로 넘긴 페이지의 유형을 판정한다. 두 경로가 이 프롬프트를 공유한다.
  (a) DEFER_LLM — 지지 신호가 1개뿐이라 확정 불가
  (b) 유형 경합 — 둘 이상의 유형이 동시에 RULE_HIGH (임의 우선순위 금지)
입력변수:
  <<candidate_types>>  후보 유형명 목록 (쉼표 구분, 1개 이상)
  <<reason>>           이 페이지가 넘어온 이유 (DEFER_LLM | TYPE_CONFLICT)
  <<signal_summary>>   규칙 단계에서 매칭된 신호 요약 (JSON)
  <<subtype_options>>  후보 subtype 목록 (없으면 "(없음)")
  <<page_text>>        페이지 원문 텍스트
출력스키마: {"type": str|null, "subtype": str|null, "evidence": [str]}
  - type: 후보 유형명 중 하나 / 어느 것도 아니면 null / 판단 불가면 "UNRESOLVED"
근거문서: docs/classification/urla.md §3-3, docs/classification/credit_report.md §4-2
-->

당신은 모기지 대출 서류 페이지의 유형을 판정한다.
규칙 엔진이 이 페이지를 넘긴 이유: **<<reason>>**

- `DEFER_LLM` = 약한 신호 1개만 발견되어 확정하지 못함
- `NO_SIGNAL` = 규칙 신호가 하나도 없음. 규칙으로 잡히지 않는 것이 정상인
  문서 종류가 있다 (예: 정해진 서식이 없는 개인 작성 문서). 신호가 없다는 것이
  곧 이 유형이 아니라는 뜻은 아니니, 내용을 읽고 판단하라.
- `TYPE_CONFLICT` = 두 개 이상 유형의 결정적 신호가 동시에 성립함.
  규칙 엔진은 임의 우선순위를 두지 않으므로 당신이 판단해야 한다.

후보 유형: **<<candidate_types>>**

규칙 단계가 발견한 신호:

```json
<<signal_summary>>
```

## 지시

1. 아래 페이지 원문을 읽고, 이 페이지가 후보 유형 중 **어느 것에 속하는지** 판단하라.
   후보가 여럿이면 하나만 고른다. 어느 것도 아니면 `null`.
2. 판단 기준은 **이 페이지가 어떤 문서의 일부인가**(문서의 기능)이다.
   다른 유형의 어휘가 인용·참조로 등장할 수 있으므로, 페이지 전체의 성격을 보라.
   ★ **발행·전달 경로와 문서의 기능이 다를 수 있다.** 다음을 지켜라:
   - **벤더 스탬프를 유형 근거로 쓰지 마라.** `Report ID:`, `Requested By:`,
     `Ref:`, `Loan Number:` 같은 주문 관리용 라벨과, "이 리포트는 ○○ 신용정보
     회사가 발행했다"는 식의 **발행 기관 언급**은 배달 경로일 뿐이다.
     이런 문구는 evidence로 인용하지도 마라.
   - **이 문서가 무엇을 확인하는가만 보라**:
     신용·부채 이력(점수, 계좌, 연체, 조회 이력)을 확인하면 `CREDIT_REPORT`,
     고용·소득의 존재를 확인하면(재직 여부, 급여액, 세무 기록) `INCOME_DOC`,
     부동산 권리관계를 확인하면 `TITLE_REPORT`,
     차주가 대출을 신청하며 신고한 내용이면 `URLA_1003`.
3. 판단 근거는 페이지에 실제로 존재하는 문구여야 한다 (evidence에 인용).
4. 확신이 없으면 type을 `"UNRESOLVED"`로 하라. 추측하지 마라.
5. 유형이 정해지면 subtype도 판단하라. 후보: <<subtype_options>>
   (판단 불가면 null)

## 출력

JSON 하나만 출력하라:

```json
{"type": "후보 유형명 또는 null 또는 UNRESOLVED", "subtype": "... 또는 null", "evidence": ["..."]}
```

## 페이지 원문

<<page_text>>
