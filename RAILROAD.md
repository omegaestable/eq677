# E677 ->fin E255 cold-start railroad

This file is the handoff for a fresh agent. The workspace is no longer a search runner. It is a compact proof/counterexample dossier.

## Status

- Problem: decide whether every finite magma satisfying `E677` also satisfies `E255`.
- Current status: open.
- Unrestricted magmas: `E677` does not imply `E255`.
- Finite magmas: still open in the Equational Theories Project, up to the dual gap `E2910 ->fin E47`.
- Source of truth: `literature.tex`.

## Equations

Use `*` or `\diamond` for the magma operation.

- `E677`: `x = y * (x * ((y * x) * y))`.
- `E255`: `x = ((x * x) * x) * x`.

For a fixed element `x` in a finite `E677` magma, write:

- `L_y(z) = y * z`, `R_y(z) = z * y`, and `S(x) = x * x`.
- `c_0 = x`, `c_{k+1} = x * c_k`.
- `d` for the minimal period of the `L_x`-orbit of `x`, so `c_d = x`.
- `d_k = c_k * x`.
- `a\b` for the unique element `u` with `a * u = b`, when left translations have been shown bijective.

## First facts to trust

These are safe starting points, but future writeups should still cite or rederive them when needed.

- In a finite `E677` magma, every left translation is bijective.
- Hence left cancellation and left division are valid.
- The inverse formula is `y\x = x * ((y * x) * y)`.
- `E255` at `x` is equivalent, in a finite `E677` magma, to solvability of `u * x = x`.
- The transformed identity
  \[
  z = (y*z) * ((y*(y*z))*y)
  \]
  is available.
- The orbit recurrence
  \[
  c_{k-1} = c_k * d_{k+1}
  \]
  is available.
- `d_1 = c_{d-2}`.
- If `d_j = x`, then `j = d-2 mod d`.
- Safe local division identities include `x\c_k = c_{k-1}`, `c_k\c_{k-1} = d_{k+1}`, `x\x = c_{d-1}`, `p\d_1 = c_1`, and `p*c_1 = d_1` for `p=x\x`.

## Facts to audit before reuse

These have appeared in older notes but should not be treated as closed unless a line-by-line proof is present in the new writeup.

- The claim that a squaring-index identity follows purely from `E677`.
- Any statement equivalent to `c_{d-2} * x = x`; this is essentially the desired fixed-point target and must not be smuggled in.
- Any cascade argument that assumes a collision `d_i=d_j` automatically propagates to `d_{i-1}=d_{j-1}`.
- Any intermediate equation proposed only because it held on stored finite models.

## Banned moves

Do not use:

- right cancellation;
- associativity;
- a left, right, or two-sided identity element;
- group or quasigroup intuition unless derived in the current argument;
- the quotient family `d_k\x = c_{k-2} * c_{k-1}`;
- the full shift law `p*d_k = d_{k+1}`;
- a conclusion such as `d=1`, idempotence, or universal small period.

The last three are not merely unproved. They are contradicted by previously tracked finite `E677` models that still satisfy `E255`.

## Next math tasks

1. Fixed-point route: prove that, for every `x`, some `u` satisfies `u*x=x`. By the ETP equivalence this finishes `E255`; the local target is `c_{d-2}*x=x`.
2. Left-division route: seek a local identity strong enough to produce the fixed point without asserting the false global shift law. A useful candidate shape is a one- or two-index relation involving `p=x\x`, `d_1`, `d_{d-1}`, and nearby `c`-terms.
3. Collision route: assume `d_i=d_j` and use the recurrence to force a contradiction or a fixed point. The missing step is the propagation of collisions; it must be derived, not assumed.
4. Counterexample route: if trying to refute the implication, focus on structural finite constructions that evade the known no-go families: non-linear, non-right-cancellative extensions are the relevant direction.

## Writeup protocol

Every future proof or counterexample note should have exactly these sections:

1. `Status`: one of proved, counterexample, reduced to missing lemma, or no durable progress.
2. `Claim`: the precise theorem, lemma, or construction being attempted.
3. `Argument`: line-by-line derivation with every nontrivial step justified.
4. `Audit`: explicit yes/no audit for the banned moves above.
5. `Next lemma`: if unfinished, state the exact missing lemma and why it would finish the route.

Do not add executable search plans, command batches, solver prompts, or size-increase tasks to this file.
