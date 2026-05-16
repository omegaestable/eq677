# E677 finite implication proof dossier

This repository is now a math-first workspace for the finite implication

\[
E677 \models_{\mathrm{fin}} E255?
\]

where

\[
E677:\quad x = y \diamond (x \diamond ((y \diamond x) \diamond y))
\]

and

\[
E255:\quad x = ((x \diamond x) \diamond x) \diamond x.
\]

This repo is a proof-first workspace for the finite implication.  Work from the local
reductions and try to close the named proof targets; use broad status checks or brute
force only when a new structural lemma makes them mathematically informative.

## Start here

1. Read [literature.tex](literature.tex) for the consolidated mathematical roadmap, source notes, trusted identities, audited trial routes, and bibliography.
2. Read [RAILROAD.md](RAILROAD.md) for the cold-start handoff protocol for a new agent.
3. Use [route_pass_2026-05-14.md](route_pass_2026-05-14.md) only as historical audit context; the live work order is in [RAILROAD.md](RAILROAD.md).
4. Keep computation proof-directed: source lookup and compilation are useful; broad search should be tied to a specific new lemma.

## Working Posture

The previous automated finite-model, theorem-prover, and random/portfolio tracks are historical audit context. Reuse them only when they answer a precise structural question raised by the current proof attempt.

Future work should aim for one of two durable outcomes:

- a line-by-line finite proof of `E677 => E255`;
- a sharp reduction to a named next lemma whose proof would finish the argument.

Any new note should explicitly audit the proof guardrails: no assumed right cancellation,
associativity, identity element, group intuition, retired quotient family, or retired full
shift law.
