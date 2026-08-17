"""Draw each package's classification as a band of one cell per page.

    uv run python scripts/visualize_results.py

Reads `results/package_<label>/classification.csv` and writes
`classification_map.png` beside it. The cells run left to right in the shuffled
input order, so the picture answers "what did each page turn out to be" at a
glance — the same table the CSV holds, read as a sequence instead of as rows.

Nothing but page numbers, type names and counts reaches the image: no page text,
no subtypes, no evidence. The labels are ASCII on purpose — a Korean title would
need a CJK font the reviewer's machine may not have, and the committed PNG has to
be reproducible anywhere.

matplotlib is a dev dependency; `docsplit run` does not import this module.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

# The four types carry identity, so they get the four hues, assigned by name and
# never by frequency — a type keeps its colour across both packages. Validated
# all-pairs (any two can end up adjacent in a shuffled order): worst CVD ΔE 9.2,
# worst normal-vision ΔE 16.3 on the light surface.
TYPE_COLORS = {
    "URLA_1003": "#2a78d6",
    "CREDIT_REPORT": "#eb6834",
    "TITLE_REPORT": "#1baf7a",
    "INCOME_DOC": "#4a3aa7",
    # Not identities but outcomes — "the four did not apply" and "nothing was
    # decided". Neutrals, so they never read as a fifth or sixth document type.
    "OTHER": "#c3c2b7",
    "UNRESOLVED": "#898781",
}

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"

CELL_IN = 0.26  # one page's width; constant so both packages' cells match
BAND_IN = 0.62
DPI = 150
GAP_PX = 2  # surface gap between cells, in place of a border around each


def _contrast(hex_a: str, hex_b: str) -> float:
    """WCAG contrast ratio between two hex colours."""

    def luminance(value: str) -> float:
        channels = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    light, dark = sorted((luminance(hex_a), luminance(hex_b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _ink_on(fill: str) -> str:
    """Whichever of the two inks is legible on this fill."""
    return max((INK_PRIMARY, "#ffffff"), key=lambda ink: _contrast(ink, fill))


def read_cells(csv_path: Path) -> list[tuple[int, str]]:
    """(1-based page, category) per row, in the input's page order.

    A page the pipeline left undecided has an empty type column and grade
    UNRESOLVED; it is shown as such rather than dropped.
    """
    with csv_path.open(encoding="utf-8") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: int(r["page"]))
    cells = []
    for row in rows:
        category = row["type"].strip() or row["grade"].strip() or "UNRESOLVED"
        if category not in TYPE_COLORS:
            raise SystemExit(f"{csv_path}: 색을 정하지 않은 분류값 '{category}'")
        cells.append((int(row["page_display"]), category))
    return cells


def draw(label: str, cells: list[tuple[int, str]], out_path: Path) -> None:
    counts = {name: 0 for name in TYPE_COLORS}
    for _, category in cells:
        counts[category] += 1
    present = [name for name in TYPE_COLORS if counts[name]]

    fig_w = len(cells) * CELL_IN + 0.8
    fig_h = BAND_IN + 1.35
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=DPI, facecolor=SURFACE)

    fig.text(0.4 / fig_w, 1 - 0.30 / fig_h, f"package_{label}",
             color=INK_PRIMARY, fontsize=13, fontweight="bold", va="top")
    fig.text(0.4 / fig_w, 1 - 0.55 / fig_h,
             f"{len(cells)} pages, left to right in the shuffled input order"
             "  ·  number = page (1-based)",
             color=INK_SECONDARY, fontsize=8.5, va="top")

    ax = fig.add_axes([0.4 / fig_w, 0.62 / fig_h, 1 - 0.8 / fig_w, BAND_IN / fig_h])
    ax.set_xlim(0, len(cells))
    ax.set_ylim(0, 1)
    ax.axis("off")

    gap = GAP_PX / DPI / CELL_IN  # 2px expressed in cell widths
    for index, (page, category) in enumerate(cells):
        fill = TYPE_COLORS[category]
        ax.add_patch(Rectangle((index + gap / 2, 0), 1 - gap, 1,
                               facecolor=fill, edgecolor="none"))
        ax.text(index + 0.5, 0.5, str(page), ha="center", va="center",
                fontsize=6.5, color=_ink_on(fill))

    # Laid out in inches so entry spacing follows the text width instead of a
    # guessed fraction of the axes.
    band_w = fig_w - 0.8
    legend = fig.add_axes([0.4 / fig_w, 0.16 / fig_h, band_w / fig_w, 0.3 / fig_h])
    legend.set_xlim(0, band_w)
    legend.set_ylim(0, 1)
    legend.axis("off")
    x = 0.0
    for name in present:
        entry = f"{name}  {counts[name]}"
        legend.add_patch(Rectangle((x, 0.34), 0.11, 0.34,
                                   facecolor=TYPE_COLORS[name], edgecolor="none"))
        legend.text(x + 0.17, 0.51, entry, ha="left", va="center",
                    fontsize=8, color=INK_SECONDARY)
        x += 0.17 + len(entry) * 0.055 + 0.30  # swatch + text + breathing room
    legend.text(band_w, 0.51, f"results/package_{label}/classification.csv",
                ha="right", va="center", fontsize=7, color=INK_MUTED)

    fig.savefig(out_path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)
    print(f"{out_path}  ({len(cells)} cells, {', '.join(f'{n} {counts[n]}' for n in present)})")


def main() -> None:
    ap = argparse.ArgumentParser(description="분류 결과를 페이지 순서 색띠로 그린다")
    ap.add_argument("--results-dir", type=Path, default=Path("results"))
    ap.add_argument("--label", action="append",
                    help="패키지 라벨 (생략하면 results/ 안의 전부)")
    args = ap.parse_args()

    dirs = ([args.results_dir / f"package_{label}" for label in args.label]
            if args.label else sorted(args.results_dir.glob("package_*")))
    if not dirs:
        raise SystemExit(f"{args.results_dir}/ 에 package_* 가 없다 — 먼저 docsplit run")
    for package_dir in dirs:
        csv_path = package_dir / "classification.csv"
        if not csv_path.exists():
            raise SystemExit(f"{csv_path} 가 없다 — 먼저 docsplit run")
        label = package_dir.name.removeprefix("package_")
        draw(label, read_cells(csv_path), package_dir / "classification_map.png")


if __name__ == "__main__":
    main()
