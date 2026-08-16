# TITLE 준거 문서 출처

다운로드 일자: **2026-08-16**

> **이 디렉터리는 SOURCES.md를 제외하고 전부 gitignore 대상이다.**
> ALTA 폼은 "The use of this Form (or any derivative thereof) is restricted to ALTA
> licensees and ALTA members in good standing as of the date of use. All other uses
> are prohibited." 표기를 달고 배포된다. 우리는 폼을 **발행·사용하는 것이 아니라
> 분류 신호의 전거로 참조**할 뿐이므로 로컬 보관·분석은 문제없으나, 공개 저장소에
> 재배포하지 않는다. 아래 URL로 언제든 재확보할 수 있다.
> (URLA의 GSE blank·CREDIT의 Xactus 가이드와 취급이 다른 지점이다.)

## 근거 등급

| 문서 | 성격 | 등급 |
|---|---|---|
| ALTA 2021 Commitment blank | 협회 제정 표준 폼 (미기입 blank) | **협회 표준 검증** |
| CA Insurance Code §12340.11 | 주 법령 | **법령** |
| Ticor Title 가이드 | 타이틀 회사 발행 교육 자료 | **벤더 문서 검증** |
| First American 소비자 안내 | 벤더 홍보·안내 페이지 | **참고** |

## 1. ALTA (pkg02 대응) — 확보 성공

| 파일 | 원본 URL | 비고 |
|---|---|---|
| `alta/alta_commitment_2021_floir.pdf` | https://floir.gov/docs-sf/property-casualty-libraries/title-insurance-2021-forms/alta-commitment-2021.pdf | 6p. 미기입 blank (`BLANK TITLE INSURANCE COMPANY`, 선택 구간은 `[...]` 표기) |

확보 경로 주의: 협회 사이트(`https://www.alta.org/policies-and-standards/policy-forms/`)와
직접 다운로드 링크(`.../downloadSub?formSubID=2159&type=pdf`)는 이 작업 시점에 **오리진 장애**
상태였다 (Cloudflare `HTTP 520` / `HTTP 526`, 재시도 5회 모두 동일). 따라서 **플로리다 주
보험규제청(Florida Office of Insurance Regulation)이 공개하는 title insurance 2021 폼
라이브러리**에서 동일 폼을 확보했다. 주 규제기관이 게시한 협회 폼 원본이며, 개별 거래
문서가 아니다. 문서 내부 표기로 진본성 확인: `[2021 v. 01.00 (07-01-2021)]`,
`Copyright 2021 American Land Title Association`, 발행사 자리가 `BLANK TITLE INSURANCE COMPANY`.

## 2. CLTA (pkg01 대응) — 확보 실패

| 시도 | 경로 | 결과 |
|---|---|---|
| 1 | CLTA 공식 (`https://www.clta.org/`) | ❌ 폼은 유료 구독 포털(`subscriptions.clta.org`) 뒤 — 공개 다운로드 없음 |
| 2 | 캘리포니아 보험국(CDI) | ❌ 공개되는 것은 **접수 목록**(`insurance.ca.gov/.../title-insur-rate-filings/`)뿐, 폼 본문 미공개 |
| 3 | 언더라이터 폼 라이브러리 (Stewart Virtual Underwriter) | ❌ `CLTA Preliminary Report Form, Exhibit A (Rev. 11-04-22)` 항목은 존재하나 본문은 로그인 벽 (미리보기 몇 줄만) |

대체 확보 — 법령 원문(폼이 아니므로 폼 대체는 아님):

| 파일 | 원본 URL | 비고 |
|---|---|---|
| `clta/ca_ins_code_12340_11.html` | https://california.public.law/codes/insurance_code_section_12340.11 | CA Ins. Code §12340.11 (preliminary report의 법적 성격). `leginfo.legislature.ca.gov` 직접 접근은 `HTTP 503` |

## 3. 벤더 자료 (보조)

| 파일 | 원본 URL | 비고 |
|---|---|---|
| `vendors/ticor_how_to_read_prelim_2023.html` | https://fntgstudio.s3.us-east-1.amazonaws.com/ttc/ca/ebooks/preliminaryreport/index.html | Ticor Title(=Fidelity National Title Group 계열) `How to Read a Preliminary Report` 2023판. **주석 달린 CLTA prelim 샘플 전문 수록** — pkg01 벤더 계열과 동일 그룹의 자료 |
| `vendors/firstam_understanding_title_commitment.html` | https://www.firstam.com/home-buying-guide/understanding-your-title-commitment/ | First American 소비자 안내. 구조 설명만 있고 고정 문구는 없음 |

Ticor 문서의 샘플은 자체 표기상 전부 가공값이다: *"All references to specific property,
dollar amounts, documents, and individual and corporate identification are fictional and for
the purpose of educational sample only."*

## 4. 확보하지 않은 것 (의도적)

공개 웹에는 실물 Preliminary Report·Commitment PDF가 다수 존재하나(지자체 회의자료, 경매
사이트 등) **개별 거래 문서이지 준거 문서가 아니며 개인정보를 포함할 수 있으므로 다운로드하지
않았다.** 검색 결과 목록에서 표기 존재 여부만 확인했다.

무결성: 확보한 4개 파일 전부 정상 오픈·텍스트 추출 확인.
