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
reductions and try to close the named proof targets; do not begin with broad status
checking or brute-force search.

## Start here

1. Read [literature.tex](literature.tex) for the consolidated mathematical roadmap, source notes, trusted identities, quarantined routes, and bibliography.
2. Read [RAILROAD.md](RAILROAD.md) for the cold-start handoff protocol for a new agent.
3. Use [route_pass_2026-05-14.md](route_pass_2026-05-14.md) only as historical audit context; the live work order is in [RAILROAD.md](RAILROAD.md).
4. Do not revive computational search unless a new structural lemma makes a very specific check mathematically informative.

## Policy

The previous automated finite-model, theorem-prover, and random/portfolio tracks have been removed from the active repo surface. Treat them as historical audit context only; repeating them is not a research plan.

Future work should aim for one of two durable outcomes:

- a line-by-line finite proof of `E677 => E255`;
- a sharp reduction to a named missing lemma whose proof would finish the argument.

Any new note should explicitly audit that it does not use right cancellation, associativity, an identity element, group intuition, the false quotient family, or the false full shift law.
