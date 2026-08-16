"""INCOME_DOC entry point — binds the shared pipeline to the INCOME policy.

Spec: docs/classification/income_doc.md. This is the type where the LLM is not
a fallback but a designed path: some subgroups (a hand-written P&L, a vendor's
verification summary) carry no rule signal at all, which the policy declares
via ``llm.classify_on_no_signal``.

  uv run python -m docsplit.income_pipeline --data-dir data --out-dir outputs
"""

from __future__ import annotations

from .pipeline import build_arg_parser, run


def main() -> None:
    args = build_arg_parser(__doc__).parse_args()
    run(policy_name="income_doc", out_subdir="income", check_prefix="I-", args=args)


if __name__ == "__main__":
    main()
