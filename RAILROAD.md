# E677 Exploration Railroad — Historical Search Tracks
## READ THIS FIRST

This workspace investigates the open problem: **Does E677 finitely imply E255?**

- Current validated theorem status: **OPEN**.
- `finite_e677_implies_e255_proof.md` is an archived failed route, not a proof.
- For the current math-first solving guidance, read `SOLVER_PROMPT.md` before using this railroad.
- Treat the TRUE/FALSE tracks below as historical search/ATP tracks, not as the default recommended next action.

- **E677**: `x = y ◇ (x ◇ ((y ◇ x) ◇ y))`
- **E255**: `x = ((x ◇ x) ◇ x) ◇ x`

## Before You Do Anything

1. **Read `SOLVER_PROMPT.md`** — it is the current theorem-status and strategy source of truth.
2. **Read `progress.json`** — it tracks historical completed steps, results, and open questions.
3. **Do NOT repeat work** already marked DONE in progress.json.
4. **Log your results** back to progress.json and to `logs/<step>.log`.

## Two Tracks

### TRUE Track (Proof): `python railroad_true.py`
Proves E677 ⊨_fin E255 via cascade-gap refutation + identity extraction + ATP.

| Step | What | Status |
|------|------|--------|
| T1 | Verify L1/L2/L3 on all DB models | DONE |
| T2 | Extract depth-4/5 identities | DONE (20 identities) |
| T3 | Cascade d=7 (21 pairs) | PARTIAL — 14/21 done, 7 open |
| T4 | Re-run 7 open d=7 pairs with T2 identities | PARTIAL — all 7 still open |
| T5 | Cascade d=6 (15 pairs) | PARTIAL — 0/15 refuted |
| T6 | Cascade d=5 (10 pairs) | PARTIAL — 0/10 refuted |
| T7 | Intermediate ATP: E677→E52930, E677→E406197 | Not started |
| T8 | General-d analysis | Blocked on T3+T5+T6 |

### FALSE Track (Counterexample)
Historical search track. Searches for a finite E677-magma violating E255.

| Step | What | Status |
|------|------|--------|
| F1 | Rust DPLL `orbit_anti255` | PARTIAL — n≤18, no model. Command: `.\target\release\eq677.exe anti255 0` |
| F2 | Mace4 direct E677+¬E255 | DONE — n≤14, no model |
| F3 | Fiber extensions (Z3, nonlinear) | PARTIAL — 7/0 K≤4, 9/0 K≤3, 29/0 K≤4 all UNSAT. **Next: add 11/0 and 13/0** |
| F4 | Construction audit A1–A6 | DONE |
| F5 | Mace4 on 7 open d=7 pairs | DONE — all timeout |
| F6 | Install Rust | DONE — cargo at `C:\Users\nacho\.cargo\bin\cargo.exe` |
| **A2** | **c_dpll anti255 (NEW)** | **READY — never run. Command: `.\target\release\eq677.exe c-anti255 0`** |

## FALSE Track: Historical Search Actions

These are still available if you have a genuinely new structural reason to use search, but they are not the default next move.

### 1. Run c_dpll anti255 (A2) — new search family, never run
This uses the c_dpll partial-model completion engine (structurally different from orbit DPLL).
Wired up 2026-04-11. Binary already built. Run in background:
```powershell
.\target\release\eq677.exe c-anti255 0
```
Or a single size: `.\target\release\eq677.exe c-anti255-n <n>`

### 2. Add 11/0 and 13/0 bases to F3 fiber extensions
Pattern: read `db/11/0` and `db/13/0`, compute colorings, add `magmadef_11_0` / `magmadef_13_0`
to `color-extensions-nonlinear.py` following the exact same pattern as `magmadef_29_0` (which was
added 2026-04-11). Then run:
```powershell
python color-extensions-nonlinear.py anti255 3 4   # 11/0
python color-extensions-nonlinear.py anti255 4 4   # 13/0
```
Coloring recipe: the diagonal gets color 0, all off-diagonal get color 1, t=[(0,0,0,0),(1,1,1,1)].
**VERIFY** this with the actual coloring structure before assuming — 29/0 happened to be 2-class;
11/0 and 13/0 may differ.

### 3. Push F1 DPLL past n=18
```powershell
.\target\release\eq677.exe anti255 19
```
Each new `n` is independent; run in the background while doing other things.

### 4. (Medium effort) A1: Piecewise / vanishing-coefficient fiber search
`color-extensions.py` only supports full affine fibers. A mode where some coefficients are forced
to zero would be much faster and could find piecewise-constant constructions. Needs code change
to `color-extensions.py`.

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
- `railroad_true.py` / `railroad_false.py` — Track executors
- `proof_candidates.py` — L1/L2/L3 verification + intermediate equations + construction audit
- `extract_identities.py` — Depth-limited identity discovery
- `generate_cascade_atp.py` — Generates Prover9 .in files for cascade-gap
- `color-extensions-nonlinear.py` — Z3 fiber extension search (non-affine), F3
- `color-extensions.py` — Z3 fiber extension search (affine)
- `atp/` — Prover9 input files and results
- `logs/` — Step-by-step execution logs
- `db/` — 439+ E677-models indexed by size/variant

## Environment
- Prover9: `C:\Program Files (x86)\Prover9-Mace4\bin-win32\prover9.exe`
- Mace4: `C:\Program Files (x86)\Prover9-Mace4\bin-win32\mace4.exe`
- Python: `.venv` active
- Rust/Cargo: installed at `C:\Users\nacho\.cargo\bin\cargo.exe` (may not be on PATH — use full path)
- Built binary: `.\target\release\eq677.exe`

## Decision Points
- If **any T-step proves a theorem** (Prover9 PROVED): escalate immediately, this is publishable.
- If **F1, A2, or F3 finds a counterexample**: escalate immediately, verify model, this resolves the open problem.
- If **all cascade d=5,6,7 close fully**: strong evidence for TRUE, attempt general-d argument (T8).
- If **T7 proves E677→E52930 or E677→E406197**: reduces the main problem to a smaller gap.

## color-extensions-nonlinear.py MAGMA_DEFS index
```
MAGMA_DEFS = [magmadef_7_0, magmadef_9_0, magmadef_29_0]
              index 0         index 1        index 2
```
Call: `python color-extensions-nonlinear.py <mode> <idx> [max_K]`
Mode: `677` or `anti255`
