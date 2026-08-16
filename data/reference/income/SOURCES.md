# INCOME 준거 문서 출처

다운로드 일자: **2026-08-17**

## 커밋 정책 — 파일마다 다르다

| 경로 | 발행 주체 | 커밋 |
|---|---|---|
| `irs/forms/*.pdf` | IRS (미국 정부 저작물) | ✅ |
| `irs/transcript_types.html` | IRS (irs.gov 페이지) | ✅ |
| `irs/transcripts/*.pdf` | **NASFAA** (© 2019, All rights reserved) | ❌ gitignore |
| `vendors/*.html` | **Fannie Mae** Selling Guide | ❌ gitignore |

IRS 발행물은 미국 정부 저작물이라 저작권이 없다. NASFAA·Fannie 자료는 제3자
저작물이므로 로컬 보관·분석만 하고 URL로 재확보 가능하게 남긴다
(TITLE의 ALTA 폼과 같은 취급).

## 근거 등급

| 문서 | 성격 | 등급 |
|---|---|---|
| IRS 양식 blank | IRS가 제정·발행한 양식 원본 | **정부 표준** |
| irs.gov transcript 종류 안내 | IRS 공식 설명 | **정부 표준** |
| NASFAA Tax Transcript Decoder | 업계 협회가 IRS 산출물 샘플을 전재·주석 | **제3자 전재** (원본은 IRS 출력) |
| Fannie Selling Guide B3-3.7-04 | GSE 인수 지침 | **업계 규범** (양식 표준 아님) |
| Xactus TWN Indicator Sample | 벤더 제품 샘플 | **벤더 문서** |

## 1. IRS transcript 준거

| 파일 | 원본 URL | 비고 |
|---|---|---|
| `irs/transcripts/nasfaa_tax_transcript_decoder.pdf` | https://askregs.nasfaa.org/uploads/resources/2020-21_Tax_Transcript_Decoder_v1_Final_November_2019.pdf | 23p. **Tax Return Transcript 샘플(p8–12)과 Wage & Income Transcript 샘플(p16)을 전재**. 2018 과세연도 기준, 가공 인물(`LUCY/JOHN MATT…`) |
| `irs/transcript_types.html` | https://www.irs.gov/individuals/transcript-types-for-individuals-and-ways-to-order-them | transcript 5종의 공식 명칭·설명. W&I가 커버하는 정보신고서(W-2/1098/1099/5498) 명시 |

**확보 실패 1건**: `irs.gov/individuals/frequently-asked-questions-about-the-customer-file-number`
→ `HTTP 503` (시스템 점검). `Customer File Number`의 도입 경위를 IRS 문서로
확인하지 못했다 — 분석 보고서 §10 UNCERTAIN에 기록.

## 2. IRS 양식 blank (미관찰 하위군 대비 — 대조 대상 아님)

| 파일 | 원본 URL | 페이지 | OMB |
|---|---|---|---|
| `irs/forms/fw2.pdf` | https://www.irs.gov/pub/irs-pdf/fw2.pdf | 11p | 1545-0029 |
| `irs/forms/f1040.pdf` | https://www.irs.gov/pub/irs-pdf/f1040.pdf | 2p | 1545-0074 |
| `irs/forms/f4506c.pdf` | https://www.irs.gov/pub/irs-pdf/f4506c.pdf | 2p | (Catalog 72627P) |
| `irs/forms/f1099msc.pdf` | https://www.irs.gov/pub/irs-pdf/f1099msc.pdf | 6p | 1545-0115 |
| `irs/forms/f1099nec.pdf` | https://www.irs.gov/pub/irs-pdf/f1099nec.pdf | 6p | 1545-0116 |

**확보 실패 1건**: Fannie Form 1005 (VOE) — `singlefamily.fanniemae.com` 다운로드
링크가 `HTTP 403`. VOE 어휘는 이번 수집에서 빠졌다.

## 3. P&L — 형식 표준 부재의 근거

| 파일 | 원본 URL |
|---|---|
| `vendors/fannie_b3-3.7-04_pl_statements.html` | https://selling-guide.fanniemae.com/sel/b3-3.7-04/analyzing-profit-and-loss-statements |

이 문서가 P&L에 요구하는 것은 **내용**뿐이고 **양식**이 아니다. 확인된 표현:

> "A typical profit and loss statement has a format similar to IRS Form 1040, Schedule C."

즉 GSE조차 "Schedule C와 비슷한 형식"이라는 **유사성 서술**에 그치며, 특정 서식·
템플릿을 요구하지 않는다. 감사 여부도 무관("audited or unaudited")하다.
**이 부재 자체가 P&L 관련 결론이다** — 준거로 검증할 대상이 존재하지 않는다.

## 4. TWN 샘플 — 중복 보관하지 않음

`data/reference/credit/xactus/twn_indicator_sample.pdf` (CREDIT 세션에서 확보,
이미 커밋됨)를 그대로 참조한다. 대조 스크립트도 그 경로를 읽는다.
출처: https://xactus.com/wp-content/uploads/2025/06/TWN-Indicator-Sample.pdf

## 5. 확보하지 않은 것 (의도적)

공개 웹에 실물 IRS transcript PDF가 다수 있으나 **실존 납세자 정보를 담을 수
있으므로 받지 않았다.** 확보한 transcript 샘플은 NASFAA가 가공 인물로 만든
교육용 전재본 하나뿐이다.

무결성: 확보한 7개 파일 전부 정상 오픈·텍스트 추출 확인.
