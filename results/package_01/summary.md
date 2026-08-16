# 패키지 01 요약

전체 **39페이지**.

## 유형 분포

| 유형 | 페이지 수 |
|---|---|
| CREDIT_REPORT | 18 |
| URLA_1003 | 11 |
| TITLE_REPORT | 8 |
| UNRESOLVED | 1 |
| OTHER | 1 |

## 판정 경로

| 경로 | 페이지 수 |
|---|---|
| deferred | 1 |
| llm | 2 |
| rule | 36 |

## 정답 대조

- accuracy **0.949** (37/39)
- macro F1 **0.735**
- 상세는 `evaluation.md` 참조

## 문서 구성

총 **3개 문서 instance**로 묶였다.

- **CREDIT_REPORT**: 1개 instance (18장)
    - `credit_1` 순서 미해결: [6, 10, 16, 22]
- **TITLE_REPORT**: 1개 instance (8장)
- **URLA_1003**: 1개 instance (11장)

## 미해결 페이지

유형을 확정하지 못한 페이지: [7]

## LLM 사용량 (이번 실행분)

| 단계 | 호출 | 캐시 적중 | prompt 토큰 | completion 토큰 |
|---|---|---|---|---|
| classify_page | 0 | 7 | 0 | 0 |
| classify_page_vision | 0 | 3 | 0 | 0 |
| grouping | 0 | 7 | 0 | 0 |

추정 비용: **$0.0000** (모델 gpt-5.4-mini, 단가 1M 토큰당 입력 $0.25/출력 $2.0 가정)

> 호출 0건은 **전부 캐시로 처리됐다는 뜻**이다 (`outputs/llm_cache/`). 캐시가 없는 첫 실행의 실측치는 `outputs/llm_usage.json` 의 `cumulative` 에 누적된다.
