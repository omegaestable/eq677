# E677 ->fin E255 Cold-Start Railroad

This is the handoff for the next agent. The repo is now a proof dossier, not a search workspace. Start from `literature.tex`; use this file as the short operating protocol.

## Solver Stance

- Target: decide whether every finite magma satisfying `E677` satisfies `E255`.
- Historical route pass: `route_pass_2026-05-14.md` adds the fixed-point gate `h=(q*x)*q`, the key identity `(y*(y*z))*y=z*(((y*z)*z)*(y*z))`, the fixed-map form `x\t=t*((x*t)*x)`, and downgrades the raw collision-lift route to a counting-only route.
- Newest proof audit: `literature.tex` now excludes principal `L_x`-orbit period `3` and records a period-four gate; use the period-four target before returning to broader fixed-map dynamics.
- Work as if the proof is local and reachable: start from the trusted package and try to close one named gate. Do not stop because public metadata has not already settled the implication.
- The unrestricted case is only a proof-discipline warning: a finite proof must visibly use finiteness.
- Allowed computation: only source lookup and document compilation. No brute force, SAT/SMT, ATP batches, model enumeration, or numerical testing.

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

These are targets, not established lemmas.

### 2. Collision Lift / Counting Only

If `d_i=d_j=e`, transformed E677 with `y=c_k,z=x` gives

```text
(c_i*e)*c_i = (c_j*e)*c_j.
```

If `i != j`, then also `c_i*e != c_j*e`; otherwise left cancellation collapses `c_i=c_j`.

The old sharp missing lemma was:

```text
d_i=d_j  =>  either q*x=x already, or c_i*e=c_j*e.
```

This would rule out nontrivial collisions through the displayed lifted equality, but the 2026-05-14 audit shows it is not a promising direct propagation target: every right fiber has an injective splitter.  For fixed `x` and `e`, if

```text
F_e={y:y*x=e},  A_e(y)=y*e,
```

then `(y*e)*y=e\x` for all `y in F_e`, and `A_e` is injective on `F_e`.  Thus a genuine collision already forces `c_i*e != c_j*e`.  The collision route now needs a finite counting restriction on the possible splitter values; do not try to prove `c_i*e=c_j*e` directly without also producing the fixed point.

### 3. Right-Collision Rectangles, Quarantined For Proof Work

If the fixed-point target fails at `x`, then no `u*x=x`. Hence `R_x` is not surjective, so by finiteness it is not injective. Thus there are `y != z` and `r != x` with

```text
y*x = z*x = r.
```

For every `y` in the fiber `R_x^{-1}(r)`, transformed E677 gives

```text
(y*r)*y = r\x.
```

Distinct collided elements must split under the second probe `t -> t*r`: if also `y*r=z*r`, left cancellation forces `y=z`.

Do not spend proof-agent time trying to construct a model unless explicitly redirected.
The following notes are retained only as constraints that prevent bad proof moves.  Any
structural construction would have to use:

- labeled-permutation sections `a*b=sigma(a)(b)`, where all `sigma(a)` are permutations, the label map `a -> sigma(a)` is injective, and `sigma(y)sigma(x)sigma(sigma(y)x)(y)=x`;
- genuinely nonlinear fiber extensions over positive `E677` bases.

Both must explicitly build the right-collision rectangles above while preserving left bijectivity.

## Banned Moves

Do not use:

- right cancellation;
- associativity;
- a left, right, or two-sided identity element;
- group or quasigroup intuition unless derived in the proof;
- the false quotient family `d_k\x = c_{k-2}*c_{k-1}`;
- the false full shift law `p*d_k=d_{k+1}`;
- universal idempotence, `d=1`, or any universal small-period conclusion;
- `k -> d_k` injective as a claimed equivalence with `E255` unless the proof also produces the fixed point.

Also do not promote model agreement, old logs, or examples from deleted search files into evidence.

## Work Order

1. Attack the period-four gate first: under `d=4`, try to rule out `r=p`, then rule out `r` outside the principal orbit. Use only the orbit recurrence, transformed identity, key identity, and left cancellation.
2. If the period-four gate stalls, return to the fixed-point target `q*x=x`. The sharp finite-map version is: before the target is proved at `x`, rule out fixed-point-free dynamics of `H_x(t)=(x*t)*x` compatible with the edge products `x\t=t*H_x(t)`. Do not try to rule out nontrivial `H_x`-cycles globally; positive models such as `u*v=2u-v` on `F_5` have a fixed point and a nontrivial 4-cycle. If using finite-map lemmas from ETP Chapter 5, first derive a non-tautological self-map identity involving `H_x`, `F_x`, `L_x`, `R_x`, `S`, `L_q`, or left division; the inverse identities for `L_x` and `x\_` alone do not help.
3. If fixed-point work stalls, use the collision lift only as a counting problem: find a natural small target set for the injective splitter `A_e(y)=y*e`, or explain why no such set is available. Do not revive unsupported collision propagation.
4. End every attempt with exactly one missing lemma if the proof is unfinished.

## Writeup Protocol

Every new proof note should contain:

1. `Outcome`: proved, reduced to one missing lemma, or no durable progress.
2. `Claim`: exact theorem or lemma attempted.
3. `Argument`: line-by-line derivation with parenthesized products.
4. `Audit`: explicit check of all banned moves.
5. `Next lemma`: the single sharp missing statement, if unfinished.
