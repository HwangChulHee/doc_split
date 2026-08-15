<!--
목적: URLA로 판정된 페이지들을 문서 instance 단위로 그룹핑한다.
입력변수:
  <<expected_type>>   유형명 (URLA_1003)
  <<cards_json>>      페이지별 신호 카드 JSON 배열
  <<attached_texts>>  신호 빈약 페이지의 원문 (없으면 "(없음)")
출력스키마: {"instances": [{"instance_id": str, "pages": [int], "evidence": [str]}],
            "unresolved_pages": [int], "notes": str}
근거문서: docs/classification/urla.md §5 (지시 요지를 이 프롬프트로 옮김)
-->

당신은 모기지 대출 서류 패키지에서 <<expected_type>> 페이지들을 문서 instance 단위로
묶는 작업을 수행한다. 아래 신호 카드는 페이지별로 기계 추출된 **후보**이며 오탐을
포함할 수 있다. 판단은 당신의 몫이다.

## 지시

1. **기대값**: URLA는 통상 패키지당 1부다. 이름이 단일하고 페이지 표기가 단일
   세트로 맞아떨어지면 1개 instance로 확정하라.
2. **신호 역할**:
   - 이름(name_candidates) 일치 = **주력 그룹핑 근거**
   - ULI/대출번호(id_candidates) 일치 = **앵커** — 등장하는 페이지에서 확정력 최고
   - 페이지 표기(page_marker_candidates) = **경보 전용**: 같은 번호가 중복되면
     (예: "3 of 11"이 두 장) 다중 instance를 의심하라. 표기 자체를 그룹핑
     근거로 쓰지는 마라.
   - 위 신호가 부족한 페이지만 동봉 원문으로 내용 기반 판단하라.
3. 같은 이름의 **다중 instance 가능성**(재제출본)을 배제하지 마라. 분리 근거:
   페이지 번호 중복, ULI 상이, 서명 타임스탬프 상이.
4. 모든 판단에 **evidence 필수** — 어떤 신호(값)와 어떤 페이지가 근거인지 명시.
   확신이 없으면 해당 페이지를 unresolved_pages에 넣어라. 추측으로 배정하지 마라.

## 출력

JSON 하나만 출력하라. 스키마:

```json
{
  "instances": [
    {"instance_id": "urla_1", "pages": [5, 37], "evidence": ["..."]}
  ],
  "unresolved_pages": [],
  "notes": "..."
}
```

- `pages`는 입력 카드의 `page` 값(0-based)을 그대로 사용
- `evidence`는 구체적으로: 신호 종류, 값(이름·ID는 그대로 인용 가능), 해당 페이지
- 순서 정렬은 하지 마라 — 그룹핑만 한다

## 신호 카드

<<cards_json>>

## 신호 빈약 페이지 원문

<<attached_texts>>
