# docsplit

Page-level classification and document grouping for merged mortgage loan
document packages.

A loan package arrives as a single PDF holding several distinct documents whose
pages have been shuffled together. `docsplit` classifies each page by document
type (`URLA_1003` / `CREDIT_REPORT` / `TITLE_REPORT` / `INCOME_DOC` / `OTHER`),
groups the pages back into document instances, and restores their order.

## Quick Start

```bash
git clone <repo> && cd doc_split
```

Put the PDFs you were given into `data/` — original file names, no subdirectory
layout required. A file whose name contains `shuffled` is treated as a package
to classify; the others are treated as answer keys and typed by a keyword in
their name (`1003`/`URLA`, `Credit`, `Title`, `INCOME`/`P&L`, …).

```bash
cp .env.example .env      # put your OPENAI_API_KEY in it
uv run docsplit run
```

Outputs:

| 경로 | 내용 |
|---|---|
| `results/package_<label>/` | 최종 결과 — 분류 CSV, 문서 구성 JSON, 요약, (정답이 있으면) 검증 리포트 |
| `outputs/` | 중간 산출물 — 페이지 원문, 신호 카드, LLM 캐시. 개인정보를 포함하므로 커밋하지 않는다 |

API 키 없이 규칙 판정만 돌려보려면:

```bash
uv run docsplit run --no-llm
```

옵션: `--data-dir` `--out-dir` `--results-dir` `--no-llm`

## 접근 방식 요약

규칙은 **표본에서 귀납하지 않고 준거 문서에서 연역한다.** 결정적 신호로 쓰는
문구는 공개된 표준 양식·정부 발행물·벤더 제품 문서에서 확인된 것이어야 하며,
데이터셋에서만 관찰된 문구(렌더러 코드, 페이지 번호 체계, 입력값)는 규칙이 아니라
그룹핑 근거로만 쓴다.

<!-- TODO: 신호 계층(normative/domain/vendor/deployment) 모델과 근거 등급 설명 -->

## 파이프라인 구조

```text
data/*.pdf
   │
   ▼
[1] 텍스트 추출            PyMuPDF, 페이지별 원문 + 메타데이터
   │
   ▼
[2] 규칙 분류              4개 정책을 페이지마다 동시 평가
   │                      → 한 유형만 결정적이면 확정, 겹치면 LLM으로
   ▼
[3] LLM / VLM 판정         규칙이 못 정한 페이지만. 텍스트 없는 페이지는 이미지로
   │
   ▼
[4] 신호 카드              regex + PDF 좌표로 그룹핑 근거 추출
   │
   ▼
[5] 그룹핑                 LLM — 같은 문서의 페이지끼리 instance로
   │
   ▼
[6] 순서 복원              코드 — 페이지 마커 우선, 없으면 구성 순서 폴백
   │
   ▼
results/
```

<!-- TODO: 각 단계의 입출력과 판정 우선순위 상세 -->

## 설계 원칙과 근거

유형마다 기준서가 있고, 그 기준서는 준거 문서 대조 분석에 근거한다.

| 유형 | 기준서 | 근거 분석 |
|---|---|---|
| URLA_1003 | [urla.md](docs/classification/urla.md) | [urla_standard_analysis.md](docs/analysis/urla_standard_analysis.md) |
| CREDIT_REPORT | [credit_report.md](docs/classification/credit_report.md) | [credit_vendor_analysis.md](docs/analysis/credit_vendor_analysis.md) |
| TITLE_REPORT | [title_report.md](docs/classification/title_report.md) | [title_standard_analysis.md](docs/analysis/title_standard_analysis.md) |
| INCOME_DOC | [income_doc.md](docs/classification/income_doc.md) | [income_standard_analysis.md](docs/analysis/income_standard_analysis.md) |

도메인 배경: [domain_knowledge.md](docs/domain_knowledge.md)

<!-- TODO: 핵심 설계 결정 5~6개를 근거와 함께 요약 (준거 등급, 임계값을 튜닝하지
     않는 이유, OTHER에 정책을 두지 않는 이유, 실패를 남기는 이유) -->

## 결과

<!-- TODO: 아래 수치는 results/ 산출물에서 옮겨온 것 — 재실행 시 갱신 -->

정답 원본이 제공된 패키지 기준:

- 페이지 분류 accuracy **0.949** (39장 중 37장), macro F1 **0.735**
- URLA_1003 / CREDIT_REPORT F1 1.000, TITLE_REPORT 0.941, INCOME_DOC 0.000

상세: [results/package_01/evaluation.md](results/package_01/evaluation.md)
정답이 없는 패키지의 산출: [results/package_02/summary.md](results/package_02/summary.md)

## 알려진 한계와 개선 방향

<!-- TODO: 각 항목의 근거 문서 링크 -->

- **정해진 서식이 없는 문서**(차주가 직접 작성한 손익 명세)는 규칙으로 잡히지
  않는다. 형식 표준이 존재하지 않음이 GSE 지침으로 확인됐고, 어휘 프로브 32종이
  전부 0건이었다. LLM 의미 판단이 유일한 경로이며 현재 오답이 남아 있다.
- **내용이 제거된 페이지**(도면 자리)는 텍스트 근거가 없어 미판정으로 남긴다.
- **같은 문서의 두 출력본 분리**는 페이지 마커 중복으로 감지하지만, 두 벌을
  장 단위로 짝지을 근거가 신호 카드에 실리지 않아 미해결이다.
- 그룹핑·순서 복원은 유형별로 편차가 있다 — 페이지 마커가 있는 유형은 정확하고,
  없는 유형은 구성 순서 폴백에 의존한다.

## 프로젝트 구조

```text
src/docsplit/
  cli.py            docsplit run — 통합 실행
  discover.py       입력 파일 역할 인식
  unified.py        4개 정책 동시 평가 + 판정 우선순위
  pdf_parser.py     텍스트 추출
  signals.py        정책 로딩·신호 평가
  classify.py       결합 규칙(등급 산출)
  cards.py          신호 카드 추출
  grouping.py       그룹핑(LLM 호출) + 순서 복원(코드)
  llm.py            OpenAI 래퍼, 프롬프트 렌더링, 디스크 캐시
  evaluate.py       개발용 검증(V1~V6)
  results.py        results/ 산출물
  policies/*.yaml   유형별 신호 정의
  prompts/*.md      LLM 지시문
docs/               도메인 지식, 유형별 기준서, 준거 대조 분석, 핸드오프
scripts/            준거 문서 대조용 일회성 관찰 스크립트
tests/              결합 규칙·순서 경로 단위 테스트
config/             개발용 검증 기대값 (실행에는 불필요)
data/reference/     공개 준거 문서 (표준 양식·정부 발행물)
```

개발 중에는 유형별 파이프라인을 따로 돌릴 수 있다 (검증 리포트 포함):

```bash
uv run python -m docsplit.urla_pipeline --package both
```
