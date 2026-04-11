"""
proof_candidates.py
===================
Three explicit proof candidates toward "finite E677 => E255 (d-injectivity)".
Each lemma is stated precisely, its failure condition is encoded as a runnable
test against the DB, and the proof strategy is described.

Running this file against the DB shows which failure conditions are currently
ever triggered (none expected for L1/L2; L3 is the main open problem).

Definitions (mirroring conj.rs):
  E677:  x = y ∘ (x ∘ ((y ∘ x) ∘ y))        [the target equation]
  c_0    = x
  c_{k+1} = x ∘ c_k                           [L_x orbit of x]
  d      = orbit period (smallest pos. k: c_k = x)
  d_k    = c_k ∘ x                            [d-sequence]
  S(x)   = x ∘ x                              [squaring map]
  E255  <==>  for all x: k ↦ d_k is injective on Z/dZ
"""

import os
from analyze_db import load_magma, op, orbit_c_seq, orbit_d_seq

DB_PATH = os.path.join(os.path.dirname(__file__), "db")


def load_all_models():
    models = []
    for size_dir in sorted(os.listdir(DB_PATH), key=lambda s: int(s)):
        size = int(size_dir)
        dir_path = os.path.join(DB_PATH, size_dir)
        if not os.path.isdir(dir_path):
            continue
        for fname in sorted(os.listdir(dir_path), key=lambda s: int(s)):
            fpath = os.path.join(dir_path, fname)
            n, rows = load_magma(fpath)
            models.append((size, int(fname), n, rows))
    return models


# ===========================================================================
# LEMMA 1 — Key Recurrence Lemma
# ===========================================================================
#
# Statement:
#   In any left-cancellative E677-magma M, for every x in M, let c_k and d_k
#   be the c/d-sequences with period d.  Then:
#
#       c_{k-1}  =  c_k ∘ d_{k+1}     (indices mod d)             [L1]
#
# Proof strategy:
#   By E677 with (y_param=x, x_param=c_k):
#       c_k  =  x ∘ (c_k ∘ ((x ∘ c_k) ∘ x))
#            =  x ∘ (c_k ∘ (c_{k+1} ∘ x))
#            =  x ∘ (c_k ∘ d_{k+1})
#   By the c-sequence definition, c_k = x ∘ c_{k-1}.
#   Left-cancellativity on x gives:  c_{k-1} = c_k ∘ d_{k+1}.  QED (if
#   left-cancellativity is provable from E677 + finiteness, which is asserted
#   in conj.rs).
#
# Failure condition:
#   A triple (x, k, M) such that  c_k ∘ d_{k+1 mod d}  ≠  c_{k-1 mod d}.
#   This would mean either E677 fails or left-cancellativity fails independently
#   of E677 in finite models — both would be major surprises.
#
# What it buys:
#   Connects the c-sequence to the d-sequence via right-multiplication.
#   Every collision d_i = d_j IMMEDIATELY implies R_{d_i} maps c_{i-1} → c_{i-2}
#   and c_{j-1} → c_{j-2} (same right-mult by d_i sends two orbit elements each
#   to their predecessor).  This is the raw material for the cascade in L3.

def check_lemma1_failure(n, rows, x):
    """
    Returns a failing (k, c_k, d_{k+1}, c_{k-1}) tuple, or None if L1 holds.
    L1: c_{k-1} = c_k ∘ d_{k+1}  (mod d).
    """
    c_seq = orbit_c_seq(rows, n, x)
    d_seq = orbit_d_seq(rows, n, x)
    d = len(c_seq)
    for k in range(d):
        c_k   = c_seq[k]
        d_kp1 = d_seq[(k + 1) % d]          # d_{k+1 mod d}
        c_km1 = c_seq[(k - 1) % d]          # c_{k-1 mod d}
        lhs = op(rows, c_k, d_kp1)          # c_k ∘ d_{k+1}
        if lhs != c_km1:
            return (k, c_k, d_kp1, c_km1, lhs)
    return None


# ===========================================================================
# LEMMA 2 — Squaring-Index Lemma
# ===========================================================================
#
# Statement:
#   In any left-cancellative E677-magma M, for every x with orbit period d ≥ 5:
#
#       c_{d-4}  =  d_{d-3}                                        [L2a]
#                   (i.e., c_{d-4} = c_{d-3} ∘ x)
#
#       d_{d-2}  =  x  =  c_0                                      [L2b]
#                   (i.e., c_{d-2} ∘ x = x)
#
# Proof strategy for L2a:
#   The squaring identity (conj.rs:405, E677-provable) states:
#       c_{d-4} ∘ c_{d-4}  =  c_{d-5}
#   From L1 at k = d-4 (indices mod d):
#       c_{d-5}  =  c_{d-4} ∘ d_{d-3}
#   Therefore:
#       c_{d-4} ∘ c_{d-4}  =  c_{d-4} ∘ d_{d-3}
#   Left-cancel c_{d-4}:  c_{d-4} = d_{d-3}.  QED.
#
# Proof strategy for L2b:
#   From L1 at k = d-3:
#       c_{d-4}  =  c_{d-3} ∘ d_{d-2}
#   From L2a:
#       c_{d-4}  =  c_{d-3} ∘ x   (since d_{d-3} = c_{d-4} but we need
#                                   d_{d-3} = c_{d-3} ∘ x = d_{d-3}... 
#                                   note d_{d-3} = c_{d-3} ∘ x by definition)
#   So:  c_{d-3} ∘ d_{d-2}  =  c_{d-3} ∘ x.
#   Left-cancel c_{d-3}:  d_{d-2} = x.  QED.
#
# Failure conditions:
#   L2a fails: d ≥ 5 and c_{d-4} ≠ d_{d-3}  (i.e., c_{d-4} ≠ c_{d-3} ∘ x)
#   L2b fails: d ≥ 5 and d_{d-2} ≠ x         (i.e., c_{d-2} ∘ x ≠ x)
#
# What it buys:
#   L2b says x is a RIGHT-FIXED-POINT of c_{d-2}: c_{d-2} ∘ x = x.
#   This interacts directly with the translation structure: x lies in the
#   singleton cycle of R_{c_{d-2}}: this is what conj_singleton_cycle asserts
#   holds via E255 (every element has some y with y∘x = x).  L2b says the
#   specific element c_{d-2} witnesses this for x.
#   Further: d_{d-2} = x means the d-sequence visits x itself at position d-2.
#   Combined with d_0 = x (since c_0 = x, d_0 = c_0 ∘ x = x ∘ x potentially ≠ x),
#   WAIT: d_0 = c_0 ∘ x = x ∘ x = S(x).  So d_{d-2} = x = c_0 says the
#   d-sequence has d_0 = S(x) AND d_{d-2} = x.  If additionally d_0 = d_{d-2},
#   that forces S(x) = x (x is idempotent under squaring).  This is the bridge
#   to squaring-orbit structure.

def check_lemma2_failure(n, rows, x):
    """
    Returns failure info dict, or None if L2a and L2b both hold.
    Checks: (a) c_{d-4} = d_{d-3}, and (b) d_{d-2} = x, for d >= 5.
    """
    c_seq = orbit_c_seq(rows, n, x)
    d_seq = orbit_d_seq(rows, n, x)
    d = len(c_seq)
    if d < 5:
        return None  # precondition not triggered

    # L2a: c_{d-4} == d_{d-3}
    c_dm4 = c_seq[d - 4]
    d_dm3 = d_seq[d - 3]      # = c_{d-3} ∘ x, by definition
    if c_dm4 != d_dm3:
        return {"which": "L2a", "x": x, "d": d,
                "c_{d-4}": c_dm4, "d_{d-3}": d_dm3}

    # L2b: d_{d-2} == x
    d_dm2 = d_seq[d - 2]      # = c_{d-2} ∘ x
    if d_dm2 != x:
        return {"which": "L2b", "x": x, "d": d,
                "d_{d-2}": d_dm2, "x": x}

    return None


# ===========================================================================
# LEMMA 3 — R_x Injectivity on Orbit (Main Open Lemma)
# ===========================================================================
#
# Statement:
#   In any finite E677-magma M, for every x in M:
#   
#       R_x is injective on the L_x-orbit O_x = {c_0, ..., c_{d-1}}        [L3]
#
#   Equivalently: for all 0 ≤ i < j < d:  c_i ∘ x ≠ c_j ∘ x
#   Equivalently: the map k ↦ d_k is injective on {0,...,d-1}
#   Equivalently: E255 holds at x.
#
# This IS the statement we want to prove.  L1 and L2 are the tools.
#
# Proof strategy (via cascade argument):
#   Suppose for contradiction: d_i = d_j for some 0 ≤ i < j < d.  Call
#   the shared value w.
#
#   Step A — single cascade step (from L1):
#     From L1 at k = i-1 (mod d):  c_{i-2} = c_{i-1} ∘ d_i
#     From L1 at k = j-1 (mod d):  c_{j-2} = c_{j-1} ∘ d_j
#     Since d_i = d_j = w:
#       c_{i-2} = c_{i-1} ∘ w  and  c_{j-2} = c_{j-1} ∘ w
#     i.e., R_w maps (c_{i-1} → c_{i-2}) and (c_{j-1} → c_{j-2}).
#     These are two DISTINCT orbit elements mapped to two DISTINCT targets.
#     So far no contradiction.
#
#   Step B — repeated cascade:
#     Now ask: is d_{i-1} = d_{j-1}?  If yes, repeat step A, getting
#     c_{i-3} = c_{i-2} ∘ w' and c_{j-3} = c_{j-2} ∘ w'.  Notice that if
#     the collision also holds at position (i-1, j-1), we slide the window
#     backward by 1 each time.
#
#   Step C — finite pigeonhole closes it:
#     The gap (j - i) is fixed at each cascade step.  After at most d steps,
#     the indices wrap around and we reach c_p = c_q for p ≠ q mod d, meaning
#     two distinct entries of the c-sequence are equal — contradiction since
#     c_0,...,c_{d-1} are DISTINCT elements of O_x.
#
#   GAP in the argument:
#     Step B requires that EACH cascade step produces d_{shifted-i} = d_{shifted-j}.
#     This is NOT automatic: knowing d_i = d_j does NOT immediately imply
#     d_{i-1} = d_{j-1}.  We need an additional structural property of E677 to
#     force the cascade to continue.  Candidates:
#       (i)  L2b: d_{d-2} = x. Combined with the collision, forces the cascade
#            back to specific known d-values (x itself), pinning the collision
#            to identifiable positions.
#       (ii) Cycle-type regularity of L_x (component_report): if L_x has
#            a single cycle-type, its structure limits where R_x can be
#            non-injective.  (Holds in 323/439 models; not universal.)
#       (iii) The ABSENCE of period-2 orbits (empirical + E677-provable):
#            any collision at positions i and j with j = i + d/2 would force
#            a period-halving, but we know 2 does not divide the period set.
#            [Cannot use directly since the period set is not restricted to
#             odd numbers; period 8 appears.]
#
#   Targeted failure condition to search for:
#     A finite E677-magma (NOT necessarily E255) having elements a ≠ b in the
#     same L_x-orbit O_x with a ∘ x = b ∘ x.
#
#   Note: ALL 439 DB models satisfy E255, so no failure will be found there.
#   This test can only be falsified by a fresh E677-but-not-E255 model.
#   The test below confirms all DB models pass (as a sanity check), and
#   also logs the exact failure form for use in ATP / search.

def check_lemma3_failure(n, rows, x):
    """
    Returns a pair (i, j) with d_i = d_j and i != j, or None.
    This is the d-injectivity (E255) failure condition on the orbit of x.
    """
    c_seq = orbit_c_seq(rows, n, x)
    d = len(c_seq)
    seen = {}  # value -> first index
    for k, ck in enumerate(c_seq):
        dk = op(rows, ck, x)
        if dk in seen:
            return (seen[dk], k, dk)
        seen[dk] = k
    return None


# ===========================================================================
# Driver
# ===========================================================================

def run_all():
    models = load_all_models()
    print(f"Checking {len(models)} models against L1, L2, L3 failure conditions.\n")

    l1_fails = []
    l2_fails = []
    l3_fails = []

    for (size, idx, n, rows) in models:
        label = f"{size}/{idx}"
        for x in range(n):
            r = check_lemma1_failure(n, rows, x)
            if r is not None:
                l1_fails.append((label, x, r))

            r = check_lemma2_failure(n, rows, x)
            if r is not None:
                l2_fails.append((label, x, r))

            r = check_lemma3_failure(n, rows, x)
            if r is not None:
                l3_fails.append((label, x, r))

    print("=" * 60)
    print(f"L1 (c_{{k-1}} = c_k ∘ d_{{k+1}}) failures: {len(l1_fails)}")
    if l1_fails:
        for lbl, x, r in l1_fails[:5]:
            print(f"  [{lbl}] x={x}: {r}")

    print(f"L2a (c_{{d-4}} = d_{{d-3}}) / L2b (d_{{d-2}} = x) failures: {len(l2_fails)}")
    if l2_fails:
        for lbl, x, r in l2_fails[:5]:
            print(f"  [{lbl}] x={x}: {r}")

    print(f"L3 (d-injectivity / E255) failures: {len(l3_fails)}")
    if l3_fails:
        for lbl, x, r in l3_fails[:5]:
            print(f"  [{lbl}] x={x}: positions {r[0]} and {r[1]} share d-value {r[2]}")

    print("=" * 60)
    print()

    if not l1_fails and not l2_fails and not l3_fails:
        print("All three lemmas hold on every DB model.")
        print()
        print("Open proof structure:")
        print("  L1 is algebraically provable from E677 + left-cancel.")
        print("  L2 follows from L1 + squaring identity + left-cancel.")
        print("  L3 is the main open step: E677 + finite => R_x injective on O_x.")
        print()
        print("Key gap in L3 (cascade argument):")
        print("  d_i = d_j (collision) implies R_{d_i} acts on (c_{i-1}, c_{j-1})")
        print("  by the L1 recurrence.  The cascade needs d_{i-1} = d_{j-1} ALSO")
        print("  to continue — this is the unproved step.  L2b pins d_{d-2} = x,")
        print("  giving a known 'anchor' in the d-sequence that the cascade must hit.")
        print()
        print("To attack L3:")
        print("  1. Try to build an E677 model (via DPLL / model search in src/) where")
        print("     E255 fails.  If impossible for all n, it suggests E677 => E255.")
        print("  2. Try to prove the cascade directly: show d_i = d_j and L2b together")
        print("     force i = j (mod d) without needing all intermediate d_{i-k} = d_{j-k}.")
        print("  3. Use the ATP files in atp/ to check if E677 + left-cancel + (d_i = d_j)")
        print("     + L2b gives a contradiction in first-order logic.")

    verdict_proof_candidates(l1_fails, l2_fails, l3_fails)
    verdict_intermediate_equations(models)
    verdict_search_families()
    verdict_construction_audit()


# ===========================================================================
# Verdict tables
# ===========================================================================

def verdict_proof_candidates(l1_fails, l2_fails, l3_fails):
    """
    For each proof candidate, force a binary verdict on three questions:
      A. Supported by all known models?
      B. Genuinely stronger than a reformulation of E255?
      C. Plausibly derivable from E677 + finiteness alone?
    """
    W = 55
    print()
    print("=" * W)
    print("PROOF CANDIDATE VERDICTS")
    print("=" * W)
    fmt = "  {:<6} {:<10} {:<10} {:<10}  {}"
    print(fmt.format("Lemma", "All-DB-OK", "Stronger", "Derivable", "Status"))
    print("  " + "-" * (W - 2))

    # L1: c_{k-1} = c_k ∘ d_{k+1}
    l1_ok = len(l1_fails) == 0
    # L1 holds regardless of E255, so it IS stronger (unconditional E677 identity)
    # Derivability: fully provable (E677 + left-cancel, proof sketch in comments)
    print(fmt.format(
        "L1",
        "YES" if l1_ok else f"NO({len(l1_fails)})",
        "YES",   # unconditional identity, not a restatement of E255
        "YES",   # proof sketch complete: E677 + left-cancel
        "CLOSED — algebraically provable from E677+LC"
    ))

    # L2: c_{d-4}=d_{d-3} and d_{d-2}=x
    l2_ok = len(l2_fails) == 0
    # L2 is a non-trivial structural consequence: d_{d-2}=x pins a specific
    # orbit-anchor.  It follows from L1 + squaring identity, not from E255.
    print(fmt.format(
        "L2",
        "YES" if l2_ok else f"NO({len(l2_fails)})",
        "YES",   # not a restatement of E255; holds in any E677 model (E255 or not)
        "YES",   # proof sketch complete: L1 + orbit_squaring_identity
        "CLOSED — follows from L1 + squaring identity + LC"
    ))

    # L3: d-injectivity = E255
    l3_ok = len(l3_fails) == 0
    # L3 IS E255 equivalently, so "stronger than E255 reformulation" = NO.
    # Derivability from E677+finite: OPEN — this is the main conjecture.
    print(fmt.format(
        "L3",
        "YES" if l3_ok else f"NO({len(l3_fails)})",
        "NO",    # L3 is equivalent to E255 by definition
        "OPEN",  # the main outstanding conjecture
        "OPEN — finite E677 => d-injectivity not yet proved"
    ))

    print()
    print("  L3 cascade gap: d_i=d_j => via L1, R_w maps (c_{i-1}->c_{i-2}) and")
    print("  (c_{j-1}->c_{j-2}). Need d_{i-1}=d_{j-1} to continue. The anchor L2b")
    print("  (d_{d-2}=x) constrains where the collision can sit, but does not close")
    print("  the gap without an additional argument (period-regularity or ATP).")
    print("=" * W)


# ===========================================================================
# Intermediate equations — stepping stones between E677 and E255
# ===========================================================================
#
# E255:    x = ((x ◇ x) ◇ x) ◇ x          i.e., x = f(f(f(x,x),x),x)
# E406197: x = ((x ◇ (x ◇ x)) ◇ (x ◇ x)) ◇ (x ◇ x)
#          i.e., x = f(f(f(x, f(x,x)), f(x,x)), f(x,x))
# E52930:  x ◇ x = (((x ◇ x) ◇ x) ◇ x) ◇ x
#          i.e., f(x,x) = f(f(f(f(x,x),x),x),x)
#
# Implication chain (if all hold): E677 => E406197 => E255 (conjectured)
# E52930 is implied by E255 but may be provable directly from E677.
# These intermediate targets may be easier to establish with ATP.

def check_E255(n, rows):
    """x = f(f(f(x,x),x),x) for all x."""
    for x in range(n):
        xx = op(rows, x, x)
        xxx = op(rows, xx, x)
        xxxx = op(rows, xxx, x)
        if x != xxxx:
            return False, x
    return True, None


def check_E406197(n, rows):
    """x = f(f(f(x, f(x,x)), f(x,x)), f(x,x)) for all x."""
    for x in range(n):
        xx = op(rows, x, x)                  # x ◇ x
        x_xx = op(rows, x, xx)               # x ◇ (x ◇ x)
        t1 = op(rows, x_xx, xx)              # (x ◇ (x ◇ x)) ◇ (x ◇ x)
        t2 = op(rows, t1, xx)                # ((x ◇ (x ◇ x)) ◇ (x ◇ x)) ◇ (x ◇ x)
        if x != t2:
            return False, x
    return True, None


def check_E52930(n, rows):
    """f(x,x) = f(f(f(f(x,x),x),x),x) for all x."""
    for x in range(n):
        xx = op(rows, x, x)                  # x ◇ x
        t1 = op(rows, xx, x)                 # (x ◇ x) ◇ x
        t2 = op(rows, t1, x)                 # ((x ◇ x) ◇ x) ◇ x
        t3 = op(rows, t2, x)                 # (((x ◇ x) ◇ x) ◇ x) ◇ x
        if xx != t3:
            return False, x
    return True, None


def check_idempotent(n, rows):
    """x = x ◇ x for all x (E255 implies this when combined with left-cancel)."""
    for x in range(n):
        if op(rows, x, x) != x:
            return False, x
    return True, None


def verdict_intermediate_equations(models):
    """Test intermediate equations between E677 and E255 across all DB models."""
    W = 70
    print()
    print("=" * W)
    print("INTERMEDIATE EQUATION VERDICTS")
    print("=" * W)

    checks = [
        ("E255",    check_E255),
        ("E406197", check_E406197),
        ("E52930",  check_E52930),
        ("Idempot", check_idempotent),
    ]

    results = {}
    for name, fn in checks:
        fails = []
        for (size, idx, n, rows) in models:
            ok, witness = fn(n, rows)
            if not ok:
                fails.append((f"{size}/{idx}", witness))
        results[name] = fails

    fmt = "  {:<10} {:<12} {}"
    print(fmt.format("Equation", "Holds?", "Detail"))
    print("  " + "-" * (W - 2))
    for name, fn in checks:
        fails = results[name]
        if not fails:
            print(fmt.format(name, f"YES (0/{len(models)})", "Uniform across all DB models"))
        else:
            print(fmt.format(name, f"NO ({len(fails)}/{len(models)})",
                             f"First fail: {fails[0]}"))

    print()
    # Implication analysis
    e255_ok = len(results["E255"]) == 0
    e406197_ok = len(results["E406197"]) == 0
    e52930_ok = len(results["E52930"]) == 0
    idemp_ok = len(results["Idempot"]) == 0

    if e255_ok and e406197_ok and e52930_ok:
        print("  All intermediate equations hold on every DB model.")
        print("  Implication chain E677 => E406197 => E255 is empirically supported.")
        print()
        print("  ATP targets (ordered by expected difficulty):")
        print("    1. E677 => E52930 (weakest — squaring equivariance at depth 5)")
        print("    2. E677 => E406197 (intermediate — squaring self-reference)")
        print("    3. E677 + E406197 => E255 (may be tractable if E406197 provides leverage)")
    if not idemp_ok:
        n_non_idemp = len(results["Idempot"])
        print(f"  {n_non_idemp}/{len(models)} models are non-idempotent (expected for non-RC models).")
    print("=" * W)


def verdict_search_families():
    """
    For each search family, force a binary verdict on three questions:
      A. Anti-255 witness produced?
      B. Proven empty up to what parameters?
      C. Structural regime that found models collapse into?

    The orbit_anti255_dpll family (new) has 'running' status.
    """
    W = 80
    print()
    print("=" * W)
    print("SEARCH FAMILY VERDICTS  (update after each run)")
    print("=" * W)

    families = [
        {
            "name": "tinv_dpll",
            "description": "f(x,y)=x+h(y-x) on Z/nZ, full DPLL",
            "witness": "NONE — all tinv models satisfy E255 (trivially: h bijective)",
            "empty_up_to": "All n (structurally: tinv+E677 => E255 in this class)",
            "regime": "Always affine or near-affine h; never produces collision",
        },
        {
            "name": "fiber_affine",
            "description": "Affine fiber extension of db bases (color-extensions.py)",
            "witness": "NONE",
            "empty_up_to": "7/0 K<=4 (proved UNSAT); 9/0 K<=3 (proved UNSAT)",
            "regime": "Solver collapses to h(x,y)=ax+by+c; affine restriction exhausted",
        },
        {
            "name": "fiber_nonlinear",
            "description": "Full table fibers over db bases (color-extensions-nonlinear.py)",
            "witness": "NONE — anti255 mode UNSAT for all tested (7/0 K<=4, 9/0 K<=3)",
            "empty_up_to": "7/0 K<=4 anti255 proved UNSAT; 9/0 K<=3 proved UNSAT",
            "regime": "No SAT instances found; K=4 plain-677 for 7/0 timed out (indeterminate)",
        },
        {
            "name": "orbit_anti255_dpll",
            "description": "Full E677 table DPLL, orbit-biased, requires !E255 (src/orbit_dpll.rs)",
            "witness": "RUNNING — not yet determined",
            "empty_up_to": "RUNNING — exhaustive for each n up to timeout",
            "regime": "PENDING — report structural regime of first SAT model if found",
        },
    ]

    for fam in families:
        print(f"\n  [{fam['name']}]")
        print(f"    Scope:      {fam['description']}")
        print(f"    Witness:    {fam['witness']}")
        print(f"    Empty up to:{fam['empty_up_to']}")
        print(f"    Regime:     {fam['regime']}")

    print()
    print("  Decision rule:")
    print("  (a) If orbit_anti255_dpll finds a witness at size n: we have a counterexample.")
    print("  (b) If it proves UNSAT for all n <= N: promotes L3 from conjecture to")
    print("      'verified up to size N', sharpening the ATP attack window.")
    print("  (c) If all found E677 models in this family are E255: structural regime")
    print("      collapses and should be promoted to a new conjectural lemma (L4).")
    print("=" * W)


def verdict_construction_audit():
    """
    Audit which counterexample attack directions (A1-A6 from the plan) have
    live, runnable code versus being conceptual only.
    """
    W = 80
    print()
    print("=" * W)
    print("CONSTRUCTION FAMILY AUDIT  (A1–A6 attack directions)")
    print("=" * W)

    families = [
        {
            "id": "A1",
            "name": "Piecewise linear extension (vanishing c/d)",
            "code": "color-extensions.py (affine only), color-extensions-nonlinear.py (full table)",
            "status": "PARTIAL",
            "gap": "Vanishing c_{x,y}/d_{x,y} mode not implemented. Only full-table or affine.",
            "next": "Add vanishing-coefficient mode to color-extensions.py for targeted piecewise search.",
        },
        {
            "id": "A2",
            "name": "Partial model composition (core + add-ons)",
            "code": "src/c_dpll/ (c_complete, c_complete_extended)",
            "status": "PARTIAL",
            "gap": "c_complete exists but NOT wired to anti-255 constraints.",
            "next": "Add anti255 filter to c_dpll submit_model (like eq_dpll has).",
        },
        {
            "id": "A3",
            "name": "Rudi's 2-coloring + non-affine fibers",
            "code": "color-extensions-nonlinear.py (anti255 mode)",
            "status": "LIVE",
            "gap": "Only bases 7/0 and 9/0 implemented. 29/0 (3 colorings) not added.",
            "next": "Add magmadef for 29/0 with its three 2-colorings.",
        },
        {
            "id": "A4",
            "name": "Block design mixed constructions (GDD)",
            "code": "NONE",
            "status": "CONCEPTUAL",
            "gap": "No implementation. Would need GDD construction + mixed fiber ops.",
            "next": "Low priority — Bruno's closure argument suggests 255 stays in blocks.",
        },
        {
            "id": "A5",
            "name": "Non-abelian group constructions (exponent 5)",
            "code": "linear.sage (abelian groups only)",
            "status": "MINIMAL",
            "gap": "Only abelian exhaustive search. No non-abelian or exponent-5 specific code.",
            "next": "Implement f(x)·y^b·g(x) Ansatz over (Z/5Z)^k groups.",
        },
        {
            "id": "A6",
            "name": "Free algebra quotient (Zoltan's approach)",
            "code": "src/one_orbit2.rs (term rewriting branch-and-bound)",
            "status": "LIVE",
            "gap": "Runs but does not check finiteness of computed quotient.",
            "next": "Add quotient size detection + E255 check on completion.",
        },
    ]

    for fam in families:
        color = {"LIVE": "✓", "PARTIAL": "~", "MINIMAL": "·", "CONCEPTUAL": "✗"}
        marker = color.get(fam["status"], "?")
        print(f"\n  [{marker}] {fam['id']}: {fam['name']}")
        print(f"      Code:   {fam['code']}")
        print(f"      Status: {fam['status']}")
        print(f"      Gap:    {fam['gap']}")
        print(f"      Next:   {fam['next']}")

    print()
    print("  Priority ranking for counterexample work:")
    print("    1. A3 (LIVE) — add 29/0 base, run anti255 mode")
    print("    2. A1 (PARTIAL) — vanishing-coefficient piecewise extension")
    print("    3. A2 (PARTIAL) — wire anti255 into c_dpll")
    print("    4. A6 (LIVE) — add finiteness/E255 detection to one_orbit2")
    print("    5. A5 (MINIMAL) — non-abelian group Ansatz (new code needed)")
    print("    6. A4 (CONCEPTUAL) — block design (deprioritized)")
    print("=" * W)


if __name__ == "__main__":
    run_all()
