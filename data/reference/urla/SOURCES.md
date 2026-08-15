# URLA 공식 양식 출처

두 GSE가 공동 발행하는 동일 양식을 발행처별로 확보. 파일명은 양쪽 디렉토리에서 동일하게 통일
(컴포넌트가 같으면 같은 이름). 원본 다운로드 파일명은 아래 표에 기록.

## `freddiemac/` — Freddie Mac 판

다운로드 일자: **2026-08-15**, curl로 직접 다운로드.
출처 페이지: `https://sf.freddiemac.com/tools-learning/uniform-mortgage-data-program/ulad`
(Fannie Mae 페이지가 Cloudflare 차단이라 먼저 확보한 쪽)

| 파일 | 원본 URL | 비고 |
|---|---|---|
| `urla_borrower_information_blank.pdf` | https://sf.freddiemac.com/docs/pdf/forms/urla_borrower_information.pdf | 본체 9p, Effective 1/2021 |
| `urla_additional_borrower_blank.pdf` | https://sf.freddiemac.com/docs/pdf/forms/urla_additional_borrower.pdf | 4p |
| `urla_unmarried_addendum_blank.pdf` | https://sf.freddiemac.com/docs/pdf/forms/urla_unmarried_addendum.pdf | 1p |
| `urla_lender_loan_information_blank.pdf` | https://sf.freddiemac.com/docs/pdf/forms/urla_lender_loan_information.pdf | 2p |
| `urla_continuation_sheet_blank.pdf` | https://sf.freddiemac.com/docs/pdf/forms/urla_continuation_sheet.pdf | 1p |
| `urla_instructions.pdf` | https://sf.freddiemac.com/docs/pdf/fact-sheet/urla_instructions.pdf | 지침 15p |
| `scif_form_1103_blank.pdf` | https://sf.freddiemac.com/docs/pdf/forms/scif-form-1103-english.pdf | SCIF 1p, 5/2022 |

## `fanniemae/` — Fannie Mae 판

다운로드 일자: **2026-08-15**, Cloudflare 차단으로 사용자가 브라우저에서 수동 다운로드.
출처 페이지: `https://singlefamily.fanniemae.com/delivering/uniform-mortgage-data-program/uniform-residential-loan-application`

| 파일 | 다운로드 원본 파일명 | 비고 |
|---|---|---|
| `urla_borrower_information_blank.pdf` | `URLA-2019-Borrower-v28.pdf` | 9p. Freddie 판과 문구 동일, 텍스트 레이어 상이 |
| `urla_additional_borrower_blank.pdf` | `URLA_2019_Addl_Borrower_v28.pdf` | Freddie 판과 **바이트 동일** (md5 일치) |
| `urla_unmarried_addendum_blank.pdf` | `URLA_2019_Unmarried_v28.pdf` | Freddie 판과 **바이트 동일** |
| `urla_continuation_sheet_blank.pdf` | `URLA_2019_Continuation_v28.pdf` | Freddie 판과 **바이트 동일** |
| `urla_lender_loan_information_blank.pdf` | `URLA-2019-Lender-v28.pdf` | 2p. 문구 동일, 텍스트 레이어 상이 |
| `urla_instructions.pdf` | `URLA_Instructions updated 11-12-2024.pdf` | Revised 11/2024 (Freddie 소장본보다 최신 개정) |
| `scif_form_1103_blank.pdf` | `SCIF Form 1103 updated 7-06-22.pdf` | 푸터 버전 5/2022 동일, 파일 상이 |
