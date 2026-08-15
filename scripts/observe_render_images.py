"""One-off: render specific PDF pages to PNG for human inspection.

Usage:
  uv run python scripts/observe_render_images.py <pdf> <out_dir> <page_idx> [...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf


def main() -> None:
    pdf_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = [int(a) for a in sys.argv[3:]]
    with pymupdf.open(pdf_path) as doc:
        for idx in pages:
            pix = doc[idx].get_pixmap(dpi=150)
            out = out_dir / f"{pdf_path.stem}_page_{idx:03d}.png"
            pix.save(out)
            print(f"wrote {out}")


if __name__ == "__main__":
    main()
