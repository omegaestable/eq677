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

## Enum backend and sweep addendum

The searcher now defaults to an `enum` backend using a finite Z3 enumeration sort instead
of the earlier integer/array encoding.  The older backend remains available with
`--backend array` for comparison.  On the same constraints, the enum backend reduced the
`order=8`, period-four external query from about `488 s` to about `3.3 s`.

The new `sweep` command checks all possible principal periods for a chosen order, splitting
period four into the `r=p` and external branches:

```powershell
& .\.venv\Scripts\python.exe scripts\e677_z3_search.py sweep --backend enum --order 8 --timeout-ms 30000
```

With the enum backend, the exhaustive order `7` sweep finishes in about `1.8 s`, and the
order `8` sweep finishes in about `14.5 s`; every period case is `unsat`.  A separate enum
frontier run has also proved unrestricted order `8` is `unsat`, and both order `9`
period-four branches are `unsat`.

The period-four external branch now has an additional split:

```powershell
--period4-external-cycle two-cycle
--period4-external-cycle third
--period4-external-lx-cycle-size N
--lx-complement-cycles 3,2,1
--fix-cell row:col:value
```

The `third` branch uses the safe relabeling `x*r=6`.  The exact-size option fixes the
length of the external `L_x` cycle containing `t=q*a`; it is backed by the local recurrence
`z*(z^+*x)=z^-` for consecutive `L_x`-cycle points.  At order `9`, both external cycle
branches are `unsat`; the exact external sizes `3`, `4`, and `5` are also `unsat`.
The complement-cycle option fixes the cycle partition of `L_x` outside the principal
witness orbit; for example, in order `10`, period `5`, the partitions of the remaining
five labels are `5`, `4,1`, `3,2`, `3,1,1`, `2,2,1`, `2,1,1,1`, and `1,1,1,1,1`.
The fixed-cell option is a generic branch splitter for hard residual cases, such as
splitting a period-four `r=p` branch by the possible values of `p*x`.  The comma form
`row,col,value` is accepted too, but it should be quoted in PowerShell.
Periods `5`, `6`, `7`, `8`, and `9` are `unsat` in the enum frontier run.

The order `10` period-four branch is now closed.  The external side closes because the
broad two-cycle case is `unsat`, the broad third-point case timed out, and the exact
external cycle sizes `3`, `4`, `5`, and `6` are all `unsat`.  The `r=p` side closes after
splitting the six-point complement cycle partition: all partitions are `unsat` except
`4,2` at the first timeout, and that residual is `unsat` for every possible value of
`p*x`.  The active order `10` frontier is now period `5` and period `6`; both broad cases
timed out once at `900 s`.  In period `5`, complement partitions `3,1,1`, `2,2,1`,
`2,1,1,1`, and `1,1,1,1,1` are `unsat`; the larger partitions `5`, `4,1`, and `3,2`
timed out at `300 s` and are being split by `g=q*x`.  Current period-five split progress:
complement `5` has `g=0,1,2,3,4` `unsat`, with `g=4` closed after splitting the lone
`a*q=8` residual by all ten `g*q` values; `g=5` is down to `a*q=7,8,9` after
`a*q=2,5,6` closed by `g*q`, and `g=6` has `a*q=2,5,7,8,9` residuals;
complement `4,1` has every `g` value except `g=7` `unsat`, with `g=7` under an `a*q`
split and only `a*q=5,8` residuals remaining; complement `3,2` has `g=0,1,2,3,4`
`unsat` after closing `g=4` by `a*q`, with residuals `g=5/a*q=4,6`,
`g=6/a*q=7,8`, and `g=7/a*q=2,5,7`.
Period `6` complement partitions `2,1,1` and `1,1,1,1` are `unsat`; partition `3,1`
is closed because all ten `q*x` values are `unsat`; partitions `4` and `2,2` remain open
only in timed-out `q*x` residuals.  Partition `4`, `q*x=4` is closed after the lone
`a*q=2` residual split by all ten `g*q` values; `q*x=5,6,7,8,9` are now split by `a*q`.
Partition `2,2`, `q*x=2` is closed by all ten `a*q` values; only parent `q*x=6` remains
as an `a*q` split.
The broad order `10` run also closed periods `8` and `9` as `unsat` in about `701 s` and
`458 s`, respectively; periods `5`, `6`, and `7` timed out in that broad run and need the
focused splits above.

Two additional ground packages were added after this split.  In period-four `r=p`, the
searcher now records `p*x=(q*q)*q=a*(q*q)`.  In period five, with
`x=c0,a=c1,b=c2,q=c3,p=c4,g=q*x`, it records
`g=a*((b*a)*b)`, `q*((a*q)*a)=x`, `(a*q)*a=x*(g*q)`, and `g notin {x,b}`.
In period six, with `x=c0,a=c1,b=c2,c=c3,q=c4,p=c5,h=c*x,g=q*x`, it records
`h=a*((b*a)*b)`, `g=b*((c*b)*c)`, `q*((a*q)*a)=x`, `(a*q)*a=x*(g*q)`, and `g!=x`.