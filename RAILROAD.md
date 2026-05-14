# E677 ->fin E255 Cold-Start Railroad

This is the handoff for the next agent. The repo is now a proof dossier, not a search workspace. Start from `literature.tex`; use this file as the short operating protocol.

## Status

- Target: decide whether every finite magma satisfying `E677` satisfies `E255`.
- Current theorem status: open.
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
- Orbit recurrence:
  \[
  c_{k-1}=c_k*d_{k+1}.
  \]
- `d_1=c_{d-2}`.
- If `d_j=x`, then `j=d-2 mod d`.
- With `p=x\x=c_{d-1}`:
  `x\c_k=c_{k-1}`, `c_k\c_{k-1}=d_{k+1}`, `x\p=d_1`, `p\d_1=c_1`, and `p*c_1=d_1`.
- ETP fixed-point equivalence: `E255` at `x` is equivalent to existence of `u` with `u*x=x`.

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

### 2. Collision Lift

If `d_i=d_j=e`, transformed E677 with `y=c_k,z=x` gives

```text
(c_i*e)*c_i = (c_j*e)*c_j.
```

If `i != j`, then also `c_i*e != c_j*e`; otherwise left cancellation collapses `c_i=c_j`.

Sharp missing lemma:

```text
d_i=d_j  =>  either q*x=x already, or c_i*e=c_j*e.
```

That would rule out nontrivial collisions through the displayed lifted equality. Do not replace this with unsupported collision propagation.

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

- labeled-permutation sections `a*b=sigma(a)(b)`, where all `sigma(a)` are permutations and `sigma(y)sigma(x)sigma(sigma(y)x)(y)=x`;
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

1. Try the fixed-point target `q*x=x`. If using finite-map lemmas from ETP Chapter 5, first derive an actual self-map identity involving `L_x`, `R_x`, `S`, `L_q`, or left division; then apply the finite lemma.
2. If fixed-point work stalls, attack the collision lift: derive `c_i*e=c_j*e` or a fixed point from `d_i=d_j=e`.
3. For counterexamples, begin from the right-collision rectangle law. A proposed construction that does not explain those rectangles is not yet a construction.
4. End every attempt with exactly one missing lemma if the proof is unfinished.

## Writeup Protocol

Every new proof/counterexample note should contain:

1. `Status`: proved, counterexample, reduced to missing lemma, or no durable progress.
2. `Claim`: exact theorem, lemma, or construction attempted.
3. `Argument`: line-by-line derivation with parenthesized products.
4. `Audit`: explicit check of all banned moves.
5. `Next lemma`: the single sharp missing statement, if unfinished.
