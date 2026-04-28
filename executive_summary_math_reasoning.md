# Executive Summary for Next Agent

## Current Status

The theorem `finite E677 => E255` remains open from the repo's validated perspective.

Two things are now known to be false and should not be reused.

1. The quotient family

   `d_k\x = c_{k-2} ◦ c_{k-1}`

   is false in tracked finite E677 models.
2. The full shift law

   `p ◦ d_k = d_{k+1}`

   is also false in tracked finite E677 models.

As a consequence, any route trying to prove universal period collapse such as `d | 3` or `d = 1` is dead.

The file `finite_e677_implies_e255_proof.md` is now an archived failed attempt, not a proof note.

## Mission Profile

This is still a **maximize-math-reasoning** problem.

- Do not default to brute-force search, SAT/SMT, ATP reruns, or random model construction.
- Use computation only as a sanity check for a structurally motivated claim.
- Prefer direct equational manipulation, cancellation, orbit arguments, and finite-set permutation arguments.

## Problem Data

We have a finite magma `(M, ◦)` satisfying

`E677: x = y ◦ (x ◦ ((y ◦ x) ◦ y))`

for all `x, y`.

Fix `x` and define

- `c_0 = x`
- `c_{k+1} = x ◦ c_k`

Let `d` be the minimal period, so `c_d = x` and `c_0, ..., c_{d-1}` are pairwise distinct. Define

- `d_k = c_k ◦ x`

The theorem target is still `E255: x = ((x ◦ x) ◦ x) ◦ x`.

## Trusted Facts

1. Left translations are bijections, so left cancellation is available.
2. The recurrence

   `c_{k-1} = c_k ◦ d_{k+1}`

   is valid.
3. The transformed identity

   `z = (y ◦ z) ◦ ((y ◦ (y ◦ z)) ◦ y)`

   is valid.
4. `d_1 = c_{d-2}`.
5. If `d_j = x`, then `j = d - 2 (mod d)`.
6. The two open part (c) statements are equivalent:

   - `c_{d-4} ◦ c_{d-4} = c_{d-5}`
   - `c_{d-2} ◦ x = x`

7. The quotient formula

   `a\b = b ◦ ((a ◦ b) ◦ a)`

   is valid.
8. The safe local quotient identities include

   - `x\c_k = c_{k-1}`
   - `c_k\c_{k-1} = d_{k+1}`
   - `p\d_1 = c_1`
   - `p ◦ c_1 = d_1`

## Best Live Targets

1. Primary local target: prove `c_{d-2} ◦ x = x`.
2. Secondary structural target: prove injectivity of `k -> d_k` on `Z/dZ`.
3. Exploratory target: find a weaker transport law sufficient to force one index with `d_j = x`, but do not assume a global shift law.

## Strategic Guidance

1. Try the direct local route first: force `d_{d-2} = x` without asserting any global quotient family.
2. If that stalls, try a collision or cascade route based on `c_{k-1} = c_k ◦ d_{k+1}` plus a correct anchor.
3. Only then investigate local transport identities involving `p`, `d_1`, `d_{d-1}`, or nearby orbit terms.
4. Do not promote a pattern seen at one or two indices into a global law unless the derivation is uniform in `k` and independent of Tier 2 false turns.
5. If you use model checks, use them to kill an over-strong claim quickly, not to replace proof.
c_{d-5}=c_{d-4}\circ d_{d-3}.
\]

Compare with the assumed identity and left-cancel \(c_{d-4}\):

\[
d_{d-3}=c_{d-4}.
\]

Now recurrence with \(k=d-3\):

\[
c_{d-4}=c_{d-3}\circ d_{d-2}.
\]

Since \(d_{d-3}=c_{d-3}\circ x\), we get

\[
c_{d-3}\circ x=c_{d-3}\circ d_{d-2}.
\]

Cancel \(c_{d-3}\):

\[
d_{d-2}=x.
\]

Thus

\[
\boxed{c_{d-4}\circ c_{d-4}=c_{d-5} \iff c_{d-2}\circ x=x.}
\]

This means **part (c) reduces to proving just one of the two statements**.

---

### 2. Part (d) would follow quickly from a shift law on the \(d_k\)

A very promising missing lemma is:

\[
\boxed{p\circ d_k=d_{k+1}\quad\text{for all }k,\text{ where }p:=c_{d-1}=x\backslash x.}
\tag{S}
\]

If (S) holds, then:

- the \(d_k\) form the orbit of \(d_0=x\circ x\) under the permutation \(L_p\);
- one can derive \(d_{d-2}=x\), giving part (c)(ii);
- injectivity in part (d) becomes immediate from uniqueness of the index where \(d_j=x\).

So the open problem was effectively reduced to proving a clean structural relation like (S).

---

## Most promising structural route found

Introduce left division using bijectivity of left translations:

- for fixed \(a\), define \(a\backslash z\) as the unique element \(u\) with \(a\circ u=z\).

Let

\[
p:=x\backslash x.
\]

Since \(x\circ c_{d-1}=c_d=x\), uniqueness gives

\[
\boxed{p=c_{d-1}.}
\]

The key candidate identity that would unlock the rest is:

\[
\boxed{(x\backslash x)\circ(y\circ x)=(x\circ y)\circ x.}
\tag{K}
\]

Equivalently, with \(p=x\backslash x\),

\[
p\circ(y\circ x)=(x\circ y)\circ x.
\]

If (K) is true, then substituting \(y=c_k\) yields

\[
p\circ d_k = p\circ(c_k\circ x)=(x\circ c_k)\circ x=c_{k+1}\circ x=d_{k+1},
\]

which is exactly the shift law (S).

Then:

1. since \(d_0=x\circ x\), repeated application gives \(d_k=p^k(d_0)\);
2. from \(y=p\) in (K), one gets
   \[
   p\circ(p\circ x)=(x\circ p)\circ x.
   \]
   But \(x\circ p=x\circ c_{d-1}=c_d=x\), so
   \[
   p\circ(p\circ x)=x\circ x=d_0;
   \]
3. since \(p\circ x=x\circ p=c_d=x\), or at least \(x\circ p=x\), one can hope to close the cycle and show
   \[
   d_{d-2}=x.
   \]

This route felt close, but **(K) was not rigorously derived**.

---

## Explicit dead ends / incomplete routes

### Dead end 1: trying to prove the shift law directly from the recurrence

From the recurrence,

\[
c_{k-1}=c_k\circ d_{k+1},
\]

one would like to convert this into a recursion purely among the \(d_k\), such as

\[
d_{k+1}=f(d_k)
\]

for a fixed left translation or fixed unary map. No clean derivation was obtained directly from (b).

What repeatedly blocked progress: right multiplication by \(x\) is not known injective or cancellative, so passing from identities among the \(c_k\) to identities among the \(d_k\) is delicate.

---

### Dead end 2: trying to prove \(d_{d-2}=x\) by orbit counting alone

The uniqueness statement

\[
d_j=x \implies j=d-2
\]

is strong, but only gives **uniqueness if existence is known**. Multiple attempts tried to use finiteness or orbit structure of left translations to force existence, but every version required an additional structural identity such as (K) or (S), which was missing.

---

### Dead end 3: trying to get a useful relation from \((\star)\) with special substitutions only

Several substitutions into \((\star)\) and (T) were productive for reproducing recurrence identities, but none alone forced the desired square identity or the shift law. In particular, specializing

- \(y=x\),
- \(x=c_k\),
- \(y=c_j\), \(z=x\),
- \(y=p\), \(z=x\),

gave local identities, but not a complete closed recurrence on \(d_k\).

---

### Dead end 4: trying to use computational exploration

A prior scratch attempt briefly looked at tool availability for symbolic packages and some BFS-style term exploration. This is **not part of the allowed solution strategy** and should be considered abandoned. Nothing from those explorations should be used as evidence. The correct next pass should remain purely algebraic.

---

## Algebraic observations worth keeping in play

### Observation 1: \(p=c_{d-1}\) acts as a left quasi-identity for \(x\)

Since \(x\circ p=x\), we know \(p\) is the unique left-division element satisfying \(x\circ p=x\). This makes \(p\) the natural candidate to propagate the \(d_k\)-sequence.

### Observation 2: if one can prove any single occurrence \(d_t=x\), then automatically \(t=d-2\)

This is likely useful in a contradiction argument. If one can show some translate or recurrence reaches \(x\), there is no ambiguity where it happens.

### Observation 3: proving part (c)(ii) is enough

Because of the equivalence already established, the proof effort should focus on

\[
\boxed{c_{d-2}\circ x=x.}
\]

Once that is done, the square identity follows immediately.

### Observation 4: proving a uniform law of the form \(u\circ(c_k\circ x)=c_{k+1}\circ x\) is likely decisive

This is stronger than needed but would solve both (c) and (d). The best candidate is \(u=p=c_{d-1}\).

---

## Clean derivations already available for reuse

These are safe to reuse verbatim.

### Recurrence proof

\[
\begin{aligned}
c_k
&=x\circ\bigl(c_k\circ((x\circ c_k)\circ x)\bigr) \\
&=x\circ(c_k\circ d_{k+1}).
\end{aligned}
\]

Since also \(c_k=x\circ c_{k-1}\), left-cancellation gives

\[
c_{k-1}=c_k\circ d_{k+1}.
\]

### Derivation of (T)

Substitute \(x=y\circ z\) into \((\star)\):

\[
y\circ z=y\circ\Bigl((y\circ z)\circ((y\circ(y\circ z))\circ y)\Bigr).
\]

Left-cancel \(y\):

\[
z=(y\circ z)\circ((y\circ(y\circ z))\circ y).
\]

### Uniqueness of index with \(d_j=x\)

Assuming \(d_j=x\):

\[
\begin{aligned}
x
&=(c_j\circ x)\circ\bigl((c_j\circ(c_j\circ x))\circ c_j\bigr) \\
&=x\circ(x\circ c_j) \\
&=x\circ c_{j+1}.
\end{aligned}
\]

Since also \(x=x\circ c_{d-1}\), left-cancel \(x\) to get \(c_{j+1}=c_{d-1}\), hence \(j=d-2\).

---

## Suggested next proof directions

### Direction A: derive the key law (K)

Try to prove

\[
(x\backslash x)\circ(y\circ x)=(x\circ y)\circ x
\]

purely from \((\star)\) and left-cancellation.

Potential approaches:

1. Apply \((\star)\) or (T) to both sides and compare their images under left multiplication by \(x\).
2. Since \(x\circ(x\backslash x)=x\), try expressing both sides as the unique preimage under \(L_x\) of a common element.
3. Use the fact that \((\star)\) gives an explicit formula for \(L_y^{-1}(x)\):
   \[
   L_y^{-1}(x)=x\circ((y\circ x)\circ y).
   \]
   There may be a way to compare two candidate preimages under some carefully chosen left translation.

### Direction B: derive a closed recurrence among the \(d_k\)

Start from

\[
c_{k-1}=c_k\circ d_{k+1}
\]

and replace \(c_{k-1},c_k\) where possible using left divisions by \(x\). A successful expression of \(d_{k+1}\) in terms of \(d_k\) or a fixed translate of \(d_k\) would likely end the problem.

### Direction C: contradiction from a repeated \(d_k\)

For part (d), suppose \(d_i=d_j\) with \(0\le i<j<d\). Use recurrence to derive a repeated \(c\)-value or force some \(d_t=x\) at two different indices, contradicting uniqueness.

At present there is no finished derivation, but this remains plausible if a mild shift identity can be extracted.

---

## Things to avoid on the next pass

- Do **not** restart from brute-force experimentation.
- Do **not** search for examples/counterexamples in small finite magmas.
- Do **not** use web search.
- Do **not** rely on group-like intuitions unless explicitly derived from \((\star)\).
- Do **not** assume right cancellation, associativity, or existence of identities.

---

## Minimal checkpoint for the next agent

The next agent should begin from the following trusted package:

1. Left translations are bijections; left cancellation holds.
2. The recurrence
   \[
   c_{k-1}=c_k\circ d_{k+1}
   \]
   is proved.
3. The transformed identity
   \[
   z=(y\circ z)\circ((y\circ(y\circ z))\circ y)
   \]
   is proved.
4. \(d_1=c_{d-2}\).
5. If \(d_j=x\), then \(j=d-2\).
6. In part (c), the two target identities are equivalent.
7. The most promising unresolved target is to prove either
   - \(c_{d-2}\circ x=x\), or
   - the key law \((x\backslash x)\circ(y\circ x)=(x\circ y)\circ x\), or
   - a shift law \(c_{d-1}\circ d_k=d_{k+1}\).

---

## Bottom line

The prior pass **did not complete** parts (c) and (d), but it reduced the problem to a much narrower algebraic bottleneck.

The highest-value next move is:

> Prove a structural identity that propagates the sequence \(d_k\) by a fixed left translation, ideally via the element \(p=c_{d-1}=x\backslash x\).

That appears to be the cleanest route to both:

- existence of the unique index with \(d_j=x\), hence part (c), and
- injectivity of \(k\mapsto d_k\), hence part (d).
