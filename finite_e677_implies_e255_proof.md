# Archived Attempt: Invalid `d | 3` / `d = 1` Route

This file no longer presents a proof of finite `E677 => E255`.

It records a route that looked promising but is now known to fail. The theorem status remains open from the repo's validated perspective.

## What Failed

The old version of this file tried to prove a global quotient identity

`d_k\x = c_{k-2} ◦ c_{k-1}`

for all `k (mod d)` and then used it to force

- `d | 3`,
- `d in {1, 3}`,
- and finally `d = 1`.

That route is invalid.

## First Fatal Gap

The derivation of the quotient family used the step

`c_{k-1} ◦ x = d_k`.

But by definition

`d_k = c_k ◦ x`.

So the correct identity is

`c_{k-1} ◦ x = d_{k-1}`,

not `d_k`.

Once that index slip is fixed, the claimed quotient family no longer follows.

## Concrete Counterexample to the Claimed Quotient Family

The identity

`d_k\x = c_{k-2} ◦ c_{k-1}`

is not just unproved; it is false in tracked finite E677 models.

In the DB model `db/7/0`, for `x = 0`, the `c`-orbit is

`[0, 5, 2, 3, 1, 6, 4]`

and the corresponding `d`-sequence is

`[5, 6, 2, 4, 3, 0, 1]`.

Then:

1. For `k = 1`, the old route predicts

   `d_1\x = d_{d-1} = 1`,

   but the actual unique element `u` satisfying `d_1 ◦ u = x` is `u = 0`.
2. For `k = 2`, the old route predicts

   `d_2\x = c_0 ◦ c_1 = 2`,

   but the actual unique element `u` satisfying `d_2 ◦ u = x` is `u = 6`.

So the core quotient family is false.

## Why the Route Cannot Be Repaired As Stated

Even beyond the false quotient family, the attempted conclusion `d = 1` is too strong to prove the theorem in this way.

The same DB model `db/7/0` with `x = 0` has

- orbit period `d = 7`,
- `x ◦ x = 5 != 0`,
- yet `(((x ◦ x) ◦ x) ◦ x) = x`.

So known finite E677 models can have nontrivial orbit period and still satisfy E255. Any proof strategy that tries to force universal idempotence or universal period collapse is aiming at a statement stronger than the theorem and therefore cannot be the right route.

## Safe Leftovers From the Failed Attempt

The route failed, but several ingredients remain useful and are rederived elsewhere in the repo.

- Left translations are bijections, so left cancellation is available.
- The recurrence `c_{k-1} = c_k ◦ d_{k+1}` is still valid.
- The transformed identity `z = (y ◦ z) ◦ ((y ◦ (y ◦ z)) ◦ y)` is still valid.
- `d_1 = c_{d-2}` is still valid.
- The reduction of part (c) to `c_{d-2} ◦ x = x` is still valid.
- The quotient formula `a\b = b ◦ ((a ◦ b) ◦ a)` is still valid.
- The local orbit identities `x\c_k = c_{k-1}`, `c_k\c_{k-1} = d_{k+1}`, `p\d_1 = c_1`, and `p ◦ c_1 = d_1` remain useful.

What is not safe is promoting these local facts into a global quotient family or a full shift law without a new derivation.

## Current Use of This File

Treat this file as an archived failure note, not as a proof note.

For the current theorem status and the current math-first solver framing, start from `SOLVER_PROMPT.md` and the up-to-date summary files instead.