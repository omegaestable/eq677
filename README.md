# E677 finite implication dossier

This repository is now a math-first workspace for the remaining finite implication

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

The current working status is **open**. The unrestricted implication is false, but the finite implication is one of the remaining finite-graph gaps in the Equational Theories Project. This repo should therefore be used as a proof and counterexample research dossier, not as a brute-force search workspace.

## Start here

1. Read [literature.tex](literature.tex) for the consolidated mathematical roadmap, source notes, trusted identities, failed routes, and bibliography.
2. Read [RAILROAD.md](RAILROAD.md) for the cold-start handoff protocol for a new agent.
3. Do not revive computational search unless a new structural lemma makes a very specific check mathematically informative.

## Policy

The previous automated finite-model, theorem-prover, and random/portfolio tracks have been removed from the active repo surface. Their value is historical negative evidence only: they did not settle the implication, and repeating them is not a research plan.

Future work should aim for one of three durable outcomes:

- a line-by-line finite proof of `E677 => E255`;
- a verified finite counterexample;
- a sharp reduction to a named missing lemma whose proof would finish the argument.

Any new note should explicitly audit that it does not use right cancellation, associativity, an identity element, group intuition, the false quotient family, or the false full shift law.
