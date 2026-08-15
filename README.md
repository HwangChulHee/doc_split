# docsplit

Page classification and document grouping for merged mortgage loan document packages.

Takes a shuffled multi-document PDF package and classifies each page
(`URLA_1003` / `INCOME_DOC` / `CREDIT_REPORT` / `TITLE_REPORT` / `OTHER`),
then groups pages into documents.

## Setup

```bash
uv sync
```

Place the provided PDFs under `data/` (original filenames, not committed):

- `data/packages/` — shuffled input packages
- `data/ground_truth/` — original per-document PDFs (answer key for package 01)
- `data/reference/` — public blank forms (committed; see `data/reference/urla/SOURCES.md`)

## Usage

Parse all PDFs in `data/` and write page-level extractions, inspection
exports, and summary stats to `outputs/`:

```bash
uv run python -m docsplit.parse --data-dir data --out-dir outputs
```

## Layout

- `src/docsplit/` — pipeline code
- `scripts/` — one-off observation/analysis scripts
- `data/` — input PDFs (gitignored except `data/reference/`)
- `outputs/` — parsing artifacts (gitignored)
- `results/` — final deliverables (committed)
- `docs/` — assignment (`assignment.md`), domain notes (`domain_knowledge.md`),
  analysis reports (`analysis/`), session handoffs (`handoffs/`)
