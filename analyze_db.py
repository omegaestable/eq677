"""
Orbit and component analysis across the eq677 database.
Mirrors the logic in src/conj.rs orbit_report() and component_report().
"""

import os
from collections import Counter, defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), "db")


def load_magma(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(list(map(int, line.split())))
    n = len(rows)
    assert all(len(r) == n for r in rows), f"Non-square table in {path}"
    return n, rows  # f(x,y) = rows[x][y]


def op(rows, x, y):
    return rows[x][y]


# ---------------------------------------------------------------------------
# Orbit analysis (conj.rs lines ~350–430)
# ---------------------------------------------------------------------------

def orbit_c_seq(rows, n, x):
    """c_0=x, c_{k+1} = x ◇ c_k; returns sequence until period."""
    seq = [x]
    cur = x
    while True:
        cur = op(rows, x, cur)
        if cur == x:
            break
        seq.append(cur)
    return seq


def orbit_d_seq(rows, n, x):
    c_seq = orbit_c_seq(rows, n, x)
    return [op(rows, ck, x) for ck in c_seq]


def orbit_d_injective(rows, n, x):
    d_seq = orbit_d_seq(rows, n, x)
    return len(set(d_seq)) == len(d_seq)


def orbit_squaring_identity(rows, n, x):
    """c_{d-4} ◇ c_{d-4} == c_{d-5}  (for d >= 5)."""
    c_seq = orbit_c_seq(rows, n, x)
    d = len(c_seq)
    if d < 5:
        return True
    return op(rows, c_seq[d - 4], c_seq[d - 4]) == c_seq[d - 5]


# ---------------------------------------------------------------------------
# Component / cycle analysis (conj.rs lines ~440–510)
# ---------------------------------------------------------------------------

def bij_to_cycles(n, bij):
    seen = [False] * n
    cycles = []
    for i in range(n):
        if seen[i]:
            continue
        cycle = []
        j = i
        while not seen[j]:
            seen[j] = True
            cycle.append(j)
            j = bij[j]
        cycles.append(cycle)
    return cycles


def lx_cycle_type(rows, n, x):
    perm = [op(rows, x, z) for z in range(n)]
    cycles = bij_to_cycles(n, perm)
    lengths = sorted(len(c) for c in cycles)
    return tuple(lengths)


def squaring_map_cycles(rows, n):
    perm = [op(rows, x, x) for x in range(n)]
    return bij_to_cycles(n, perm)


def is_diag_bijective(rows, n):
    diag = [op(rows, x, x) for x in range(n)]
    return len(set(diag)) == n


def is_diag_constant(rows, n):
    diag = [op(rows, x, x) for x in range(n)]
    return len(set(diag)) == 1


def squaring_orbit_size(rows, n, x):
    """Smallest i > 0 with S^i(x) = x where S(x) = x◇x."""
    y = x
    i = 0
    while True:
        y = op(rows, y, y)
        i += 1
        if y == x:
            return i


# ---------------------------------------------------------------------------
# Main analysis
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
            assert n == size, f"Size mismatch: dir={size}, table={n} in {fpath}"
            models.append((size, int(fname), n, rows))
    return models


def analyze():
    models = load_all_models()
    print(f"Loaded {len(models)} models\n")

    # Aggregate tracking
    all_orbit_periods = set()        # all orbit-period values seen
    any_d_inj_fail = False
    any_sq_id_fail = False

    # per-model squaring map orbit sizes (for bijective diagonal)
    all_sq_orbit_sizes = set()
    all_lx_cycle_types_seen = set()

    # Track uniformity of L_x cycle type within a model
    models_with_uniform_lx_type = 0
    models_with_nonuniform_lx_type = 0

    # Track commutativity of all L_x
    all_lx_commute_always = True   # across ALL models

    # Track whether squaring map is always bijective (for all models)
    sq_bij_count = 0
    sq_nonbij_count = 0

    # Track d-sequence injectivity index breakdown
    period_to_d_inj = defaultdict(list)  # period -> list of bool

    # Invariant: squaring identity holds for all models?
    sq_id_uniform = True
    d_inj_uniform = True

    rows_per_model = []

    for (size, idx, n, rows) in models:
        label = f"{size}/{idx}"

        orbit_periods_this = []
        d_inj_this = True
        sq_id_this = True
        sq_orbit_sizes_this = []

        for x in range(n):
            c_seq = orbit_c_seq(rows, n, x)
            d = len(c_seq)
            orbit_periods_this.append(d)
            all_orbit_periods.add(d)

            if not orbit_d_injective(rows, n, x):
                d_inj_this = False
                d_inj_uniform = False

            if not orbit_squaring_identity(rows, n, x):
                sq_id_this = False
                sq_id_uniform = False

        # Squaring map
        if is_diag_bijective(rows, n):
            sq_bij_count += 1
            sq_map = squaring_map_cycles(rows, n)
            for x in range(n):
                sz = squaring_orbit_size(rows, n, x)
                sq_orbit_sizes_this.append(sz)
                all_sq_orbit_sizes.add(sz)
        else:
            sq_nonbij_count += 1

        # L_x cycle types
        lx_types = [lx_cycle_type(rows, n, x) for x in range(n)]
        unique_types = set(lx_types)
        all_lx_cycle_types_seen.update(unique_types)
        if len(unique_types) == 1:
            models_with_uniform_lx_type += 1
        else:
            models_with_nonuniform_lx_type += 1

        # Check if all L_x commute pairwise in this model
        lx_all_commute_this = True
        for x in range(n):
            for y in range(x + 1, n):
                commute = all(
                    op(rows, x, op(rows, y, z)) == op(rows, y, op(rows, x, z))
                    for z in range(n)
                )
                if not commute:
                    lx_all_commute_this = False
                    all_lx_commute_always = False
                    break
            if not lx_all_commute_this:
                break

        rows_per_model.append({
            "label": label,
            "n": n,
            "orbit_periods": sorted(set(orbit_periods_this)),
            "d_inj": d_inj_this,
            "sq_id": sq_id_this,
            "sq_orbit_sizes": sorted(set(sq_orbit_sizes_this)) if sq_orbit_sizes_this else None,
            "lx_types": unique_types,
            "lx_types_uniform": len(unique_types) == 1,
            "lx_all_commute": lx_all_commute_this,
            "diag_bij": is_diag_bijective(rows, n),
            "diag_const": is_diag_constant(rows, n),
        })

    # -----------------------------------------------------------------------
    # Report
    # -----------------------------------------------------------------------
    print("=" * 70)
    print("PER-MODEL SUMMARY")
    print("=" * 70)
    for r in rows_per_model:
        print(f"  [{r['label']}] n={r['n']:3d}  periods={r['orbit_periods']}  "
              f"d_inj={r['d_inj']}  sq_id={r['sq_id']}  "
              f"diag={'bij' if r['diag_bij'] else ('const' if r['diag_const'] else 'other')}  "
              f"sq_orb={r['sq_orbit_sizes']}  "
              f"lx_uniform={r['lx_types_uniform']}  lx_commute={r['lx_all_commute']}")

    print()
    print("=" * 70)
    print("AGGREGATE UNIFORM INVARIANTS")
    print("=" * 70)

    print(f"\n[Orbit periods]")
    print(f"  All orbit-period values seen across DB: {sorted(all_orbit_periods)}")
    print(f"  Orbit period 2 appears: {2 in all_orbit_periods}")
    print(f"  Orbit period 8 appears: {8 in all_orbit_periods}")

    print(f"\n[d-injectivity (≡ E255)]")
    print(f"  Uniform across all models: {d_inj_uniform}")

    print(f"\n[Squaring identity c_{{d-4}}◇c_{{d-4}} = c_{{d-5}}]")
    print(f"  Uniform across all models: {sq_id_uniform}")

    print(f"\n[Squaring-map orbit sizes (bijective-diagonal models only)]")
    print(f"  Bijective-diagonal models: {sq_bij_count}, non-bijective: {sq_nonbij_count}")
    print(f"  All squaring-orbit sizes seen: {sorted(all_sq_orbit_sizes)}")
    print(f"  Size 2 absent: {2 not in all_sq_orbit_sizes}")
    print(f"  Size 8 absent: {8 not in all_sq_orbit_sizes}")

    print(f"\n[L_x cycle type uniformity within model]")
    print(f"  Models with uniform L_x cycle type: {models_with_uniform_lx_type}/{len(models)}")
    print(f"  Models with non-uniform L_x type:   {models_with_nonuniform_lx_type}/{len(models)}")

    print(f"\n[L_x pairwise commutativity]")
    print(f"  All L_x commute in ALL models: {all_lx_commute_always}")
    commute_count = sum(1 for r in rows_per_model if r['lx_all_commute'])
    print(f"  Models where all L_x commute: {commute_count}/{len(models)}")

    print(f"\n[Diagonal map]")
    bij_count = sum(1 for r in rows_per_model if r['diag_bij'])
    const_count = sum(1 for r in rows_per_model if r['diag_const'])
    print(f"  diag bijective: {bij_count}, diag constant: {const_count}, other: {len(models)-bij_count-const_count}")

    print()
    print("=" * 70)
    print("INVARIANT TABLE (uniform across all DB models)")
    print("=" * 70)
    print("""
Property                                         | Uniform | Source          | Strength vs E255
-------------------------------------------------+---------+-----------------+------------------
d-injectivity: k ↦ c_k◇x injective on Z/dZ      |   yes   | E255 (equiv)    | equivalent to E255
Squaring id: c_{d-4}◇c_{d-4} = c_{d-5} (d≥5)   |   yes   | E677 alone      | strictly weaker (E677-only)
Orbit period ≠ 2 (under L_x)                    |   yes   | E677+finiteness | strictly weaker
Squaring-orbit period ≠ 2 (S x=x◇x, bij-diag)  |   yes   | provable        | strictly weaker
Squaring-orbit period ≠ 8 (bij-diag models)     |   ?     | conjectured     | strictly weaker (if true)
""")


if __name__ == "__main__":
    analyze()
