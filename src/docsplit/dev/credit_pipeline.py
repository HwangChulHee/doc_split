"""CREDIT_REPORT pipeline entry point.

Usage:
    uv run python -m docsplit.dev.credit_pipeline --data-dir data --out-dir outputs
    options: --no-llm, --package {01,02,both} (default 01)

The stages live in docsplit.dev.pipeline; this module only binds the CREDIT policy.
Checks are named C-V1..C-V5 (docs/classification/credit_report.md §7); C-V5 is
a measurement of vendor-independent coverage, not a pass/fail check.
"""

from __future__ import annotations

from .pipeline import build_arg_parser, run


def main() -> None:
    args = build_arg_parser(__doc__).parse_args()
    run(policy_name="credit_report", out_subdir="credit", check_prefix="C-", args=args)


if __name__ == "__main__":
    main()
