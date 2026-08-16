# docsplit

Page-level classification and document grouping for merged mortgage loan
document packages.

A loan package arrives as a single PDF holding several distinct documents whose
pages have been shuffled together. `docsplit` classifies each page by document
type (`URLA_1003` / `INCOME_DOC` / `CREDIT_REPORT` / `TITLE_REPORT` / `OTHER`)
and groups pages back into document instances, restoring their order.

The current implementation covers the `URLA_1003` type end to end; the engine is
policy-driven so additional types are added as policy and prompt files rather
than engine code.

## Approach

Rules are derived from official standards, not induced from the sample data:
signals used for deterministic classification must be verifiable against the
published GSE blank forms in `data/reference/`. Anything that turned out to be
renderer-specific (print codes, page numbering, form field values) is collected
as evidence for the LLM stages instead of being hardcoded as a rule.

```text
page text ──▶ [1] rule classification   (policies/urla.yaml)
                    │
                    ▼
              [2] signal cards          (regex + PDF geometry)
                    │
                    ▼
              [3] grouping              (LLM, prompts/group_urla.md)
                    │
                    ▼
              [4] ordering              (code path; standard section order fallback)
```

See `docs/classification/urla.md` for the design spec and
`docs/analysis/urla_standard_analysis.md` for the standards comparison behind it.

## Setup

```bash
uv sync
```

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` (only needed for the LLM
stages; `--no-llm` runs stages 1–2 without a key).

Place input PDFs under `data/` — the contents are gitignored:

- `data/packages/` — shuffled input packages
- `data/ground_truth/` — original per-document PDFs, when an answer key exists
- `data/reference/` — public blank forms (committed; see `data/reference/urla/SOURCES.md`)

## Usage

Parse every input PDF into page-level text, inspection exports, and stats:

```bash
uv run python -m docsplit.parse --data-dir data --out-dir outputs
```

Run the URLA pipeline (classification, grouping, ordering, verification):

```bash
uv run python -m docsplit.urla_pipeline --data-dir data --out-dir outputs
```

Options: `--no-llm` (stages 1–2 only), `--package {01,02,both}`.

Results land in `outputs/urla/` — `classification.jsonl`, `cards.jsonl`,
`grouping.json`, `ordering.json`, and a human-readable `report.md` carrying the
V1–V4 verification table.

## Layout

- `src/docsplit/` — pipeline code (`policies/` and `prompts/` hold the
  type-specific knowledge; the engine stays type-agnostic)
- `scripts/` — one-off observation and comparison scripts
- `data/` — input PDFs (gitignored except `data/reference/`)
- `outputs/` — parsing and pipeline artifacts (gitignored)
- `results/` — final deliverables
- `docs/` — domain notes, design specs (`classification/`), analysis reports
  (`analysis/`), session handoffs (`handoffs/`)

## Data handling

Input packages are not committed: `data/` is gitignored apart from
`data/reference/`, which holds publicly available blank forms. Committed
documents quote form labels and fixed template wording only — no borrower
values, and no page text extracted from the input packages.
