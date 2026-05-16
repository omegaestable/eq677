# Math/search pass, 2026-05-16

## Outcome

This pass strengthened the counterexample searcher by turning the current proof dossier
into default solver constraints.  The main point is that a bad witness is not merely an
element failing `E255`; it carries a rigid local signature.  Encoding that signature makes
the unrestricted order `6` bad-witness query change from timeout/`unknown` to `unsat` in
about 13 seconds on this machine.

No finite counterexample was found.  The useful advance is a sharper normal form for any
future counterexample and a faster regression harness for candidate lemmas.

## Lemma 1: bad-witness normal form

Let `M` be a finite `E677` magma and let `x` be a point where `E255` fails.  Write

```text
a = x*x,
q = a*x,
p = x\x = x*q,
r = q*x,
h = r*q.
```

Then all of the following are safe pruning constraints:

```text
q*x != x,
u*x != x                     for every u,
{x, x*x, x*(x*x), x*(x*(x*x))} has four distinct elements,
H_x(t)=((x*t)*x) has no fixed point,
F_x(t)=x*(t*x) has no fixed point,
h != p,
((x*x)*q)*(x*x) != x,
x*h != x.
```

### Argument

The first line is exactly failure of `E255` at `x`, since `q=(x*x)*x`.  If some `u`
satisfied `u*x=x`, the unique fixed-point witness lemma would force `u=q`, giving
`q*x=x`, contradiction.  Thus the whole right column over `x` misses `x`.

The first four `L_x` orbit points are distinct because a bad point has principal orbit
period at least `4`: period `1` gives `E255` directly, while periods `2` and `3` are
excluded in the dossier.

The fixed-map lemma says `E255` at `x` is equivalent to the existence of a fixed point of
either `H_x(t)=((x*t)*x)` or `F_x(t)=x*(t*x)`.  Hence both maps are fixed-point-free at a
bad point.

The remaining three inequalities are the known equivalent fixed-point targets written as
failures: `(q*x)*q=p`, `((x*x)*q)*(x*x)=x`, and `q\x=x`.  Since
`q\x=x*((q*x)*q)=x*h`, the last target fails as `x*h != x`.

## Lemma 2: global right-fiber splitter

For any `z`, if two distinct elements collide in the right column over `z`,

```text
y*z = w*z = e,    y != w,
```

then their second-probe splitter values are distinct:

```text
y*e != w*e.
```

### Argument

The transformed identity gives

```text
z = e*((y*e)*y) = e*((w*e)*w).
```

Left cancellation by `e` gives `(y*e)*y = (w*e)*w`.  If also `y*e=w*e=s`, then
`s*y=s*w`, and left cancellation by `s` gives `y=w`, contradiction.  This is the
right-collision rectangle upgraded from the witness column to every right column.

## Lemma 3: first-orbit symmetry break

Any finite counterexample can be relabeled so that a failing witness is `0` and

```text
0*0 = 1,
0*1 = 2,
0*2 = 3.
```

### Argument

By Lemma 1 the first four points in the principal `L_x` orbit of a bad witness are
distinct.  Relabel those four points as `0,1,2,3` and extend arbitrarily to the remaining
carrier.  This loses no counterexamples up to isomorphism and gives the solver a much
smaller search space before any period is fixed.

## Lemma 4: period-four external normal form

Assume the bad witness has principal period `4`.  Write

```text
x=c_0,  a=c_1=x*x,  q=c_2,  p=c_3=x\x,  r=q*x,
s=p*x,  h=r*q,  t=q*a,  u=x*r.
```

In every period-four branch one has

```text
q*s = a,
(p*q)*p = s,
a*h = r.
```

In the external branch `r notin {x,a,q,p}` one also has

```text
x*t = r,
t notin {x,a,q,p,r},
u notin {x,a,q,p,r}.
```

There is also a reusable local `L_x`-cycle recurrence.  If
`z^- -> z -> z^+` are consecutive points under `L_x`, then

```text
z*(z^+*x)=z^-.
```

Hence on the external component `t -> r -> u -> ...`, with `v=x*u`,

```text
r*(u*x)=t,
u*(v*x)=r.
```

Consequently a period-four external counterexample can be relabeled so that

```text
x=0, a=1, q=2, p=3, r=4, t=5.
```

It then splits into `u=t`, where the external `L_x` component contains the two-cycle
`t -> r -> t`, or a third-point branch `u notin {x,a,q,p,r,t}`, where one may relabel
`u=6`.

### Argument

The identity `q*s=a` is the orbit recurrence at `k=2`, because `s=d_3=p*x`.  The key
identity with `y=x,z=q` gives

```text
(x*(x*q))*x = q*(((x*q)*q)*(x*q)).
```

Using `x*q=p` and `x*p=x`, this becomes `a=q*((p*q)*p)`.  Since the orbit recurrence
also gives `a=q*s`, left cancellation by `q` gives `(p*q)*p=s`.

For `a*h=r`, apply `E677` with law variable `r` and parameter `a`:

```text
r = a*(r*((a*r)*a)) = a*(r*(x*a)) = a*(r*q) = a*h.
```

In the external branch, the transformed identity with `y=a,z=r` gives

```text
r=(a*r)*((a*(a*r))*a)=x*((a*x)*a)=x*(q*a)=x*t.
```

Since the row `L_x` sends the principal orbit `{x,a,q,p}` back into itself, `t` cannot be
principal.  Since `L_q` is injective and `q*x=r`, the equality `t=q*a` cannot be `r`
unless `a=x`.  Thus `t` is a second external point, distinct from `r`.  Relabeling the
external points puts `r=4` and `t=5` without losing counterexamples.

The same row-injectivity argument gives `u=x*r notin {x,a,q,p,r}`: it cannot be
principal because `L_x` maps the principal orbit to itself, and it cannot be `r` because
`x*t=r` with `t!=r`.  Thus either `u=t` or `u` is a third external point, which can be
relabeled as `6` in that branch.

## Implementation changes

The searcher now adds the following default constraint families:

```text
transformed identity:        z=(y*z)*((y*(y*z))*y)
key identity:                (y*(y*z))*y=z*(((y*z)*z)*(y*z))
bad-witness normal form:     Lemma 1
right-fiber splitter:        Lemma 2
first-orbit symmetry break:  Lemma 3, when witness=0 and no period is fixed
period-four external break:  Lemma 4, when branch=external
external cycle split:        optional `x*r=t` versus third-point branch `x*r=6`
external L_x cycle size:     optional exact size of the cycle containing `t=q*a`
L_x complement cycles:       optional exact cycle partition outside the principal orbit
fixed cells:                optional row*col=value branch splits for stubborn cases
enum finite-sort backend:    avoids integer/array search overhead
```

Each family can be disabled for debugging:

```powershell
--no-derived-identities
--no-bad-point-lemmas
--no-collision-splitter
--no-symmetry-break-bad-orbit
--no-symmetry-break-period4-external
--period4-external-cycle two-cycle
--period4-external-cycle third
--period4-external-lx-cycle-size N
--lx-complement-cycles 3,2,1
--fix-cell row:col:value
```

The comma form `row,col,value` is also accepted, but quote it in PowerShell.

The command `--show-constraint-counts` prints the active constraint groups.
The command `sweep --order N` checks all witness periods `4..N`, splitting period four
into the `r=p` and external branches.

## Benchmarks and probes

All timings are approximate wall-clock timings on the current machine with a `30000 ms`
Z3 timeout.

| Query | Result / timing |
| --- | --- |
| `order=6`, optimized defaults | `unsat`, about `13.5 s` |
| `order=6`, no derived identities | about `25.8 s` |
| `order=6`, no bad-point lemmas | timeout boundary, about `30.2 s` |
| `order=6`, no splitter constraints | about `24.1 s` |
| `order=7`, period `4`, branch `r=p` | `unsat` |
| `order=7`, period `4`, branch `external`, before Lemma 4 symmetry | `unsat`, about `232 s` in long run |
| `order=7`, period `4`, branch `external`, after Lemma 4 symmetry | `unsat`, about `17 s` |
| `order=7`, period `5` | `unsat`, about `96 s` in long run |
| `order=7`, period `6` | `unsat` |
| `order=7`, exhaustive enum sweep | all periods `unsat`, about `1.8 s` |
| `order=8`, exhaustive enum sweep | all periods `unsat`, about `14.5 s` |
| `order=8`, unrestricted enum search | `unsat`, about `35 s` |
| `order=9`, period `4`, branch `external` | `unsat`, about `26.5 s` |
| `order=9`, period `4`, branch `r=p` | `unsat`, about `34.7 s` |
| `order=9`, period `4`, external two-cycle branch | `unsat` |
| `order=9`, period `4`, external third-point branch | `unsat` |
| `order=9`, period `4`, external exact sizes `3`, `4`, `5` | all `unsat` |
| `order=9`, period `5` | `unsat`, about `149 s` |
| `order=9`, period `6` | `unsat`, about `42 s` |
| `order=9`, period `7` | `unsat`, about `18 s` |
| `order=9`, period `8` | `unsat`, about `8 s` |
| `order=10`, period `4`, external two-cycle branch | `unsat`, about `812 s` |
| `order=10`, period `4`, broad external third-point branch | timeout at `900 s` |
| `order=10`, period `4`, external exact sizes `3`, `4`, `5`, `6` | all `unsat`; closes external branch |
| `order=10`, period `4`, branch `r=p`, complement partitions except `4,2` | all `unsat` |
| `order=10`, period `4`, branch `r=p`, complement `4,2`, split by `p*x` | all ten values `unsat`; closes `r=p` |
| `order=10`, period `5` | timeout at `900 s`; complement partition split active |
| `order=10`, period `6` | timeout at `900 s`; complement partition split active |
| `order=10`, period `7` | timeout at `900 s` in the broad run |
| `order=10`, period `8` | `unsat`, about `701 s` in the broad run |
| `order=10`, period `9` | `unsat`, about `458 s` in the broad run |
| `order=10`, period `5`, complement `3,1,1`, `2,2,1`, `2,1,1,1`, `1,1,1,1,1` | all `unsat` |
| `order=10`, period `5`, complement `5`, `4,1`, `3,2` | timeout at `300 s`; split by `g=q*x` active |
| `order=10`, period `5`, complement `5`, `g=0,1,2,3,4` | all `unsat`; `g=4` closed after the lone `a*q=8` residual split by all ten `g*q` values; `g=5` now has only `a*q=7,8,9` residuals after `a*q=2,5,6` closed by `g*q`; `g=6` now has only `a*q=5,7,8,9` residuals after `a*q=2` closed by `g*q`; `g=7,8,9` timed out in the parent |
| `order=10`, period `5`, complement `4,1`, `g=0,1,2,3,4,5,6,8,9` | all `unsat`; `g=7` has only `a*q=5,8` residuals, now split by `g*q` |
| `order=10`, period `5`, complement `3,2`, `g=0,1,2,3,4` | all `unsat`, with `g=4` closed by the `a*q` split; `g=5` has only `a*q=4,6` residuals; `g=6` has only `a*q=7,8` residuals; `g=7` has only `a*q=2,5,7` residuals; `g=8,9` timed out in the parent |
| `order=10`, period `6`, complement `2,1,1` and `1,1,1,1` | both `unsat` |
| `order=10`, period `6`, complement `3,1`, split by `q*x` | all ten values `unsat`; closes this partition |
| `order=10`, period `6`, complement `4`, split by `q*x` | `q*x=0,1,2,3` `unsat`; `q*x=4` closed after `a*q=2` was split by all ten `g*q` values; `q*x=5,6,7,8,9` timed out in the parent and are split by `a*q` |
| `order=10`, period `6`, complement `2,2`, split by `q*x` | `q*x=0,1,3,4,5,7,8,9` `unsat`; `q*x=2` closed by all ten `a*q` values; `q*x=6` timed out in the parent and is split by `a*q` |

The ablation says the mathematical bad-point constraints are currently the biggest win,
and the transformed/key identities plus splitter constraints are both material.

For the `order=7`, period-four external contradiction, bounded group-core minimization
keeps these families:

```text
domain, left row permutations, E677, transformed identity, key identity,
bad column misses x, H_x/F_x fixed-point-free, equivalent target failures,
right-fiber splitter, period orbit, orbit facts, period-four gate,
period-four derived facts, external branch facts, external symmetry break.
```

It drops the separate label-injectivity group and the summary bad-witness/collision
groups.  This is not yet a line-by-line proof, but it says the external contradiction is
not coming from the label-injectivity shortcut; it is coming from the local fixed-map and
splitter geometry.

## Research interpretation

The period-four branch now looks strongly local on both sides.  Both `r=p` and the
external branch are `unsat` through carrier size `9`, and order `10` period four is also
closed.  The external branch closes by splitting the external `L_x` cycle containing
`t=q*a`: size `2` is the old two-cycle case, and exact sizes `3`, `4`, `5`, and `6` are
all `unsat`.  The `r=p` branch closes by splitting the six-point complement cycle
partition; all partitions are `unsat` except `4,2` at the first timeout, and the `4,2`
residual is closed by the ten possible values of `p*x`.

In the period-four `r=p` branch the simplified hand identities

```text
q*a=q,
p*x=(q*q)*q=a*(q*q)
```

are now explicit solver constraints.  For period five, with
`x=c0`, `a=c1`, `b=c2`, `q=c3`, `p=c4`, and `g=q*x`, the searcher also records

```text
g = a*((b*a)*b),
q*((a*q)*a)=x,
(a*q)*a=x*(g*q),
g notin {x,b}.
```

Core mining suggests the period-five principal splits have different character.  On the
smaller order `9` proxy, the `g=a` split has a compact core using only left rows, `E677`,
transformed/key identities, the bad-column miss, the fixed cell, and the orbit/complement
cycle facts.  The `g=q` split pulls in the fixed-map failures, right-fiber splitter, and
the period-five derived identities.  This points to `g=a` as an orbit-local proof target
and `g=q` as a finite splitter/fixed-map target.

For period `5`, the order `7` case is now `unsat` but needed a longer run.  The next
mathematical search target is to add cycle-structure constraints for the fixed-point-free
maps `H_x` and `F_x`, or to derive one non-tautological finite-map identity involving
`H_x`, `F_x`, `R_x`, `L_x`, `S`, or the gate map `t -> (t*x)*t`.

For period six, with `x=c0`, `a=c1`, `b=c2`, `c=c3`, `q=c4`, `p=c5`, `h=c*x`, and
`g=q*x`, the searcher now records the analogous first identities

```text
h = a*((b*a)*b),
g = b*((c*b)*c),
q*((a*q)*a)=x,
(a*q)*a=x*(g*q),
g != x.
```

This was added after the first broad period-six split, so active second-level period-six
residuals using `a*q` are the first runs with this extra pruning.

## Next lemma

Period-four external third-point lemma:

```text
Assume d=4, a=x*x, q=c_2, p=x\x, r=q*x, and r notin {x,a,q,p}.
Set t=q*a.  We have r,t outside the principal orbit and r!=t.  Prove that no third
external point can consistently absorb h=r*q, p*x, r*x, and t*x while preserving the
right-fiber splitter rectangles.
```

This would move the period-four external branch from finite search pressure toward an
actual orbit-counting contradiction.

## Rejected shortcut

Do not use `p*a=r` in period four.  The trusted period-four gate gives `p*a=q`.  The
nearby true identities are `q*(p*x)=a` and `(p*q)*p=p*x`.  The false `p*a=r` comes from
mixing up the recurrence indices and should be treated like the retired quotient-family
slip.