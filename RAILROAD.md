# E677 ->fin E255 Cold-Start Hints

This is the handoff for the next agent. The repo is a mathematical proof dossier: a
compact set of identities, hints, guardrails, and trial routes for attacking the finite
implication. Start from `literature.tex`; use this file as the short operating protocol.

## Solver Stance

- Target: decide whether every finite magma satisfying `E677` satisfies `E255`.
- Historical route pass: `route_pass_2026-05-14.md` adds the fixed-point gate `h=(q*x)*q`, the key identity `(y*(y*z))*y=z*(((y*z)*z)*(y*z))`, the fixed-map form `x\t=t*((x*t)*x)`, and downgrades the raw collision-lift route to a counting-only route.
- Newest proof audit: `literature.tex` now excludes principal `L_x`-orbit period `3` and records a period-four gate; use the period-four target before returning to broader fixed-map dynamics.
- Work as if the proof is local and reachable: start from the trusted package and try to close one named gate. Use public metadata only for labels and source cross-checks.
- The unrestricted case is calibration: a finite proof should visibly use finiteness.
- Computation posture: keep computation proof-directed. Source lookup and document compilation are always fine; broader searches should wait for a new structural lemma that makes them informative.

## Notation

Use `*` for the magma operation.

- `E677`: `x = y * (x * ((y * x) * y))`.
- `E255`: `x = ((x * x) * x) * x`.
- `L_y(z)=y*z`, `R_y(z)=z*y`, `S(x)=x*x`.
- Fix `x`; set `c_0=x`, `c_{k+1}=x*c_k`.
- Let `d` be the minimal `L_x`-orbit period of `x`, so `c_d=x`.
- Set `d_k=c_k*x`.
- Use `a\b` for the unique `u` with `a*u=b`.

## Trusted Package

These may be used, but cite or rederive them when writing a proof.

- In a finite `E677` magma, each `L_y` is bijective; left cancellation and left division are valid.
- `y\x = x*((y*x)*y)`.
- Transformed identity:
  \[
  z=(y*z)*((y*(y*z))*y).
  \]
- Key identity:
  \[
  (y*(y*z))*y=z*(((y*z)*z)*(y*z)).
  \]
- Orbit recurrence:
  \[
  c_{k-1}=c_k*d_{k+1}.
  \]
- `d_1=c_{d-2}`.
- If `d_j=x`, then `j=d-2 mod d`.
- With `p=x\x=c_{d-1}`:
  `x\c_k=c_{k-1}`, `c_k\c_{k-1}=d_{k+1}`, `x\p=d_1`, `p\d_1=c_1`, and `p*c_1=d_1`.
- ETP fixed-point equivalence: `E255` at `x` is equivalent to existence of `u` with `u*x=x`.
- Fixed-map form: with `H_x(t)=(x*t)*x`, `x\t=t*H_x(t)`.  `H_x` is conjugate via `L_x` to `F_x(t)=x*(t*x)`, and `E255` at `x` is equivalent to either map having a fixed point.  Such a fixed point is unique: for `F_x` it is `x\q`, and for `H_x` it is `x\(x\q)`.
- The `L_x`-orbit period is never `2` or `3`; a point where the target has not yet been established has period at least `4`.
- If the `L_x`-orbit of `x` has period `4`, then with `a=c_1=x*x`, `q=c_2`, `p=c_3=x\x`, and `r=q*x`, one has `x*a=q`, `a*x=q`, and `r notin {x,a,q}`. Thus a period-four proof only has to eliminate `r=p` or `r` outside the principal orbit.

## Current Proof Targets

### Single Gap Summary

For fixed `x`, set `a=x*x`, `q=a*x`, and `p=x\x`.  The local target is any one of

```text
q*x=x,
((x*x)*((x*x)*x))*(x*x)=x,
(q*x)*q=p.
```

Under the contrary assumption `q*x != x`, finiteness gives a right-collision fiber

```text
F_r={t:t*x=r},    A_r(t)=t*r,
```

with at least two elements.  The identities prove only

```text
(t*r)*t=r\x for t in F_r,
A_r is injective on F_r.
```

The next useful lemma is: turn this injective splitter into a finite contradiction, a
fixed point, or Lemma L.  Treat injectivity of `A_r` as structure to exploit, not as a
contradiction by itself.

### 0. Period-Four Orbit Gate

The newest proof progress is local to the principal `L_x`-orbit.  Periods `2` and `3`
are impossible.  If a proof can also eliminate the two period-four gate cases, then every
point where the target has not yet been established must have principal orbit period at
least `5`.

For `d=4`, write

```text
a=c_1=x*x,  q=c_2,  p=c_3=x\x,  r=q*x.
```

The trusted period-four data are

```text
x*a=q,   a*x=q,   a*r=x,   x*q=p,   p*a=q,   r notin {x,a,q}.
```

Additional safe bookkeeping: with `s=p*x`, `h=r*q`, and `t=q*a`, one has

```text
q*s=a,   (p*q)*p=s,   a*h=r.
```

In the external branch `r notin {x,a,q,p}` one also has

```text
x*t=r,   t notin {x,a,q,p,r}.
```

So an external period-four counterexample has at least two non-principal elements, `r`
and `t=q*a`.  This supports the sound search symmetry break `r=4`, `t=5` after the
principal orbit is labeled `x=0,a=1,q=2,p=3`.

The immediate proof target is therefore:

```text
If d=4, rule out r=p and rule out r outside {x,a,q,p}.
```

The `r=a` and `r=q` exclusions use the key identity, not quotient-family reasoning.

### 1. Unique Fixed-Point Witness

Let
`a=x*x`, `p=x\x`, and `q=x\p=a*x=d_1=c_{d-2}`.

If `u*x=x`, then necessarily `u=q`. Proof: transformed E677 with `y=u,z=x` gives `x=x*(x*u)`, while E677 with both variables `x` gives `x=x*(x*q)`; two left cancellations give `u=q`.

So the fixed-point route is exactly:

```text
q*x = x.
```

Equivalent sharp targets:

- `q\x=x`;
- `((x*x)*((x*x)*x))*(x*x)=x`;
- `(q*x)*q=p`.

Use these as equivalent targets for the same local gate.

### 2. Collision Lift / Counting Only

If `d_i=d_j=e`, transformed E677 with `y=c_k,z=x` gives

```text
(c_i*e)*c_i = (c_j*e)*c_j.
```

If `i != j`, then also `c_i*e != c_j*e`; otherwise left cancellation collapses `c_i=c_j`.

The old direct-propagation target was:

```text
d_i=d_j  =>  either q*x=x already, or c_i*e=c_j*e.
```

This would rule out nontrivial collisions through the displayed lifted equality, but the 2026-05-14 audit redirects the route toward counting: every right fiber has an injective splitter.  For fixed `x` and `e`, if

```text
F_e={y:y*x=e},  A_e(y)=y*e,
```

then `(y*e)*y=e\x` for all `y in F_e`, and `A_e` is injective on `F_e`.  Thus a genuine collision already forces `c_i*e != c_j*e`.  The useful version of the collision route is to find a finite counting restriction on the possible splitter values, or to produce the fixed point at the same time.

### 3. Right-Collision Rectangles And Construction Hints

Under the contrary assumption `q*x != x`, no `u*x=x`. Hence `R_x` is not surjective, so by finiteness it is not injective. Thus there are `y != z` and `r != x` with

```text
y*x = z*x = r.
```

For every `y` in the fiber `R_x^{-1}(r)`, transformed E677 gives

```text
(y*r)*y = r\x.
```

Distinct collided elements must split under the second probe `t -> t*r`: if also `y*r=z*r`, left cancellation forces `y=z`.

Keep construction work proof-directed. The following notes are useful if a structural
construction or structural constraint is attempted; any such attempt has to use:

- labeled-permutation sections `a*b=sigma(a)(b)`, where all `sigma(a)` are permutations, the label map `a -> sigma(a)` is injective, and `sigma(y)sigma(x)sigma(sigma(y)x)(y)=x`;
- genuinely nonlinear fiber extensions over positive `E677` bases.

Both must explicitly build the right-collision rectangles above while preserving left bijectivity.

## Proof Guardrails

A proof note should explicitly justify, rather than assume:

- right cancellation;
- associativity;
- a left, right, or two-sided identity element;
- group or quasigroup intuition;
- the retired quotient family `d_k\x = c_{k-2}*c_{k-1}`;
- the retired full shift law `p*d_k=d_{k+1}`;
- universal idempotence, `d=1`, or any universal small-period conclusion;
- `k -> d_k` injective as a claimed equivalence with `E255`, unless the proof also produces the fixed point.

Treat model agreement, old logs, and examples from deleted search files as prompts for
new lemmas, not as evidence by themselves.

## Work Order

1. Attack the period-four gate first: under `d=4`, try to rule out `r=p`, then rule out `r` outside the principal orbit. Use only the orbit recurrence, transformed identity, key identity, and left cancellation.
2. If the period-four gate stalls, return to the fixed-point target `q*x=x`. The sharp finite-map version is: before the target is proved at `x`, rule out fixed-point-free dynamics of `H_x(t)=(x*t)*x` compatible with the edge products `x\t=t*H_x(t)`. Use positive models such as `u*v=2u-v` on `F_5` as calibration: global nontrivial `H_x`-cycles may exist when the fixed point already exists. If using finite-map lemmas from ETP Chapter 5, first derive a non-tautological self-map identity involving `H_x`, `F_x`, `L_x`, `R_x`, `S`, `L_q`, or left division.
3. If fixed-point work stalls, use the collision lift as a counting problem: find a natural small target set for the injective splitter `A_e(y)=y*e`, or derive collision propagation as a new lemma rather than assuming it.
4. End unfinished attempts with exactly one next lemma.

## Writeup Protocol

Every new proof note should contain:

1. `Outcome`: proved, reduced to one next lemma, or paused with a clear reason.
2. `Claim`: exact theorem or lemma attempted.
3. `Argument`: line-by-line derivation with parenthesized products.
4. `Audit`: explicit check of the proof guardrails.
5. `Next lemma`: the single sharp statement to try next, if unfinished.
