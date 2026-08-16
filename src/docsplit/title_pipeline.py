"""TITLE_REPORT entry point — binds the shared pipeline to the TITLE policy.

Spec: docs/classification/title_report.md. This is the first type whose pages
include image-only scans, so the VLM branch of pipeline.run is exercised here.

  uv run python -m docsplit.title_pipeline --data-dir data --out-dir outputs
"""

from __future__ import annotations

from .pipeline import build_arg_parser, run


def main() -> None:
    args = build_arg_parser(__doc__).parse_args()
    run(policy_name="title_report", out_subdir="title", check_prefix="T-", args=args)


if __name__ == "__main__":
    main()
