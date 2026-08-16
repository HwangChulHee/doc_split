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
