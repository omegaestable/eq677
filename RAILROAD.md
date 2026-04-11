# E677 Exploration Railroad — Agent Instructions
## READ THIS FIRST

This workspace investigates the open problem: **Does E677 finitely imply E255?**

- **E677**: `x = y ◇ (x ◇ ((y ◇ x) ◇ y))`
- **E255**: `x = ((x ◇ x) ◇ x) ◇ x`

## Before You Do Anything

1. **Read `progress.json`** — it tracks every completed step, every result, every open question.
2. **Do NOT repeat work** already marked DONE in progress.json.
3. **Log your results** back to progress.json and to `logs/<step>.log`.

## Two Tracks

### TRUE Track (Proof): `python railroad_true.py`
Proves E677 ⊨_fin E255 via cascade-gap refutation + identity extraction + ATP.

| Step | What | Status guidance |
|------|------|-----------------|
| T1 | Verify L1/L2/L3 on all DB models | Quick baseline, run first |
| T2 | Extract depth-4/5 identities | Feeds T4 |
| T3 | Cascade d=7 (21 pairs) | 14/21 done, 7 open |
| T4 | Re-run 7 open pairs with T2 identities | Needs T2 first |
| T5 | Cascade d=6 (15 pairs) | Independent |
| T6 | Cascade d=5 (10 pairs) | Smallest, most likely to fully close |
| T7 | Intermediate ATP: E677→E52930, E677→E406197 | Independent |
| T8 | General-d analysis | Needs T3+T5+T6 |

### FALSE Track (Counterexample): `python railroad_false.py`
Searches for a finite E677-magma violating E255.

| Step | What | Status guidance |
|------|------|-----------------|
| F1 | Rust DPLL orbit_anti255 | BLOCKED: no Rust installed |
| F2 | Mace4 direct E677+¬E255 | No compilation needed |
| F3 | Fiber extensions on more bases | Partial: 7/0, 9/0 done |
| F4 | Construction audit | Quick, run from proof_candidates.py |
| F5 | Mace4 on 7 open d=7 pairs | DONE: all timeout, no models |
| F6 | Install Rust | Unblocks F1 |

## Running

```powershell
# Auto-run next step (reads progress, picks, executes, logs):
python railroad_true.py
python railroad_false.py

# Force a specific step:
python railroad_true.py T1
python railroad_false.py F2

# Check status only:
python railroad_true.py status
python railroad_false.py status
```

## Key Files
- `progress.json` — Machine-readable state (AGENTS: read+update this)
- `railroad_true.py` — Proof track executor
- `railroad_false.py` — Counter track executor
- `proof_candidates.py` — L1/L2/L3 verification + intermediate equations + construction audit
- `extract_identities.py` — Depth-limited identity discovery
- `generate_cascade_atp.py` — Generates Prover9 .in files for cascade-gap
- `atp/` — Prover9 input files and results
- `logs/` — Step-by-step execution logs

## Environment
- Prover9: `C:\Program Files (x86)\Prover9-Mace4\bin-win32\prover9.exe`
- Mace4: `C:\Program Files (x86)\Prover9-Mace4\bin-win32\mace4.exe`
- Python: `.venv` active
- Rust/Cargo: NOT installed (blocks F1)

## Decision Points
- If **any T-step proves a theorem** (Prover9 PROVED): escalate immediately, this is publishable.
- If **F1 or F2 finds a counterexample**: escalate immediately, verify model, this resolves the open problem.
- If **all cascade d=5,6,7 close fully**: strong evidence for TRUE, attempt general-d argument (T8).
- If **T7 proves E677→E52930 or E677→E406197**: reduces the main problem to a smaller gap.
