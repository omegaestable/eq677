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
    # New, default-on optimizations:
    use_uf: bool = True                # uninterpreted Function instead of Array
    inverse_channel: bool = True       # add Tinv with channeling equations
    explicit_inverse: bool = True      # Tinv(y,x) = x o ((y o x) o y)
    transformed_identity: bool = True  # z = (y o z) o ((y o (y o z)) o y)
    cycle_ground_facts: bool = True    # bake in d>=3 cycle consequences
    distinct_rows_under_channeling: bool = False  # redundant when channeling on
    bv: bool = False                   # use BitVec encoding instead of Int
    tactic: str = ""                   # optional Z3 tactic, e.g. "qffd", "smt", "psmt"


def build_solver(opts: BuildOptions):
    """
    Build and return (solver, T_at, Cell, z3_module).

    By default the table is encoded as an uninterpreted function
        T : Int x Int -> Int
    which is significantly faster for Z3 than the Array(IntSort,IntSort)
    flattening that this script used previously.  An auxiliary function Tinv
    represents the row inverses with full channeling, plus the closed-form
    identity Tinv(y,x) = x o ((y o x) o y) which is a direct rewrite of E677.

    Cell is kept in the return tuple only for backward compatibility and is
    None in the default UF mode.
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

    # Construct the solver. If a tactic is requested, derive the solver from
    # a tactic chain so Z3 picks a different decision procedure (e.g. qffd
    # for finite-domain bit-vector problems).
    if opts.tactic:
        try:
            tac = z3.Then("simplify", "propagate-values", opts.tactic)
            solver = tac.solver()
        except z3.Z3Exception as exc:
            die(f"unknown Z3 tactic {opts.tactic!r}: {exc}")
    else:
        solver = z3.Solver()

    if opts.timeout_ms > 0:
        try:
            solver.set(timeout=opts.timeout_ms)
        except Exception:
            pass
    # Tactic-derived solvers may not expose 'random_seed'; only set it for
    # the default Solver().
    if opts.seed is not None and not opts.tactic:
        try:
            solver.set(random_seed=opts.seed)
        except Exception:
            pass

    # Choose the value sort.  Bit-vectors of width k = ceil(log2 max(n,2)) are
    # often dramatically faster than unbounded Int for finite-domain problems
    # because Z3 bit-blasts to SAT.
    if opts.bv:
        k = max(1, (max(n, 2) - 1).bit_length())
        ValSort = z3.BitVecSort(k)

        def vconst(v: int):
            return z3.BitVecVal(v, k)

        def in_range(expr):
            # Unsigned less-than against n.
            return z3.ULT(expr, vconst(n))

        def eq_const(expr, c: int):
            return expr == vconst(c)
    else:
        ValSort = z3.IntSort()

        def vconst(v: int):
            return z3.IntVal(v)

        def in_range(expr):
            return z3.And(expr >= 0, expr < n)

        def eq_const(expr, c: int):
            return expr == vconst(c)

    def zint(v):
        # Used for indexing the UF/Array.  In BV mode keep indices as bit-vectors
        # of the same width to share sorts everywhere.
        if opts.bv:
            return v if z3.is_expr(v) else vconst(int(v))
        return v if z3.is_expr(v) else z3.IntVal(int(v))

    if opts.use_uf:
        Cell = None
        IdxSort = ValSort
        T_func = z3.Function("T", IdxSort, IdxSort, ValSort)
        Tinv_func = z3.Function("Tinv", IdxSort, IdxSort, ValSort)

        def T_at(row, col):
            return T_func(zint(row), zint(col))

        def Tinv_at(row, col):
            return Tinv_func(zint(row), zint(col))
    else:
        if opts.bv:
            # Wider index BV so row*n + col can't overflow.
            kk = max(1, (n * n - 1).bit_length())
            FlatSort = z3.BitVecSort(kk)
            Cell = z3.Array("T", FlatSort, ValSort)

            def T_at(row, col):
                r = row if z3.is_expr(row) else z3.BitVecVal(int(row), kk)
                if z3.is_expr(r) and r.size() != kk:
                    r = z3.ZeroExt(kk - r.size(), r)
                c = col if z3.is_expr(col) else z3.BitVecVal(int(col), kk)
                if z3.is_expr(c) and c.size() != kk:
                    c = z3.ZeroExt(kk - c.size(), c)
                return z3.Select(Cell, r * z3.BitVecVal(n, kk) + c)
        else:
            Cell = z3.Array("T", z3.IntSort(), z3.IntSort())

            def T_at(row, col):
                return z3.Select(Cell, zint(row) * n + zint(col))

        Tinv_at = None  # not available without UF

    # All cells are values in Omega = {0, ..., n-1}.
    for y in range(n):
        for x in range(n):
            val = T_at(y, x)
            solver.add(in_range(val))
            if opts.inverse_channel and Tinv_at is not None:
                ival = Tinv_at(y, x)
                solver.add(in_range(ival))

    if opts.inverse_channel and Tinv_at is not None:
        # Inverse channeling: each row L_y is a permutation, witnessed by L_y^{-1}.
        # This replaces and strengthens the per-row Distinct constraint.
        for y in range(n):
            for x in range(n):
                solver.add(Tinv_at(y, T_at(y, x)) == x)
                solver.add(T_at(y, Tinv_at(y, x)) == x)
    else:
        # Fall back to per-row Distinct.
        for y in range(n):
            solver.add(z3.Distinct([T_at(y, x) for x in range(n)]))

    # Optional Distinct on top of channeling. Redundant but sometimes a useful cut.
    if opts.distinct_rows_under_channeling and opts.inverse_channel and Tinv_at is not None:
        for y in range(n):
            solver.add(z3.Distinct([T_at(y, x) for x in range(n)]))

    # Optional but implied by E677: x -> L_x is injective.
    if opts.distinct_rows:
        for i in range(n):
            for j in range(i + 1, n):
                solver.add(z3.Or([T_at(i, x) != T_at(j, x) for x in range(n)]))

    # Fixed cycles of L_0.
    for cyc in opts.fixed_l0_cycles:
        for i, src in enumerate(cyc):
            dst = cyc[(i + 1) % len(cyc)]
            solver.add(eq_const(T_at(0, src), dst))

    # E677:
    #     L_y( L_x( L_{L_y(x)}(y) ) ) = x
    for y in range(n):
        for x in range(n):
            u = T_at(y, x)
            v = T_at(u, y)
            w = T_at(x, v)
            solver.add(eq_const(T_at(y, w), x))

    # Transformed identity (consequence of E677, see HINT_PACK):
    #     z = (y o z) o ((y o (y o z)) o y)
    if opts.transformed_identity:
        for y in range(n):
            for zz in range(n):
                yz = T_at(y, zz)
                yyz = T_at(y, yz)
                yyzy = T_at(yyz, y)
                solver.add(eq_const(T_at(yz, yyzy), zz))

    # Closed-form inverse from E677:
    #     L_y^{-1}(x) = x o ((y o x) o y)
    if opts.explicit_inverse and Tinv_at is not None:
        for y in range(n):
            for x in range(n):
                yx = T_at(y, x)
                yxy = T_at(yx, y)
                solver.add(Tinv_at(y, x) == T_at(x, yxy))

    # E255 failure at the witness:
    #     L_{L_{L_a(a)}(a)}(a) != a
    b = T_at(a, a)
    c = T_at(b, a)
    solver.add(T_at(c, a) != vconst(a))

    if opts.require_no_fixer_of_witness:
        # Under E677 + column-fixer uniqueness this is equivalent to E255
        # failure at a: no row L_y fixes the witness-column entry a.
        for y in range(n):
            solver.add(T_at(y, a) != vconst(a))

    if opts.structural_cuts:
        # Column-fixer uniqueness:
        # for each column x, at most one row y may satisfy L_y(x)=x.
        # This follows from E677, but the Boolean AtMost form propagates well.
        for x in range(n):
            solver.add(z3.AtMost(*[eq_const(T_at(y, x), x) for y in range(n)], 1))

        # No proper 2-cycle or proper 3-cycle through x under L_x.
        # Fixed points L_x(x)=x are allowed.
        for x in range(n):
            x1 = T_at(x, x)
            x2 = T_at(x, x1)
            x3 = T_at(x, x2)
            solver.add(z3.Implies(x1 != vconst(x), x2 != vconst(x)))
            solver.add(z3.Implies(z3.And(x1 != vconst(x), x2 != vconst(x)), x3 != vconst(x)))

    # Cycle-derived ground facts.
    # If a fixed L_0 cycle of length d >= 3 starts at the witness a, then E677
    # together with d_1 = c_{d-2} (HINT_PACK item 4) forces:
    #     L_{c_1}(a)       = c_{d-2}     (from d_1 = c_1 o a and L_a^2(d_1) = a)
    #     L_{c_{d-1}}(c_1) = c_{d-2}     (from c_{d-2} = c_{d-1} o d_0, d_0 = c_1)
    if opts.cycle_ground_facts:
        for cyc in opts.fixed_l0_cycles:
            if len(cyc) >= 3 and cyc[0] == a:
                d = len(cyc)
                c1 = cyc[1]
                cdm1 = cyc[d - 1]
                cdm2 = cyc[d - 2]
                solver.add(eq_const(T_at(c1, a), cdm2))
                solver.add(eq_const(T_at(cdm1, c1), cdm2))

    return solver, T_at, Cell, z3


def extract_table(model, T_at, n: int) -> List[List[int]]:
    table: List[List[int]] = []
    for y in range(n):
        row = []
        for x in range(n):
            v = model.evaluate(T_at(y, x), model_completion=True)
            # Works for both IntNumRef and BitVecNumRef.
            try:
                row.append(int(v.as_long()))
            except AttributeError:
                row.append(int(v.as_string()))
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
        use_uf=not args.no_uf,
        inverse_channel=not args.no_inverse_channel,
        explicit_inverse=not args.no_explicit_inverse,
        transformed_identity=not args.no_transformed_identity,
        cycle_ground_facts=not args.no_cycle_ground_facts,
        bv=args.bv,
        tactic=args.tactic or "",
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
        print(f"  uf encoding={opts.use_uf}")
        print(f"  inverse channeling={opts.inverse_channel}")
        print(f"  explicit inverse={opts.explicit_inverse}")
        print(f"  transformed identity={opts.transformed_identity}")
        print(f"  cycle ground facts={opts.cycle_ground_facts}")
        print(f"  bv encoding={opts.bv}")
        print(f"  tactic={opts.tactic or 'default'}")
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
                    "use_uf": opts.use_uf,
                    "inverse_channel": opts.inverse_channel,
                    "explicit_inverse": opts.explicit_inverse,
                    "transformed_identity": opts.transformed_identity,
                    "cycle_ground_facts": opts.cycle_ground_facts,
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
        "--no-uf",
        action="store_true",
        help="use the legacy Array(IntSort,IntSort) encoding instead of UF Function",
    )
    p.add_argument(
        "--no-inverse-channel",
        action="store_true",
        help="disable Tinv channeling (per-row Distinct is used as fallback)",
    )
    p.add_argument(
        "--no-explicit-inverse",
        action="store_true",
        help="disable Tinv(y,x) = x o ((y o x) o y) closed-form rewrite",
    )
    p.add_argument(
        "--no-transformed-identity",
        action="store_true",
        help="disable the redundant transformed-identity axiom",
    )
    p.add_argument(
        "--no-cycle-ground-facts",
        action="store_true",
        help="disable cycle-derived ground unit literals (L_{c_1}(a), L_{c_{d-1}}(c_1))",
    )
    p.add_argument(
        "--bv",
        action="store_true",
        help="use bit-vector value sort (Z3 bit-blasts to SAT; often much faster)",
    )
    p.add_argument(
        "--tactic",
        default="",
        help="optional Z3 tactic to wrap the solver, e.g. 'qffd', 'smt', 'psmt', 'qfbv'",
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


def solve_once(opts_dict: dict) -> dict:
    """
    Picklable, side-effect-light entry point used by the portfolio driver.

    Input is a plain dict matching the BuildOptions fields, plus optional keys:
      - "label": a string identifying the worker (returned in the result)

    Output is a plain dict:
      {
        "label": <str>,
        "status": "sat" | "unsat" | "unknown",
        "elapsed_seconds": <float>,
        "table": <list[list[int]]> or None,    # only on sat
        "verified": <bool>,                    # only on sat
        "reason": <str>,                       # only on unknown
        "n": <int>,
        "witness": <int>,
      }
    """
    label = str(opts_dict.pop("label", ""))
    # Only keep keys that BuildOptions actually accepts.
    allowed = {f.name for f in BuildOptions.__dataclass_fields__.values()}
    clean = {k: v for k, v in opts_dict.items() if k in allowed}
    opts = BuildOptions(**clean)

    solver, T_at, _Cell, z3 = build_solver(opts)

    start = time.time()
    result = solver.check()
    elapsed = time.time() - start

    out = {
        "label": label,
        "elapsed_seconds": elapsed,
        "n": opts.n,
        "witness": opts.witness,
        "table": None,
        "verified": False,
    }
    if result == z3.sat:
        model = solver.model()
        table = extract_table(model, T_at, opts.n)
        out["status"] = "sat"
        out["table"] = table
        out["verified"] = verify_table(table, witness=opts.witness, verbose=False)
    elif result == z3.unsat:
        out["status"] = "unsat"
    else:
        out["status"] = "unknown"
        try:
            out["reason"] = solver.reason_unknown()
        except Exception:
            out["reason"] = "unknown"
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = make_parser().parse_args(argv)
    if args.verify:
        return run_verify(args)
    return run_search(args)


if __name__ == "__main__":
    raise SystemExit(main())
