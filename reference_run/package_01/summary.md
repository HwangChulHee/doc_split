# 패키지 01 요약

전체 **39페이지**.

## 유형 분포

| 유형 | 페이지 수 |
|---|---|
| CREDIT_REPORT | 18 |
| URLA_1003 | 11 |
| TITLE_REPORT | 8 |
| UNRESOLVED | 1 |
| INCOME_DOC | 1 |

## 판정 경로

| 경로 | 페이지 수 |
|---|---|
| deferred | 1 |
| llm | 2 |
| rule | 36 |

## 정답 대조

- accuracy **0.974** (38/39)
- macro F1 **0.985**
- 상세는 `evaluation.md` 참조

## 문서 구성

총 **5개 문서 instance**로 묶였다.

- **CREDIT_REPORT**: 1개 instance (18장)
    - `credit_1` 순서 미해결: [6, 10, 16, 22]
- **INCOME_DOC**: 1개 instance (1장)
- **TITLE_REPORT**: 1개 instance (8장)
- **URLA_1003**: 2개 instance (4장, 7장)

## 미해결 페이지

유형을 확정하지 못한 페이지: [7]

## LLM 사용량 (이번 실행분)

| 단계 | 호출 | 캐시 적중 | prompt 토큰 | completion 토큰 |
|---|---|---|---|---|
| classify_page | 7 | 0 | 11,775 | 553 |
| classify_page_vision | 3 | 0 | 9,963 | 491 |
| grouping | 8 | 0 | 45,122 | 3,374 |

추정 비용: **$0.0700** (모델 gpt-5.4-mini, 단가 1M 토큰당 입력 $0.75/출력 $4.5 가정)

이 캐시로 지금까지 실제 지출한 누계: **$0.0700** (호출 18회, 개발 중 반복 실행 포함)
