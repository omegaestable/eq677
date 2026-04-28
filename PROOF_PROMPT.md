# TASK

Prove: every magma satisfying E677 satisfies E255.

- E677:  `x = y ◦ (x ◦ ((y ◦ x) ◦ y))`
- E255:  `x = ((x ◦ x) ◦ x) ◦ x`

Goal: derive E255 from E677 in arbitrary magma. Finite hypothesis allowed but not required.

# KNOWN TRUE (use free)

`x` = arbitrary element. `c_0 = x`. `c_{k+1} = x ◦ c_k`. `d` = orbit period (when finite). `d_k = c_k ◦ x`. `p = x \ x = c_{d-1}`.

1. `L_a : z ↦ a ◦ z` bijection. Left cancel yes. Right cancel no.
2. `c_{k-1} = c_k ◦ d_{k+1}`.
3. Transformed: `z = (y ◦ z) ◦ ((y ◦ (y ◦ z)) ◦ y)`.
4. `a \ b = b ◦ ((a ◦ b) ◦ a)`.
5. E255 at `x` ⇔ `c_{d-2} ◦ x = x` ⇔ `d_1 ◦ x = x`.
6. `d_j = x` ⇒ `j ≡ d − 2 (mod d)`.
7. `x \ c_k = c_{k-1}`. `c_k \ c_{k-1} = d_{k+1}`. `p \ d_1 = c_1`. `p ◦ c_1 = d_1`. `p ◦ d_d = d_1`.
8. E255 at `x` ⇔ Lemma L: `(c_1 ◦ d_1) ◦ c_1 = x`, i.e. `[(x◦x)◦((x◦x)◦x)] ◦ (x◦x) = x`. Reduction unconditional. Prove L → done.

# KNOWN FALSE (do not use)

- `d_k \ x = c_{k-2} ◦ c_{k-1}`. False.
- `p ◦ d_k = d_{k+1}`. False.
- `d | 3`. `d = 1`. False.

DB witnesses against these exist. Any chain that needs them is broken.

# BANS

- No right cancel.
- No associativity.
- No two-sided identity.
- No KNOWN FALSE law, even as intermediate step.
- No re-derive KNOWN TRUE (cite by number).
- No "by symmetry" without explicit substitution.
- No "WLOG" without justification.
- No "morally", "should", "presumably", "by analogy", "essentially".
- No "future agent will finish".
- No restate prompt.
- No counterexample-side reasoning. You prove, you do not search for a magma.
- No proof relying on finiteness unless you state it explicitly and the bound is a Tier-1 fact.

# OUTPUT

**Proof of E677 ⊨ E255.**

- Target: derive E255 universally, OR derive Lemma L (Tier-1 fact 8) which is equivalent.
- Format: numbered steps. Each step:
  - Statement (an equation between terms in `x, y, ...` and `◦`).
  - Justification: which earlier step or KNOWN TRUE item, and which substitution.
- Every variable substitution written explicitly: "apply (3) with `y := c_1`, `z := x`".
- Every left-cancellation step shows the common left factor explicitly.
- End with E255 (or L) on a single line, justified from the chain.
- Audit: each ban listed, answer "no" to each. Each KNOWN FALSE item listed, confirm not used.
- Confidence: `high` / `medium` / `low` + one weak link (the single step you trust least).

Nothing else accepted. No "reduction to a sub-lemma" unless the sub-lemma is then proved in the same reply. No "obstruction". No "almost". No "needs more compute". No flip to building a counterexample.
