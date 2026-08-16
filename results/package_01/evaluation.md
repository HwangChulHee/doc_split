# 패키지 01 검증 결과 (정답 대조)

- 페이지 39장 중 **38장 정확** (accuracy **0.974**)
- macro F1: **0.985**

## 유형별 정밀도·재현율

| 유형 | precision | recall | F1 | 정답 장수 |
|---|---|---|---|---|
| CREDIT_REPORT | 1.000 | 1.000 | 1.000 | 18 |
| INCOME_DOC | 1.000 | 1.000 | 1.000 | 1 |
| TITLE_REPORT | 1.000 | 0.889 | 0.941 | 9 |
| UNRESOLVED | 0.000 | 0.000 | 0.000 | 0 |
| URLA_1003 | 1.000 | 1.000 | 1.000 | 11 |

## 혼동 행렬 (정답 → 예측)

- **CREDIT_REPORT** → CREDIT_REPORT 18장
- **INCOME_DOC** → INCOME_DOC 1장
- **TITLE_REPORT** → TITLE_REPORT 8장, UNRESOLVED 1장
- **URLA_1003** → URLA_1003 11장

## 오분류 상세

| 페이지(0-based) | 정답 | 예측 |
|---|---|---|
| 7 | TITLE_REPORT | UNRESOLVED |

## 그룹핑·정렬

정답 원본의 페이지 순서와 비교한다. `순서 일치`는 복원된 순서가 원본 순서와 같다는 뜻이다.

### CREDIT_REPORT
- `credit_1`: 18장, 정렬 CODE_B_FALLBACK_ORDER → ❌ 순서 불일치, 미해결 [6, 10, 16, 22]

### INCOME_DOC
- 그룹핑 미배정: [35]

### TITLE_REPORT
- `title_1`: 8장, 정렬 CODE_A_PAGE_MARKER → ✅ 순서 일치

### URLA_1003
- `urla_1`: 11장, 정렬 CODE_A_PAGE_MARKER → ✅ 순서 일치

