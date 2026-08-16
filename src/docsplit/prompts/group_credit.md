<!--
목적: CREDIT_REPORT로 판정된 페이지들을 신용조회 건(instance) 단위로 그룹핑한다.
입력변수:
  <<expected_type>>   유형명 (CREDIT_REPORT)
  <<cards_json>>      페이지별 신호 카드 JSON 배열
  <<attached_texts>>  신호 빈약 페이지의 원문 (없으면 "(없음)")
출력스키마: {"instances": [{"instance_id": str, "pages": [int], "evidence": [str]}],
            "unresolved_pages": [int], "notes": str}
근거문서: docs/classification/credit_report.md §6-1 (지시 요지를 이 프롬프트로 옮김)
-->

당신은 모기지 대출 서류 패키지에서 <<expected_type>> 페이지들을 **신용조회 건**
단위로 묶는 작업을 수행한다. 아래 신호 카드는 페이지별로 기계 추출된 **후보**이며
오탐을 포함할 수 있다. 판단은 당신의 몫이다.

## 배경

한 번의 신용조회는 여러 산출물을 낳는다 — 본 리포트(main_report), 점수 고지서
(score_disclosure), 소비자 안내 편지(consumer_letter), 주문 요약(order_summary).
이들은 **같은 조회 건이면 한 instance로 묶인다**. 점수 고지서가 렌더(대출기관)
레터헤드를 쓰더라도 소속이 바뀌지 않는다.

## 지시

1. **기대값**: 신용조회 1건당 산출물 패키지 1세트. 단, 재조회(Refresh/LQI)나
   Supplement로 같은 유형이 복수 존재할 수 있으므로 단정하지 마라.
2. **신호 역할**:
   - `report_id` 값 일치 = **주력 그룹핑 근거** (가장 강한 앵커)
   - `loan_number`, `client_code` = 보조 앵커
   - `date_candidates`(Ordered/Released/Reissued/편지 날짜) **상이** = 재조회 분리 근거.
     단, 같은 조회 건에서도 발행·재발행 날짜가 함께 인쇄될 수 있으니 날짜 하나가
     다르다고 즉시 분리하지 말고 report_id와 함께 판단하라.
   - `vendor_identity` 상이 = 다른 조회 건
   - `page_marker_candidates` = **경보 전용**: 같은 번호가 중복되면 다중 instance를
     의심하라. 표기 자체를 그룹핑 근거로 쓰지는 마라.
   - 위 신호가 부족한 페이지만 동봉 원문으로 내용 기반 판단하라.
3. **부속 문서(score_disclosure / consumer_letter / order_summary)는 본체와 같은
   instance로 묶되, `report_id`가 다르면 분리하라.**
4. 모든 판단에 **evidence 필수** — 어떤 신호(값)와 어떤 페이지가 근거인지 명시.
   확신이 없으면 해당 페이지를 unresolved_pages에 넣어라. 추측으로 배정하지 마라.

## 출력

JSON 하나만 출력하라. 스키마:

```json
{
  "instances": [
    {"instance_id": "credit_1", "pages": [0, 1], "evidence": ["..."]}
  ],
  "unresolved_pages": [],
  "notes": "..."
}
```

- `pages`는 입력 카드의 `page` 값(0-based)을 그대로 사용
- `evidence`는 구체적으로: 신호 종류, 값, 해당 페이지
- 순서 정렬은 하지 마라 — 그룹핑만 한다

## 신호 카드

<<cards_json>>

## 신호 빈약 페이지 원문

<<attached_texts>>
