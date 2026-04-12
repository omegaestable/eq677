"""
Exotic counterexample search for E677 ⊨_fin E255.

Implements multiple advanced search strategies beyond the current DPLL/Z3 approaches,
targeting magma sizes and structures where counterexamples are most likely to hide.

== STRATEGIES ==

1. GREEDY CONSTRUCTION (inspired by Asterix/Obelix project methodology):
   Build magma tables one cell at a time, greedily choosing values that satisfy
   E677 while maximally violating E255 orbit constraints.

2. NON-ABELIAN GROUP ANSATZ:
   x ◇ y = α(x) · β(y) · c on non-abelian groups (S_n, dihedral, etc.)
   Blueprint proves linear+abelian => E255 holds, but non-abelian is unexplored.

3. WREATH PRODUCT / SEMIDIRECT CONSTRUCTION:
   Build magma on G ⋊ H using twisted fiber operations, explicitly targeting
   the non-right-cancellative construction from blueprint Section 13.1.

4. PRIME POWER FIELDS with QUADRATIC CHARACTER SPLITTING:
   The blueprint's Section 13.1 uses quadratic residue character χ on F_q to
   split fiber operations. Search over GF(p^k) for suitable parameters.

5. RANDOM LOCAL SEARCH (simulated annealing / WalkSAT):
   Start from a random n×n latin-square-like table, flip cells to reduce
   E677 violations while monitoring E255 status.

== TARGET SIZES ==

Based on analysis of known model spectrum and number theory:
- Sizes NOT in DB that could admit exotic models:
  n=16 (2^4, has ω_3 and ζ_5 in GF(16))  -- blueprint non-RC example!
  n=32 (2^5), n=64 (2^6) -- GF extensions
  n=p for primes p ≡ 1 (mod 30) -- has both 3rd and 5th roots of unity
  n=p for p ≡ 1 (mod 10) -- has 5th roots of unity (linear Type I)
  n=p^k where GF(p^k) has primitive 10th root -- smaller non-prime fields

Key insight from blueprint: The non-right-cancellative example uses GF(16) fibers
(has ω_3 and ζ_5) over GF(31) base (has β_5 with -1, β+1 non-residues).
Product size = 31 × 16 = 496 -- this IS in the DB and satisfies E255!
So the construction itself doesn't violate E255, but VARIATIONS might.

Strategy: search for alternative fiber assignments on the same skeleton
that DO break E255.

Usage:
    python exotic_search.py <strategy> [args...]

    python exotic_search.py greedy <n> [--attempts N] [--seed S]
    python exotic_search.py annealing <n> [--steps N] [--temp T] [--seed S]
    python exotic_search.py nonabelian <group> [args...]
    python exotic_search.py quadchar <p> [--max-k K]
    python exotic_search.py all <n_min> <n_max>   # run all strategies on range
"""

import sys
import random
import itertools
import time
from collections import defaultdict
from typing import Optional


# ============================================================
# Core magma utilities
# ============================================================

class Magma:
    """Mutable n×n magma with fast E677/E255 checking."""

    __slots__ = ('n', 'table', '_e677_cache_valid')

    def __init__(self, n, table=None):
        self.n = n
        if table is not None:
            self.table = [list(row) for row in table]
        else:
            self.table = [[None] * n for _ in range(n)]
        self._e677_cache_valid = False

    def op(self, x, y):
        return self.table[x][y]

    def set(self, x, y, v):
        self.table[x][y] = v
        self._e677_cache_valid = False

    def copy(self):
        return Magma(self.n, self.table)

    def is_defined(self, x, y):
        return self.table[x][y] is not None

    def count_e677_violations(self):
        """Count pairs (x,y) where E677 fails. Returns 0 if fully satisfied."""
        n = self.n
        t = self.table
        violations = 0
        for x in range(n):
            for y in range(n):
                try:
                    yx = t[y][x]
                    if yx is None: continue
                    yxy = t[yx][y]
                    if yxy is None: continue
                    xyxy = t[x][yxy]
                    if xyxy is None: continue
                    result = t[y][xyxy]
                    if result is None: continue
                    if result != x:
                        violations += 1
                except (IndexError, TypeError):
                    violations += 1
        return violations

    def check_e255(self):
        """Return list of elements where E255 fails: x != ((x◇x)◇x)◇x."""
        n = self.n
        t = self.table
        failures = []
        for x in range(n):
            try:
                xx = t[x][x]
                if xx is None: continue
                xxx = t[xx][x]
                if xxx is None: continue
                xxxx = t[xxx][x]
                if xxxx is None: continue
                if xxxx != x:
                    failures.append(x)
            except (IndexError, TypeError):
                pass
        return failures

    def check_left_cancel(self):
        """Check if all left multiplications L_y are injective (guaranteed by E677+finite)."""
        n = self.n
        for y in range(n):
            seen = set()
            for x in range(n):
                v = self.table[y][x]
                if v is None: return False
                if v in seen: return False
                seen.add(v)
        return True

    def orbit(self, x):
        """Compute the L_x orbit: x, L_x(x) = x◇x, L_x(x◇x), ..."""
        t = self.table
        path = [x]
        seen = {x}
        cur = x
        while True:
            nxt = t[cur][cur] if cur == x else t[x][cur]
            # Actually orbit under L_x: c_0 = x, c_{k+1} = x ◇ c_k = L_x(c_k)
            # Wait, the convention: c_0 = x, c_1 = x◇x = L_x(x), c_2 = x◇c_1 = L_x(c_1)
            nxt = t[x][cur]
            if nxt is None: return path
            if nxt in seen:
                return path
            seen.add(nxt)
            path.append(nxt)
            cur = nxt
        return path

    def squaring_map(self):
        """Return S(x) = x◇x for all x."""
        return [self.table[x][x] for x in range(self.n)]

    def display(self):
        n = self.n
        for i in range(n):
            print(" ".join(f"{v if v is not None else '.':>3}" for v in self.table[i]))


# ============================================================
# Strategy 1: Greedy Construction
# ============================================================

def greedy_search(n, attempts=1000, seed=None, verbose=False):
    """
    Build E677 magma greedily, biasing toward E255-violating choices.

    For each cell (x,y), choose a value that:
    1. Maintains E677 consistency for all already-determined constraints
    2. Preserves left-cancellation (L_y injective)
    3. Among valid choices, prefer those that make E255 harder to satisfy

    Returns (magma, e255_failures) or None.
    """
    rng = random.Random(seed)

    best_e255_fails = 0
    best_magma = None

    for attempt in range(attempts):
        m = Magma(n)

        # Fill in a random order, but prioritize diagonal (squaring map)
        # and orbit-critical cells
        cells = []
        # Diagonal first (determines S(x) = x◇x)
        for x in range(n):
            cells.append((x, x))
        # Then off-diagonal in random order
        offdiag = [(x, y) for x in range(n) for y in range(n) if x != y]
        rng.shuffle(offdiag)
        cells.extend(offdiag)

        success = True
        for (x, y) in cells:
            # Determine which values are still available for column y (L_y injectivity)
            col_used = set()
            for r in range(n):
                if m.is_defined(r, y):
                    col_used.add(m.op(r, y))
            available = [v for v in range(n) if v not in col_used]

            if not available:
                success = False
                break

            # Filter by E677 forward consistency:
            # For all (a, b) involving cell (x, y), check that setting table[x][y]=v
            # doesn't create an E677 violation
            valid = []
            for v in available:
                m.set(x, y, v)
                ok = True
                # Check E677 for all pairs that use this cell
                for a in range(n):
                    for b in range(n):
                        # Only check if all 4 cells in the chain are defined
                        yx_val = m.op(b, a)
                        if yx_val is None: continue
                        yxy_val = m.op(yx_val, b)
                        if yxy_val is None: continue
                        xyxy_val = m.op(a, yxy_val)
                        if xyxy_val is None: continue
                        result = m.op(b, xyxy_val)
                        if result is None: continue
                        if result != a:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    valid.append(v)
                m.set(x, y, None)

            if not valid:
                success = False
                break

            # Among valid choices, score by E255-violation potential:
            # Prefer values that make ((x◇x)◇x)◇x ≠ x more likely
            scored = []
            for v in valid:
                m.set(x, y, v)
                e255_fails = m.check_e255()
                scored.append((len(e255_fails), v))
                m.set(x, y, None)

            # Pick the choice with most E255 failures (greedy anti-E255)
            # With some randomness to explore
            scored.sort(key=lambda t: -t[0])
            if rng.random() < 0.3 and len(scored) > 1:
                # Random among top-3
                idx = rng.randint(0, min(2, len(scored) - 1))
                chosen = scored[idx][1]
            else:
                chosen = scored[0][1]

            m.set(x, y, chosen)

        if not success:
            continue

        # Verify
        e677_v = m.count_e677_violations()
        if e677_v == 0:
            e255_f = m.check_e255()
            if len(e255_f) > best_e255_fails:
                best_e255_fails = len(e255_f)
                best_magma = m.copy()
                if verbose:
                    print(f"  Attempt {attempt}: E677 OK, E255 fails={len(e255_f)}/{n}")
                if len(e255_f) > 0:
                    print(f"\n*** COUNTEREXAMPLE FOUND at n={n}! ***")
                    print(f"E255 fails at elements: {e255_f}")
                    m.display()
                    return m, e255_f

    return best_magma, []


# ============================================================
# Strategy 2: Simulated Annealing / WalkSAT
# ============================================================

def annealing_search(n, steps=500000, temp_init=2.0, temp_min=0.01,
                     seed=None, verbose=False):
    """
    Local search starting from a random latin square, flipping cells
    to minimize E677 violations while monitoring E255.

    Score = E677_violations * 1000 - E255_violations * 1
    (we want E677_violations=0 and E255_violations>0)
    """
    rng = random.Random(seed)

    # Initialize with a random collection of permutations (ensures left-cancel)
    table = []
    for y in range(n):
        perm = list(range(n))
        rng.shuffle(perm)
        table.append(perm)

    m = Magma(n, table)

    def score(magma):
        e677 = magma.count_e677_violations()
        e255 = len(magma.check_e255())
        # Primary: minimize E677 violations
        # Secondary: maximize E255 violations (negative contribution)
        return e677 * 10000 - e255

    current_score = score(m)
    best_score = current_score
    best_magma = m.copy()
    best_e677 = m.count_e677_violations()

    temp = temp_init
    decay = (temp_min / temp_init) ** (1.0 / steps)

    last_report = time.time()

    for step in range(steps):
        temp *= decay

        # Pick a random cell and try swapping two values in the same column
        # (preserves left-cancellation)
        col = rng.randint(0, n - 1)
        r1, r2 = rng.sample(range(n), 2)

        # Swap
        old_v1 = m.table[r1][col]
        old_v2 = m.table[r2][col]
        m.table[r1][col] = old_v2
        m.table[r2][col] = old_v1

        new_score = score(m)
        delta = new_score - current_score

        # Accept or reject
        if delta <= 0 or rng.random() < (2.718281828 ** (-delta / max(temp, 1e-10))):
            current_score = new_score
            e677_v = m.count_e677_violations()
            if e677_v == 0:
                e255_f = m.check_e255()
                if len(e255_f) > 0:
                    print(f"\n*** COUNTEREXAMPLE FOUND at n={n}, step={step}! ***")
                    print(f"E255 fails at elements: {e255_f}")
                    m.display()
                    return m, e255_f
            if current_score < best_score:
                best_score = current_score
                best_magma = m.copy()
                best_e677 = e677_v
        else:
            # Revert
            m.table[r1][col] = old_v1
            m.table[r2][col] = old_v2

        if verbose and time.time() - last_report > 5.0:
            e677_v = m.count_e677_violations()
            e255_f = len(m.check_e255())
            print(f"  Step {step}/{steps}: score={current_score}, "
                  f"E677_viol={e677_v}, E255_fails={e255_f}, "
                  f"temp={temp:.4f}, best_E677={best_e677}")
            last_report = time.time()

    return best_magma, []


# ============================================================
# Strategy 3: Quadratic Character Fiber Search (blueprint 13.1)
# ============================================================

def find_roots_of_unity(p, k):
    """Find primitive k-th roots of unity in GF(p), if they exist."""
    if p <= 2: return []
    if (p - 1) % k != 0: return []
    roots = []
    for g in range(2, p):
        val = pow(g, (p - 1) // k, p)
        if val != 1 and pow(val, k, p) == 1:
            # Check it's primitive (order exactly k)
            is_primitive = True
            for d in range(1, k):
                if pow(val, d, p) == 1:
                    is_primitive = False
                    break
            if is_primitive:
                roots.append(val)
    return roots


def quadratic_residues(p):
    """Return set of quadratic residues mod p."""
    return {(x * x) % p for x in range(p)}


def quadchar_fiber_search(p, max_fiber_k=8, verbose=True):
    """
    Implement the blueprint Section 13.1 construction and search for
    variations that might break E255.

    Base magma: x ◇ y = x - β(y - x) on GF(p), where β is a primitive
    5th root of unity and -1, β+1 are non-residues.

    Fibers: Three operations ◇_0 (diagonal), ◇_+ (QR), ◇_- (QNR) on GF(q).
    Standard: ◇_0: s - ζ(t-s), ◇_+: t (right projection), ◇_-: s - ω(t-s)
    where ζ = prim 5th root in GF(q), ω = prim 3rd root in GF(q).

    We search for alternative fiber triples that satisfy E677 but break E255.
    """
    if not is_prime(p):
        return None

    # Check p has a suitable β
    roots5 = find_roots_of_unity(p, 5)
    if not roots5:
        if verbose: print(f"  p={p}: no 5th root of unity")
        return None

    qr = quadratic_residues(p)

    for beta in roots5:
        # Check -1 is QNR
        neg1 = (p - 1) % p
        if neg1 in qr:
            continue
        # Check β+1 is QNR
        bp1 = (beta + 1) % p
        if bp1 == 0 or bp1 in qr:
            continue

        if verbose:
            print(f"  p={p}, β={beta}: valid base. Building base magma...")

        # Base magma on GF(p)
        def base_op(x, y):
            return (x + p - (beta * ((y + p - x) % p)) % p) % p
            # = x - β(y - x) mod p

        # Verify E677 on base
        ok = True
        for x in range(p):
            for y in range(p):
                yx = base_op(y, x)
                yxy = base_op(yx, y)
                xyxy = base_op(x, yxy)
                result = base_op(y, xyxy)
                if result != x:
                    ok = False
                    break
            if not ok:
                break

        if not ok:
            if verbose: print(f"    Base E677 check FAILED")
            continue

        if verbose: print(f"    Base E677 OK. Searching fiber alternatives...")

        # The character map: χ(d) = 0 if d=0, +1 if QR, -1 if QNR
        def chi(d):
            d = d % p
            if d == 0: return 0
            return 1 if d in qr else -1

        # Now search for alternative fiber operations on small fields GF(q)
        # For q = 2^k, we'd need Galois field arithmetic.
        # For simplicity, search over Z/qZ for small q (not a field for non-prime q,
        # but still valid as a magma carrier).
        for q in range(2, max_fiber_k + 1):
            # Enumerate all triples (f0, f+, f-) of q×q operation tables
            # that jointly satisfy the fiber E677 constraint.
            # This is the key functional equation (4) from the blueprint:
            #
            #   s = t ◇_{y,L_y^{-1}(x)} (s ◇_{x,(y◇x)◇y} ((t ◇_{y,x} s) ◇_{y◇x,y} t))
            #
            # For the translation-invariant base, the character assignments depend
            # on the difference y-x. With χ(y-x) determining which fiber op to use,
            # the functional equation becomes:
            #
            #   For all (a,b) in GF(p)^2, for all (r,s) in [q]^2:
            #     The composite fiber chain must return r.

            if verbose and q > 3:
                print(f"    Trying fiber size q={q} (product = {p*q})...")

            # For small q, do exhaustive search over bijective fiber ops
            # (since left-cancel requires each L in the fiber to be bijective too)
            #
            # Actually, the fibers need not individually be left-cancellative;
            # only the product magma needs left-cancel (which E677+finite gives).
            # But the base is left-cancellative, so each fiber column must also
            # be a permutation (for the product L_y to be bijective).

            # For q <= 4, enumerate all possible triples exhaustively:
            if q > 4:
                if verbose: print(f"    q={q} too large for exhaustive fiber search, skipping")
                continue

            # Generate all left-cancel q×q tables (each column is a permutation)
            # There are (q!)^q such tables for each of the 3 fiber slots.
            from itertools import permutations
            perms = list(permutations(range(q)))

            # Generate all tables where each column is a permutation
            def gen_tables():
                for combo in itertools.product(perms, repeat=q):
                    # combo[y] is the column for input y
                    table = [[combo[y][x] for y in range(q)] for x in range(q)]
                    yield table

            # Count to estimate
            n_tables = len(perms) ** q
            if verbose:
                print(f"    {n_tables} candidate tables per fiber slot, "
                      f"total triples = {n_tables}^3 = {n_tables**3}")

            if n_tables ** 3 > 50_000_000:
                if verbose: print(f"    Too many triples, using sampling...")
                # Sample random triples
                _sample_fiber_triples(p, q, beta, chi, qr, base_op, n_samples=1000000,
                                     verbose=verbose)
                continue

            # Full exhaustive search for small q
            found = _exhaustive_fiber_search(p, q, beta, chi, qr, base_op, verbose=verbose)
            if found:
                return found

    return None


def _check_fiber_e677(p, q, f0, fp, fm, chi, base_op):
    """
    Check if the fiber triple (f0, fp, fm) satisfies E677 on the product GF(p) × [q].

    f0[r][s] = r ◇_0 s (diagonal fiber)
    fp[r][s] = r ◇_+ s (QR fiber)
    fm[r][s] = r ◇_- s (QNR fiber)
    """
    fibers = {0: f0, 1: fp, -1: fm}

    for a in range(p):
        for b in range(p):
            c_ba = chi((a - b) % p)  # character of a-b for base_op(b,a)
            ba_base = base_op(b, a)

            c_ba_y = chi((b - ba_base) % p)  # character for base_op(ba_base, b)
            bay_base = base_op(ba_base, b)

            c_a_bay = chi((bay_base - a) % p)  # character for base_op(a, bay_base)
            abay_base = base_op(a, bay_base)

            c_b_abay = chi((abay_base - b) % p)  # character for base_op(b, abay_base)

            # fiber indices
            f_ba = fibers[c_ba]
            f_bay = fibers[c_ba_y]
            f_abay = fibers[c_a_bay]
            f_final = fibers[c_b_abay]

            for r in range(q):
                for s in range(q):
                    # (b,s) ◇ (a,r): base = ba_base, fiber = f_ba[s][r]
                    ba_fib = f_ba[s][r]

                    # (ba_base, ba_fib) ◇ (b, s): base = bay_base, fiber = f_bay[ba_fib][s]
                    bay_fib = f_bay[ba_fib][s]

                    # (a, r) ◇ (bay_base, bay_fib): base = abay_base, fiber = f_abay[r][bay_fib]
                    abay_fib = f_abay[r][bay_fib]

                    # (b, s) ◇ (abay_base, abay_fib): base = b ◇ abay_base, fiber = f_final[s][abay_fib]
                    final_fib = f_final[s][abay_fib]

                    if final_fib != r:
                        return False
    return True


def _check_fiber_e255(p, q, f0, fp, fm, chi, base_op):
    """Check E255 on the product. Return list of failing elements."""
    fibers = {0: f0, 1: fp, -1: fm}
    failures = []

    for a in range(p):
        for r in range(q):
            # x = (a, r)
            # x◇x: base = base_op(a,a), fiber = f0[r][r]  (chi(0)=0)
            xx_base = base_op(a, a)
            xx_fib = f0[r][r]

            # (x◇x)◇x: base = base_op(xx_base, a), fiber = fibers[chi(a - xx_base)][xx_fib][r]
            c1 = chi((a - xx_base) % p)
            xxx_base = base_op(xx_base, a)
            xxx_fib = fibers[c1][xx_fib][r]

            # ((x◇x)◇x)◇x: base = base_op(xxx_base, a), fiber = fibers[chi(a - xxx_base)][xxx_fib][r]
            c2 = chi((a - xxx_base) % p)
            xxxx_base = base_op(xxx_base, a)
            xxxx_fib = fibers[c2][xxx_fib][r]

            if xxxx_base != a or xxxx_fib != r:
                failures.append((a, r))

    return failures


def _exhaustive_fiber_search(p, q, beta, chi, qr, base_op, verbose=True):
    """Exhaustive search over all fiber triples for small q."""
    from itertools import permutations

    perms = list(permutations(range(q)))

    def make_table(col_combo):
        return [[col_combo[y][x] for y in range(q)] for x in range(q)]

    col_combos = list(itertools.product(perms, repeat=q))
    tables = [make_table(cc) for cc in col_combos]

    n_tables = len(tables)
    checked = 0
    t0 = time.time()

    for i0, f0 in enumerate(tables):
        if verbose and i0 % max(1, n_tables // 20) == 0:
            elapsed = time.time() - t0
            print(f"    f0: {i0}/{n_tables} ({elapsed:.1f}s, {checked} checked)")

        for ip, fp in enumerate(tables):
            for im, fm in enumerate(tables):
                checked += 1
                if _check_fiber_e677(p, q, f0, fp, fm, chi, base_op):
                    fails = _check_fiber_e255(p, q, f0, fp, fm, chi, base_op)
                    if fails:
                        print(f"\n*** COUNTEREXAMPLE via fiber search! ***")
                        print(f"  p={p}, q={q}, product={p*q}")
                        print(f"  f0 = {f0}")
                        print(f"  f+ = {fp}")
                        print(f"  f- = {fm}")
                        print(f"  E255 failures: {fails[:20]}...")
                        return (f0, fp, fm, fails)
                    elif verbose and checked % 100000 == 0:
                        print(f"      ...{checked} checked, E677-valid found (but E255 holds)")

    if verbose:
        elapsed = time.time() - t0
        print(f"    Exhaustive done: {checked} triples in {elapsed:.1f}s, no counterexample")
    return None


def _sample_fiber_triples(p, q, beta, chi, qr, base_op, n_samples=100000, verbose=True):
    """Random sampling of fiber triples for larger q."""
    from itertools import permutations
    rng = random.Random(42)

    perms = list(permutations(range(q)))

    def random_table():
        cols = [rng.choice(perms) for _ in range(q)]
        return [[cols[y][x] for y in range(q)] for x in range(q)]

    t0 = time.time()
    e677_valid = 0

    for i in range(n_samples):
        f0 = random_table()
        fp = random_table()
        fm = random_table()

        if _check_fiber_e677(p, q, f0, fp, fm, chi, base_op):
            e677_valid += 1
            fails = _check_fiber_e255(p, q, f0, fp, fm, chi, base_op)
            if fails:
                print(f"\n*** COUNTEREXAMPLE via random fiber sampling! ***")
                print(f"  p={p}, q={q}, product={p*q}")
                print(f"  f0 = {f0}")
                print(f"  f+ = {fp}")
                print(f"  f- = {fm}")
                print(f"  E255 failures: {fails[:20]}...")
                return (f0, fp, fm, fails)

        if verbose and (i + 1) % 100000 == 0:
            elapsed = time.time() - t0
            print(f"    {i+1}/{n_samples}: {e677_valid} E677-valid found ({elapsed:.1f}s)")

    if verbose:
        elapsed = time.time() - t0
        print(f"    Sampling done: {n_samples} triples, {e677_valid} E677-valid, "
              f"no counterexample ({elapsed:.1f}s)")
    return None


# ============================================================
# Strategy 4: Non-Abelian Group Ansatz
# ============================================================

def nonabelian_search(max_n=30, verbose=True):
    """
    Search for E677 magmas on non-abelian groups.
    x ◇ y = α(x) · β(y) · c where α,β are group endomorphisms.

    For non-abelian groups, the map x ↦ α(x) · β(y) · c is NOT equivalent
    to the abelian case. The blueprint proves no ABELIAN+LINEAR counterexample
    exists. Non-abelian groups are the natural next target.

    We focus on small non-abelian groups: S_3 (n=6), D_4 (n=8), S_4 (n=24), etc.
    """
    # S_3: permutations of {0,1,2}, order 6
    # Elements: (0)(1)(2), (01), (02), (12), (012), (021)
    # Represented as functions {0,1,2} -> {0,1,2}

    def s3_mult(a, b):
        """Compose permutations: (a·b)(x) = a(b(x))."""
        return tuple(a[b[i]] for i in range(3))

    s3_elems = [
        (0, 1, 2),  # identity
        (1, 0, 2),  # (01)
        (0, 2, 1),  # (12)
        (2, 1, 0),  # (02)
        (1, 2, 0),  # (012)
        (2, 0, 1),  # (021)
    ]
    s3_n = len(s3_elems)
    s3_idx = {e: i for i, e in enumerate(s3_elems)}

    # Endomorphisms of S_3: the trivial one, inner auts, and outer aut
    # Actually all automorphisms of S_3 are inner (Aut(S_3) ≅ S_3).
    # Endomorphisms include: trivial (everything -> id), and automorphisms.
    # For S_3, the automorphisms are conjugation by each element.

    s3_autos = []
    for g in s3_elems:
        # Conjugation by g: x -> g·x·g^{-1}
        g_inv = None
        for h in s3_elems:
            if s3_mult(g, h) == (0, 1, 2):
                g_inv = h
                break
        auto = {}
        for x in s3_elems:
            auto[x] = s3_mult(g, s3_mult(x, g_inv))
        s3_autos.append(auto)

    # Also add trivial endomorphism (everything maps to identity)
    s3_endos = list(s3_autos)
    trivial = {x: (0, 1, 2) for x in s3_elems}
    s3_endos.append(trivial)

    if verbose:
        print(f"S_3: {s3_n} elements, {len(s3_endos)} endomorphisms")

    count = 0
    for alpha in s3_endos:
        for beta_endo in s3_endos:
            for c in s3_elems:
                def magma_op(x_idx, y_idx, _a=alpha, _b=beta_endo, _c=c):
                    x = s3_elems[x_idx]
                    y = s3_elems[y_idx]
                    result = s3_mult(s3_mult(_a[x], _b[y]), _c)
                    return s3_idx[result]

                # Check E677
                ok = True
                for xi in range(s3_n):
                    for yi in range(s3_n):
                        yx = magma_op(yi, xi)
                        yxy = magma_op(yx, yi)
                        xyxy = magma_op(xi, yxy)
                        result = magma_op(yi, xyxy)
                        if result != xi:
                            ok = False
                            break
                    if not ok:
                        break

                if ok:
                    count += 1
                    # Check E255
                    e255_ok = True
                    for xi in range(s3_n):
                        xx = magma_op(xi, xi)
                        xxx = magma_op(xx, xi)
                        xxxx = magma_op(xxx, xi)
                        if xxxx != xi:
                            e255_ok = False
                            break

                    if verbose:
                        print(f"  E677 model found on S_3 (#{count}): E255={'PASS' if e255_ok else 'FAIL'}")
                    if not e255_ok:
                        print(f"\n*** COUNTEREXAMPLE on S_3! ***")
                        return True

    if verbose:
        print(f"S_3 done: {count} E677 models found, all satisfy E255")

    # Dihedral D_4 (order 8)
    # D_4 = <r, s | r^4 = s^2 = 1, srs = r^{-1}>
    # Elements: 1, r, r^2, r^3, s, sr, sr^2, sr^3
    d4_n = 8

    # Represent as (rotation, flip): (k, f) where k in {0,1,2,3}, f in {0,1}
    d4_elems = [(k, f) for f in range(2) for k in range(4)]
    d4_idx = {e: i for i, e in enumerate(d4_elems)}

    def d4_mult(a, b):
        """Multiply in D_4: (k1,f1)·(k2,f2)."""
        k1, f1 = a
        k2, f2 = b
        if f1 == 0:
            return ((k1 + k2) % 4, f2)
        else:
            return ((k1 - k2) % 4, (f1 + f2) % 2)

    # Automorphisms of D_4: |Aut(D_4)| = 8
    # Generated by: r -> r^k (k odd), s -> sr^j
    d4_autos = []
    for k_r in [1, 3]:  # r -> r^k
        for j_s in range(4):  # s -> sr^j
            auto_map = {}
            # Build: r -> (k_r, 0), s -> (j_s, 1)
            for elem in d4_elems:
                rot, flip = elem
                if flip == 0:
                    # r^rot -> (k_r * rot mod 4, 0)
                    auto_map[elem] = ((k_r * rot) % 4, 0)
                else:
                    # s·r^rot -> (j_s, 1)·(k_r*rot, 0)
                    sr = d4_mult((j_s, 1), ((k_r * rot) % 4, 0))
                    auto_map[elem] = sr
            d4_autos.append(auto_map)

    d4_endos = list(d4_autos)
    d4_endos.append({e: (0, 0) for e in d4_elems})  # trivial

    if verbose:
        print(f"\nD_4: {d4_n} elements, {len(d4_endos)} endomorphisms")

    count = 0
    for alpha in d4_endos:
        for beta_endo in d4_endos:
            for c in d4_elems:
                def magma_op_d4(x_idx, y_idx, _a=alpha, _b=beta_endo, _c=c):
                    x = d4_elems[x_idx]
                    y = d4_elems[y_idx]
                    result = d4_mult(d4_mult(_a[x], _b[y]), _c)
                    return d4_idx[result]

                ok = True
                for xi in range(d4_n):
                    for yi in range(d4_n):
                        yx = magma_op_d4(yi, xi)
                        yxy = magma_op_d4(yx, yi)
                        xyxy = magma_op_d4(xi, yxy)
                        result = magma_op_d4(yi, xyxy)
                        if result != xi:
                            ok = False
                            break
                    if not ok:
                        break

                if ok:
                    count += 1
                    e255_ok = True
                    for xi in range(d4_n):
                        xx = magma_op_d4(xi, xi)
                        xxx = magma_op_d4(xx, xi)
                        xxxx = magma_op_d4(xxx, xi)
                        if xxxx != xi:
                            e255_ok = False
                            break

                    if verbose:
                        print(f"  E677 model on D_4 (#{count}): E255={'PASS' if e255_ok else 'FAIL'}")
                    if not e255_ok:
                        print(f"\n*** COUNTEREXAMPLE on D_4! ***")
                        return True

    if verbose:
        print(f"D_4 done: {count} E677 models, all satisfy E255")

    return False


# ============================================================
# Strategy 5: Targeted Primes (number-theoretic)
# ============================================================

def is_prime(n):
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or (n + 2) % i == 0: return False
        i += 6
    return True


def find_target_primes(limit=1000):
    """
    Find primes where exotic E677 models are most likely:

    1. p ≡ 1 (mod 30): has 3rd, 5th, and 10th roots of unity
       These support the full blueprint 13.1 construction.

    2. p ≡ 1 (mod 10), p ≢ 1 (mod 3): has 5th roots but not 3rd
       Forces different fiber structure.

    3. p ≡ 1 (mod 3), p ≢ 1 (mod 5): has 3rd roots but not 5th
       Another structural variant.

    4. p ≡ 1 (mod 7): has 7th roots — might enable period-7 constructions

    5. p where p-1 has many small factors: rich automorphism structure
    """
    categories = {
        'mod30_1': [],    # p ≡ 1 (mod 30)
        'mod10_not3': [], # p ≡ 1 (mod 10), p ≢ 1 (mod 3)
        'mod3_not5': [],  # p ≡ 1 (mod 3), p ≢ 1 (mod 5)
        'mod7': [],       # p ≡ 1 (mod 7)
        'highly_composite': [],  # p-1 has many factors
    }

    for p in range(5, limit):
        if not is_prime(p): continue

        if (p - 1) % 30 == 0:
            categories['mod30_1'].append(p)
        elif (p - 1) % 10 == 0 and (p - 1) % 3 != 0:
            categories['mod10_not3'].append(p)
        elif (p - 1) % 3 == 0 and (p - 1) % 5 != 0:
            categories['mod3_not5'].append(p)

        if (p - 1) % 7 == 0:
            categories['mod7'].append(p)

        # Count factors of p-1
        n_factors = 0
        m = p - 1
        for d in range(2, m + 1):
            if d * d > m: break
            while m % d == 0:
                n_factors += 1
                m //= d
        if m > 1: n_factors += 1
        if n_factors >= 5:
            categories['highly_composite'].append(p)

    return categories


def targeted_prime_search(p, verbose=True):
    """
    For a given prime p, search for ALL linear E677 models and check E255.
    Then try piecewise-linear with quadratic character splitting.
    """
    if verbose:
        print(f"\n=== Targeted search for p={p} ===")

    # 1. Linear: x ◇ y = (a*x + b*y) mod p
    #    E677 requires: a + a²b² + b³ ≡ 0 and a·b(1+b²) ≡ 1 (mod p)
    linear_models = []
    for b in range(p):
        b4 = (b + b*b*b) % p
        for a in range(p):
            if (a * b4) % p != 1: continue
            if (a + a*a*b*b + b*b*b) % p != 0: continue
            linear_models.append((a, b))

    if verbose:
        print(f"  Linear models: {len(linear_models)}")
        for (a, b) in linear_models:
            print(f"    f(x,y) = ({a}*x + {b}*y) mod {p}")

    # 2. Check if any linear model has interesting orbit structure
    for (a, b) in linear_models:
        def op(x, y, _a=a, _b=b, _p=p):
            return (_a*x + _b*y) % _p

        # Compute orbits
        orbits = {}
        for x in range(p):
            path = [x]
            cur = x
            for _ in range(p):
                cur = op(x, cur)  # L_x(cur) = x ◇ cur
                if cur in set(path):
                    break
                path.append(cur)
            orbits[x] = len(path)

        orbit_sizes = set(orbits.values())
        if verbose:
            print(f"    Orbit sizes: {sorted(orbit_sizes)}")

    # 3. Piecewise linear with quadratic residue splitting
    qr = quadratic_residues(p)

    pw_count = 0
    for (a1, b1) in linear_models:
        for (a2, b2) in linear_models:
            if (a1, b1) == (a2, b2): continue

            def pw_op(x, y, _a1=a1, _b1=b1, _a2=a2, _b2=b2, _p=p, _qr=qr):
                d = (y - x) % _p
                if d in _qr:
                    return (_a1*x + _b1*y) % _p
                else:
                    return (_a2*x + _b2*y) % _p

            # Quick E677 check
            ok = True
            for x in range(p):
                for y in range(p):
                    yx = pw_op(y, x)
                    yxy = pw_op(yx, y)
                    xyxy = pw_op(x, yxy)
                    result = pw_op(y, xyxy)
                    if result != x:
                        ok = False
                        break
                if not ok:
                    break

            if ok:
                pw_count += 1
                # Check E255
                e255_ok = True
                for x in range(p):
                    xx = pw_op(x, x)
                    xxx = pw_op(xx, x)
                    xxxx = pw_op(xxx, x)
                    if xxxx != x:
                        e255_ok = False
                        break

                if verbose:
                    print(f"    Piecewise model #{pw_count}: E255={'PASS' if e255_ok else 'FAIL'}")
                if not e255_ok:
                    print(f"\n*** COUNTEREXAMPLE (piecewise linear) at p={p}! ***")
                    return True

    if verbose:
        print(f"  Piecewise models: {pw_count}")

    return False


# ============================================================
# Strategy 6: Power-of-2 Galois field search (GF(2^k))
# ============================================================

def gf2k_search(k_max=6, verbose=True):
    """
    Search for E677 magmas on GF(2^k) using polynomial arithmetic.

    GF(2^k) is special because:
    - characteristic 2: addition = XOR, no sign issues
    - GF(16) = GF(2^4) has both primitive 3rd and 5th roots of unity
      (since 2^4 - 1 = 15 = 3 × 5)
    - This is exactly what the blueprint 13.1 construction needs!

    We represent GF(2^k) elements as integers 0..2^k-1, with multiplication
    via irreducible polynomial.
    """
    # Irreducible polynomials for GF(2^k)
    # k=2: x^2 + x + 1 (0b111 = 7)
    # k=3: x^3 + x + 1 (0b1011 = 11)
    # k=4: x^4 + x + 1 (0b10011 = 19)
    # k=5: x^5 + x^2 + 1 (0b100101 = 37)
    # k=6: x^6 + x + 1 (0b1000011 = 67)
    irred = {2: 0b111, 3: 0b1011, 4: 0b10011, 5: 0b100101, 6: 0b1000011}

    for k in range(2, k_max + 1):
        if k not in irred:
            continue
        q = 1 << k
        poly = irred[k]

        if verbose:
            print(f"\n=== GF(2^{k}) search (q={q}) ===")

        # Build multiplication table
        def gf_mult(a, b):
            result = 0
            while b > 0:
                if b & 1:
                    result ^= a
                a <<= 1
                if a >= q:
                    a ^= poly
                b >>= 1
            return result

        # Build power table for finding roots of unity
        # Find a generator of GF(q)*
        gen = None
        for g in range(2, q):
            # Check if g generates the multiplicative group
            elem = g
            order = 1
            while elem != 1:
                elem = gf_mult(elem, g)
                order += 1
                if order > q:
                    break
            if order == q - 1:
                gen = g
                break

        if gen is None:
            if verbose: print(f"  No generator found for GF(2^{k})")
            continue

        if verbose:
            print(f"  Generator: {gen}, order={q-1}")

        # Find roots of unity
        def gf_pow(base, exp):
            result = 1
            b = base
            while exp > 0:
                if exp & 1:
                    result = gf_mult(result, b)
                b = gf_mult(b, b)
                exp >>= 1
            return result

        # Primitive d-th roots of unity
        def prim_root(d):
            if (q - 1) % d != 0: return None
            r = gf_pow(gen, (q - 1) // d)
            # Verify it's primitive
            val = r
            for i in range(1, d):
                if val == 1: return None
                val = gf_mult(val, r)
            return r if val == 1 else None

        root3 = prim_root(3)
        root5 = prim_root(5)
        root10 = prim_root(10)

        if verbose:
            print(f"  ω_3 = {root3}, ζ_5 = {root5}, ζ_10 = {root10}")

        # Search for linear E677 models: x ◇ y = α·x + β·y + c
        # where + is GF addition (XOR), · is GF multiplication
        # E677 constraint: α + α²β² + β³ = 0, αβ(1+β²) = 1

        linear_count = 0
        for alpha in range(q):
            for beta_val in range(q):
                # Check: α + α²β² + β³ = 0
                a2 = gf_mult(alpha, alpha)
                b2 = gf_mult(beta_val, beta_val)
                b3 = gf_mult(b2, beta_val)
                a2b2 = gf_mult(a2, b2)
                lhs = alpha ^ a2b2 ^ b3  # GF(2^k) addition is XOR
                if lhs != 0:
                    continue

                # Check: αβ(1+β²) = 1
                ab = gf_mult(alpha, beta_val)
                one_plus_b2 = 1 ^ b2  # 1 + β² in GF(2^k)
                rhs = gf_mult(ab, one_plus_b2)
                if rhs != 1:
                    continue

                linear_count += 1

                # Build and verify full model
                for c_val in range(q):
                    def op(x, y, _a=alpha, _b=beta_val, _c=c_val):
                        return gf_mult(_a, x) ^ gf_mult(_b, y) ^ _c

                    # Quick E677 spot check
                    ok = True
                    for x in range(min(q, 8)):
                        for y in range(min(q, 8)):
                            yx = op(y, x)
                            yxy = op(yx, y)
                            xyxy = op(x, yxy)
                            result = op(y, xyxy)
                            if result != x:
                                ok = False
                                break
                        if not ok:
                            break
                    if not ok:
                        continue

                    # Full E677 check
                    ok = True
                    for x in range(q):
                        for y in range(q):
                            yx = op(y, x)
                            yxy = op(yx, y)
                            xyxy = op(x, yxy)
                            result = op(y, xyxy)
                            if result != x:
                                ok = False
                                break
                        if not ok:
                            break

                    if ok:
                        # Check E255
                        e255_ok = True
                        for x in range(q):
                            xx = op(x, x)
                            xxx = op(xx, x)
                            xxxx = op(xxx, x)
                            if xxxx != x:
                                e255_ok = False
                                break

                        if verbose:
                            print(f"  Model: α={alpha}, β={beta_val}, c={c_val}: "
                                  f"E255={'PASS' if e255_ok else 'FAIL'}")
                        if not e255_ok:
                            print(f"\n*** COUNTEREXAMPLE on GF(2^{k})! ***")
                            return True

        if verbose:
            print(f"  Linear (α,β) pairs: {linear_count}")

    return False


# ============================================================
# Main dispatcher
# ============================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    strategy = sys.argv[1]

    if strategy == "greedy":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        attempts = 1000
        seed = None
        for i, arg in enumerate(sys.argv):
            if arg == "--attempts" and i + 1 < len(sys.argv):
                attempts = int(sys.argv[i + 1])
            if arg == "--seed" and i + 1 < len(sys.argv):
                seed = int(sys.argv[i + 1])
        print(f"Greedy search: n={n}, attempts={attempts}")
        result, fails = greedy_search(n, attempts=attempts, seed=seed, verbose=True)
        if fails:
            print("COUNTEREXAMPLE FOUND!")
        else:
            print(f"No counterexample at n={n}")

    elif strategy == "annealing":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        steps = 500000
        temp = 2.0
        seed = None
        for i, arg in enumerate(sys.argv):
            if arg == "--steps" and i + 1 < len(sys.argv):
                steps = int(sys.argv[i + 1])
            if arg == "--temp" and i + 1 < len(sys.argv):
                temp = float(sys.argv[i + 1])
            if arg == "--seed" and i + 1 < len(sys.argv):
                seed = int(sys.argv[i + 1])
        print(f"Annealing search: n={n}, steps={steps}, temp={temp}")
        result, fails = annealing_search(n, steps=steps, temp_init=temp, seed=seed, verbose=True)
        if fails:
            print("COUNTEREXAMPLE FOUND!")
        else:
            print(f"No counterexample at n={n}")

    elif strategy == "nonabelian":
        nonabelian_search(verbose=True)

    elif strategy == "quadchar":
        p = int(sys.argv[2]) if len(sys.argv) > 2 else 31
        max_k = 4
        for i, arg in enumerate(sys.argv):
            if arg == "--max-k" and i + 1 < len(sys.argv):
                max_k = int(sys.argv[i + 1])
        quadchar_fiber_search(p, max_fiber_k=max_k, verbose=True)

    elif strategy == "gf2k":
        k_max = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        gf2k_search(k_max=k_max, verbose=True)

    elif strategy == "primes":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        cats = find_target_primes(limit)
        print("\nTarget prime categories:")
        for cat, primes in cats.items():
            print(f"  {cat}: {primes[:20]}")

    elif strategy == "targeted":
        p_min = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        p_max = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        for p in range(p_min, p_max + 1):
            if is_prime(p):
                targeted_prime_search(p, verbose=True)

    elif strategy == "all":
        n_min = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        n_max = int(sys.argv[3]) if len(sys.argv) > 3 else 20

        print("=" * 60)
        print("COMPREHENSIVE EXOTIC SEARCH")
        print("=" * 60)

        # Phase 1: Non-abelian groups
        print("\n--- Phase 1: Non-abelian group ansatz ---")
        nonabelian_search(verbose=True)

        # Phase 2: GF(2^k) linear models
        print("\n--- Phase 2: GF(2^k) linear models ---")
        gf2k_search(k_max=6, verbose=True)

        # Phase 3: Target primes
        print("\n--- Phase 3: Targeted prime search ---")
        cats = find_target_primes(max(n_max, 200))
        all_primes = sorted(set(
            p for ps in cats.values() for p in ps if n_min <= p <= n_max
        ))
        for p in all_primes:
            targeted_prime_search(p, verbose=True)

        # Phase 4: Quadratic character fiber search on key primes
        print("\n--- Phase 4: Quadratic character fiber search ---")
        qc_primes = [p for p in cats.get('mod30_1', []) if p <= n_max]
        for p in qc_primes[:5]:
            quadchar_fiber_search(p, max_fiber_k=4, verbose=True)

        # Phase 5: Greedy + annealing on each size
        print("\n--- Phase 5: Greedy construction ---")
        for n in range(n_min, min(n_max + 1, 15)):
            print(f"\n  n={n}:")
            greedy_search(n, attempts=200, verbose=True)

        print("\n--- Phase 6: Simulated annealing ---")
        for n in range(max(n_min, 5), min(n_max + 1, 20)):
            print(f"\n  n={n}:")
            annealing_search(n, steps=100000, verbose=True)

        print("\n" + "=" * 60)
        print("SEARCH COMPLETE")
        print("=" * 60)

    else:
        print(f"Unknown strategy: {strategy}")
        print("Available: greedy, annealing, nonabelian, quadchar, gf2k, primes, targeted, all")


if __name__ == "__main__":
    main()
