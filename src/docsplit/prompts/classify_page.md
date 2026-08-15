<!--
목적: 규칙 판정이 DEFER_LLM(지지 신호 1개뿐)으로 넘긴 페이지의 유형을 판정한다.
입력변수:
  <<candidate_type>>  후보 유형명 (예: URLA_1003)
  <<signal_summary>>  규칙 단계에서 매칭된 신호 요약 (JSON)
  <<page_text>>       페이지 원문 텍스트
출력스키마: {"type": str|null, "subtype": str|null, "evidence": [str]}
  - type: 후보 유형명 그대로 / 아니면 null / 판단 불가면 "UNRESOLVED"
근거문서: docs/classification/urla.md §3-3 (S=1 → DEFER_LLM)
-->

당신은 모기지 대출 서류 페이지의 유형을 판정한다. 규칙 엔진이 이 페이지에서
약한 신호 1개만 발견해 판단을 넘겼다.

후보 유형: **<<candidate_type>>**

규칙 단계가 발견한 신호:

```json
<<signal_summary>>
```

## 지시

1. 아래 페이지 원문을 읽고, 이 페이지가 후보 유형에 속하는지 판단하라.
2. 판단 근거는 페이지에 실제로 존재하는 문구여야 한다 (evidence에 인용).
3. 확신이 없으면 type을 "UNRESOLVED"로 하라. 추측하지 마라.
4. 후보 유형이 맞다면 컴포넌트 subtype도 판단하라
   (main / additional_borrower / unmarried_addendum / continuation_sheet /
   lender_loan_information — 판단 불가면 null).

## 출력

JSON 하나만 출력하라:

```json
{"type": "<<candidate_type>>" 또는 null 또는 "UNRESOLVED", "subtype": "...", "evidence": ["..."]}
```

## 페이지 원문

<<page_text>>
