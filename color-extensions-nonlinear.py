"""
Non-linear fiber extension search for E677 counterexamples.

Unlike color-extensions.py (which uses affine fibers f(x,y) = Ax+By+C mod K),
this script uses full function tables for the fiber operations, allowing
non-affine structures. Supports optional anti-E255 mode to search for
E677-satisfying magmas that violate E255.

Usage:
  python color-extensions-nonlinear.py <mode> <magma_idx> [max_K]

  mode: "677" (find E677 models) or "anti255" (find E677 ∧ ¬E255 models)
  magma_idx: index into MAGMA_DEFS (0-7)
  max_K: maximum fiber size (default: 5)
"""

from z3 import *
import sys


# --- Base magma definitions (imported from color-extensions.py) ---
# Only the small ones are practical for non-linear search.

def magmadef_7_0():
    name = "7/0"
    n = 7
    m = dict()
    c = dict()
    m[(0, 0)] = 0; m[(0, 1)] = 1; m[(0, 2)] = 2; m[(0, 3)] = 3; m[(0, 4)] = 4; m[(0, 5)] = 5; m[(0, 6)] = 6; m[(1, 0)] = 4; m[(1, 1)] = 5; m[(1, 2)] = 6; m[(1, 3)] = 0; m[(1, 4)] = 1; m[(1, 5)] = 2; m[(1, 6)] = 3; m[(2, 0)] = 1; m[(2, 1)] = 2; m[(2, 2)] = 3; m[(2, 3)] = 4; m[(2, 4)] = 5; m[(2, 5)] = 6; m[(2, 6)] = 0; m[(3, 0)] = 5; m[(3, 1)] = 6; m[(3, 2)] = 0; m[(3, 3)] = 1; m[(3, 4)] = 2; m[(3, 5)] = 3; m[(3, 6)] = 4; m[(4, 0)] = 2; m[(4, 1)] = 3; m[(4, 2)] = 4; m[(4, 3)] = 5; m[(4, 4)] = 6; m[(4, 5)] = 0; m[(4, 6)] = 1; m[(5, 0)] = 6; m[(5, 1)] = 0; m[(5, 2)] = 1; m[(5, 3)] = 2; m[(5, 4)] = 3; m[(5, 5)] = 4; m[(5, 6)] = 5; m[(6, 0)] = 3; m[(6, 1)] = 4; m[(6, 2)] = 5; m[(6, 3)] = 6; m[(6, 4)] = 0; m[(6, 5)] = 1; m[(6, 6)] = 2;
    c[(0, 0)] = 0; c[(0, 1)] = 1; c[(0, 2)] = 1; c[(0, 3)] = 1; c[(0, 4)] = 1; c[(0, 5)] = 1; c[(0, 6)] = 1; c[(1, 0)] = 2; c[(1, 1)] = 3; c[(1, 2)] = 4; c[(1, 3)] = 5; c[(1, 4)] = 6; c[(1, 5)] = 7; c[(1, 6)] = 8; c[(2, 0)] = 2; c[(2, 1)] = 6; c[(2, 2)] = 3; c[(2, 3)] = 7; c[(2, 4)] = 4; c[(2, 5)] = 8; c[(2, 6)] = 5; c[(3, 0)] = 2; c[(3, 1)] = 7; c[(3, 2)] = 5; c[(3, 3)] = 3; c[(3, 4)] = 8; c[(3, 5)] = 6; c[(3, 6)] = 4; c[(4, 0)] = 2; c[(4, 1)] = 4; c[(4, 2)] = 6; c[(4, 3)] = 8; c[(4, 4)] = 3; c[(4, 5)] = 5; c[(4, 6)] = 7; c[(5, 0)] = 2; c[(5, 1)] = 5; c[(5, 2)] = 8; c[(5, 3)] = 4; c[(5, 4)] = 7; c[(5, 5)] = 3; c[(5, 6)] = 6; c[(6, 0)] = 2; c[(6, 1)] = 8; c[(6, 2)] = 7; c[(6, 3)] = 6; c[(6, 4)] = 5; c[(6, 5)] = 4; c[(6, 6)] = 3;
    t = [(0, 0, 0, 0, ), (1, 2, 6, 1, ), (2, 4, 1, 5, ), (3, 5, 2, 6, ), (4, 8, 4, 7, ), (5, 1, 7, 8, ), (6, 3, 5, 2, ), (7, 6, 8, 3, ), (8, 7, 3, 4, ), ]
    return n, name, m, c, t

def magmadef_9_0():
    name = "9/0"
    n = 9
    m = dict()
    c = dict()
    m[(0, 0)] = 0; m[(0, 1)] = 8; m[(0, 2)] = 4; m[(0, 3)] = 7; m[(0, 4)] = 3; m[(0, 5)] = 2; m[(0, 6)] = 5; m[(0, 7)] = 1; m[(0, 8)] = 6; m[(1, 0)] = 1; m[(1, 1)] = 6; m[(1, 2)] = 5; m[(1, 3)] = 8; m[(1, 4)] = 4; m[(1, 5)] = 0; m[(1, 6)] = 3; m[(1, 7)] = 2; m[(1, 8)] = 7; m[(2, 0)] = 2; m[(2, 1)] = 7; m[(2, 2)] = 3; m[(2, 3)] = 6; m[(2, 4)] = 5; m[(2, 5)] = 1; m[(2, 6)] = 4; m[(2, 7)] = 0; m[(2, 8)] = 8; m[(3, 0)] = 3; m[(3, 1)] = 2; m[(3, 2)] = 7; m[(3, 3)] = 1; m[(3, 4)] = 6; m[(3, 5)] = 5; m[(3, 6)] = 8; m[(3, 7)] = 4; m[(3, 8)] = 0; m[(4, 0)] = 4; m[(4, 1)] = 0; m[(4, 2)] = 8; m[(4, 3)] = 2; m[(4, 4)] = 7; m[(4, 5)] = 3; m[(4, 6)] = 6; m[(4, 7)] = 5; m[(4, 8)] = 1; m[(5, 0)] = 5; m[(5, 1)] = 1; m[(5, 2)] = 6; m[(5, 3)] = 0; m[(5, 4)] = 8; m[(5, 5)] = 4; m[(5, 6)] = 7; m[(5, 7)] = 3; m[(5, 8)] = 2; m[(6, 0)] = 6; m[(6, 1)] = 5; m[(6, 2)] = 1; m[(6, 3)] = 4; m[(6, 4)] = 0; m[(6, 5)] = 8; m[(6, 6)] = 2; m[(6, 7)] = 7; m[(6, 8)] = 3; m[(7, 0)] = 7; m[(7, 1)] = 3; m[(7, 2)] = 2; m[(7, 3)] = 5; m[(7, 4)] = 1; m[(7, 5)] = 6; m[(7, 6)] = 0; m[(7, 7)] = 8; m[(7, 8)] = 4; m[(8, 0)] = 8; m[(8, 1)] = 4; m[(8, 2)] = 0; m[(8, 3)] = 3; m[(8, 4)] = 2; m[(8, 5)] = 7; m[(8, 6)] = 1; m[(8, 7)] = 6; m[(8, 8)] = 5;
    c[(0, 0)] = 0; c[(0, 1)] = 1; c[(0, 2)] = 1; c[(0, 3)] = 1; c[(0, 4)] = 1; c[(0, 5)] = 1; c[(0, 6)] = 1; c[(0, 7)] = 1; c[(0, 8)] = 1; c[(1, 0)] = 2; c[(1, 1)] = 3; c[(1, 2)] = 4; c[(1, 3)] = 5; c[(1, 4)] = 6; c[(1, 5)] = 7; c[(1, 6)] = 8; c[(1, 7)] = 9; c[(1, 8)] = 10; c[(2, 0)] = 2; c[(2, 1)] = 4; c[(2, 2)] = 3; c[(2, 3)] = 8; c[(2, 4)] = 10; c[(2, 5)] = 9; c[(2, 6)] = 5; c[(2, 7)] = 7; c[(2, 8)] = 6; c[(3, 0)] = 2; c[(3, 1)] = 8; c[(3, 2)] = 5; c[(3, 3)] = 3; c[(3, 4)] = 9; c[(3, 5)] = 6; c[(3, 6)] = 4; c[(3, 7)] = 10; c[(3, 8)] = 7; c[(4, 0)] = 2; c[(4, 1)] = 7; c[(4, 2)] = 9; c[(4, 3)] = 10; c[(4, 4)] = 3; c[(4, 5)] = 5; c[(4, 6)] = 6; c[(4, 7)] = 8; c[(4, 8)] = 4; c[(5, 0)] = 2; c[(5, 1)] = 6; c[(5, 2)] = 10; c[(5, 3)] = 7; c[(5, 4)] = 8; c[(5, 5)] = 3; c[(5, 6)] = 9; c[(5, 7)] = 4; c[(5, 8)] = 5; c[(6, 0)] = 2; c[(6, 1)] = 5; c[(6, 2)] = 8; c[(6, 3)] = 4; c[(6, 4)] = 7; c[(6, 5)] = 10; c[(6, 6)] = 3; c[(6, 7)] = 6; c[(6, 8)] = 9; c[(7, 0)] = 2; c[(7, 1)] = 10; c[(7, 2)] = 6; c[(7, 3)] = 9; c[(7, 4)] = 5; c[(7, 5)] = 4; c[(7, 6)] = 7; c[(7, 7)] = 3; c[(7, 8)] = 8; c[(8, 0)] = 2; c[(8, 1)] = 9; c[(8, 2)] = 7; c[(8, 3)] = 6; c[(8, 4)] = 4; c[(8, 5)] = 8; c[(8, 6)] = 10; c[(8, 7)] = 5; c[(8, 8)] = 3;
    t = [(0, 0, 0, 0, ), (1, 2, 10, 1, ), (2, 3, 1, 7, ), (3, 5, 7, 2, ), (4, 6, 4, 9, ), (5, 9, 9, 8, ), (6, 7, 2, 6, ), (7, 1, 5, 4, ), (8, 8, 8, 3, ), (9, 4, 3, 10, ), (10, 10, 6, 5, ), ]
    return n, name, m, c, t


MAGMA_DEFS = [magmadef_7_0, magmadef_9_0]


def analyze_fiber(table_vals, K, label=""):
    """
    Analyze a K×K fiber operation table for structural regularity.
    table_vals[x][y] is the integer result in {0,...,K-1}.
    Returns a dict of properties and a summary string.
    """
    props = {}

    # Idempotent: F[x][x] == x for all x
    props["idempotent"] = all(table_vals[x][x] == x for x in range(K))

    # Commutative: F[x][y] == F[y][x]
    props["commutative"] = all(
        table_vals[x][y] == table_vals[y][x] for x in range(K) for y in range(K)
    )

    # Left projection: F[x][y] == x
    props["left_proj"] = all(table_vals[x][y] == x for x in range(K) for y in range(K))

    # Right projection: F[x][y] == y
    props["right_proj"] = all(table_vals[x][y] == y for x in range(K) for y in range(K))

    # Constant: all values equal some c
    flat = [table_vals[x][y] for x in range(K) for y in range(K)]
    props["constant"] = len(set(flat)) == 1
    if props["constant"]:
        props["constant_val"] = flat[0]

    # Affine: F[x][y] == (a*x + b*y + c) % K for some a,b,c in Z/KZ
    best_affine = None
    best_affine_mismatches = K*K + 1
    for a in range(K):
        for b in range(K):
            for c in range(K):
                mismatches = sum(
                    1 for x in range(K) for y in range(K)
                    if (a*x + b*y + c) % K != table_vals[x][y]
                )
                if mismatches < best_affine_mismatches:
                    best_affine_mismatches = mismatches
                    best_affine = (a, b, c)
    props["affine"] = (best_affine_mismatches == 0)
    props["best_affine"] = best_affine
    props["affine_mismatches"] = best_affine_mismatches

    # Near-affine: fraction of cells matching best affine
    props["affine_coverage"] = (K*K - best_affine_mismatches) / (K*K)

    # Latin square: each value appears exactly K times in each row and column
    rows_latin = all(len(set(table_vals[x])) == K for x in range(K))
    cols_latin = all(len(set(table_vals[x][y] for x in range(K))) == K for y in range(K))
    props["latin"] = rows_latin and cols_latin

    # Associative (quick check — only feasible for small K)
    if K <= 4:
        assoc = True
        for x in range(K):
            for y in range(K):
                for z in range(K):
                    if table_vals[table_vals[x][y]][z] != table_vals[x][table_vals[y][z]]:
                        assoc = False
                        break
                if not assoc:
                    break
            if not assoc:
                break
        props["associative"] = assoc
    else:
        props["associative"] = None  # not checked

    # Build summary
    tags = []
    if props["constant"]:
        tags.append(f"const={props.get('constant_val','?')}")
    elif props["left_proj"]:
        tags.append("left-proj")
    elif props["right_proj"]:
        tags.append("right-proj")
    elif props["affine"]:
        a, b, c = props["best_affine"]
        tags.append(f"affine({a}x+{b}y+{c})")
    else:
        a, b, c = props["best_affine"]
        cov = props["affine_coverage"]
        tags.append(f"near-affine({a}x+{b}y+{c},cov={cov:.2f})")

    if props["idempotent"]:
        tags.append("idem")
    if props["commutative"]:
        tags.append("comm")
    if props["latin"]:
        tags.append("latin")
    if props.get("associative"):
        tags.append("assoc")

    summary = f"F[{label}]: " + ", ".join(tags)
    return props, summary


def summarize_fiber_regularity(fiber_props_list, K, num_colors):
    """Print a summary of which structural patterns dominate across all colors."""
    n = num_colors
    affine_count = sum(1 for p in fiber_props_list if p.get("affine"))
    idem_count = sum(1 for p in fiber_props_list if p.get("idempotent"))
    comm_count = sum(1 for p in fiber_props_list if p.get("commutative"))
    latin_count = sum(1 for p in fiber_props_list if p.get("latin"))
    const_count = sum(1 for p in fiber_props_list if p.get("constant"))
    proj_count = sum(1 for p in fiber_props_list if p.get("left_proj") or p.get("right_proj"))
    avg_cov = sum(p.get("affine_coverage", 0) for p in fiber_props_list) / max(n, 1)

    print(f"  --- Fiber regularity summary ({n} colors, K={K}) ---")
    print(f"  Affine:    {affine_count}/{n}")
    print(f"  NearAff:   avg coverage {avg_cov:.3f}")
    print(f"  Idempotent:{idem_count}/{n}")
    print(f"  Commutative:{comm_count}/{n}")
    print(f"  Latin sq:  {latin_count}/{n}")
    print(f"  Constant:  {const_count}/{n}")
    print(f"  Projection:{proj_count}/{n}")
    if affine_count == n:
        print(f"  => ALL fibers are affine (fully affine extension)")
    elif avg_cov >= 0.9:
        print(f"  => Fibers near-affine (>=90% coverage)")
    elif idem_count == n:
        print(f"  => All fibers idempotent, non-affine")
    else:
        print(f"  => Mixed/irregular fiber structure")


def main_nonlinear(K, magmadef, anti255=False):
    """
    Search for E677-satisfying fiber extensions using full function tables.

    Each fiber operation f_i: Z/KZ × Z/KZ → Z/KZ is a K×K table of values,
    rather than being restricted to affine form.

    If anti255=True, additionally require that E255 fails for at least one element.
    """
    N, m_name, m_m, m_c, m_t = magmadef()
    num_colors = len(m_t)

    s = Solver()
    s.set("timeout", 300000)  # 5 minute timeout per K

    # Fiber operations: F[color][x][y] = result in Z/KZ
    F = [[[Int(f"F_{i}_{x}_{y}") for y in range(K)] for x in range(K)] for i in range(num_colors)]

    # Domain constraints: each F[i][x][y] in {0, ..., K-1}
    for i in range(num_colors):
        for x in range(K):
            for y in range(K):
                s.add(F[i][x][y] >= 0, F[i][x][y] < K)

    # E677 constraints:
    # For the product magma M × Z/KZ with operation:
    #   (a, r) ◇ (b, s) = (m[a][b], F[c[a][b]][r][s])
    # E677: x = y ◇ (x ◇ ((y ◇ x) ◇ y))
    # must hold for all (a,r), (b,s).

    # We encode this for all base elements a,b and all fiber values r,s.
    for a in range(N):
        for b in range(N):
            for r in range(K):
                for s2 in range(K):
                    # Compute y ◇ x = (b,s2) ◇ (a,r)
                    yx_base = m_m[(b, a)]
                    yx_color = m_c[(b, a)]
                    yx_fiber = F[yx_color][s2][r]

                    # Compute (y ◇ x) ◇ y
                    yxy_base = m_m[(yx_base, b)]
                    yxy_color = m_c[(yx_base, b)]
                    # yx_fiber is a Z3 expr, need to select from table
                    # yxy_fiber = F[yxy_color][yx_fiber][s2]
                    # This requires If-chains since yx_fiber is symbolic
                    yxy_fiber = F[yxy_color][0][s2]  # placeholder
                    for v in range(K):
                        yxy_fiber = If(yx_fiber == v, F[yxy_color][v][s2], yxy_fiber)

                    # Compute x ◇ ((y ◇ x) ◇ y)
                    xyxy_base = m_m[(a, yxy_base)]
                    xyxy_color = m_c[(a, yxy_base)]
                    xyxy_fiber = F[xyxy_color][0][0]
                    for v in range(K):
                        xyxy_fiber = If(yxy_fiber == v, F[xyxy_color][r][v], xyxy_fiber)

                    # Compute y ◇ (x ◇ ((y ◇ x) ◇ y))
                    final_base = m_m[(b, xyxy_base)]
                    final_color = m_c[(b, xyxy_base)]
                    final_fiber = F[final_color][0][0]
                    for v in range(K):
                        final_fiber = If(xyxy_fiber == v, F[final_color][s2][v], final_fiber)

                    # E677: result must equal x = (a, r)
                    s.add(final_base == a)  # base equation (should be guaranteed by base magma)
                    s.add(final_fiber == r)

    # Anti-E255 constraints (if requested):
    # E255: x = ((x ◇ x) ◇ x) ◇ x for all x
    # We require this to FAIL for at least one element.
    if anti255:
        anti_clauses = []
        for a in range(N):
            for r in range(K):
                # Compute x ◇ x = (a,r) ◇ (a,r)
                xx_base = m_m[(a, a)]
                xx_color = m_c[(a, a)]
                xx_fiber = F[xx_color][r][r]

                # Compute (x ◇ x) ◇ x
                xxx_base = m_m[(xx_base, a)]
                xxx_color = m_c[(xx_base, a)]
                xxx_fiber = F[xxx_color][0][r]
                for v in range(K):
                    xxx_fiber = If(xx_fiber == v, F[xxx_color][v][r], xxx_fiber)

                # Compute ((x ◇ x) ◇ x) ◇ x
                xxxx_base = m_m[(xxx_base, a)]
                xxxx_color = m_c[(xxx_base, a)]
                xxxx_fiber = F[xxxx_color][0][r]
                for v in range(K):
                    xxxx_fiber = If(xxx_fiber == v, F[xxxx_color][v][r], xxxx_fiber)

                # E255 fails for this element if result != x
                anti_clauses.append(Or(xxxx_base != a, xxxx_fiber != r))

        s.add(Or(*anti_clauses))

    print(f"  constraints added, solving...", flush=True)
    result = s.check()

    if result == sat:
        m = s.model()
        print(f"  SOLUTION FOUND! K={K}, base={m_name}")

        # Extract and print fiber tables; collect for analysis
        fiber_tables = []
        fiber_props_list = []
        for i in range(num_colors):
            table_vals = [
                [m.eval(F[i][x][y], model_completion=True).as_long() for y in range(K)]
                for x in range(K)
            ]
            fiber_tables.append(table_vals)
            props, summary = analyze_fiber(table_vals, K, label=str(i))
            fiber_props_list.append(props)
            print(f"  Fiber F[{i}]:  {summary}")
            for x in range(K):
                print(f"    {table_vals[x]}")

        # Build the full magma table from already-extracted fiber_tables
        total_n = N * K
        table = [[0]*total_n for _ in range(total_n)]
        for a in range(N):
            for b in range(N):
                ab_base = m_m[(a, b)]
                ab_color = m_c[(a, b)]
                for r in range(K):
                    for ss in range(K):
                        fval = fiber_tables[ab_color][r][ss]
                        table[a*K+r][b*K+ss] = ab_base*K + fval

        # Verify E677
        def f(xi, yi):
            return table[yi][xi]  # careful: table[row][col] = row ◇ col

        # Actually: table[a][b] = a ◇ b
        def op(xi, yi):
            return table[xi][yi]

        e677_ok = True
        for x in range(total_n):
            for y in range(total_n):
                yx = op(y, x)
                yxy = op(yx, y)
                xyxy = op(x, yxy)
                result = op(y, xyxy)
                if result != x:
                    e677_ok = False
                    print(f"  E677 FAIL: x={x}, y={y}")
                    break
            if not e677_ok:
                break

        e255_ok = True
        e255_fail_elems = []
        for x in range(total_n):
            xx = op(x, x)
            xxx = op(xx, x)
            xxxx = op(xxx, x)
            if xxxx != x:
                e255_ok = False
                e255_fail_elems.append(x)

        print(f"  E677: {'PASS' if e677_ok else 'FAIL'}")
        print(f"  E255: {'PASS' if e255_ok else 'FAIL'}")
        if e255_fail_elems:
            print(f"  E255 fails at elements: {e255_fail_elems}")
            print(f"  *** COUNTEREXAMPLE FOUND! ***")

        # Fiber regularity summary
        summarize_fiber_regularity(fiber_props_list, K, num_colors)

        # Print full table
        print(f"  Full magma table ({total_n}x{total_n}):")
        for i in range(total_n):
            print("  ", " ".join(str(table[i][j]) for j in range(total_n)))

        return True
    elif result == unsat:
        print(f"  UNSAT for K={K}", flush=True)
        return False
    else:
        print(f"  UNKNOWN/TIMEOUT for K={K}", flush=True)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python color-extensions-nonlinear.py <mode> <magma_idx> [max_K]")
        print("  mode: '677' or 'anti255'")
        print("  magma_idx: 0=7/0, 1=9/0")
        sys.exit(1)

    mode = sys.argv[1]
    magma_idx = int(sys.argv[2])
    max_K = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    anti255 = (mode == "anti255")
    magma = MAGMA_DEFS[magma_idx]

    N, m_name, _, _, _ = magma()
    print(f"Mode: {mode}, Base: {m_name}, max_K: {max_K}", flush=True)

    for K in range(2, max_K + 1):
        print(f"K={K} (product size={N*K}):", flush=True)
        found = main_nonlinear(K, magma, anti255=anti255)
        if found and anti255:
            print("COUNTEREXAMPLE FOUND - STOPPING")
            break
