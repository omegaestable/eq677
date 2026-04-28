# E677 Hint Pack

This file is the short version of the repo state for a math-first solving pass.

## Main Goal

Resolve whether E677 finitely implies E255. The best immediate target is to prove

- `c_{d-2} ◦ x = x`

because this is equivalent to the other open part (c) identity and is the cleaner statement to aim at.

## Trusted Package

1. Left translations are bijections, so left cancellation holds.
2. With `c_0 = x`, `c_{k+1} = x ◦ c_k`, minimal period `d`, and `d_k = c_k ◦ x`, the recurrence

   `c_{k-1} = c_k ◦ d_{k+1}`

   is established.
3. The transformed identity

   `z = (y ◦ z) ◦ ((y ◦ (y ◦ z)) ◦ y)`

   is established.
4. `d_1 = c_{d-2}` is established.
5. If `d_j = x`, then `j = d - 2` modulo `d`.
6. The open part (c) statements are equivalent:

   - `c_{d-4} ◦ c_{d-4} = c_{d-5}`
   - `c_{d-2} ◦ x = x`
7. The quotient formula

   `a\b = b ◦ ((a ◦ b) ◦ a)`

   is established.
8. With `p = x \ x = c_{d-1}`, the following local identities are safe:

   - `x\c_k = c_{k-1}`
   - `c_k\c_{k-1} = d_{k+1}`
   - `p\d_1 = c_1`
   - `p ◦ c_1 = d_1`

## Known False Turns

1. The global quotient family

   `d_k\x = c_{k-2} ◦ c_{k-1}`

   is false in tracked finite E677 models.
2. The full shift law

   `p ◦ d_k = d_{k+1}`

   is also false in tracked finite E677 models.
3. Any route trying to prove universal period collapse such as `d | 3` or `d = 1` is dead. Known finite E677 models can have nontrivial orbit period and still satisfy E255.
4. `finite_e677_implies_e255_proof.md` is an archived failed route, not a finished proof.

## What The Repo Already Explored

1. L1, L2, L3 were verified on all tracked DB models.
2. Depth-4 identity extraction succeeded; deeper extraction stalled on runtime.
3. ATP closed 14 of 21 cascade pairs for `d = 7`, but later ATP reruns did not close the remaining 7.
4. ATP closed none of the tracked pairs for `d = 6` and `d = 5`.
5. Intermediate ATP implications remained open.
6. Recorded counterexample search found nothing through the tracked DPLL, Mace4, and nonlinear fiber-extension runs.

## What Not To Do First

1. Do not restart finite-model search.
2. Do not rerun old ATP batches unchanged.
3. Do not assume right cancellation or associativity.
4. Do not treat the false quotient family or the full shift law as live candidates.
5. Do not aim to prove `d = 1` or any universal small-period theorem for the `x`-orbit.
6. Do not promote a local identity to a global law without a derivation that really works uniformly in `k`.

## Recommended Proof Order

1. Try the direct local route: prove `c_{d-2} ◦ x = x`.
2. If that stalls, try a collision or cascade route based on `c_{k-1} = c_k ◦ d_{k+1}` plus a correct anchor.
3. Only then look for a weaker transport law sufficient to force some `d_t = x`.
4. Once any `d_t = x` is proved, use uniqueness to conclude `t = d - 2`.
5. Use model checks only as sanity checks for a structurally motivated claim, not as a replacement for proof.