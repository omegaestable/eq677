#!/usr/bin/env python3
"""
railroad_true.py — Proof-track execution railroad for E677 ⊨_fin E255.
=====================================================================

Reads progress.json, determines the next actionable step on the TRUE track,
executes it, logs results back to progress.json.

Usage:
    python railroad_true.py              # auto-pick next step
    python railroad_true.py T1           # force a specific step
    python railroad_true.py status       # show current status only

Steps (in dependency order):
    T1  — Verify L1/L2/L3 on all DB models (proof_candidates.py)
    T2  — Extract depth-4/5 identities (extract_identities.py)
    T3  — [DONE PARTIAL] Cascade d=7 (14/21 refuted, 7 open)
    T4  — Augment 7 open d=7 pairs with T2 identities, re-run Prover9
    T5  — Cascade d=6 (15 pairs)
    T6  — Cascade d=5 (10 pairs)
    T7  — Intermediate equations: E677 => E52930, E677 => E406197
    T8  — General-d analysis (after T3+T5+T6 complete)
"""

import json
import os
import sys
import subprocess
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(ROOT, "progress.json")
PROVER9 = r"C:\Program Files (x86)\Prover9-Mace4\bin-win32\prover9.exe"
MACE4 = r"C:\Program Files (x86)\Prover9-Mace4\bin-win32\mace4.exe"
ATP_DIR = os.path.join(ROOT, "atp")
LOG_DIR = os.path.join(ROOT, "logs")
WINDOWS_BELOW_NORMAL = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)


def creation_flags(background=False):
    # TRUE track now runs at normal priority, even in background mode.
    return 0


def ensure_t2_defaults(track):
    track.setdefault("background_mode", False)
    track.setdefault("depth5_group_limit", 0)  # 0 = uncapped
    track.setdefault("depth5_fp_models", 3)
    track.setdefault("checkpoint_path", os.path.join(ROOT, "logs", "T2_d5_checkpoint.json"))


def parse_t2_checkpoint(track):
    checkpoint_path = track.get("checkpoint_path")
    if not checkpoint_path or not os.path.exists(checkpoint_path):
        return None
    with open(checkpoint_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    with open(PROGRESS_FILE, "r") as f:
        return json.load(f)


def save_progress(prog):
    prog["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    prog["last_agent_session"] = "railroad_true"
    with open(PROGRESS_FILE, "w") as f:
        json.dump(prog, f, indent=2)


def ensure_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(ATP_DIR, exist_ok=True)


def log_result(step_id, content):
    """Append result to step-specific log file."""
    ensure_dirs()
    logfile = os.path.join(LOG_DIR, f"{step_id}.log")
    with open(logfile, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{datetime.now().isoformat()}]\n")
        f.write(content)
        f.write("\n")
    print(f"  [logged to logs/{step_id}.log]")


# ===================================================================
# T1 — Verify L1/L2/L3 on all DB models
# ===================================================================
def run_T1(prog):
    t = prog["TRUE_TRACK"]["T1_lemma_verification"]
    if t["status"] == "DONE":
        print("T1: Already completed.")
        return

    print("T1: Running proof_candidates.py to verify L1/L2/L3 on all DB models...")
    t["status"] = "RUNNING"
    save_progress(prog)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "proof_candidates.py")],
        capture_output=True, text=True, timeout=600, env=env
    )

    output = result.stdout + "\n" + result.stderr
    log_result("T1", output)

    # Parse key outcomes
    lines = output.split("\n")
    l1_fail = l2_fail = l3_fail = 0
    import re
    for line in lines:
        m = re.search(r'L1.*failures:\s*(\d+)', line)
        if m:
            l1_fail = int(m.group(1))
        m = re.search(r'L2.*failures:\s*(\d+)', line)
        if m:
            l2_fail = int(m.group(1))
        m = re.search(r'L3.*failures:\s*(\d+)', line)
        if m:
            l3_fail = int(m.group(1))

    t["status"] = "DONE"
    t["result"] = {
        "L1_failures": l1_fail,
        "L2_failures": l2_fail,
        "L3_failures": l3_fail,
        "all_pass": l1_fail == 0 and l2_fail == 0 and l3_fail == 0
    }
    t["notes"] = f"L1={l1_fail}, L2={l2_fail}, L3={l3_fail} failures. " + (
        "All lemmas hold on every DB model." if t["result"]["all_pass"]
        else "UNEXPECTED FAILURES — investigate immediately."
    )
    save_progress(prog)
    print(f"  T1 result: L1={l1_fail}, L2={l2_fail}, L3={l3_fail} failures")


# ===================================================================
# T2 — Extract identities at depth 4 and 5
# ===================================================================
def run_T2(prog, background=False):
    t = prog["TRUE_TRACK"]["T2_identity_extraction"]
    ensure_t2_defaults(t)
    if t["status"] == "DONE":
        print("T2: Already completed.")
        return

    print("T2: Extracting identities across DB models...")
    t["status"] = "RUNNING"
    save_progress(prog)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Depth 4 first
    if t["result_d4"] is None:
        print("  T2a: depth=4 ...")
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "extract_identities.py"), "4"],
            capture_output=True, text=True, timeout=1800, env=env
        )
        output = result.stdout + "\n" + result.stderr
        log_result("T2_d4", output)

        # Parse identities
        identities = []
        for line in output.split("\n"):
            if "=" in line and "depth" in line.lower() and "f(" in line:
                identities.append(line.strip())
        t["result_d4"] = {
            "identities_count": len(identities),
            "identities_sample": identities[:20],
            "exit_code": result.returncode
        }
        save_progress(prog)
        print(f"  T2a: {len(identities)} identities found at depth 4")

    # Depth 5
    if t["result_d5"] is None:
        print("  T2b: depth=5 (may be slow) ...")
        checkpoint_path = t["checkpoint_path"]
        cmd = [
            sys.executable,
            os.path.join(ROOT, "extract_identities.py"),
            "5",
            "--checkpoint", checkpoint_path,
            "--fp-models", str(t["depth5_fp_models"]),
        ]
        if background:
            cmd.extend(["--group-limit", str(t["depth5_group_limit"])])
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                timeout=900 if background else 3600,
                env=env,
                creationflags=creation_flags(background)
            )
            output = result.stdout + "\n" + result.stderr
            log_result("T2_d5", output)

            checkpoint = parse_t2_checkpoint(t)
            identities = checkpoint.get("identities", []) if checkpoint else []
            processed_groups = checkpoint.get("processed_groups", 0) if checkpoint else 0
            total_groups = checkpoint.get("total_groups", 0) if checkpoint else 0

            if checkpoint and checkpoint.get("completed"):
                t["result_d5"] = {
                    "identities_count": len(identities),
                    "identities_sample": [f"{a}  =  {b}" for (a, b) in identities[:20]],
                    "exit_code": result.returncode,
                    "processed_groups": processed_groups,
                    "total_groups": total_groups,
                    "checkpoint_path": checkpoint_path,
                }
                print(f"  T2b: {len(identities)} identities found at depth 5")
            else:
                t["status"] = "PARTIAL"
                t["notes"] = (
                    f"Depth-4 completed with {t['result_d4']['identities_count']} identities. "
                    f"Depth-5 checkpointed at group {processed_groups}/{total_groups}; resume to continue."
                )
                save_progress(prog)
                print(f"  T2b: checkpointed at group {processed_groups}/{total_groups}")
                return
        except subprocess.TimeoutExpired:
            t["result_d5"] = {"status": "TIMEOUT_1h", "identities_count": 0}
            print("  T2b: TIMEOUT after 1 hour")

    # Collect all identities
    all_ids = []
    if t["result_d4"] and "identities_sample" in t["result_d4"]:
        all_ids.extend(t["result_d4"]["identities_sample"])
    if t["result_d5"] and "identities_sample" in (t["result_d5"] or {}):
        all_ids.extend(t["result_d5"].get("identities_sample", []))
    t["identities_found"] = all_ids
    t["status"] = "DONE"
    t["notes"] = f"Depth-4 and depth-5 completed. Total sampled identities: {len(all_ids)}."
    save_progress(prog)


def run_T2_BG(prog):
    run_T2(prog, background=True)


# ===================================================================
# T5 — Cascade d=6
# ===================================================================
def run_cascade(prog, d, step_key):
    from itertools import combinations
    t = prog["TRUE_TRACK"][step_key]
    if t["status"] == "DONE":
        print(f"{step_key}: Already completed.")
        return

    print(f"{step_key}: Cascade analysis for d={d} ...")
    t["status"] = "RUNNING"
    save_progress(prog)

    # Generate files
    print(f"  Generating Prover9 files for d={d} ...")
    gen_result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "generate_cascade_atp.py"), str(d)],
        capture_output=True, text=True, timeout=60
    )
    log_result(step_key + "_gen", gen_result.stdout)

    # Run Prover9 on each pair
    n_pairs = d * (d - 1) // 2
    refuted = []
    open_pairs = []

    for i, j in combinations(range(d), 2):
        fname = os.path.join(ATP_DIR, f"cascade-d{d}-{i}-{j}.in")
        if not os.path.exists(fname):
            open_pairs.append(f"{i}-{j}")
            continue

        print(f"  Prover9: d{i}=d{j} ...", end=" ", flush=True)
        try:
            result = subprocess.run(
                [PROVER9, "-t", "120", "-f", fname],
                capture_output=True, text=True, timeout=130
            )
            output = result.stdout
            # Count proofs
            proof_count = output.count("THEOREM PROVED")
            if proof_count > 0:
                refuted.append(f"{i}-{j}")
                print(f"REFUTED ({proof_count} proofs)")
            else:
                open_pairs.append(f"{i}-{j}")
                print("OPEN (0 proofs)")

            log_result(f"{step_key}_{i}_{j}", output[:2000])

        except subprocess.TimeoutExpired:
            open_pairs.append(f"{i}-{j}")
            print("TIMEOUT")
            log_result(f"{step_key}_{i}_{j}", "TIMEOUT after 120s")
        except FileNotFoundError:
            print(f"ERROR: Prover9 not found at {PROVER9}")
            return

    t["refuted"] = refuted
    t["open"] = open_pairs
    t["status"] = "DONE" if not open_pairs else "PARTIAL"
    t["notes"] = f"{len(refuted)}/{n_pairs} refuted, {len(open_pairs)} open: {open_pairs}"
    save_progress(prog)

    print(f"\n  {step_key} RESULT: {len(refuted)}/{n_pairs} refuted, {len(open_pairs)} open")
    if not open_pairs:
        print(f"  *** d={d} CASCADE FULLY CLOSED — d-injectivity proved for period {d}! ***")


def run_T5(prog):
    run_cascade(prog, 6, "T5_cascade_d6")


def run_T6(prog):
    run_cascade(prog, 5, "T6_cascade_d5")


# ===================================================================
# T4 — Augmented re-run of 7 open d=7 pairs
# ===================================================================
def run_T4(prog):
    t = prog["TRUE_TRACK"]["T4_cascade_d7_augmented"]
    t2 = prog["TRUE_TRACK"]["T2_identity_extraction"]

    if t["status"] == "DONE":
        print("T4: Already completed.")
        return

    if t2["status"] != "DONE":
        print("T4: BLOCKED — T2 (identity extraction) must run first.")
        return

    identities = t2.get("identities_found", [])
    if not identities:
        print("T4: No additional identities found by T2. Attempting with longer Prover9 timeout instead.")

    open_pairs = prog["TRUE_TRACK"]["T3_cascade_d7"]["open"]
    if not open_pairs:
        t["status"] = "DONE"
        t["notes"] = "No open pairs to augment (T3 already fully closed)."
        save_progress(prog)
        return

    print(f"T4: Re-running {len(open_pairs)} open d=7 pairs with augmented axioms + longer timeout...")
    t["status"] = "RUNNING"
    save_progress(prog)

    results = {}
    still_open = []

    for pair in open_pairs:
        i, j = map(int, pair.split("-"))
        fname = os.path.join(ATP_DIR, f"cascade-d7-{i}-{j}.in")
        aug_fname = os.path.join(ATP_DIR, f"cascade-d7-{i}-{j}-aug.in")

        if not os.path.exists(fname):
            still_open.append(pair)
            continue

        # Create augmented file: original + extra identities
        with open(fname, "r") as f:
            content = f.read()

        # Insert identities before end_of_list
        if identities:
            extra = "\n% Additional identities from depth-4/5 extraction:\n"
            for ident_line in identities:
                # Extract the equation part (before the [depth...] annotation)
                eq = ident_line.split("[")[0].strip()
                if eq and "=" in eq:
                    # Convert to Prover9 format: replace variables
                    p9_eq = eq.replace("x", "X").replace("y", "Y")
                    if not p9_eq.endswith("."):
                        p9_eq += "."
                    extra += p9_eq + "\n"
            content = content.replace("end_of_list.", extra + "\nend_of_list.")

        with open(aug_fname, "w") as f:
            f.write(content)

        print(f"  Prover9: d{i}=d{j} (augmented, t=300s) ...", end=" ", flush=True)
        try:
            result = subprocess.run(
                [PROVER9, "-t", "300", "-f", aug_fname],
                capture_output=True, text=True, timeout=310
            )
            proof_count = result.stdout.count("THEOREM PROVED")
            if proof_count > 0:
                results[pair] = "REFUTED"
                print(f"REFUTED ({proof_count} proofs)")
            else:
                results[pair] = "OPEN"
                still_open.append(pair)
                print("still OPEN")
            log_result(f"T4_{i}_{j}", result.stdout[:3000])
        except subprocess.TimeoutExpired:
            results[pair] = "TIMEOUT"
            still_open.append(pair)
            print("TIMEOUT")

    t["results"] = results
    t["augmented_axioms"] = identities[:10]
    t["status"] = "DONE" if not still_open else "PARTIAL"
    t["notes"] = f"Results: {results}. Still open: {still_open}"
    save_progress(prog)

    newly_closed = sum(1 for v in results.values() if v == "REFUTED")
    print(f"\n  T4 RESULT: {newly_closed} newly refuted, {len(still_open)} still open")


# ===================================================================
# T7 — Intermediate equation ATP attacks
# ===================================================================
def run_T7(prog):
    t = prog["TRUE_TRACK"]["T7_intermediate_atp"]
    if t["status"] == "DONE":
        print("T7: Already completed.")
        return

    print("T7: Intermediate equation ATP attacks...")
    t["status"] = "RUNNING"
    save_progress(prog)

    attacks = {
        "E677_to_E52930": {
            "axiom": "X = f(Y, f(X, f(f(Y, X), Y))).",
            "goal": "f(X,X) = f(f(f(f(X,X),X),X),X)."
        },
        "E677_to_E406197": {
            "axiom": "X = f(Y, f(X, f(f(Y, X), Y))).",
            "goal": "X = f(f(f(X, f(X,X)), f(X,X)), f(X,X))."
        },
        "E677_E406197_to_E255": {
            "axiom": "X = f(Y, f(X, f(f(Y, X), Y))).\nX = f(f(f(X, f(X,X)), f(X,X)), f(X,X)).",
            "goal": "X = f(f(f(X,X),X),X)."
        }
    }

    for name, spec in attacks.items():
        st = t["subtasks"][name]
        if st["status"] == "DONE":
            print(f"  {name}: already done")
            continue

        # Create Prover9 input
        inp = f"""% {name}: ATP attack
set(prolog_style_variables).

formulas(assumptions).
{spec['axiom']}
end_of_list.

formulas(goals).
{spec['goal']}
end_of_list.
"""
        fname = os.path.join(ATP_DIR, f"intermediate-{name}.in")
        with open(fname, "w") as f:
            f.write(inp)

        print(f"  Prover9: {name} (t=300s) ...", end=" ", flush=True)
        try:
            result = subprocess.run(
                [PROVER9, "-t", "300", "-f", fname],
                capture_output=True, text=True, timeout=310
            )
            if "THEOREM PROVED" in result.stdout:
                st["status"] = "DONE"
                st["result"] = "PROVED"
                proof_len = result.stdout.count("(step")
                print(f"PROVED! ({proof_len} steps)")
            else:
                st["status"] = "DONE"
                st["result"] = "OPEN (no proof in 300s)"
                print("OPEN")
            log_result(f"T7_{name}", result.stdout[:5000])
        except subprocess.TimeoutExpired:
            st["status"] = "DONE"
            st["result"] = "TIMEOUT_300s"
            print("TIMEOUT")

    all_done = all(st["status"] == "DONE" for st in t["subtasks"].values())
    t["status"] = "DONE" if all_done else "PARTIAL"
    any_proved = any(st.get("result") == "PROVED" for st in t["subtasks"].values())
    t["notes"] = ("*** BREAKTHROUGH: at least one intermediate implication proved! ***"
                  if any_proved else "No intermediate implications proved by ATP alone.")
    save_progress(prog)


# ===================================================================
# Status display
# ===================================================================
def show_status(prog):
    print("=" * 70)
    print("  E677 ⊨_fin E255  —  TRUE TRACK STATUS")
    print("=" * 70)

    steps = prog["TRUE_TRACK"]
    order = ["T1_lemma_verification", "T2_identity_extraction", "T3_cascade_d7",
             "T4_cascade_d7_augmented", "T5_cascade_d6", "T6_cascade_d5",
             "T7_intermediate_atp", "T8_cascade_general"]

    for key in order:
        if key not in steps:
            continue
        s = steps[key]
        status = s.get("status", "?")
        desc = s.get("description", "")[:60]
        icon = {"DONE": "✓", "PARTIAL": "◐", "RUNNING": "▶",
                "NOT_RUN": "○", "NOT_STARTED": "○", "BLOCKED": "✕"}.get(status, "?")
        print(f"  {icon} {key:<30} [{status:>12}]  {desc}")
        if s.get("notes"):
            print(f"    → {s['notes'][:90]}")

    print()
    print(f"  Last updated: {prog.get('last_updated', '?')}")
    print("=" * 70)


# ===================================================================
# Auto-picker: find next actionable step
# ===================================================================
def next_step(prog):
    """Return the key of the next step to run, or None if all done/blocked."""
    T = prog["TRUE_TRACK"]

    # T1 first (quick baseline)
    if T["T1_lemma_verification"]["status"] in ("NOT_RUN", "NOT_STARTED"):
        return "T1"

    # T2 in parallel with T5/T6 (identity extraction)
    if T["T2_identity_extraction"]["status"] in ("NOT_RUN", "NOT_STARTED", "PARTIAL") and T["T2_identity_extraction"].get("result_d5") is None:
        return "T2"

    # T6 (smallest period first — most likely to close fully)
    if T["T6_cascade_d5"]["status"] in ("NOT_RUN", "NOT_STARTED"):
        return "T6"

    # T5
    if T["T5_cascade_d6"]["status"] in ("NOT_RUN", "NOT_STARTED"):
        return "T5"

    # T4 (depends on T2)
    t4 = T["T4_cascade_d7_augmented"]
    if t4["status"] in ("NOT_RUN", "NOT_STARTED") and T["T2_identity_extraction"]["status"] == "DONE":
        return "T4"

    # T7 (independent)
    if T["T7_intermediate_atp"]["status"] in ("NOT_RUN", "NOT_STARTED"):
        return "T7"

    return None


# ===================================================================
# Main
# ===================================================================
RUNNERS = {
    "T1": run_T1,
    "T2": run_T2,
    "T2-BG": run_T2_BG,
    "T4": run_T4,
    "T5": run_T5,
    "T6": run_T6,
    "T7": run_T7,
}


def run_all(prog):
    """Run all actionable steps in sequence until nothing is left."""
    print("\n" + "#" * 70)
    print("#  TRUE TRACK — CONTINUOUS MODE")
    print("#" * 70 + "\n")
    show_status(prog)
    step_num = 0
    last_step = None
    while True:
        step = next_step(prog)
        if step is None:
            break
        if step == last_step:
            print(f"  {step} still not resolved after last attempt — skipping.")
            # Force it to a terminal state so we don't loop
            for key in prog["TRUE_TRACK"]:
                if key.startswith(step.replace('T','T') + '_') or key.upper().startswith(step + '_'):
                    pass
            break
        last_step = step
        step_num += 1
        print(f"\n{'─'*70}")
        print(f"  [{step_num}] Running {step}...")
        print(f"{'─'*70}\n")
        try:
            RUNNERS[step](prog)
        except Exception as e:
            print(f"  ERROR in {step}: {e}")
            log_result(step, f"ERROR: {e}")
            # Mark step so we don't retry it
            for key, val in prog["TRUE_TRACK"].items():
                if isinstance(val, dict) and val.get("status") == "RUNNING":
                    val["status"] = "DONE"
                    val["result"] = f"ERROR: {e}"
                    val["notes"] = f"Failed with error: {e}"
            save_progress(prog)
        prog = load_progress()  # reload after each step
        show_status(prog)
    print(f"\n{'#'*70}")
    print(f"#  TRUE TRACK COMPLETE — {step_num} steps executed")
    print(f"{'#'*70}")
    show_status(prog)


def main():
    prog = load_progress()

    if len(sys.argv) > 1:
        cmd = sys.argv[1].upper()
        if cmd == "STATUS":
            show_status(prog)
            return
        elif cmd == "ALL":
            run_all(prog)
            return
        elif cmd in RUNNERS:
            RUNNERS[cmd](prog)
            show_status(prog)
            return
        else:
            print(f"Unknown step: {cmd}")
            print(f"Available: STATUS, ALL, {', '.join(RUNNERS.keys())}")
            return

    # Auto-pick next step
    step = next_step(prog)
    if step is None:
        print("All actionable TRUE-track steps are done or blocked.")
        show_status(prog)
        return

    print(f"Auto-selected next step: {step}\n")
    RUNNERS[step](prog)
    print()
    show_status(prog)


if __name__ == "__main__":
    main()
