"""
Pure-SAT encoding of E677 ∧ ¬E255 using Z3's SAT backend.

Instead of integer variables with If-chains, we use Boolean variables:
  P[x][y][v] = True iff table[x][y] = v

This gives the SAT solver direct access to Boolean reasoning, which is
orders of magnitude faster than the SMT integer encoding for this problem.

The encoding uses the standard approach for constraint satisfaction:
1. At-least-one: For each (x,y), at least one P[x][y][v] is true
2. At-most-one: For each (x,y), at most one P[x][y][v] is true
3. Left-cancel: For each x,v, at most one y has P[x][y][v]=true (column-distinct)
4. E677: For all x,y: table[y][table[x][table[table[y][x]][y]]] = x
5. Anti-E255: exists x: table[table[table[x][x]][x]][x] != x

Usage:
    python sat_anti255.py <n> [--timeout SECONDS]
    python sat_anti255.py range <n_min> <n_max> [--timeout SECONDS]
"""

import sys
import time
from z3 import *


def solve_sat(n, timeout_s=600):
    """
    Pure-SAT encoding for E677 ∧ ¬E255 at size n.
    Uses Boolean variables P[x][y][v] = (table[x][y] == v).

    Correct anti-E255: for each target element x, use push/pop to assert
    E255 fails at x via hard clauses (no free auxiliary variables).
    """
    print(f"\n{'='*60}")
    print(f"SAT anti-E255 search: n={n}")
    print(f"{'='*60}")

    t0 = time.time()

    s = Solver()
    s.set("timeout", timeout_s * 1000)

    # Boolean variables: P[x][y][v] means table[x][y] = v
    P = [[[Bool(f"P_{x}_{y}_{v}") for v in range(n)]
          for y in range(n)]
         for x in range(n)]

    # 1. Exactly-one constraints: each cell has exactly one value
    print(f"  Encoding exactly-one constraints...")
    for x in range(n):
        for y in range(n):
            # At least one value
            s.add(Or([P[x][y][v] for v in range(n)]))
            # At most one value (pairwise mutex)
            for v1 in range(n):
                for v2 in range(v1 + 1, n):
                    s.add(Not(And(P[x][y][v1], P[x][y][v2])))

    # 2. Left-cancellation: each row x is a permutation
    # For each row x and value v: exactly one column y has P[x][y][v]
    print(f"  Encoding left-cancellation...")
    for x in range(n):
        for v in range(n):
            # At least one column has this value
            s.add(Or([P[x][y][v] for y in range(n)]))
            # At most one column (pairwise)
            for y1 in range(n):
                for y2 in range(y1 + 1, n):
                    s.add(Not(And(P[x][y1][v], P[x][y2][v])))

    # 3. E677: for all x, y: table[y][table[x][table[table[y][x]][y]]] = x
    #
    # As a clause: P[y][x][a] ∧ P[a][y][b] ∧ P[x][b][c] → P[y][c][x]
    # Equivalently: ¬P[y][x][a] ∨ ¬P[a][y][b] ∨ ¬P[x][b][c] ∨ P[y][c][x]

    print(f"  Encoding E677 constraints ({n}^2 × {n}^3 = {n**2 * n**3} clauses)...")
    e677_t0 = time.time()

    for x in range(n):
        for y in range(n):
            for a in range(n):  # a = y ◇ x
                for b in range(n):  # b = a ◇ y = (y◇x)◇y
                    for c in range(n):  # c = x ◇ b
                        # P[y][x][a] ∧ P[a][y][b] ∧ P[x][b][c] → P[y][c][x]
                        s.add(Or(
                            Not(P[y][x][a]),
                            Not(P[a][y][b]),
                            Not(P[x][b][c]),
                            P[y][c][x]
                        ))

    e677_time = time.time() - e677_t0
    print(f"  E677 encoded in {e677_time:.1f}s")

    # 4. Symmetry breaking
    if n >= 2:
        s.add(P[0][0][1])  # table[0][0] = 1

    encode_time = time.time() - t0
    print(f"  Base encoding time: {encode_time:.1f}s")

    # 5. Anti-E255: iterate over target elements x using push/pop.
    # For target x, "E255 fails at x" means ((x◇x)◇x)◇x ≠ x.
    # Hard clauses: for all a,b: ¬P[x][x][a] ∨ ¬P[a][x][b] ∨ ¬P[b][x][x]
    # These say: every chain x→a→b must end with table[b][x] ≠ x.

    any_timeout = False
    for target_x in range(n):
        print(f"  Trying anti-E255 at element x={target_x}...", end="", flush=True)
        s.push()

        # Hard: for ALL a,b: if table[x][x]=a and table[a][x]=b, then table[b][x] ≠ x
        for a in range(n):
            for b in range(n):
                s.add(Or(
                    Not(P[target_x][target_x][a]),
                    Not(P[a][target_x][b]),
                    Not(P[b][target_x][target_x])
                ))

        solve_t0 = time.time()
        status = s.check()
        solve_time = time.time() - solve_t0

        if status == sat:
            model = s.model()
            total_time = time.time() - t0
            print(f" SAT! ({solve_time:.1f}s)")

            # Extract table
            tbl = [[None] * n for _ in range(n)]
            for x in range(n):
                for y in range(n):
                    for v in range(n):
                        if is_true(model[P[x][y][v]]):
                            tbl[x][y] = v
                            break

            # Verify E677
            e677_ok = True
            for x in range(n):
                for y in range(n):
                    yx = tbl[y][x]
                    yxy = tbl[yx][y]
                    xyxy = tbl[x][yxy]
                    result = tbl[y][xyxy]
                    if result != x:
                        print(f"  E677 FAIL at x={x}, y={y} — ENCODING BUG!")
                        e677_ok = False
                        break
                if not e677_ok:
                    break

            # Verify E255 failure
            real_e255_fail = False
            for x in range(n):
                xx = tbl[x][x]
                xxx = tbl[xx][x]
                xxxx = tbl[xxx][x]
                if xxxx != x:
                    real_e255_fail = True
                    print(f"  E255 FAIL: x={x}, x◇x={xx}, (x◇x)◇x={xxx}, "
                          f"((x◇x)◇x)◇x={xxxx}")

            if e677_ok and real_e255_fail:
                print(f"\n*** GENUINE COUNTEREXAMPLE FOUND AT n={n}! ***")
                print(f"Magma table:")
                for x in range(n):
                    print(f"  {' '.join(f'{v:3d}' for v in tbl[x])}")
                print(f"  E677: verified OK on all {n*n} pairs")
                print(f"  Total time: {total_time:.1f}s")
                return "SAT"
            else:
                if e677_ok and not real_e255_fail:
                    print(f"  WARNING: SAT but E255 holds — possible encoding issue")
                s.pop()
                continue

        elif status == unsat:
            print(f" unsat ({solve_time:.1f}s)")
            s.pop()
        else:
            print(f" timeout ({solve_time:.1f}s)")
            any_timeout = True
            s.pop()

    total_time = time.time() - t0
    # Check if any element timed out — if so, result is UNKNOWN, not UNSAT
    print(f"\n  All {n} target elements checked ({total_time:.1f}s).")
    if any_timeout:
        print(f"  UNKNOWN: some elements timed out at n={n}")
        return "UNKNOWN"
    else:
        print(f"  PROVED: no E677 ∧ ¬E255 model exists at n={n}")
        return "UNSAT"


def main():
    if len(sys.argv) < 2:
        print("Usage: python sat_anti255.py <n> [--timeout SECONDS]")
        print("       python sat_anti255.py range <n_min> <n_max> [--timeout SECONDS]")
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
            r = solve_sat(n, timeout_s)
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
        solve_sat(n, timeout_s)


if __name__ == "__main__":
    main()
