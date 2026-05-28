---
name: eq677-colored-smart-sweep
description: "Use when: pursuing Eq677 colored F_p x F_q counterexample searches, launching smart colored-slope SAT sweeps, resuming unknown branches, compacting logs, or deciding next structured split. Keywords: colored_smart, run_colored_smart_sweep, O_1 row 0, p7 q7 A4 B3 bad3, E255 slope chain."
---

# Eq677 Colored Smart Sweep

Use this workflow for the current counterexample search direction: structured colored-slope magmas over `F_p x F_q`, not broad random brute force.

## Current Best Thread

- Top candidate: `p=7 q=7 A=4 B=3 bad=3`.
- E255 slope chain: `1 -> 0 -> 3`; slope `3` is the fixed C3 bad operation.
- Best first split: branch on `O_1 row 0` with `--branch-row 1:0`.
- First pass at `50000` conflicts: `4739` `unsat-prop`, `301` `unknown`, `0` SAT.
- Resumed pass at `500000` conflicts: latest compacted state is `4908` `unsat-prop`, `132` `unknown`, `0` SAT.
- No `solution*.json` witness has appeared in this thread.

## Default Commands

Launch or resume the smart split in pop-up terminals:

```powershell
& .\run_colored_smart_sweep.ps1 -ConflictBudget 500000 -BranchRow 1:0
```

Summarize and compact logs without launching new solvers:

```powershell
& .\run_colored_smart_sweep.ps1 -SummaryOnly
```

Run inline instead of pop-ups when automation is preferred:

```powershell
& .\run_colored_smart_sweep.ps1 -NoPopup -ConflictBudget 500000 -BranchRow 1:0
```

## Operating Rules

- Always summarize latest status per `branch_no`; raw JSONL may contain earlier retry records.
- Compact logs before resuming so stale `unknown` records do not pollute counts.
- `--resume` skips only completed statuses (`sat`, `verified-sat`, `bad-model`, `unsat`, `unsat-prop`); `unknown` branches are intentionally retried.
- Treat `unknown` as hard, not as killed and not as found.
- Prefer increasing budget on the compacted hard set before widening to larger primes.
- If budget increases stall, split the remaining hard set along the E255 chain rather than changing to unrelated candidate families.