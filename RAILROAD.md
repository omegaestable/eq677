# E677 ->fin E255 Cold-Start Railroad

This is the handoff for the next agent. The repo is now a proof dossier, not a search workspace. Start from `literature.tex`; use this file as the short operating protocol.

## Status

- Target: decide whether every finite magma satisfying `E677` satisfies `E255`.
- Current theorem status: open.
- Latest route pass: `route_pass_2026-05-14.md` adds the fixed-point gate `h=(q*x)*q`, the key identity `(y*(y*z))*y=z*(((y*z)*z)*(y*z))`, the fixed-map form `x\t=t*((x*t)*x)`, downgrades the raw collision-lift route to a counting-only route, and sharpens counterexample work to injectively labeled permutation systems / witness-fiber maps over positive bases.
- Unrestricted status: false; the free `E677` magma does not satisfy `E255`.
- ETP status: the paper calls this the last remaining finite implication up to duality and tentatively conjectures it is false. Treat that as strategic color, not evidence.
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
- The `L_x`-orbit period is never `2`; a counterexample point has period at least `3`.

## Current Frontiers

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

### 3. Counterexample Rectangles

If `x` is a counterexample point, then no `u*x=x`. Hence `R_x` is not surjective, so by finiteness it is not injective. Thus there are `y != z` and `r != x` with

```text
y*x = z*x = r.
```

For every `y` in the fiber `R_x^{-1}(r)`, transformed E677 gives

```text
(y*r)*y = r\x.
```

Distinct collided elements must split under the second probe `t -> t*r`: if also `y*r=z*r`, left cancellation forces `y=z`.

Honest counterexample languages:

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

1. Try the fixed-point target `q*x=x`. The sharp finite-map version is now: at a bad point, rule out fixed-point-free dynamics of `H_x(t)=(x*t)*x` compatible with the edge products `x\t=t*H_x(t)`. Do not try to rule out nontrivial `H_x`-cycles globally; positive models such as `u*v=2u-v` on `F_5` have a fixed point and a nontrivial 4-cycle. If using finite-map lemmas from ETP Chapter 5, first derive a non-tautological self-map identity involving `H_x`, `F_x`, `L_x`, `R_x`, `S`, `L_q`, or left division; the inverse identities for `L_x` and `x\_` alone do not help.
2. If fixed-point work stalls, use the collision lift only as a counting problem: find a natural small target set for the injective splitter `A_e(y)=y*e`, or explain why no such set is available. Do not revive unsupported collision propagation.
3. For counterexamples, begin from the right-collision rectangle law and the injective labeled-permutation constraint. A proposed construction that does not explain those rectangles is not yet a construction.
4. End every attempt with exactly one missing lemma if the proof is unfinished.

## Writeup Protocol

Every new proof/counterexample note should contain:

1. `Status`: proved, counterexample, reduced to missing lemma, or no durable progress.
2. `Claim`: exact theorem, lemma, or construction attempted.
3. `Argument`: line-by-line derivation with parenthesized products.
4. `Audit`: explicit check of all banned moves.
5. `Next lemma`: the single sharp missing statement, if unfinished.
