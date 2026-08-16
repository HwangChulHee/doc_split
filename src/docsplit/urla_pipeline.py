"""URLA pipeline entry point.

Usage:
    uv run python -m docsplit.urla_pipeline --data-dir data --out-dir outputs
    options: --no-llm, --package {01,02,both} (default 01)

The stages live in docsplit.pipeline; this module only binds the URLA policy.
"""

from __future__ import annotations

from .pipeline import build_arg_parser, run


def main() -> None:
    args = build_arg_parser(__doc__).parse_args()
    run(policy_name="urla", out_subdir="urla", check_prefix="", args=args)


if __name__ == "__main__":
    main()
