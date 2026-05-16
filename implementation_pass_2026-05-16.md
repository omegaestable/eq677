# Implementation pass, 2026-05-16

## Outcome

Added `scripts/e677_z3_search.py`, a proof-directed Z3 harness for finite `E677`
counterexample probes. It encodes a finite operation table, left-translation
permutations, the full `E677` law, a chosen bad witness for `E255`, optional principal
`L_x`-orbit period constraints, and the period-four gate branches `r=p` and `external`.

The tool also verifies extracted tables independently and prints the local diagnostics
used in the dossier: `a=x*x`, `q=(x*x)*x`, `p=x\x`, `r=q*x`, `h=(q*x)*q`, the principal
`L_x`-orbit, `H_x`/`F_x` cycle decompositions, and right-collision splitter rectangles.

## Usage

Run with the repository virtualenv:

```powershell
& .\.venv\Scripts\python.exe scripts\e677_z3_search.py calibrate-linear --prime 5 --alpha 2 --beta -1 --const 0
& .\.venv\Scripts\python.exe scripts\e677_z3_search.py search --order 5 --timeout-ms 30000
& .\.venv\Scripts\python.exe scripts\e677_z3_search.py search --order 6 --period 4 --branch 'r=p' --timeout-ms 30000
& .\.venv\Scripts\python.exe scripts\e677_z3_search.py search --order 6 --period 4 --branch external --timeout-ms 30000
```

By default, search constraints include left-row permutation constraints and injective row
labels. These are trusted consequences in the finite `E677` setting and can be disabled
with `--no-left-permutations` or `--no-label-injective` for debugging the encoding.
Trusted orbit recurrence facts are added when `--period` is supplied; disable them with
`--no-orbit-facts` to isolate the raw law encoding.

## Initial probes

All probes below used the default trusted constraints and a 30 second Z3 timeout.

| Query | Result |
| --- | --- |
| Calibrate `F_5`, `u*v=2u-v` | Verified `E677`; no `E255` failures; nontrivial `H_x` cycle observed |
| `order=4` bad witness | `unsat` |
| `order=4`, period `4`, branch `r=p` | `unsat` |
| `order=5` bad witness | `unsat` |
| `order=5`, period `4`, branch `r=p` | `unsat` |
| `order=5`, period `4`, branch `external` | `unsat` |
| `order=6`, period `4`, branch `r=p` | `unsat` |
| `order=6`, period `4`, branch `external` | `unsat` |
| `order=6`, period `5` | `unsat` |
| `order=6` bad witness, no period fixed | `unknown` at 30 seconds |

These are finite search facts, not a proof of the period-four gate in arbitrary carrier
size. The useful implementation advance is that period-specific branches are now cheap
enough to test and to serve as regression checks for stronger local lemmas.

## Audit

The search does not assume associativity, identity elements, right cancellation, the
retired quotient family, the retired full-shift law, or direct collision propagation.
Every operation value is table-based and fully non-associative. The added pruning
constraints are either direct finite table requirements or trusted consequences recorded
in the dossier.

## Next lemma / next implementation

Add tracked constraint groups for the period-four branch facts and transformed/key
identity instances, so an `unsat` result can be minimized into a readable local skeleton.
This is the best next step toward turning small-order UNSAT pressure into a proof-grade
period-four argument.

## Optimization addendum

The later math/search pass in `math_search_pass_2026-05-16.md` added default pruning
from the bad-witness normal form, transformed/key identities, global right-fiber splitter
injectivity, first-orbit symmetry breaking, and a period-four external symmetry break.
With these constraints the previously inconclusive unrestricted `order=6` bad-witness
search now returns `unsat` in about `13.5 s` on this machine.

The period-four external branch at `order=7` changed from timeout to `unsat` once the
forced external points `r=q*x` and `t=q*a` were relabeled as `4` and `5`.  A longer run
also proved `order=7`, period `5` is `unsat` in about `96 s`.  The active computational
frontier has moved to order `8` constrained periods and to extracting a proof-readable
skeleton from the period-four external normal form.

The searcher now supports group-level contradiction inspection:

```powershell
& .\.venv\Scripts\python.exe scripts\e677_z3_search.py search --order 7 --period 4 --branch external --track-groups --minimize-core
```

The minimizer uses a bounded per-check timeout controlled by `--core-check-timeout-ms`.
At the group level, the order `7` period-four external contradiction still needs the
fixed-point-free map constraints, the global splitter, derived identities, orbit facts,
and the period-four external normal form, but it does not need the separate label
injectivity or summary bad-witness/collision groups.