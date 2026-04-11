"""
extract_identities.py
=====================
Systematically discover finite-model identities of E677-magmas at depth <= MAX_DEPTH.

An identity is a universally quantified equation t1(x,y) = t2(x,y) that holds
in every model in the database.  We are interested in identities that:
  (a) hold in all 439+ finite E677 models, AND
  (b) are NOT equational consequences of E677 (detected by checking against
      an infinite free model or an ATP refutation attempt).

These "non-equational finite identities" are the best known source of extra
constraints that exploitation of finiteness gives us.

Strategy:
  1. Enumerate all terms of depth <= D over variables {x, y} and f(_, _).
  2. For each pair (t1, t2), check t1 = t2 in every DB model.
  3. Filter trivially true identities (e.g., both sides reduce to same term).
  4. Output survivors as candidate non-equational identities.

We include single-variable identities (x only) since those are the most
proof-relevant (E255 is single-variable).
"""

import os
import sys
from itertools import product as cartprod
from analyze_db import load_magma, op

DB_PATH = os.path.join(os.path.dirname(__file__), "db")
MAX_DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 4  # depth 5 is expensive


# ---------------------------------------------------------------------------
# Term representation
# ---------------------------------------------------------------------------
# A term is either:
#   ("x",)          — the variable x
#   ("y",)          — the variable y
#   ("f", t1, t2)   — f(t1, t2)

def gen_terms(depth, variables=("x", "y")):
    """Generate all terms of depth <= `depth` over the given variables."""
    if depth == 0:
        return [(v,) for v in variables]
    smaller = gen_terms(depth - 1, variables)
    current = [(v,) for v in variables]
    # Build f(t1, t2) where max(depth(t1), depth(t2)) == depth
    prev = gen_terms(depth - 1, variables)
    for t1 in prev:
        for t2 in prev:
            t = ("f", t1, t2)
            if term_depth(t) <= depth:
                current.append(t)
    return current


def gen_terms_up_to(max_depth, variables=("x", "y")):
    """Generate all distinct terms of depth <= max_depth."""
    seen = set()
    terms = []
    for d in range(max_depth + 1):
        for t in gen_terms(d, variables):
            key = term_to_str(t)
            if key not in seen:
                seen.add(key)
                terms.append(t)
    return terms


def term_depth(t):
    if len(t) == 1:
        return 0
    return 1 + max(term_depth(t[1]), term_depth(t[2]))


def term_size(t):
    if len(t) == 1:
        return 1
    return 1 + term_size(t[1]) + term_size(t[2])


def term_to_str(t):
    if len(t) == 1:
        return t[0]
    return f"f({term_to_str(t[1])},{term_to_str(t[2])})"


def eval_term(t, rows, n, x, y):
    if t == ("x",):
        return x
    if t == ("y",):
        return y
    return op(rows, eval_term(t[1], rows, n, x, y), eval_term(t[2], rows, n, x, y))


# ---------------------------------------------------------------------------
# Identity checking
# ---------------------------------------------------------------------------

def check_identity_all_models(t1, t2, models, nvars=2):
    """Return True if t1 = t2 holds in all models for all (x, y) assignments."""
    for (size, idx, n, rows) in models:
        if nvars == 1:
            for x in range(n):
                if eval_term(t1, rows, n, x, 0) != eval_term(t2, rows, n, x, 0):
                    return False
        else:
            for x in range(n):
                for y in range(n):
                    if eval_term(t1, rows, n, x, y) != eval_term(t2, rows, n, x, y):
                        return False
    return True


def terms_equivalent_under_e677(t1, t2, models):
    """Fast check: do t1 and t2 evaluate identically in every model?"""
    return check_identity_all_models(t1, t2, models)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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


def main():
    print(f"Generating terms up to depth {MAX_DEPTH}...")
    # Single-variable identities (most proof-relevant)
    terms_1v = gen_terms_up_to(MAX_DEPTH, variables=("x",))
    # Two-variable identities
    terms_2v = gen_terms_up_to(MAX_DEPTH, variables=("x", "y"))

    print(f"  Single-variable terms: {len(terms_1v)}")
    print(f"  Two-variable terms:    {len(terms_2v)}")

    models = load_all_models()
    print(f"  Models loaded: {len(models)}")

    # --- Phase 1: single-variable identities (cheaper, more relevant) ---
    print(f"\n{'='*60}")
    print(f"SINGLE-VARIABLE IDENTITIES (depth <= {MAX_DEPTH})")
    print(f"{'='*60}")

    # Canonical form: for each term, compute its evaluation vector on a
    # small model as a fast fingerprint, then only compare terms with
    # matching fingerprints across all models.
    fingerprints_1v = {}  # fingerprint -> list of (term, str)
    # Use the first few models as fingerprint base
    fp_models = models[:5]  # small models for fast fingerprinting
    for t in terms_1v:
        fp = []
        for (size, idx, n, rows) in fp_models:
            for x in range(min(n, 8)):
                fp.append(eval_term(t, rows, n, x, 0))
        fp = tuple(fp)
        if fp not in fingerprints_1v:
            fingerprints_1v[fp] = []
        fingerprints_1v[fp].append(t)

    # Equivalence classes with >1 member are candidate identities
    sv_identities = []
    for fp, group in fingerprints_1v.items():
        if len(group) < 2:
            continue
        # Verify on ALL models
        canonical = group[0]
        for other in group[1:]:
            if check_identity_all_models(canonical, other, models, nvars=1):
                sv_identities.append((canonical, other))

    # Filter trivial (same term structure)
    nontrivial = [(t1, t2) for t1, t2 in sv_identities
                  if term_to_str(t1) != term_to_str(t2)]

    # Deduplicate: keep only one representative per equivalence class
    classes_1v = {}
    for t in terms_1v:
        fp = []
        for (size, idx, n, rows) in models[:3]:
            for x in range(min(n, 12)):
                fp.append(eval_term(t, rows, n, x, 0))
        fp = tuple(fp)
        if fp not in classes_1v:
            classes_1v[fp] = t

    print(f"  Equivalence classes: {len(classes_1v)}")
    print(f"  Non-trivial identities: {len(nontrivial)}")

    # Print representative identities
    if nontrivial:
        print(f"\n  Representative identities (first of each class):")
        seen_pairs = set()
        for t1, t2 in sorted(nontrivial, key=lambda p: term_size(p[0]) + term_size(p[1])):
            s1, s2 = term_to_str(t1), term_to_str(t2)
            pair_key = tuple(sorted([s1, s2]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            d1, d2 = term_depth(t1), term_depth(t2)
            print(f"    {s1}  =  {s2}   [depth {max(d1,d2)}, size {term_size(t1)}+{term_size(t2)}]")
            if len(seen_pairs) > 50:
                print("    ... (truncated)")
                break

    # --- Phase 2: two-variable identities (more expensive) ---
    if MAX_DEPTH <= 3:
        print(f"\n{'='*60}")
        print(f"TWO-VARIABLE IDENTITIES (depth <= {MAX_DEPTH})")
        print(f"{'='*60}")

        fingerprints_2v = {}
        for t in terms_2v:
            fp = []
            for (size, idx, n, rows) in fp_models:
                for x in range(min(n, 5)):
                    for y in range(min(n, 5)):
                        fp.append(eval_term(t, rows, n, x, y))
            fp = tuple(fp)
            if fp not in fingerprints_2v:
                fingerprints_2v[fp] = []
            fingerprints_2v[fp].append(t)

        tv_identities = []
        for fp, group in fingerprints_2v.items():
            if len(group) < 2:
                continue
            canonical = group[0]
            for other in group[1:]:
                if check_identity_all_models(canonical, other, models, nvars=2):
                    tv_identities.append((canonical, other))

        nontrivial_2v = [(t1, t2) for t1, t2 in tv_identities
                         if term_to_str(t1) != term_to_str(t2)]

        print(f"  Non-trivial two-variable identities: {len(nontrivial_2v)}")
        if nontrivial_2v:
            seen_pairs = set()
            for t1, t2 in sorted(nontrivial_2v, key=lambda p: term_size(p[0]) + term_size(p[1])):
                s1, s2 = term_to_str(t1), term_to_str(t2)
                pair_key = tuple(sorted([s1, s2]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                print(f"    {s1}  =  {s2}   [depth {max(term_depth(t1), term_depth(t2))}]")
                if len(seen_pairs) > 50:
                    print("    ... (truncated)")
                    break
    else:
        print(f"\n  (Skipping two-variable identities at depth {MAX_DEPTH} — too expensive.)")
        print(f"  Run with MAX_DEPTH=3 to include two-variable identities.")

    # --- Phase 3: E677 ATP cross-reference ---
    print(f"\n{'='*60}")
    print("ATP CROSS-REFERENCE")
    print(f"{'='*60}")
    print("  To determine which identities above are NON-equational (require finiteness):")
    print("  For each identity t1 = t2, run:")
    print("    vampire --mode casc -t 60 <<< 'cnf(eq677,axiom,X=f(Y,f(X,f(f(Y,X),Y)))).")
    print("                                    cnf(target,negated_conjecture, t1 != t2).'")
    print("  If Vampire proves it: the identity is an equational consequence (less interesting).")
    print("  If Vampire fails: the identity likely REQUIRES finiteness (very interesting).")
    print()
    print("  McKenna reported 13 depth-5 non-equational identities.")
    print(f"  Run this script with depth 5 to rediscover them:")
    print(f"    python extract_identities.py 5")


if __name__ == "__main__":
    main()
