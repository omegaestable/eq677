# TASK

Find finite magma `(M, ◦)` where E677 holds, E255 fails.

- E677:  `x = y ◦ (x ◦ ((y ◦ x) ◦ y))`
- E255:  `x = ((x ◦ x) ◦ x) ◦ x`

One witness `x*` with E255 fail enough. Goal: refute `E677 ⊨_fin E255`.

# KNOWN TRUE (use free)

`x` = witness. `c_0 = x`. `c_{k+1} = x ◦ c_k`. `d` = orbit period. `d_k = c_k ◦ x`. `p = x \ x = c_{d-1}`.

1. `L_a : z ↦ a ◦ z` bijection. Left cancel yes. Right cancel no.
2. `c_{k-1} = c_k ◦ d_{k+1}`.
3. Transformed: `z = (y ◦ z) ◦ ((y ◦ (y ◦ z)) ◦ y)`.
4. `a \ b = b ◦ ((a ◦ b) ◦ a)`.
5. E255 at `x` ⇔ `c_{d-2} ◦ x = x` ⇔ `d_1 ◦ x = x`.
6. `d_j = x` ⇒ `j ≡ d − 2 (mod d)`.
7. `x \ c_k = c_{k-1}`. `c_k \ c_{k-1} = d_{k+1}`. `p \ d_1 = c_1`. `p ◦ c_1 = d_1`. `p ◦ d_d = d_1`.
8. E255 at `x` ⇔ Lemma L: `(c_1 ◦ d_1) ◦ c_1 = x`. Break L at one `x` → done.

# KNOWN FALSE (do not use)

- `d_k \ x = c_{k-2} ◦ c_{k-1}`. False.
- `p ◦ d_k = d_{k+1}`. False.
- `d | 3`. `d = 1`. False.

# DEAD ZONES (counterexample search exhausted here)

- DPLL `n ≤ 18`. UNSAT.
- Mace4 `n ≤ 14`. UNSAT.
- Affine fiber over base 7/0, 9/0, 29/0, 11/0, 13/0, `K ≤ 4`. UNSAT.
- Z3 nonlinear fiber same bases `K ≤ 4`. UNSAT.
- Cascade ATP `d ∈ {5,6,7}`: open pairs consistent with E255 holding.

Counterexample, if any, lives outside these zones. Bigger `n`, new construction class, or new base.

# BANS

- No right cancel.
- No associativity.
- No two-sided identity.
- No KNOWN FALSE law.
- No re-derive KNOWN TRUE.
- No "by symmetry" without group + fundamental domain.
- No unfilled cell. No unfixed parameter.
- No "morally", "should", "presumably", "by analogy".
- No "future agent will finish".
- No restate prompt.
- No proof-side reasoning. You build, you do not prove `E677 ⊨ E255`.

# OUTPUT

**Counterexample magma.**

- Set `M`, size `n`, full `n × n` Cayley table OR closed form `a ◦ b = f(a, b)` evaluable on every pair.
- Witness `x*`.
- Proof E677 holds all `n²` pairs. Uniform algebraic derivation, OR full case split with every case closed by one-line check.
- Compute `a = x*◦x*`, `b = a◦x*`, `c = b◦x*`. Show `c ≠ x*` as explicit elements.
- Audit: each ban listed, answer "no" to each.
- Confidence: `high` / `medium` / `low` + one weak link.

Nothing else accepted. No "reduction". No "obstruction". No "almost". No "needs more compute". No flip to proving the implication.
