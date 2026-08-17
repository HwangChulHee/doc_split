"""How far does rule classification scale across cores?

Rule classification is normalize + regex over page text: CPU bound, so threads
would just queue behind the GIL. Pages are independent (no shared state, the
policies are read-only), which is the precondition for a process pool. This
script measures what that buys, and asserts the parallel verdicts are identical
to the serial ones — a speedup that changes an answer is not a speedup.

    uv run python scripts/bench_parallel.py                  # 2000 pages
    uv run python scripts/bench_parallel.py --pages 4000 --procs 8
    uv run python scripts/bench_parallel.py --scaling         # 1·2·4·8·all cores

Observation only: nothing here is imported by ``docsplit run``.

Synthetic pages are built from the phrases the policies already carry — public
standard text (GSE footers, ALTA notices, IRS transcript headers) plus random
filler words. No document content, real or invented, goes in: a benchmark has
no business handling borrower data.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import random
import string
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from docsplit.rules.signals import (  # noqa: E402
    available_policies,
    load_policy,
    universal_block,
)
from docsplit.rules.unified import classify_page_unified  # noqa: E402

FILLER_WORDS = [
    "reference", "section", "paragraph", "attached", "hereto", "schedule",
    "amount", "date", "number", "record", "notice", "statement", "summary",
    "listed", "above", "below", "following", "provided", "issued", "dated",
]


def _phrases(spec: dict) -> list[str]:
    """Every literal phrase a signal spec can match on (patterns excluded)."""
    out: list[str] = list(spec.get("phrases") or [])
    out += list(spec.get("require_all") or [])
    for group in spec.get("require_all_any") or []:
        out += list(group)
    return [p for p in out if isinstance(p, str)]


def collect_phrase_pools(policies: dict[str, dict]) -> dict[str, dict[str, list[list[str]]]]:
    """Per type: the phrase groups of its universal decisive and supportive signals.

    Kept grouped by signal id so a page can be built to satisfy a whole signal
    (``require_all`` needs every phrase of its group present).
    """
    pools: dict[str, dict[str, list[list[str]]]] = {}
    for type_name, policy in policies.items():
        block = universal_block(policy)
        pools[type_name] = {
            kind: [_phrases(spec) for spec in (block.get(kind) or {}).values() if _phrases(spec)]
            for kind in ("decisive", "supportive")
        }
    return pools


def _filler(rng: random.Random, words: int) -> str:
    parts = []
    for _ in range(words):
        w = rng.choice(FILLER_WORDS)
        if rng.random() < 0.15:  # a token that looks like an id but means nothing
            w = "".join(rng.choices(string.ascii_uppercase + string.digits, k=6))
        parts.append(w)
    return " ".join(parts)


def make_pages(count: int, policies: dict[str, dict], seed: int) -> list[str]:
    """A mix of grades, not just the fast path.

    Roughly: 45% carry a decisive signal, 30% carry two supportive signals, 10%
    carry one, 15% are filler only. The last two land on DEFER_LLM either way —
    the unified decision defers both "one weak signal" and "no signal" — and
    they are the expensive pages: nothing short-circuits, so all four policies
    run to exhaustion. Measuring only decisive pages would flatter the result.
    """
    rng = random.Random(seed)
    pools = collect_phrase_pools(policies)
    types = sorted(pools)
    pages: list[str] = []
    for i in range(count):
        roll = rng.random()
        lines: list[str] = []
        t = types[i % len(types)]
        decisive, supportive = pools[t]["decisive"], pools[t]["supportive"]
        if roll < 0.45 and decisive:
            lines += rng.choice(decisive)
        elif roll < 0.75 and len(supportive) >= 2:
            for group in rng.sample(supportive, 2):
                lines += group
        elif roll < 0.85 and supportive:
            lines += rng.choice(supportive)
        lines.insert(0, _filler(rng, rng.randint(40, 120)))
        lines.append(_filler(rng, rng.randint(40, 120)))
        rng.shuffle(lines)
        pages.append("\n".join(lines))
    return pages


# ── worker side ───────────────────────────────────────────────
_POLICIES: dict[str, dict] = {}


def _init_worker() -> None:
    """Load the policies once per worker, not once per page.

    Passing them through as job arguments would serialize four parsed yaml
    trees per page and drown the measurement in pickling.
    """
    global _POLICIES
    _POLICIES = _load_policies()


def _classify(job: tuple[int, str]) -> tuple[int, str | None, str, str | None]:
    page_index, raw = job
    verdict, _, _ = classify_page_unified("bench", page_index, raw, _POLICIES)
    return page_index, verdict.type, verdict.rule_grade, verdict.subtype


def _load_policies() -> dict[str, dict]:
    out = {}
    for name in available_policies():
        policy = load_policy(name)
        out[policy["type"]] = policy
    return out


# ── measurement ───────────────────────────────────────────────
def run_serial(pages: list[str], policies: dict[str, dict]) -> tuple[list, float]:
    start = time.perf_counter()
    out = []
    for i, raw in enumerate(pages):
        verdict, _, _ = classify_page_unified("bench", i, raw, policies)
        out.append((i, verdict.type, verdict.rule_grade, verdict.subtype))
    return out, time.perf_counter() - start


def run_parallel(pages: list[str], procs: int, chunksize: int) -> tuple[list, float]:
    jobs = list(enumerate(pages))
    start = time.perf_counter()
    ctx = mp.get_context("fork" if sys.platform != "win32" else "spawn")
    with ctx.Pool(processes=procs, initializer=_init_worker) as pool:
        out = pool.map(_classify, jobs, chunksize=chunksize)
    return out, time.perf_counter() - start


def grade_mix(results: list) -> dict[str, int]:
    mix: dict[str, int] = {}
    for _, _, grade, _ in results:
        mix[grade] = mix.get(grade, 0) + 1
    return dict(sorted(mix.items(), key=lambda kv: -kv[1]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages", type=int, default=2000)
    ap.add_argument("--procs", type=int, default=mp.cpu_count())
    ap.add_argument("--chunksize", type=int, default=0, help="0 = pages/(procs*4)")
    ap.add_argument("--seed", type=int, default=20260817)
    ap.add_argument("--scaling", action="store_true",
                    help="1·2·4·8 프로세스와 전체 코어를 차례로 측정")
    args = ap.parse_args(argv)

    policies = _load_policies()
    pages = make_pages(args.pages, policies, args.seed)
    print(f"합성 페이지 {len(pages)}장 (seed {args.seed}), 정책 {len(policies)}종, "
          f"코어 {mp.cpu_count()}개")

    serial, serial_s = run_serial(pages, policies)
    print(f"\n직렬   {serial_s:7.3f}s  {len(pages) / serial_s:9,.0f} pages/s")
    print(f"등급 분포: {grade_mix(serial)}")

    proc_list = [args.procs]
    if args.scaling:
        proc_list = sorted({1, 2, 4, 8, mp.cpu_count()})

    print()
    print(f"{'procs':>6} {'chunk':>6} {'time(s)':>9} {'pages/s':>11} {'speedup':>8}  일치")
    for procs in proc_list:
        chunk = args.chunksize or max(1, len(pages) // (procs * 4))
        par, par_s = run_parallel(pages, procs, chunk)
        same = sorted(par) == sorted(serial)
        assert same, f"병렬 판정이 직렬과 다르다 (procs={procs}) — 벤치마크 무효"
        print(f"{procs:>6} {chunk:>6} {par_s:>9.3f} {len(pages) / par_s:>11,.0f} "
              f"{serial_s / par_s:>7.2f}x  {'✅' if same else '❌'}")

    print("\n판정 결과는 직렬과 완전히 일치한다 (유형·등급·subtype 전부).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
