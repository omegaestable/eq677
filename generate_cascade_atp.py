#!/usr/bin/env python3
"""
generate_cascade_atp.py
=======================
Generate Prover9-format (.in) files for the cascade-gap refutation, one per
collision pair (d_i = d_j).

For orbit period d=7, there are C(7,2) = 21 collision pairs.
Each file hypothesises d_i = d_j and asks Prover9 to derive FALSE
from E677 + left-cancel + L1 + L2b + orbit structure + collision.

Usage:
    python generate_cascade_atp.py [d]

    d = orbit period (default 7, the smallest interesting case)

Outputs files:  atp/cascade-d{d}-{i}-{j}.in   for all 0 <= i < j < d.
"""

import os
import sys
from itertools import combinations

PROVER9 = r'"C:\Program Files (x86)\Prover9-Mace4\bin-win32\prover9.exe"'
MACE4   = r'"C:\Program Files (x86)\Prover9-Mace4\bin-win32\mace4.exe"'


def generate_prover9_file(d, i, j):
    """Generate Prover9 input for orbit period d with collision d_i = d_j."""
    C = [f"c{k}" for k in range(d)]
    D = [f"d{k}" for k in range(d)]

    lines = []
    lines.append(f"% Auto-generated cascade-gap refutation for orbit period d={d}.")
    lines.append(f"% Collision: d_{i} = d_{j}.")
    lines.append(f"% Target: derive contradiction from E677 + left-cancel + L1 + L2b + collision.")
    lines.append("")
    lines.append("set(prolog_style_variables).")
    lines.append("")
    lines.append("formulas(assumptions).")
    lines.append("")

    # E677
    lines.append("% E677 (two equivalent forms).")
    lines.append("X = f(Y, f(X, f(f(Y, X), Y))).")
    lines.append("X = f(f(Y, X), f(f(Y, f(Y, X)), Y)).")
    lines.append("")

    # Left-cancel
    lines.append("% Left-cancellativity via left-inverse function g.")
    lines.append("g(X, f(X, Y)) = Y.")
    lines.append("")

    # Orbit
    lines.append(f"% Orbit of element a, period {d}.")
    lines.append("c0 = a.")
    for k in range(d - 1):
        lines.append(f"f(a, {C[k]}) = {C[k+1]}.")
    lines.append(f"f(a, {C[d-1]}) = a.")
    lines.append("")

    # Distinctness
    lines.append("% All orbit elements are distinct.")
    for ci, cj in combinations(range(d), 2):
        lines.append(f"{C[ci]} != {C[cj]}.")
    lines.append("")

    # d-sequence
    lines.append("% d-sequence: d_k = f(c_k, a).")
    for k in range(d):
        lines.append(f"f({C[k]}, a) = {D[k]}.")
    lines.append("")

    # L1 instances
    lines.append("% L1 recurrence: c_{k-1} = f(c_k, d_{k+1})  [mod d].")
    for k in range(d):
        km1 = (k - 1) % d
        kp1 = (k + 1) % d
        c_km1 = C[km1]
        lines.append(f"f({C[k]}, {D[kp1]}) = {c_km1}.")
    lines.append("")

    # L2b anchor (d >= 5)
    if d >= 5:
        anchor_idx = d - 2
        lines.append(f"% L2b anchor: d_{{d-2}} = a, i.e., d{anchor_idx} = a.")
        lines.append(f"{D[anchor_idx]} = a.")
        lines.append("")

    # Squaring identity (d >= 5)
    if d >= 5:
        sq_lhs = C[d - 4]
        sq_rhs = C[d - 5]
        lines.append(f"% Squaring identity: f(c{{d-4}}, c{{d-4}}) = c{{d-5}}.")
        lines.append(f"f({sq_lhs}, {sq_lhs}) = {sq_rhs}.")
        lines.append("")

    # Collision
    lines.append(f"% COLLISION: d_{i} = d_{j}.")
    lines.append(f"{D[i]} = {D[j]}.")
    lines.append("")
    lines.append("end_of_list.")
    lines.append("")
    lines.append("% No goals — prover should derive contradiction from assumptions.")

    return "\n".join(lines) + "\n"


def main():
    d = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    outdir = os.path.join(os.path.dirname(__file__), "atp")
    os.makedirs(outdir, exist_ok=True)

    generated = []
    for i, j in combinations(range(d), 2):
        content = generate_prover9_file(d, i, j)
        fname = os.path.join(outdir, f"cascade-d{d}-{i}-{j}.in")
        with open(fname, "w") as fh:
            fh.write(content)
        generated.append(fname)

    print(f"Generated {len(generated)} Prover9 cascade-gap files for d={d}:")
    for f in generated:
        print(f"  {os.path.basename(f)}")
    print()
    print("Run with Prover9:")
    print(f"  {PROVER9} -f atp\\cascade-d{d}-0-1.in")
    print()
    print("Run all 21 in sequence (PowerShell):")
    print(f'  Get-ChildItem atp\\cascade-d{d}-*.in | ForEach-Object {{ {PROVER9} -f $_.FullName }}')
    print()
    print("Run Mace4 countermodel search (if Prover9 times out):")
    print(f"  {MACE4} -n 12 -f atp\\cascade-d{d}-0-1.in")
    print()
    print(f"If ALL {len(generated)} files are refuted, d-injectivity holds for d={d}.")


if __name__ == "__main__":
    main()
