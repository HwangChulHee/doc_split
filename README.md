# docsplit

Page classification and document grouping for merged mortgage loan document packages.

Takes a shuffled multi-document PDF package and classifies each page
(`URLA_1003` / `INCOME_DOC` / `CREDIT_REPORT` / `TITLE_REPORT` / `OTHER`),
then groups pages into documents.

## Setup

```bash
uv sync
```

Place the provided PDFs in `data/` (original filenames, not committed).

## Usage

Parse all PDFs in `data/` and write page-level extractions, inspection
exports, and summary stats to `outputs/`:

```bash
uv run python -m docsplit.parse --data-dir data --out-dir outputs
```

## Layout

- `src/docsplit/` — pipeline code
- `data/` — input PDFs (gitignored)
- `outputs/` — parsing artifacts (gitignored)
- `results/` — final deliverables (committed)
- `docs/assignment.md` — assignment description
