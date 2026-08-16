# 패키지 02 요약

전체 **44페이지**.

## 유형 분포

| 유형 | 페이지 수 |
|---|---|
| CREDIT_REPORT | 15 |
| TITLE_REPORT | 13 |
| URLA_1003 | 10 |
| INCOME_DOC | 4 |
| OTHER | 1 |
| UNRESOLVED | 1 |

## 판정 경로

| 경로 | 페이지 수 |
|---|---|
| deferred | 1 |
| llm | 3 |
| rule | 37 |
| vlm | 3 |

## 정답 대조

이 패키지는 정답 원본이 제공되지 않아 대조하지 않았다 — 분류 결과만 산출한다.

## 문서 구성

총 **4개 문서 instance**로 묶였다.

- **CREDIT_REPORT**: 1개 instance (15장)
    - `credit_1` 순서 미해결: [3, 9, 31]
- **INCOME_DOC**: 1개 instance (3장)
    - `income_1` 순서 미해결: [11, 26, 30]
    - 어느 instance에도 배정하지 못한 페이지: [35]
- **TITLE_REPORT**: 1개 instance (9장)
    - `title_1` 순서 미해결: [6]
    - 어느 instance에도 배정하지 못한 페이지: [4, 25, 29, 39]
- **URLA_1003**: 1개 instance (10장)

## 미해결 페이지

유형을 확정하지 못한 페이지: [38]

## LLM 사용량 (이번 실행분)

| 단계 | 호출 | 캐시 적중 | prompt 토큰 | completion 토큰 |
|---|---|---|---|---|
| classify_page | 0 | 7 | 0 | 0 |
| classify_page_vision | 0 | 3 | 0 | 0 |
| grouping | 0 | 7 | 0 | 0 |

추정 비용: **$0.0000** (모델 gpt-5.4-mini, 단가 1M 토큰당 입력 $0.25/출력 $2.0 가정)

> 호출 0건은 **전부 캐시로 처리됐다는 뜻**이다 (`outputs/llm_cache/`). 캐시가 없는 첫 실행의 실측치는 `outputs/llm_usage.json` 의 `cumulative` 에 누적된다.
