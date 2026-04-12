"""
Targeted cascade-gap counterexample search for E677 ⊨_fin E255.

The mathematical gap in the proof (L3 from eq677-invariants.md) is:
  Given d_i = d_j, we need d_{i-1} = d_{j-1} to cascade the collision.
  This is UNPROVED — so counterexamples might exploit this exact gap.

This script constructs magma tables that satisfy E677 and deliberately
engineer orbit structures where the cascade collision FAILS to propagate —
meaning d_i = d_j but d_{i-1} ≠ d_{j-1}.

== MATHEMATICAL SETUP ==

For element x with L_x orbit period d:
  c_0 = x, c_1 = x◇x, c_2 = x◇c_1, ..., c_{d-1} = x◇c_{d-2}, c_d = c_0
  d_k = c_k ◇ x  (the "d-sequence")

From L1 (Key Recurrence): c_{k-1} = c_k ◇ d_{k+1}
From L2 (Squaring Index): c_{d-4} ◇ c_{d-4} = c_{d-5} (for d ≥ 5)
From L2b: d_{d-2} = x (anchor)

E255 (d-injectivity) = all d_k distinct
Counterexample = some d_i = d_j with i ≠ j

The cascade argument: if d_i = d_j, then from L1:
  c_{i-2} = c_{i-1} ◇ d_i = c_{i-1} ◇ d_j
But we DON'T know c_{i-1} = c_{j-1}, so we can't conclude c_{i-2} = c_{j-2}.
The gap is precisely that the R_x collision doesn't propagate backwards.

== CONSTRUCTION APPROACH ==

1. Fix orbit period d (try d=7, the smallest fully open cascade case)
2. Prescribe the c-sequence: c_0, c_1, ..., c_{d-1} (a d-cycle under L_x)
3. Choose d_i values such that d_i = d_j for some i ≠ j (violating E255)
   but NOT triggering the cascade contradiction
4. Try to extend to a full n×n magma table satisfying E677

Usage:
    python cascade_gap_search.py <d> [n_min] [n_max] [--workers N]
"""

import sys
import random
import time
import itertools
from collections import defaultdict


def e677_check_pair(table, n, x, y):
    """Check E677 for a single (x, y) pair. Returns True if satisfied."""
    yx = table[y][x]
    if yx is None: return True  # undefined, skip
    yxy = table[yx][y]
    if yxy is None: return True
    xyxy = table[x][yxy]
    if xyxy is None: return True
    result = table[y][xyxy]
    if result is None: return True
    return result == x


def build_orbit_constrained_magma(d, n, collision_pair, max_attempts=10000, seed=None):
    """
    Attempt to build an n-element E677 magma with orbit period d at element 0,
    where the d-sequence has a specific collision pair (i, j) with d_i = d_j.

    Parameters:
        d: target orbit period at element 0
        n: total magma size (must be >= d)
        collision_pair: (i, j) with 0 <= i < j < d, meaning d_i = d_j
        max_attempts: number of random completion attempts
        seed: random seed

    Returns: (table, success_info) or None
    """
    if n < d:
        return None

    rng = random.Random(seed)

    # c-sequence: elements 0, 1, ..., d-1 form the orbit of element 0
    # c_0 = 0, c_1 = 1, ..., c_{d-1} = d-1
    # L_0(c_k) = c_{k+1} mod d, i.e., table[0][k] = (k+1) % d for k < d

    ci, cj = collision_pair  # d_ci = d_cj (these are the colliding d-sequence indices)

    for attempt in range(max_attempts):
        table = [[None] * n for _ in range(n)]

        # Step 1: Set up the L_0 orbit
        for k in range(d):
            table[0][k] = (k + 1) % d

        # Fill remaining L_0 entries (0 acts on elements d..n-1)
        remaining = list(range(d, n))
        rng.shuffle(remaining)
        # L_0 must be a bijection on {0,...,n-1}
        # We already have 0->1, 1->2, ..., d-1->0
        # Need a permutation of {d,...,n-1} for the rest
        for idx, elem in enumerate(range(d, n)):
            table[0][elem] = remaining[idx]

        # Step 2: Set up d-sequence with collision
        # d_k = c_k ◇ 0 = table[k][0] for k < d
        # We want d_ci = d_cj = some shared value v
        # The other d_k values should be distinct (to make E255 "almost" hold)

        # Choose d-sequence values
        # d_{d-2} = 0 (anchor from L2b)
        d_seq = [None] * d

        # Anchor: d_{d-2} = x = 0
        d_seq[d - 2] = 0

        # Collision: d_ci = d_cj = some value v
        # v should not be 0 (unless ci or cj == d-2)
        available = list(range(n))
        # Remove 0 (used by d_{d-2})
        available.remove(0)

        # Choose collision value
        collision_val = rng.choice(available)
        d_seq[ci] = collision_val
        d_seq[cj] = collision_val

        # Fill other d-sequence entries
        used = {0, collision_val}
        if ci == d - 2 or cj == d - 2:
            # collision_val must be 0
            collision_val = 0
            d_seq[ci] = 0
            d_seq[cj] = 0
            used = {0}

        for k in range(d):
            if d_seq[k] is not None:
                continue
            choices = [v for v in range(n) if v not in used]
            if not choices:
                break
            v = rng.choice(choices)
            d_seq[k] = v
            used.add(v)

        if any(v is None for v in d_seq):
            continue

        # Set d-sequence in table: table[k][0] = d_seq[k]
        for k in range(d):
            table[k][0] = d_seq[k]

        # For elements d..n-1, set table[elem][0] to fill remaining column 0 values
        col0_used = set(d_seq)
        col0_remaining = [v for v in range(n) if v not in col0_used]
        rng.shuffle(col0_remaining)
        for idx, elem in enumerate(range(d, n)):
            if idx < len(col0_remaining):
                table[elem][0] = col0_remaining[idx]
            else:
                # Column 0 already full — shouldn't happen if n > d
                break

        # Verify column 0 is a valid permutation (R_0 can be non-injective for E677)
        # Actually: L_y injectivity means each ROW must be a permutation.
        # Column constraints come from R_x, which need NOT be injective.
        # So column 0 having d_ci = d_cj is allowed!

        # Step 3: Fill remaining table entries greedily
        # Maintain row-injectivity (left-cancellation)

        # Process cells in priority order:
        # First: complete E677 chains involving the orbit
        # Then: random fill

        cells_to_fill = []
        for x in range(n):
            for y in range(n):
                if table[x][y] is None:
                    cells_to_fill.append((x, y))

        rng.shuffle(cells_to_fill)

        success = True
        for (x, y) in cells_to_fill:
            if table[x][y] is not None:
                continue

            # Already used in row x
            row_used = set(v for v in table[x] if v is not None)
            available = [v for v in range(n) if v not in row_used]

            if not available:
                success = False
                break

            # Filter by E677 consistency
            valid = []
            for v in available:
                table[x][y] = v
                ok = True
                # Check all E677 constraints involving cell (x, y)
                for a in range(n):
                    for b in range(n):
                        if not e677_check_pair(table, n, a, b):
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    valid.append(v)
                table[x][y] = None

            if not valid:
                # Try relaxed: just pick one that doesn't violate any FULLY-DETERMINED constraint
                valid = available  # fall back to any available

            if not valid:
                success = False
                break

            table[x][y] = rng.choice(valid)

        if not success:
            continue

        # Step 4: Verify full E677 and check E255
        e677_ok = True
        for x in range(n):
            for y in range(n):
                if not e677_check_pair(table, n, x, y):
                    e677_ok = False
                    break
            if not e677_ok:
                break

        if not e677_ok:
            continue

        # Check E255
        e255_failures = []
        for x in range(n):
            xx = table[x][x]
            xxx = table[xx][x]
            xxxx = table[xxx][x]
            if xxxx != x:
                e255_failures.append(x)

        return table, {
            'e677': True,
            'e255_failures': e255_failures,
            'd': d,
            'n': n,
            'collision': collision_pair,
            'd_seq': d_seq,
            'attempt': attempt,
        }

    return None


def enumerate_collision_patterns(d):
    """
    Enumerate collision patterns (i, j) for orbit period d.
    Only consider pairs that don't trivially trigger cascade contradiction.

    The cascade argument fully works for some pairs (those are "refuted" by ATP).
    For d=7, the OPEN pairs from progress.json are:
      (0,3), (1,3), (2,3), (2,4), (2,6), (3,6), (4,6)
    """
    # d=7 open pairs (from cascade-gap ATP results)
    if d == 7:
        return [(0, 3), (1, 3), (2, 3), (2, 4), (2, 6), (3, 6), (4, 6)]

    # For other d: all pairs where the cascade isn't trivially closed
    # (conservative: try all)
    return [(i, j) for i in range(d) for j in range(i + 1, d)
            if abs(i - j) > 1]  # adjacent pairs cascade trivially


def main():
    d = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    n_min = int(sys.argv[2]) if len(sys.argv) > 2 else d + 1
    n_max = int(sys.argv[3]) if len(sys.argv) > 3 else d + 20
    max_attempts = 5000
    seed = 42

    for i, arg in enumerate(sys.argv):
        if arg == "--attempts" and i + 1 < len(sys.argv):
            max_attempts = int(sys.argv[i + 1])
        if arg == "--seed" and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1])

    print(f"Cascade-gap search: d={d}, n={n_min}..{n_max}, "
          f"attempts={max_attempts}, seed={seed}")

    collision_patterns = enumerate_collision_patterns(d)
    print(f"Collision patterns to try: {collision_patterns}")
    print()

    for n in range(n_min, n_max + 1):
        print(f"\n--- n={n} ---")
        for (ci, cj) in collision_patterns:
            print(f"  Collision ({ci},{cj}): ", end="", flush=True)
            t0 = time.time()

            result = build_orbit_constrained_magma(
                d, n, (ci, cj), max_attempts=max_attempts,
                seed=seed + n * 1000 + ci * 100 + cj
            )

            elapsed = time.time() - t0

            if result is None:
                print(f"no valid table found ({elapsed:.1f}s)")
                continue

            table, info = result
            e255_f = info['e255_failures']
            print(f"E677 OK, E255 fails={len(e255_f)}, attempt={info['attempt']}, "
                  f"time={elapsed:.1f}s")

            if e255_f:
                print(f"\n{'='*60}")
                print(f"*** COUNTEREXAMPLE FOUND! ***")
                print(f"n={n}, d={d}, collision=({ci},{cj})")
                print(f"d-sequence: {info['d_seq']}")
                print(f"E255 failures: {e255_f}")
                print(f"Table:")
                for row in table:
                    print("  " + " ".join(f"{v:3d}" for v in row))
                print(f"{'='*60}")
                return

    print("\nNo counterexample found in the searched range.")


if __name__ == "__main__":
    main()
