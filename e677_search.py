#!/usr/bin/env python3
"""
e677_search.py

Search for a finite left quasigroup / finite magma encoded by permutations L_x
satisfying

    E677:  L_y( L_x( L_{L_y(x)}(y) ) ) = x

and failing

    E255 at witness a:  L_{L_{L_a(a)}(a)}(a) != a.

The operation is y o z = L_y(z).  Each row L_y must be a permutation.

This script uses Z3.  Install with:

    python -m pip install z3-solver

Typical order-20 search, normalized to the 4-cycle branch discussed in the
derivation:

    python e677_search.py --n 20 --witness 0 --cycle 0,1,2,3 --timeout 600

Save a solution if found:

    python e677_search.py --n 20 --cycle 0,1,2,3 --timeout 600 --output sol.json

Verify or print an existing solution:

    python e677_search.py --verify sol.json
    python e677_search.py --verify sol.json --show-cycles

Useful options:

    --no-structural-cuts
        Disable extra mathematically derived constraints.  The core constraints
        are still exactly row-permutation + E677 + E255 failure.

    --require-no-fixer-of-witness
        Adds L_y(a) != a for every y.  This is equivalent to E255 failure under
        E677, but it is often a stronger propagation form for the solver.

    --fix-l0 "0,1,2,3;4,5,6,7,8;9,10"
        Additionally fix selected cycles of L_0.  Elements not mentioned remain
        unconstrained.  The option --cycle is just a convenient shorthand for
        fixing one cycle through the witness.

    --emit-smt2 model.smt2
        Write the SMT-LIB model to a file instead of solving.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def parse_cycle(text: str) -> List[int]:
    """
    Parse one cycle such as:
        "0,1,2,3"
        "0 1 2 3"
        "(0 1 2 3)"
    """
    s = text.strip()
    if not s:
        return []
    s = s.replace("(", " ").replace(")", " ").replace(",", " ")
    try:
        return [int(tok) for tok in s.split()]
    except ValueError as exc:
        die(f"could not parse cycle {text!r}: {exc}")


def parse_cycles(text: str) -> List[List[int]]:
    """
    Parse semicolon-separated cycles such as:
        "0,1,2,3;4,5,6;7,8"
    """
    if not text:
        return []
    cycles = []
    for part in text.split(";"):
        cyc = parse_cycle(part)
        if cyc:
            cycles.append(cyc)
    return cycles


def validate_cycles(cycles: Sequence[Sequence[int]], n: int) -> None:
    seen = set()
    for cyc in cycles:
        if len(cyc) <= 1:
            die(f"cycles must have length at least 2; got {cyc}")
        for x in cyc:
            if not 0 <= x < n:
                die(f"cycle element {x} is outside 0..{n-1}")
            if x in seen:
                die(f"cycle element {x} appears in more than one fixed L_0 cycle")
            seen.add(x)


def row_to_cycles(row: Sequence[int]) -> str:
    n = len(row)
    seen = [False] * n
    parts = []
    for i in range(n):
        if seen[i]:
            continue
        cyc = []
        j = i
        while not seen[j]:
            seen[j] = True
            cyc.append(j)
            j = row[j]
        if len(cyc) > 1:
            parts.append("(" + " ".join(map(str, cyc)) + ")")
    return " ".join(parts) if parts else "()"


def validate_permutation(row: Sequence[int]) -> bool:
    n = len(row)
    return sorted(row) == list(range(n))


def e677_holds(table: Sequence[Sequence[int]]) -> bool:
    n = len(table)
    for y in range(n):
        for x in range(n):
            u = table[y][x]
            v = table[u][y]
            w = table[x][v]
            t = table[y][w]
            if t != x:
                return False
    return True


def e255_fails_at(table: Sequence[Sequence[int]], a: int) -> bool:
    b = table[a][a]
    c = table[b][a]
    lhs = table[c][a]
    return lhs != a


def verify_table(table: Sequence[Sequence[int]], witness: int = 0, verbose: bool = True) -> bool:
    n = len(table)
    ok = True

    if not 0 <= witness < n:
        if verbose:
            print(f"witness {witness} outside 0..{n-1}")
        return False

    if any(len(row) != n for row in table):
        if verbose:
            print("table is not square")
        return False

    for i, row in enumerate(table):
        if not validate_permutation(row):
            if verbose:
                print(f"row {i} is not a permutation: {row}")
            ok = False

    if ok and not e677_holds(table):
        if verbose:
            print("E677 failed")
        ok = False

    if ok and not e255_fails_at(table, witness):
        if verbose:
            print(f"E255 did not fail at witness {witness}")
        ok = False

    if verbose:
        print("verification:", "PASS" if ok else "FAIL")
        if ok:
            b = table[witness][witness]
            c = table[b][witness]
            lhs = table[c][witness]
            print(f"witness a={witness}: L_a(a)={b}, L_{{L_a(a)}}(a)={c}, L_c(a)={lhs} != {witness}")
    return ok


def load_solution(path: str | Path) -> Tuple[List[List[int]], int]:
    data = json.loads(Path(path).read_text())
    table = data.get("table")
    if table is None:
        die("solution JSON has no 'table' field")
    witness = int(data.get("witness", 0))
    return table, witness


@dataclass
class BuildOptions:
    n: int
    witness: int
    fixed_l0_cycles: List[List[int]]
    structural_cuts: bool = True
    require_no_fixer_of_witness: bool = True
    distinct_rows: bool = True
    timeout_ms: int = 0
    seed: Optional[int] = None
    verbose: bool = True


def build_solver(opts: BuildOptions):
    """
    Build and return (solver, T_at, Cell, z3_module).

    Cell is a single Z3 array indexed by row*n + column.
    T_at(row, col) returns Select(Cell, row*n + col), where row and col may be
    Python ints or Z3 integer expressions.
    """
    try:
        import z3  # type: ignore
    except ImportError:
        die(
            "missing dependency 'z3-solver'. Install with:\n"
            "    python -m pip install z3-solver"
        )

    n = opts.n
    a = opts.witness

    z3.set_param("parallel.enable", True)

    Cell = z3.Array("T", z3.IntSort(), z3.IntSort())
    solver = z3.Solver()

    if opts.timeout_ms > 0:
        solver.set(timeout=opts.timeout_ms)
    if opts.seed is not None:
        solver.set(random_seed=opts.seed)

    def zint(v):
        return z3.IntVal(v) if isinstance(v, int) else v

    def T_at(row, col):
        row_e = zint(row)
        col_e = zint(col)
        return z3.Select(Cell, row_e * n + col_e)

    # All fixed cells are values in Omega.
    for y in range(n):
        for x in range(n):
            val = T_at(y, x)
            solver.add(val >= 0, val < n)

    # Each L_y is a permutation.
    for y in range(n):
        solver.add(z3.Distinct([T_at(y, x) for x in range(n)]))

    # Optional but implied by E677: x -> L_x is injective.
    # This is useful as a search cut.
    if opts.distinct_rows:
        for i in range(n):
            for j in range(i + 1, n):
                solver.add(z3.Or([T_at(i, x) != T_at(j, x) for x in range(n)]))

    # Fixed cycles of L_0.
    for cyc in opts.fixed_l0_cycles:
        for i, src in enumerate(cyc):
            dst = cyc[(i + 1) % len(cyc)]
            solver.add(T_at(0, src) == dst)

    # E677:
    #     L_y( L_x( L_{L_y(x)}(y) ) ) = x
    for y in range(n):
        for x in range(n):
            u = T_at(y, x)
            v = T_at(u, y)
            w = T_at(x, v)
            solver.add(T_at(y, w) == x)

    # E255 failure at the witness:
    #     L_{L_{L_a(a)}(a)}(a) != a
    b = T_at(a, a)
    c = T_at(b, a)
    solver.add(T_at(c, a) != a)

    if opts.require_no_fixer_of_witness:
        # Under E677 this is equivalent to E255 failure at a:
        # no row L_y fixes the witness-column entry a.
        for y in range(n):
            solver.add(T_at(y, a) != a)

    if opts.structural_cuts:
        # Column-fixer uniqueness:
        # for each column x, at most one row y may satisfy L_y(x)=x.
        # This follows from E677, but the Boolean AtMost form propagates well.
        for x in range(n):
            solver.add(z3.AtMost(*[T_at(y, x) == x for y in range(n)], 1))

        # No proper 2-cycle or proper 3-cycle through x under L_x.
        # Fixed points L_x(x)=x are allowed.
        for x in range(n):
            x1 = T_at(x, x)
            x2 = T_at(x, x1)
            x3 = T_at(x, x2)
            solver.add(z3.Implies(x1 != x, x2 != x))
            solver.add(z3.Implies(z3.And(x1 != x, x2 != x), x3 != x))

    return solver, T_at, Cell, z3


def extract_table(model, T_at, n: int) -> List[List[int]]:
    table: List[List[int]] = []
    for y in range(n):
        row = []
        for x in range(n):
            v = model.evaluate(T_at(y, x), model_completion=True)
            row.append(int(v.as_long()))
        table.append(row)
    return table


def save_solution(path: str | Path, table: Sequence[Sequence[int]], witness: int, meta: dict) -> None:
    data = {
        "n": len(table),
        "witness": witness,
        "table": table,
        "permutations_as_cycles": {str(i): row_to_cycles(row) for i, row in enumerate(table)},
        "meta": meta,
    }
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"wrote {path}")


def print_table(table: Sequence[Sequence[int]]) -> None:
    n = len(table)
    width = max(2, len(str(n - 1)))
    header = " " * (width + 3) + " ".join(f"{i:{width}d}" for i in range(n))
    print(header)
    print(" " * (width + 3) + "-" * ((width + 1) * n - 1))
    for i, row in enumerate(table):
        print(f"{i:{width}d} | " + " ".join(f"{v:{width}d}" for v in row))


def print_cycles(table: Sequence[Sequence[int]]) -> None:
    for i, row in enumerate(table):
        print(f"L_{i:>2} = {row_to_cycles(row)}")


def run_search(args: argparse.Namespace) -> int:
    n = args.n
    witness = args.witness

    if n <= 0:
        die("--n must be positive")
    if not 0 <= witness < n:
        die(f"--witness must be in 0..{n-1}")

    fixed_cycles: List[List[int]] = []

    if args.cycle:
        cyc = parse_cycle(args.cycle)
        if witness not in cyc:
            die(f"--cycle must contain the witness {witness}")
        if cyc[0] != witness:
            # Rotate so the witness is first. This only changes notation.
            k = cyc.index(witness)
            cyc = cyc[k:] + cyc[:k]
        fixed_cycles.append(cyc)

    if args.fix_l0:
        fixed_cycles.extend(parse_cycles(args.fix_l0))

    validate_cycles(fixed_cycles, n)

    # A 4-cycle witness is the branch that mathematically guarantees E255
    # failure, but we still include the explicit E255-failure constraint below.
    if args.cycle and len(parse_cycle(args.cycle)) == 4 and witness == parse_cycle(args.cycle)[0]:
        # This adds the derived forced value L_{L_0(0)}(0) = L_0^{-2}(0)
        # only when the supplied cycle starts at the witness.
        cyc = parse_cycle(args.cycle)
        if cyc[0] == witness:
            pass  # E677 will force this anyway; no separate action needed.

    opts = BuildOptions(
        n=n,
        witness=witness,
        fixed_l0_cycles=fixed_cycles,
        structural_cuts=not args.no_structural_cuts,
        require_no_fixer_of_witness=args.require_no_fixer_of_witness,
        distinct_rows=not args.no_distinct_rows,
        timeout_ms=max(0, int(args.timeout * 1000)),
        seed=args.seed,
        verbose=args.verbose,
    )

    solver, T_at, _Cell, z3 = build_solver(opts)

    if args.emit_smt2:
        Path(args.emit_smt2).write_text(solver.to_smt2())
        print(f"wrote {args.emit_smt2}")
        return 0

    if args.verbose:
        print("search parameters:")
        print(f"  n={n}")
        print(f"  witness={witness}")
        print(f"  fixed L_0 cycles={fixed_cycles if fixed_cycles else 'none'}")
        print(f"  structural cuts={opts.structural_cuts}")
        print(f"  require no fixer of witness={opts.require_no_fixer_of_witness}")
        print(f"  distinct rows cut={opts.distinct_rows}")
        print(f"  timeout={args.timeout} seconds" if args.timeout else "  timeout=none")
        if args.seed is not None:
            print(f"  random seed={args.seed}")
        print("solving...")

    start = time.time()
    result = solver.check()
    elapsed = time.time() - start

    print(f"Z3 result: {result}  ({elapsed:.2f}s)")

    if result == z3.sat:
        model = solver.model()
        table = extract_table(model, T_at, n)
        ok = verify_table(table, witness=witness, verbose=True)
        if not ok:
            print("internal warning: model failed independent verifier", file=sys.stderr)
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
                    "elapsed_seconds": elapsed,
                    "fixed_l0_cycles": fixed_cycles,
                    "structural_cuts": opts.structural_cuts,
                    "require_no_fixer_of_witness": opts.require_no_fixer_of_witness,
                    "distinct_rows": opts.distinct_rows,
                    "seed": args.seed,
                },
            )
        elif not args.show_table and not args.show_cycles:
            print("solution found. Use --show-cycles or --show-table, or --output sol.json.")
        return 0

    if result == z3.unsat:
        print("No solution exists under the supplied constraints.")
        print("Note: if you fixed extra L_0 cycles, this is only for that normalized branch.")
        return 20

    print("Solver returned unknown. Increase --timeout, change --seed, or relax cuts.")
    try:
        print("reason:", solver.reason_unknown())
    except Exception:
        pass
    return 30


def run_verify(args: argparse.Namespace) -> int:
    table, witness = load_solution(args.verify)
    if args.witness is not None:
        witness = args.witness
    ok = verify_table(table, witness=witness, verbose=True)
    if args.show_table:
        print_table(table)
    if args.show_cycles:
        print_cycles(table)
    return 0 if ok else 1


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Search for an order-n left quasigroup satisfying E677 and failing E255.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Main size-20 branch with witness 0 and L_0 containing (0 1 2 3)
  python e677_search.py --n 20 --witness 0 --cycle 0,1,2,3 --timeout 600 --output sol.json

  # Same branch, print cycles if found
  python e677_search.py --n 20 --cycle 0,1,2,3 --timeout 600 --show-cycles

  # Add a stronger normalization of L_0
  python e677_search.py --n 20 --cycle 0,1,2,3 --fix-l0 "4,5,6,7;8,9,10,11" --timeout 600

  # Verify a saved solution
  python e677_search.py --verify sol.json --show-cycles
""",
    )

    p.add_argument("--n", type=int, default=20, help="order of Omega; default: 20")
    p.add_argument("--witness", type=int, default=0, help="witness a for E255 failure; default: 0")
    p.add_argument(
        "--cycle",
        default="0,1,2,3",
        help="fix one L_0 cycle, usually through witness; default: 0,1,2,3",
    )
    p.add_argument(
        "--fix-l0",
        default="",
        help='additional semicolon-separated cycles to fix in L_0, e.g. "4,5,6;7,8"',
    )
    p.add_argument("--timeout", type=float, default=0.0, help="Z3 timeout in seconds; 0 means none")
    p.add_argument("--seed", type=int, default=None, help="Z3 random seed")
    p.add_argument("--output", default="", help="write solution JSON here if SAT")
    p.add_argument("--emit-smt2", default="", help="write SMT-LIB problem here and exit")
    p.add_argument("--show-table", action="store_true", help="print the operation table if SAT or when verifying")
    p.add_argument("--show-cycles", action="store_true", help="print each L_x in disjoint cycle notation")
    p.add_argument(
        "--no-structural-cuts",
        action="store_true",
        help="disable derived search cuts; core E677/E255/permutation constraints remain",
    )
    p.add_argument(
        "--no-distinct-rows",
        action="store_true",
        help="disable the derived row-injectivity cut",
    )
    p.add_argument(
        "--require-no-fixer-of-witness",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="add/remove L_y(a) != a for every y; default: true",
    )
    p.add_argument("--quiet", dest="verbose", action="store_false", help="less progress output")

    p.add_argument(
        "--verify",
        default="",
        help="verify a saved JSON solution instead of searching",
    )

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = make_parser().parse_args(argv)
    if args.verify:
        return run_verify(args)
    return run_search(args)


if __name__ == "__main__":
    raise SystemExit(main())
