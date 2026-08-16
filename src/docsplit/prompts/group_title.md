<!--
목적: TITLE_REPORT로 판정된 페이지들을 문서(instance) 단위로 묶는다.
입력변수:
  <<expected_type>>   유형명 (TITLE_REPORT)
  <<cards_json>>      페이지별 신호 카드 JSON 배열
  <<attached_texts>>  신호 빈약 페이지의 원문 (없으면 "(없음)")
출력스키마: {"instances": [{"instance_id": str, "pages": [int], "evidence": [str],
                          "related_to": {"instance_id": str, "relation": str, "differs_in": [str]}}],
            "unresolved_pages": [int], "notes": str}
근거문서: docs/classification/title_report.md §4-2 (지시 요지를 이 프롬프트로 옮김)
-->

당신은 모기지 대출 서류 패키지에서 <<expected_type>> 페이지들을 **문서 단위**로
묶는 작업을 수행한다. 아래 신호 카드는 페이지별로 기계 추출된 **후보**이며
오탐을 포함할 수 있다. 판단은 당신의 몫이다.

## 배경

Title 문서는 지역 관습에 따라 두 형태로 존재한다 — Preliminary Report(CLTA 계열)와
Title Commitment(ALTA 계열). 한 문서는 Schedule A / Legal Description /
Schedule B Part I·II / 약관 같은 여러 장으로 구성된다.

**이 유형에서는 같은 거래의 문서가 여러 벌 존재할 수 있다.** 아래 2번 지시가
그 처리 방법이며, 이는 다른 유형의 "ID가 같으면 묶어라"와 방향이 다르다.

## 지시

1. **그룹핑 앵커**: 파일번호·Commitment Number 등 `id_candidates` 값이 일치하면
   같은 거래 계열이다.

2. ★ **마커 세트가 중복 완비되면 앵커가 전부 같아도 별도 instance로 분리하라.**
   예: `page_marker_candidates`에 `Page 1 of 5`가 두 장 있고, 2·3·4·5도 각각
   두 장씩 있다면 → 물리적으로 두 벌의 출력물이다. 문서는 물리적 출력 단위다.
   이때 반드시:
   - `evidence`에 **공유 앵커**(어떤 값이 두 벌에서 같은지)를 기록하고,
   - 두 벌 사이의 **상이 필드**를 찾아 기록하며(동봉 원문 또는 카드 값 대조),
   - 두 instance를 `related_to`로 서로 연결하라.

3. **쌍 맞추기**: 마커 번호가 같은 페이지들끼리 내용을 대조해 어느 장이 어느 벌에
   속하는지 정하라. 벌 간 차이는 매우 작을 수 있으니(값 한 줄 수준) 신중히 보라.
   근거가 서지 않으면 임의로 배정하지 말고 그 사실을 `notes`에 적어라.

4. **`vendor_identity`가 다르면 무조건 다른 instance다.** 서로 다른 title 회사가
   발행한 문서는 같은 문서가 될 수 없다.

5. **텍스트 근거가 없는 페이지는 인접성만으로 배정하지 마라.** 페이지 번호가
   가깝다는 이유로 묶는 것은 금지한다. 근거가 없으면 `unresolved_pages`에 넣어라.
   (입력 패키지는 페이지가 뒤섞여 있으므로 인접성 자체가 신호가 아니다)

6. 모든 판단에 **evidence 필수** — 어떤 신호(값)와 어떤 페이지가 근거인지 명시.
   확신이 없으면 unresolved. 추측으로 배정하지 마라.

## 출력

JSON 하나만 출력하라. 스키마:

```json
{
  "instances": [
    {
      "instance_id": "title_1",
      "pages": [0, 2],
      "evidence": ["..."],
      "related_to": {
        "instance_id": "title_2",
        "relation": "같은 거래의 다른 출력본으로 보임",
        "differs_in": ["..."]
      }
    }
  ],
  "unresolved_pages": [],
  "notes": "..."
}
```

- `pages`는 입력 카드의 `page` 값(0-based)을 그대로 사용
- `related_to`는 **관계가 확인된 경우에만** 넣는다 (없으면 필드 자체를 생략)
- `differs_in`에는 값 자체가 아니라 **어느 항목이 다른지**를 적어라
  (예: "보험금액 한 건", "발행 일자")
- `evidence`는 구체적으로: 신호 종류, 값, 해당 페이지
- 순서 정렬은 하지 마라 — 그룹핑만 한다

## 신호 카드

<<cards_json>>

## 신호 빈약 페이지 원문

<<attached_texts>>
