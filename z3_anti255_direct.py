"""
Direct Z3-based search for E677 ∧ ¬E255 counterexamples.

Unlike color-extensions-nonlinear.py (which builds product magma over a known base),
this script directly encodes the full n×n magma table as Z3 variables and searches
for a model satisfying E677 where some element violates E255.

This is an exact SAT/SMT search — if it returns UNSAT, no counterexample exists at that size.

The script uses several optimizations:
1. Symmetry breaking: fix element 0's orbit start
2. Left-cancellation: L_y is a permutation (each row is a bijection)
3. Orbit constraints from known invariants (d-injectivity at element 0 is negated)
4. Incremental solving: check each orbit period d separately

Usage:
    python z3_anti255_direct.py <n> [--timeout SECONDS] [--orbit-d D]
    python z3_anti255_direct.py range <n_min> <n_max> [--timeout SECONDS]
"""

import sys
import time
from z3 import *


def create_magma_solver(n, timeout_ms=600000, orbit_d=None):
    """
    Create a Z3 solver for E677 ∧ ¬E255 at size n.

    Returns (solver, table_vars, status_info) or None if trivially unsat.
    """
    s = Solver()
    s.set("timeout", timeout_ms)

    # Table variables: table[x][y] = x ◇ y ∈ {0, ..., n-1}
    table = [[Int(f"t_{x}_{y}") for y in range(n)] for x in range(n)]

    # Domain constraints
    for x in range(n):
        for y in range(n):
            s.add(table[x][y] >= 0, table[x][y] < n)

    # Left-cancellation: each row is a permutation (L_y bijective)
    # Row x: table[x][0], table[x][1], ..., table[x][n-1] are all distinct
    for x in range(n):
        s.add(Distinct([table[x][y] for y in range(n)]))

    # E677: for all x, y: x = y ◇ (x ◇ ((y ◇ x) ◇ y))
    # Rewritten with table indexing:
    # Let a = table[y][x] (= y ◇ x)
    # Let b = table[a][y] (= (y ◇ x) ◇ y)
    # Let c = table[x][b] (= x ◇ ((y ◇ x) ◇ y))
    # Require: table[y][c] == x (= y ◇ (x ◇ ((y ◇ x) ◇ y)))

    # For small n, we can encode E677 using nested If-chains
    def encode_lookup(row_idx_expr, col_idx_expr, name_prefix):
        """Encode table[row_idx_expr][col_idx_expr] as a Z3 expression."""
        result = table[0][0]  # fallback
        for r in range(n - 1, -1, -1):
            for c in range(n - 1, -1, -1):
                result = If(And(row_idx_expr == r, col_idx_expr == c),
                           table[r][c], result)
        return result

    # More efficient: two-level lookup
    def encode_lookup_2level(row_expr, col_expr):
        """Two-level If-chain: first select row, then select column."""
        # Inner: for each possible row r, compute table[r][col_expr]
        def row_lookup(r):
            result = table[r][0]
            for c in range(n - 1, 0, -1):
                result = If(col_expr == c, table[r][c], result)
            return result

        # Outer: select the right row
        result = row_lookup(0)
        for r in range(n - 1, 0, -1):
            result = If(row_expr == r, row_lookup(r), result)
        return result

    print(f"  Encoding E677 constraints for n={n}...")
    t0 = time.time()

    for x in range(n):
        for y in range(n):
            # a = y ◇ x = table[y][x]  (concrete indices, so just table[y][x])
            a = table[y][x]
            # b = a ◇ y = table[a][y]  (a is symbolic, so we need If-chain for row)
            b = encode_lookup_2level(a, IntVal(y))
            # c = x ◇ b = table[x][b]  (b is symbolic, so If-chain for column)
            c_val = table[x][0]
            for col in range(n - 1, 0, -1):
                c_val = If(b == col, table[x][col], c_val)
            # result = y ◇ c = table[y][c]  (c is symbolic)
            result = table[y][0]
            for col in range(n - 1, 0, -1):
                result = If(c_val == col, table[y][col], result)
            s.add(result == x)

    print(f"  E677 encoded in {time.time()-t0:.1f}s")

    # ¬E255: there exists some x where ((x◇x)◇x)◇x ≠ x
    # Encode: OR over all x of [table[table[table[x][x]][x]][x] != x]
    anti_e255_clauses = []
    for x in range(n):
        xx = table[x][x]
        # table[xx][x]: xx is symbolic
        xxx = table[0][x]
        for r in range(n - 1, 0, -1):
            xxx = If(xx == r, table[r][x], xxx)
        # table[xxx][x]: xxx is symbolic
        xxxx = table[0][x]
        for r in range(n - 1, 0, -1):
            xxxx = If(xxx == r, table[r][x], xxxx)
        anti_e255_clauses.append(xxxx != x)

    s.add(Or(anti_e255_clauses))

    # Symmetry breaking: fix table[0][0] = 1 (element 0 maps to 1 under L_0)
    # This is valid because we can always relabel so L_0 starts the orbit 0->1
    if n >= 2:
        s.add(table[0][0] == 1)

    # Known invariant: no period-2 orbits. For x=0: table[0][table[0][0]] != 0 when n >= 3
    # Actually let's not over-constrain — the solver should find this quickly.

    print(f"  Total constraints encoded. Solving...")

    return s, table


def solve_and_report(n, timeout_s=600):
    """Run the Z3 search at size n and report results."""
    print(f"\n{'='*60}")
    print(f"Z3 direct anti-E255 search: n={n}")
    print(f"{'='*60}")

    t0 = time.time()
    result = create_magma_solver(n, timeout_ms=timeout_s * 1000)
    if result is None:
        print("Trivially unsatisfiable.")
        return "UNSAT"

    s, table = result
    status = s.check()
    elapsed = time.time() - t0

    print(f"  Result: {status} ({elapsed:.1f}s)")

    if status == sat:
        model = s.model()
        print(f"\n*** COUNTEREXAMPLE FOUND AT n={n}! ***")
        print(f"Magma table:")
        for x in range(n):
            row = [model.evaluate(table[x][y]).as_long() for y in range(n)]
            print(f"  {' '.join(f'{v:3d}' for v in row)}")

        # Verify E255 failure
        tbl = [[model.evaluate(table[x][y]).as_long() for y in range(n)] for x in range(n)]
        print(f"\nE255 check:")
        for x in range(n):
            xx = tbl[x][x]
            xxx = tbl[xx][x]
            xxxx = tbl[xxx][x]
            if xxxx != x:
                print(f"  x={x}: x◇x={xx}, (x◇x)◇x={xxx}, ((x◇x)◇x)◇x={xxxx} ≠ {x}  FAIL")

        # Verify E677
        e677_ok = True
        for x in range(n):
            for y in range(n):
                yx = tbl[y][x]
                yxy = tbl[yx][y]
                xyxy = tbl[x][yxy]
                result = tbl[y][xyxy]
                if result != x:
                    print(f"  E677 FAIL at x={x}, y={y}")
                    e677_ok = False
                    break
            if not e677_ok:
                break
        if e677_ok:
            print(f"  E677 verified OK on all {n*n} pairs")

        return "SAT"
    elif status == unsat:
        print(f"  UNSAT at n={n}: no E677 ∧ ¬E255 model exists at this size")
        return "UNSAT"
    else:
        print(f"  UNKNOWN (timeout or resource limit) at n={n}")
        return "UNKNOWN"


def main():
    if len(sys.argv) < 2:
        print("Usage: python z3_anti255_direct.py <n> [--timeout SECONDS]")
        print("       python z3_anti255_direct.py range <n_min> <n_max> [--timeout SECONDS]")
        sys.exit(1)

    timeout_s = 600
    for i, arg in enumerate(sys.argv):
        if arg == "--timeout" and i + 1 < len(sys.argv):
            timeout_s = int(sys.argv[i + 1])

    if sys.argv[1] == "range":
        n_min = int(sys.argv[2])
        n_max = int(sys.argv[3])
        results = {}
        for n in range(n_min, n_max + 1):
            r = solve_and_report(n, timeout_s)
            results[n] = r
            if r == "SAT":
                print(f"\n*** Counterexample found at n={n}! Stopping. ***")
                break
        print(f"\n{'='*60}")
        print("Summary:")
        for n, r in sorted(results.items()):
            print(f"  n={n}: {r}")
    else:
        n = int(sys.argv[1])
        solve_and_report(n, timeout_s)


if __name__ == "__main__":
    main()
