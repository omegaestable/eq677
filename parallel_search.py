"""
High-performance multiprocessing counterexample search for E677 ⊨_fin E255.

Uses Python multiprocessing to parallelize across CPU cores, with specialized
search strategies targeting the most promising magma sizes.

== KEY MATHEMATICAL INSIGHTS FOR SIZE SELECTION ==

From the blueprint (Section 13, Lemma 13.4):
  - Linear extensions over abelian groups CANNOT give counterexamples.
  - NON-linear fiber operations are required.
  - The non-right-cancellative construction (Section 13.1) shows that
    product magmas with quadratic-residue-split fibers CAN break right-cancel.
  - But all known such constructions still satisfy E255.

From invariant analysis (eq677-invariants.md):
  - All 439 known models satisfy d-injectivity (= E255 on orbits)
  - Orbit periods seen: {1,6,7,8,9,10,11,...} — no period 2, 3, 4
  - No 8-cycle in squaring map S(x) = x◇x
  - If a counterexample exists, it must have a novel orbit structure

== TARGET SIZES ==

Tier 1 (highest priority — algebraic structure enables exotic constructions):
  n=16: GF(2^4), has ω_3 and ζ_5 simultaneously
  n=31: smallest p≡1(mod 30), supports full Section 13.1 construction
  n=61: next p≡1(mod 30)
  n=32: GF(2^5), has 31st roots forming rich structure
  n=64: GF(2^6), 63 = 7·9, has 7th and 9th roots

Tier 2 (secondary — structural variants):
  n=11, 23, 41, 71: p≡1(mod 10) but not mod 3 — Type I only, no Type II
  n=p for p ≡ 1 (mod 7) — period-7 orbit structures
  n=p² (25, 49) — product/wreath structures on Z/p × Z/p

Tier 3 (long-shot — large random search):
  n in 19..30: WalkSAT/annealing on each, millions of steps

Usage:
    python parallel_search.py [--workers N] [--strategy STR] [args...]
"""

import multiprocessing as mp
import sys
import time
import random
import itertools
from functools import partial


# ============================================================
# Optimized E677/E255 checking
# ============================================================

def make_flat_table(n, table_2d):
    """Convert 2D table to flat array for cache-friendly access."""
    flat = [0] * (n * n)
    for x in range(n):
        for y in range(n):
            flat[x * n + y] = table_2d[x][y]
    return flat


def count_e677_violations_flat(n, flat):
    """Count E677 violations using flat table. Optimized inner loop."""
    violations = 0
    for x in range(n):
        xn = x * n
        for y in range(n):
            yx = flat[y * n + x]
            yxy = flat[yx * n + y]
            xyxy = flat[xn + yxy]
            if flat[y * n + xyxy] != x:
                violations += 1
    return violations


def check_e255_flat(n, flat):
    """Return count of E255 failures using flat table."""
    failures = 0
    for x in range(n):
        xx = flat[x * n + x]
        xxx = flat[xx * n + x]
        xxxx = flat[xxx * n + x]
        if xxxx != x:
            failures += 1
    return failures


def check_left_cancel_flat(n, flat):
    """Check left cancellation (each row of L_y is a permutation)."""
    for y in range(n):
        seen = 0  # bitmask
        yn = y * n
        for x in range(n):
            v = flat[yn + x]
            bit = 1 << v
            if seen & bit:
                return False
            seen |= bit
    return True


# ============================================================
# Worker: WalkSAT-style local search
# ============================================================

def walksat_worker(args):
    """
    WalkSAT-style search: maintain a latin-square table (left-cancel guaranteed),
    walk through cell swaps to minimize E677 violations.

    When E677 = 0, check E255.
    """
    n, max_flips, noise_prob, worker_id, seed = args
    rng = random.Random(seed)

    # Initialize: random latin square (each column is a random permutation)
    table = [[0]*n for _ in range(n)]
    for col in range(n):
        perm = list(range(n))
        rng.shuffle(perm)
        for row in range(n):
            table[row][col] = perm[row]

    flat = make_flat_table(n, table)
    best_viol = count_e677_violations_flat(n, flat)

    t0 = time.time()
    report_interval = max(max_flips // 20, 10000)

    for flip in range(max_flips):
        # Pick a random column (= which L_y to modify)
        col = rng.randint(0, n - 1)

        # Pick two random rows to swap in that column
        r1 = rng.randint(0, n - 1)
        r2 = rng.randint(0, n - 1)
        while r2 == r1:
            r2 = rng.randint(0, n - 1)

        # Swap
        v1 = flat[r1 * n + col]
        v2 = flat[r2 * n + col]
        flat[r1 * n + col] = v2
        flat[r2 * n + col] = v1

        new_viol = count_e677_violations_flat(n, flat)

        if new_viol <= best_viol or rng.random() < noise_prob:
            best_viol = new_viol

            if new_viol == 0:
                e255_fails = check_e255_flat(n, flat)
                if e255_fails > 0:
                    # COUNTEREXAMPLE!
                    elapsed = time.time() - t0
                    return {
                        'status': 'FOUND',
                        'n': n,
                        'worker': worker_id,
                        'flip': flip,
                        'time': elapsed,
                        'e255_fails': e255_fails,
                        'table': [flat[i*n:(i+1)*n] for i in range(n)],
                    }
        else:
            # Revert
            flat[r1 * n + col] = v1
            flat[r2 * n + col] = v2

        if flip % report_interval == 0 and flip > 0:
            elapsed = time.time() - t0
            return {
                'status': 'PROGRESS',
                'worker': worker_id,
                'n': n,
                'flip': flip,
                'best_viol': best_viol,
                'time': elapsed,
            }

    elapsed = time.time() - t0
    return {
        'status': 'DONE',
        'worker': worker_id,
        'n': n,
        'flips': max_flips,
        'best_viol': best_viol,
        'time': elapsed,
    }


# ============================================================
# Worker: Structured construction search
# ============================================================

def structured_worker(args):
    """
    Search for E677 magmas with specific algebraic structure.

    Tries translation-invariant constructions: x ◇ y = x + h(y - x) mod n,
    where h: Z/nZ -> Z/nZ is an arbitrary function.

    There are n^n such functions. We sample randomly or enumerate for small n.
    """
    n, max_attempts, worker_id, seed = args
    rng = random.Random(seed)

    t0 = time.time()
    e677_count = 0

    for attempt in range(max_attempts):
        # Random function h: Z/nZ -> Z/nZ
        h = [rng.randint(0, n - 1) for _ in range(n)]

        # Build table: f(x, y) = (x + h[(y - x) % n]) % n
        flat = [0] * (n * n)
        for x in range(n):
            xn = x * n
            for y in range(n):
                d = (y - x) % n
                flat[xn + y] = (x + h[d]) % n

        # Quick left-cancel check: h must be a permutation of Z/nZ
        # Actually for translation-invariant, L_y = x + h[(y-x)%n],
        # which is injective iff h is a permutation? No — L_y injectivity
        # requires that for fixed y, x ↦ x + h[(y-x)%n] is injective.
        # That means d ↦ h[d] - d must be injective (since x = y - d).
        # I.e., h(d) - d mod n is a permutation.

        diffs = set()
        lc_ok = True
        for d in range(n):
            val = (h[d] - d) % n
            if val in diffs:
                lc_ok = False
                break
            diffs.add(val)
        if not lc_ok:
            continue

        # Check E677
        viol = count_e677_violations_flat(n, flat)
        if viol == 0:
            e677_count += 1
            e255_fails = check_e255_flat(n, flat)
            if e255_fails > 0:
                elapsed = time.time() - t0
                return {
                    'status': 'FOUND',
                    'n': n,
                    'worker': worker_id,
                    'attempt': attempt,
                    'time': elapsed,
                    'e255_fails': e255_fails,
                    'h': h,
                    'table': [flat[i*n:(i+1)*n] for i in range(n)],
                }

    elapsed = time.time() - t0
    return {
        'status': 'DONE',
        'worker': worker_id,
        'n': n,
        'attempts': max_attempts,
        'e677_found': e677_count,
        'time': elapsed,
    }


# ============================================================
# Worker: Twisted product construction
# ============================================================

def twisted_product_worker(args):
    """
    Search for E677 counterexamples using twisted products.

    Given a known E677 model G (from the DB), try to build G × Z/kZ
    with a twisted operation:
        (a, r) ◇ (b, s) = (a ◇_G b, f_{a,b}(r, s))

    where f_{a,b} depends on the pair (a,b) in the base.

    The key insight: we DON'T require f_{a,b} to be affine.
    We parametrize f_{a,b} by a few "profile types" and enumerate.
    """
    base_n, base_table_flat, k, max_attempts, worker_id, seed = args
    rng = random.Random(seed)

    total_n = base_n * k
    t0 = time.time()
    e677_count = 0

    # Number of distinct color classes: partition (a,b) pairs into equivalence
    # classes by the pair (a◇b, character).
    # For translation-invariant base with chi splitting, there are ~3 classes.
    # For general base, there could be up to n^2 classes.
    # We simplify: assign each (a,b) a fiber table from a small pool.

    pool_size = min(base_n, 6)  # at most 6 distinct fiber operations

    for attempt in range(max_attempts):
        # Generate pool_size random left-cancellative k×k tables
        perms = list(itertools.permutations(range(k)))
        pool = []
        for _ in range(pool_size):
            # Each column is a random permutation
            cols = [list(rng.choice(perms)) for _ in range(k)]
            tbl = [[cols[y][x] for y in range(k)] for x in range(k)]
            pool.append(tbl)

        # Assign each (a,b) -> pool index
        assignments = [[rng.randint(0, pool_size - 1) for _ in range(base_n)]
                       for _ in range(base_n)]

        # Build the product table
        flat = [0] * (total_n * total_n)
        for a in range(base_n):
            for b in range(base_n):
                ab_base = base_table_flat[a * base_n + b]
                fiber_tbl = pool[assignments[a][b]]
                for r in range(k):
                    for s in range(k):
                        fval = fiber_tbl[r][s]
                        row = a * k + r
                        col = b * k + s
                        flat[row * total_n + col] = ab_base * k + fval

        # Check E677
        viol = count_e677_violations_flat(total_n, flat)
        if viol == 0:
            e677_count += 1
            e255_fails = check_e255_flat(total_n, flat)
            if e255_fails > 0:
                elapsed = time.time() - t0
                return {
                    'status': 'FOUND',
                    'n': total_n,
                    'base_n': base_n,
                    'k': k,
                    'worker': worker_id,
                    'attempt': attempt,
                    'time': elapsed,
                    'e255_fails': e255_fails,
                    'table': [flat[i*total_n:(i+1)*total_n] for i in range(total_n)],
                }

    elapsed = time.time() - t0
    return {
        'status': 'DONE',
        'worker': worker_id,
        'n': total_n,
        'attempts': max_attempts,
        'e677_found': e677_count,
        'time': elapsed,
    }


# ============================================================
# Parallel coordinator
# ============================================================

def run_walksat_parallel(n_values, workers=4, flips_per_worker=2000000, noise=0.02, seed=42):
    """Run WalkSAT search in parallel across multiple sizes and workers."""
    print(f"WalkSAT: {len(n_values)} sizes, {workers} workers/size, "
          f"{flips_per_worker} flips/worker")

    tasks = []
    task_id = 0
    for n in n_values:
        for w in range(workers):
            tasks.append((n, flips_per_worker, noise, task_id, seed + task_id * 137))
            task_id += 1

    with mp.Pool(processes=min(workers, mp.cpu_count())) as pool:
        for result in pool.imap_unordered(walksat_worker, tasks):
            if result['status'] == 'FOUND':
                print(f"\n{'='*60}")
                print(f"*** COUNTEREXAMPLE FOUND at n={result['n']}! ***")
                print(f"Worker {result['worker']}, flip {result['flip']}, "
                      f"time={result['time']:.1f}s")
                print(f"E255 fails: {result['e255_fails']}")
                print(f"Table:")
                for row in result['table']:
                    print("  " + " ".join(str(v) for v in row))
                print(f"{'='*60}")
                pool.terminate()
                return result
            elif result['status'] == 'DONE':
                print(f"  Worker {result['worker']} (n={result['n']}): "
                      f"done, best_viol={result['best_viol']}, "
                      f"time={result['time']:.1f}s")

    print("No counterexample found.")
    return None


def run_structured_parallel(n_values, workers=4, attempts_per_worker=500000, seed=42):
    """Run translation-invariant search in parallel."""
    print(f"Structured (tinv): {len(n_values)} sizes, {workers} workers/size, "
          f"{attempts_per_worker} attempts/worker")

    tasks = []
    task_id = 0
    for n in n_values:
        for w in range(workers):
            tasks.append((n, attempts_per_worker, task_id, seed + task_id * 137))
            task_id += 1

    with mp.Pool(processes=min(workers, mp.cpu_count())) as pool:
        for result in pool.imap_unordered(structured_worker, tasks):
            if result['status'] == 'FOUND':
                print(f"\n{'='*60}")
                print(f"*** COUNTEREXAMPLE FOUND at n={result['n']}! ***")
                print(f"Worker {result['worker']}, attempt {result['attempt']}, "
                      f"time={result['time']:.1f}s")
                print(f"E255 fails: {result['e255_fails']}")
                print(f"h = {result['h']}")
                print(f"Table:")
                for row in result['table']:
                    print("  " + " ".join(str(v) for v in row))
                print(f"{'='*60}")
                pool.terminate()
                return result
            elif result['status'] == 'DONE':
                print(f"  Worker {result['worker']} (n={result['n']}): "
                      f"done, {result['e677_found']} E677 models, "
                      f"time={result['time']:.1f}s")

    print("No counterexample found.")
    return None


def run_twisted_product_parallel(base_table_flat, base_n, k_values,
                                  workers=4, attempts_per_worker=200000, seed=42):
    """Run twisted product search over a known E677 base."""
    print(f"Twisted product: base_n={base_n}, k_values={k_values}, "
          f"{workers} workers, {attempts_per_worker} attempts/worker")

    tasks = []
    task_id = 0
    for k in k_values:
        for w in range(workers):
            tasks.append((base_n, base_table_flat, k, attempts_per_worker,
                          task_id, seed + task_id * 137))
            task_id += 1

    with mp.Pool(processes=min(workers, mp.cpu_count())) as pool:
        for result in pool.imap_unordered(twisted_product_worker, tasks):
            if result['status'] == 'FOUND':
                print(f"\n{'='*60}")
                print(f"*** COUNTEREXAMPLE FOUND! n={result['n']} = "
                      f"{result['base_n']}×{result['k']} ***")
                print(f"Worker {result['worker']}, attempt {result['attempt']}, "
                      f"time={result['time']:.1f}s")
                print(f"E255 fails: {result['e255_fails']}")
                print(f"{'='*60}")
                pool.terminate()
                return result
            elif result['status'] == 'DONE':
                print(f"  Worker {result['worker']} (n={result['n']}): "
                      f"done, {result['e677_found']} E677 models, "
                      f"time={result['time']:.1f}s")

    print("No counterexample found.")
    return None


# ============================================================
# Known base models from the DB
# ============================================================

def load_base_model_5():
    """f(x,y) = (2x + 4y) mod 5 — the smallest E677 model."""
    n = 5
    flat = [0] * 25
    for x in range(5):
        for y in range(5):
            flat[x * 5 + y] = (2*x + 4*y) % 5
    return n, flat


def load_base_model_7():
    """f(x,y) = (4x + 3y) mod 7 — Type II linear model."""
    n = 7
    flat = [0] * 49
    for x in range(7):
        for y in range(7):
            flat[x * 7 + y] = (4*x + 3*y) % 7
    return n, flat


def load_base_model_11():
    """f(x,y) = (2x + 10y) mod 11 — Type I (translation-invariant)."""
    n = 11
    flat = [0] * (n * n)
    for x in range(n):
        for y in range(n):
            flat[x * n + y] = (2*x + 10*y) % n
    return n, flat


# ============================================================
# Main
# ============================================================

def main():
    workers = 4  # safe for thermal constraints (per repo notes)
    seed = 42

    for i, arg in enumerate(sys.argv):
        if arg == "--workers" and i + 1 < len(sys.argv):
            workers = int(sys.argv[i + 1])
        if arg == "--seed" and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1])

    strategy = sys.argv[1] if len(sys.argv) > 1 else "all"

    if strategy == "walksat":
        # Target sizes where DPLL hasn't reached
        n_values = [int(sys.argv[2])] if len(sys.argv) > 2 else [19, 20, 21, 22, 23]
        run_walksat_parallel(n_values, workers=workers, seed=seed)

    elif strategy == "tinv":
        # Translation-invariant search
        n_values = [int(sys.argv[2])] if len(sys.argv) > 2 else list(range(5, 50))
        run_structured_parallel(n_values, workers=workers, seed=seed)

    elif strategy == "twisted":
        # Twisted product over known bases
        base_n, base_flat = load_base_model_7()
        k_values = [2, 3, 4, 5]
        run_twisted_product_parallel(base_flat, base_n, k_values,
                                     workers=workers, seed=seed)

    elif strategy == "all":
        print("=" * 60)
        print("COMPREHENSIVE PARALLEL SEARCH")
        print(f"Workers: {workers}, Seed: {seed}")
        print("=" * 60)

        # Phase 1: WalkSAT on sizes 19-30 (beyond current DPLL)
        print("\n--- Phase 1: WalkSAT local search (n=19..30) ---")
        run_walksat_parallel(list(range(19, 31)), workers=workers,
                            flips_per_worker=1000000, seed=seed)

        # Phase 2: Translation-invariant random search
        print("\n--- Phase 2: Translation-invariant (n=5..60) ---")
        run_structured_parallel(list(range(5, 61)), workers=workers,
                               attempts_per_worker=200000, seed=seed+1000)

        # Phase 3: Twisted products over base models
        print("\n--- Phase 3: Twisted products ---")
        for name, loader in [("5", load_base_model_5),
                             ("7", load_base_model_7),
                             ("11", load_base_model_11)]:
            base_n, base_flat = loader()
            print(f"\n  Base model n={name}:")
            run_twisted_product_parallel(base_flat, base_n, [2, 3, 4],
                                        workers=workers,
                                        attempts_per_worker=100000,
                                        seed=seed+2000)

        print("\n" + "=" * 60)
        print("PARALLEL SEARCH COMPLETE")
        print("=" * 60)

    else:
        print(f"Unknown strategy: {strategy}")
        print("Available: walksat, tinv, twisted, all")


if __name__ == "__main__":
    main()
