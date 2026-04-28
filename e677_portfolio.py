#!/usr/bin/env python3
"""
e677_portfolio.py

Race a portfolio of diverse Z3 configurations in parallel processes searching
for an order-n left quasigroup that satisfies E677 and fails E255.

Each worker is a separate Python process running ``e677_search.solve_once``
with a different (seed, encoding, tactic) combination.  The driver returns
as soon as any worker reports ``sat`` and cancels the rest.  If every worker
finishes with ``unsat`` the branch is refuted.  Otherwise the result is
``unknown`` and the per-worker outcomes are summarized.

Examples
--------

  python e677_portfolio.py --n 20 --workers 8 --timeout 1800

  # Aggressive: 16 workers, mixed strategy, large timeout
  python e677_portfolio.py --n 20 --workers 16 --strategy mixed --timeout 3600 \
      --output sol.json --show-cycles
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Reuse the search machinery.
from e677_search import (
    BuildOptions,
    parse_cycle,
    parse_cycles,
    print_cycles,
    print_table,
    save_solution,
    solve_once,
    validate_cycles,
    verify_table,
)


# ---------------------------------------------------------------------------
# Strategy generation
# ---------------------------------------------------------------------------

def _base_opts(args: argparse.Namespace, fixed_cycles: List[List[int]]) -> Dict[str, Any]:
    """Return a dict of BuildOptions fields shared by every worker."""
    return {
        "n": args.n,
        "witness": args.witness,
        "fixed_l0_cycles": fixed_cycles,
        "structural_cuts": not args.no_structural_cuts,
        "require_no_fixer_of_witness": not args.no_require_no_fixer_of_witness,
        "distinct_rows": not args.no_distinct_rows,
        "timeout_ms": max(0, int(args.timeout * 1000)),
        "verbose": False,
        "use_uf": not args.no_uf,
        "inverse_channel": not args.no_inverse_channel,
        "explicit_inverse": not args.no_explicit_inverse,
        "transformed_identity": not args.no_transformed_identity,
        "cycle_ground_facts": not args.no_cycle_ground_facts,
    }


# A handful of Z3 tactics that can be useful on this kind of problem.  Empty
# string means "no tactic, use the default Solver".
_TACTIC_POOL = ("", "qffd", "smt", "psmt", "qfbv")


def make_jobs(args: argparse.Namespace, fixed_cycles: List[List[int]]) -> List[Dict[str, Any]]:
    """Build a list of opts dicts for the worker pool."""
    base = _base_opts(args, fixed_cycles)
    workers = max(1, args.workers)
    strategy = args.strategy
    base_seed = args.base_seed

    jobs: List[Dict[str, Any]] = []

    def add(seed: Optional[int], bv: bool, tactic: str, label: str) -> None:
        opts = dict(base)
        opts["seed"] = seed
        opts["bv"] = bv
        opts["tactic"] = tactic
        opts["label"] = label
        jobs.append(opts)

    if strategy == "seeds":
        for i in range(workers):
            add(base_seed + i, False, "", f"int#{i}-seed{base_seed + i}")

    elif strategy == "tactics":
        for i in range(workers):
            tac = _TACTIC_POOL[i % len(_TACTIC_POOL)]
            bv = tac in {"qfbv", "qffd"}
            add(base_seed + i, bv, tac, f"tac{i}-{tac or 'default'}-{'bv' if bv else 'int'}")

    elif strategy == "mixed":
        # Half pure-seed Int diversity, half encoding/tactic diversity.
        half = max(1, workers // 2)
        for i in range(half):
            add(base_seed + i, False, "", f"int#{i}-seed{base_seed + i}")
        # Diversification slot: cycle through (bv, tactic) combos.
        diverse = [
            (True, ""),
            (True, "qffd"),
            (True, "qfbv"),
            (False, "qffd"),
            (False, "smt"),
            (False, "psmt"),
        ]
        rest = workers - half
        for i in range(rest):
            bv, tac = diverse[i % len(diverse)]
            seed = base_seed + half + i
            add(seed, bv, tac, f"div{i}-{'bv' if bv else 'int'}-{tac or 'default'}-seed{seed}")

    else:
        raise ValueError(f"unknown strategy: {strategy!r}")

    return jobs


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_portfolio(args: argparse.Namespace) -> int:
    n = args.n
    if n <= 0:
        print("error: --n must be positive", file=sys.stderr)
        return 2

    fixed_cycles: List[List[int]] = []
    if args.cycle:
        cyc = parse_cycle(args.cycle)
        if cyc:
            if args.witness not in cyc:
                print(f"error: --cycle must contain the witness {args.witness}",
                      file=sys.stderr)
                return 2
            if cyc[0] != args.witness:
                k = cyc.index(args.witness)
                cyc = cyc[k:] + cyc[:k]
            fixed_cycles.append(cyc)
    if args.fix_l0:
        fixed_cycles.extend(parse_cycles(args.fix_l0))
    validate_cycles(fixed_cycles, n)

    jobs = make_jobs(args, fixed_cycles)

    print(f"portfolio: n={n} workers={len(jobs)} strategy={args.strategy} "
          f"timeout={args.timeout}s")
    print(f"fixed L_0 cycles: {fixed_cycles if fixed_cycles else 'none'}")
    for j in jobs:
        print(f"  - {j['label']}  seed={j['seed']}  bv={j['bv']}  "
              f"tactic={j['tactic'] or 'default'}")
    sys.stdout.flush()

    overall_start = time.time()
    found: Optional[Dict[str, Any]] = None
    unsat_count = 0
    unknown_count = 0
    finished: List[Dict[str, Any]] = []

    # Use spawn semantics: each worker reimports e677_search and z3 fresh.
    with ProcessPoolExecutor(max_workers=len(jobs)) as ex:
        future_to_label = {ex.submit(solve_once, j): j["label"] for j in jobs}
        pending = set(future_to_label.keys())

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED,
                                 timeout=args.timeout + 30)
            if not done:
                # Outer wall-clock guard: kill the pool.
                print("portfolio: outer timeout, cancelling workers")
                for f in pending:
                    f.cancel()
                break
            for fut in done:
                label = future_to_label[fut]
                try:
                    res = fut.result()
                except Exception as exc:  # pragma: no cover - worker crashed
                    print(f"[{label}] worker crashed: {exc}")
                    unknown_count += 1
                    continue
                finished.append(res)
                elapsed = res.get("elapsed_seconds", 0.0)
                status = res.get("status", "unknown")
                print(f"[{label}] {status} in {elapsed:.2f}s")
                sys.stdout.flush()
                if status == "sat" and res.get("verified"):
                    found = res
                    # Cancel remaining workers.
                    for f in pending:
                        f.cancel()
                    pending = set()
                    break
                if status == "unsat":
                    unsat_count += 1
                else:
                    unknown_count += 1

    total = time.time() - overall_start
    print(f"portfolio: total wall time {total:.2f}s, "
          f"sat={1 if found else 0} unsat={unsat_count} unknown={unknown_count}")

    if found:
        table = found["table"]
        witness = found["witness"]
        ok = verify_table(table, witness=witness, verbose=True)
        if not ok:
            print("internal warning: model failed independent verifier",
                  file=sys.stderr)
            return 1
        if args.show_table:
            print_table(table)
        if args.show_cycles:
            print_cycles(table)
        if args.output:
            save_solution(
                args.output,
                table,
                witness,
                meta={
                    "winner_label": found.get("label"),
                    "winner_elapsed_seconds": found.get("elapsed_seconds"),
                    "portfolio_total_seconds": total,
                    "fixed_l0_cycles": fixed_cycles,
                    "workers": len(jobs),
                    "strategy": args.strategy,
                },
            )
        return 0

    if unsat_count == len(jobs):
        # Every worker returned unsat for the same problem -- branch refuted.
        print("All workers returned UNSAT. This branch is refuted.")
        return 20

    return 30


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Parallel portfolio search for E677/!E255 (races diverse Z3 configs).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--witness", type=int, default=0)
    p.add_argument("--cycle", default="0,1,2,3",
                   help="fix one L_0 cycle through the witness; default 0,1,2,3. "
                        "Use --cycle '' to disable.")
    p.add_argument("--fix-l0", default="",
                   help='additional cycles to fix in L_0, e.g. "4,5,6,7;8,9,10,11"')
    p.add_argument("--workers", type=int, default=max(2, (os.cpu_count() or 4)),
                   help="number of parallel worker processes")
    p.add_argument("--strategy", default="mixed",
                   choices=["seeds", "tactics", "mixed"],
                   help="how to diversify the workers")
    p.add_argument("--base-seed", type=int, default=1,
                   help="first random seed used by the workers")
    p.add_argument("--timeout", type=float, default=1800.0,
                   help="per-worker Z3 timeout in seconds")
    p.add_argument("--output", default="", help="write winning solution JSON here")
    p.add_argument("--show-table", action="store_true")
    p.add_argument("--show-cycles", action="store_true")

    # Mirrors of e677_search flags so the portfolio matches the same constraint
    # set on every worker.
    p.add_argument("--no-structural-cuts", action="store_true")
    p.add_argument("--no-distinct-rows", action="store_true")
    p.add_argument("--no-uf", action="store_true")
    p.add_argument("--no-inverse-channel", action="store_true")
    p.add_argument("--no-explicit-inverse", action="store_true")
    p.add_argument("--no-transformed-identity", action="store_true")
    p.add_argument("--no-cycle-ground-facts", action="store_true")
    p.add_argument("--no-require-no-fixer-of-witness", action="store_true")

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = make_parser().parse_args(argv)
    return run_portfolio(args)


if __name__ == "__main__":
    raise SystemExit(main())
