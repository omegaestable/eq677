# E677 finite implication proof dossier

This repository is a proof-first workspace for the finite implication

\[
E677 \models_{\mathrm{fin}} E255?
\]

where

\[
E677:\quad x = y \diamond (x \diamond ((y \diamond x) \diamond y)),
\qquad
E255:\quad x = ((x \diamond x) \diamond x) \diamond x.
\]

The current local target is: for fixed `x`, set `a=x*x`, `q=a*x`, and
`p=x\x`; prove `q*x=x`.  The dossier records equivalent targets, orbit
reductions, right-collision geometry, examples, search status, and the open gates.

## Start Here

1. Read [literature.tex](literature.tex). It is the canonical roadmap and contains the
   state-of-the-art summary, all trusted identities, proof guardrails, examples, and open
   gates.
2. Read [RAILROAD.md](RAILROAD.md) for the short cold-start protocol.
3. Treat [route_pass_2026-05-14.md](route_pass_2026-05-14.md),
   [math_search_pass_2026-05-16.md](math_search_pass_2026-05-16.md), and
   [implementation_pass_2026-05-16.md](implementation_pass_2026-05-16.md) as audit
   history and command logs.

## Current Status

- No finite counterexample is known.
- The public database currently has `841` records, all marked `satisfies_255=True`;
  `116` are non-right-cancellative positive examples, which are the useful near-miss pool.
- Solver evidence closes bad-witness searches through order `9`; at order `10`, periods
  `4`, `5`, `6`, `8`, and `9` are closed, while broad period `7` and `10` branches remain
  computational frontiers.
- The most important open gates are the fixed-point gate `q*x=x`, the expert collision
  gate, the splitter-counting gate, the period-four external gate, and the period-five
  pruning gate.

## Tooling

Use the repository virtualenv:

```powershell
& .\.venv\Scripts\python.exe scripts\e677_db_analyze.py selftest
& .\.venv\Scripts\python.exe scripts\e677_db_analyze.py analyze-file path\to\table.txt
& .\.venv\Scripts\python.exe scripts\e677_db_analyze.py manifest
& .\.venv\Scripts\python.exe scripts\e677_z3_search.py db-frontier --max-size 40
& .\.venv\Scripts\python.exe scripts\e677_z3_search.py piecewise-prime --prime 127 --qr-slope 58 --nqr-slope 29
& .\.venv\Scripts\python.exe scripts\e677_construct.py linear-bases --max-prime 200
& .\.venv\Scripts\python.exe scripts\e677_construct.py translation --max-order 8 --max-hits 20
& .\.venv\Scripts\python.exe scripts\e677_construct.py polynomial-translation --max-prime 17 --degree 3 --zero-value 0
& .\.venv\Scripts\python.exe scripts\e677_construct.py affine-colors --prime 19 --q 7 --alpha 7 --beta 4 --max-models 5
& .\.venv\Scripts\python.exe scripts\e677_construct.py colored-candidates --max-prime 200 --q 7 --top 30 --show-commands
& .\run_colored_candidate_sweep.ps1 -ConflictBudget 2000000 -ProgressConflicts 50000
& .\run_colored_smart_sweep.ps1 -ConflictBudget 500000 -BranchRow 1:0
& .\run_colored_smart_sweep.ps1 -SummaryOnly
& .\.venv\Scripts\python.exe explore_colored_magma.py --config primary --mode affine-o11-projection-sweep --solver cadical --out ""
& .\.venv\Scripts\python.exe explore_colored_magma.py --config primary --mode deep --solver cadical --primary-o11-symmetry --branch-o11-column 0 --branch-mod 8 --branch-index 0 --log run_logs\colored_magma\primary_o11_col0_shard0.jsonl --out run_logs\colored_magma\primary_solution.json
& .\.venv\Scripts\python.exe explore_colored_magma.py --config primary --mode dimacs --symbreak-o11-00 0 --cnf-out run_logs\colored_magma\primary_o11_00.cnf
& .\.venv\Scripts\python.exe explore_colored_magma.py --mode log-summary --log-in run_logs\colored_magma
& .\.venv\Scripts\python.exe explore_colored_magma.py --mode log-compact --log-in run_logs\colored_magma --log-out run_logs\colored_magma\compact.jsonl
```

The colored-slope solver is the current explicit-construction branch for the primary
candidate described in [finite_counterexample_path.tex](finite_counterexample_path.tex).
Use `--mode deep` with `--branch-mod/--branch-index` for long sharded runs; omit
`--conflicts` or set it to `0` for an uninterrupted branch.  Deep runs now use stable
default JSONL log names, fsync each branch record, and write durable solver heartbeats
every 10 minutes by default.  Use `--stop-file path\to\run.stop` to request a graceful
stop after the current solver chunk, and `--touch-stop-file-on-sat` on sibling shards so
one verified solution winds the others down.  `--primary-o11-symmetry` uses the
homogeneous color-scalar normalization `O_11(0,0)=0` or `1`; in the zero column branch it
also uses the residual scalar symmetry to normalize `O_11(1,0)=1`.

Authenticated API writes are explicit opt-in subcommands on
`scripts/e677_db_analyze.py` and require `EQ677_API_TOKEN`; ordinary manifest/table
analysis is read-only.

## Working Posture

Aim for either a line-by-line finite proof of `E677 =>fin E255`, or a sharp reduction to
one named lemma whose proof would finish the argument.  Keep computation proof-directed:
use broad search only when it tests a structural lemma or mines positive examples.

Every proof note should explicitly audit the guardrails: no assumed right cancellation,
associativity, identity element, group intuition, retired quotient family, retired full
shift law, or universal idempotence.
