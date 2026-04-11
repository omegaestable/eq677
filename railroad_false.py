#!/usr/bin/env python3
"""
railroad_false.py — Counterexample-track execution railroad for E677 ⊭_fin E255.
================================================================================

Reads progress.json, determines the next actionable step on the FALSE track,
executes it, logs results back to progress.json.

Usage:
    python railroad_false.py             # auto-pick next step
    python railroad_false.py F2          # force a specific step
    python railroad_false.py status      # show current status only

Steps (in priority order):
    F2  — Mace4 direct search for E677 + ¬E255 model (no compilation needed)
    F3  — Fiber extension attacks over more DB bases
    F4  — Run construction audit from proof_candidates.py
    F6  — Install Rust (unblocks F1)
    F1  — DPLL search orbit_anti255 (needs Rust)
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
    # FALSE track now runs at normal priority, even in background mode.
    return 0


def ensure_f1_defaults(track):
    # thread_cap=0 means uncapped Rayon threads (use full machine parallelism).
    track.setdefault("thread_cap", 0)
    track.setdefault("batch_sizes", 20)
    track.setdefault("background_mode", False)
    track.setdefault("binary_path", os.path.join(ROOT, "target", "release", "eq677.exe"))


def build_f1_env(prog, track, background=False):
    env = os.environ.copy()
    env["LIBCLANG_PATH"] = env.get("LIBCLANG_PATH", r"C:\Program Files\LLVM\bin")
    llvm_bin = r"C:\Program Files\LLVM\bin"
    cargo_bin = os.path.dirname(prog["ENVIRONMENT"].get("cargo_path", r"C:\Users\nacho\.cargo\bin\cargo.exe"))
    env["PATH"] = f"{llvm_bin};{cargo_bin};" + env.get("PATH", "")
    thread_cap = int(track.get("thread_cap", 0))
    if thread_cap > 0:
        env["EQ677_RAYON_THREADS"] = str(thread_cap)
        env["RAYON_NUM_THREADS"] = str(thread_cap)
    else:
        env.pop("EQ677_RAYON_THREADS", None)
        env.pop("RAYON_NUM_THREADS", None)
    return env


def get_f1_binary_path(track):
    binary = track.get("binary_path") or os.path.join(ROOT, "target", "release", "eq677.exe")
    if not os.path.exists(binary):
        fallback = os.path.join(ROOT, "target", "release", "eq677")
        return fallback if os.path.exists(fallback) else binary
    return binary


def build_f1_binary(prog, track, background=False):
    cargo = prog["ENVIRONMENT"].get("cargo_path", "cargo")
    env = build_f1_env(prog, track, background=background)
    binary = get_f1_binary_path(track)
    if os.path.exists(binary):
        print("  Build skipped: existing release binary present.")
        return binary, True

    print("  Building release binary...")
    build_result = subprocess.run(
        [cargo, "build", "--release"],
        capture_output=True, text=True, timeout=300,
        cwd=ROOT, env=env,
        creationflags=creation_flags(background)
    )
    if build_result.returncode != 0:
        print(f"  BUILD FAILED: {build_result.stderr[:500]}")
        track["status"] = "BLOCKED"
        track["blocker"] = f"Build failed: {build_result.stderr[:200]}"
        log_result("F1_build", build_result.stdout + "\n" + build_result.stderr)
        save_progress(prog)
        return binary, False

    return get_f1_binary_path(track), True


def load_progress():
    with open(PROGRESS_FILE, "r") as f:
        return json.load(f)


def save_progress(prog):
    prog["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    prog["last_agent_session"] = "railroad_false"
    with open(PROGRESS_FILE, "w") as f:
        json.dump(prog, f, indent=2)


def ensure_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(ATP_DIR, exist_ok=True)


def log_result(step_id, content):
    ensure_dirs()
    logfile = os.path.join(LOG_DIR, f"{step_id}.log")
    with open(logfile, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{datetime.now().isoformat()}]\n")
        f.write(content)
        f.write("\n")
    print(f"  [logged to logs/{step_id}.log]")


# ===================================================================
# F2 — Mace4 direct: E677 + ¬E255
# ===================================================================
def create_anti255_mace4_input():
    """Create a Mace4 input file searching for E677-model violating E255."""
    content = """% Direct search: E677-magma where E255 fails.
% E677: x = y * (x * ((y*x) * y))
% E255: x = ((x*x)*x)*x
%
% We want a MODEL of E677 where E255 fails for some element.

set(prolog_style_variables).

formulas(assumptions).

% E677
X = f(Y, f(X, f(f(Y, X), Y))).

end_of_list.

formulas(goals).

% E255 — if Mace4 finds a model where this FAILS, we have a counterexample
X = f(f(f(X, X), X), X).

end_of_list.
"""
    fname = os.path.join(ATP_DIR, "anti255-direct.in")
    with open(fname, "w") as f:
        f.write(content)
    return fname


def run_F2(prog):
    t = prog["FALSE_TRACK"]["F2_mace4_direct"]
    if t["status"] == "DONE" and t.get("result") == "COUNTEREXAMPLE_FOUND":
        print("F2: COUNTEREXAMPLE ALREADY FOUND — check logs!")
        return

    print("F2: Mace4 direct search for E677 + ¬E255 models...")
    t["status"] = "RUNNING"
    save_progress(prog)

    fname = create_anti255_mace4_input()
    max_n_prev = t.get("max_n_searched") or 1

    # Search incrementally from where we left off
    results = {}
    max_n_target = 30  # Mace4 is unlikely to go beyond ~20 in reasonable time

    for n in range(max(2, max_n_prev + 1), max_n_target + 1):
        print(f"  Mace4 n={n} ...", end=" ", flush=True)
        timeout_sec = min(60 + n * 10, 600)  # scale timeout with size
        try:
            result = subprocess.run(
                [MACE4, "-n", str(n), "-N", str(n), "-t", str(timeout_sec), "-f", fname],
                capture_output=True, text=True, timeout=timeout_sec + 10
            )
            output = result.stdout

            if "Exiting with 1 model" in output:
                # COUNTEREXAMPLE FOUND!
                print(f"*** COUNTEREXAMPLE FOUND AT n={n}! ***")
                t["status"] = "DONE"
                t["result"] = "COUNTEREXAMPLE_FOUND"
                t["max_n_searched"] = n
                t["notes"] = f"COUNTEREXAMPLE at n={n}! E677-model violating E255. CHECK logs/F2.log!"
                log_result("F2", f"COUNTEREXAMPLE AT n={n}:\n{output}")
                save_progress(prog)
                return

            if "Exiting with 0 model" in output or result.returncode == 2:
                results[n] = "EXHAUSTED"
                print(f"exhausted (no E677+¬E255 model of size {n})")
            elif "TIMEOUT" in output.upper() or "time" in output.lower():
                results[n] = "TIMEOUT"
                print(f"timeout ({timeout_sec}s)")
                # Stop escalating if we're timing out
                if n >= 15:
                    print("  (stopping: timeouts at this size suggest Mace4 limit reached)")
                    break
            else:
                results[n] = f"OTHER (rc={result.returncode})"
                print(f"rc={result.returncode}")

            log_result(f"F2_n{n}", output[:3000])
            t["max_n_searched"] = n

        except subprocess.TimeoutExpired:
            results[n] = "HARD_TIMEOUT"
            print("hard timeout")
            t["max_n_searched"] = n
            if n >= 12:
                break

    t["status"] = "DONE"
    t["result"] = "NO_COUNTEREXAMPLE"
    t["notes"] = f"No E677+¬E255 model found for n ≤ {t['max_n_searched']}. Results: {results}"
    save_progress(prog)
    print(f"\n  F2 RESULT: No counterexample found up to n={t['max_n_searched']}")


# ===================================================================
# F3 — Fiber extension attacks
# ===================================================================
def run_F3(prog):
    t = prog["FALSE_TRACK"]["F3_fiber_extensions"]
    if t["status"] == "DONE":
        print("F3: Already completed.")
        return

    print("F3: Fiber extension attacks...")
    t["status"] = "RUNNING"
    save_progress(prog)

    # Check what scripts exist
    nonlinear_script = os.path.join(ROOT, "color-extensions-nonlinear.py")
    linear_script = os.path.join(ROOT, "color-extensions.py")

    if not os.path.exists(nonlinear_script):
        print("  ERROR: color-extensions-nonlinear.py not found.")
        t["status"] = "BLOCKED"
        t["notes"] = "color-extensions-nonlinear.py missing"
        save_progress(prog)
        return

    # Run nonlinear anti-255 on pending bases
    pending = t.get("pending_bases", ["29/0", "11/0", "13/0"])
    completed = t.get("completed_bases", {})

    for base in pending[:]:
        base_key = base.split(" ")[0]  # strip annotations like "(3 colorings)"
        if base_key in completed:
            continue

        print(f"\n  Fiber attack on base {base_key}...")
        # The nonlinear script needs specific arguments; log that we attempted
        log_result("F3", f"Attempting fiber extension on base {base_key} — requires manual configuration")
        print(f"  NOTE: {base_key} not yet configured in color-extensions-nonlinear.py.")
        print(f"  To add: define magma table + colorings for base {base_key} in the script.")

    t["status"] = "PARTIAL"
    t["notes"] = f"Completed bases: {list(completed.keys())}. Pending: {pending}. Manual config needed for new bases."
    save_progress(prog)


# ===================================================================
# F4 — Construction audit
# ===================================================================
def run_F4(prog):
    t = prog["FALSE_TRACK"]["F4_construction_audit"]
    if t["status"] == "DONE":
        print("F4: Already completed.")
        return

    print("F4: Running construction audit (proof_candidates.py includes this)...")
    t["status"] = "RUNNING"
    save_progress(prog)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "proof_candidates.py")],
        capture_output=True, text=True, timeout=600, env=env
    )

    output = result.stdout + "\n" + result.stderr
    log_result("F4", output)

    # Extract construction audit section
    in_audit = False
    audit_lines = []
    for line in output.split("\n"):
        if "CONSTRUCTION FAMILY AUDIT" in line:
            in_audit = True
        if in_audit:
            audit_lines.append(line)
        if in_audit and line.strip().startswith("=" * 10) and len(audit_lines) > 3:
            break

    t["status"] = "DONE"
    t["result"] = "\n".join(audit_lines) if audit_lines else "Audit section not found in output"

    # Count live vs partial vs conceptual
    live = output.count("LIVE")
    partial = output.count("PARTIAL")
    conceptual = output.count("CONCEPTUAL")
    t["notes"] = f"A1-A6 audit: {live} LIVE, {partial} PARTIAL, {conceptual} CONCEPTUAL attack vectors."
    save_progress(prog)
    print(f"  F4 RESULT: {live} LIVE, {partial} PARTIAL, {conceptual} CONCEPTUAL")


# ===================================================================
# F6 — Install Rust
# ===================================================================
def run_F6(prog):
    t = prog["FALSE_TRACK"]["F6_install_rust"]
    if t["status"] == "DONE":
        prog["ENVIRONMENT"]["cargo_installed"] = True
        if prog["ENVIRONMENT"].get("cargo_path"):
            prog["FALSE_TRACK"]["F1_dpll_search"]["status"] = "NOT_STARTED"
            prog["FALSE_TRACK"]["F1_dpll_search"]["blocker"] = None
            save_progress(prog)
        print("F6: Rust already installed.")
        return

    # Check if cargo is now available
    try:
        result = subprocess.run(["cargo", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            t["status"] = "DONE"
            t["notes"] = f"Cargo found: {result.stdout.strip()}"
            prog["ENVIRONMENT"]["cargo_installed"] = True
            prog["FALSE_TRACK"]["F1_dpll_search"]["status"] = "NOT_STARTED"
            prog["FALSE_TRACK"]["F1_dpll_search"]["blocker"] = None
            save_progress(prog)
            print(f"  Cargo already available: {result.stdout.strip()}")
            return
    except FileNotFoundError:
        pass

    # Check common locations
    cargo_paths = [
        os.path.expanduser(r"~\.cargo\bin\cargo.exe"),
        r"C:\Users\nacho\.cargo\bin\cargo.exe",
    ]
    for p in cargo_paths:
        if os.path.exists(p):
            t["status"] = "DONE"
            t["notes"] = f"Cargo found at {p} (not on PATH — add to PATH)"
            prog["ENVIRONMENT"]["cargo_installed"] = True
            prog["ENVIRONMENT"]["cargo_path"] = p
            prog["FALSE_TRACK"]["F1_dpll_search"]["status"] = "NOT_STARTED"
            prog["FALSE_TRACK"]["F1_dpll_search"]["blocker"] = None
            save_progress(prog)
            print(f"  Cargo found at {p}")
            print(f"  Add to PATH: $env:PATH += ';{os.path.dirname(p)}'")
            return

    print("F6: Rust is not installed.")
    print("  To install: Run in PowerShell (admin):")
    print("    winget install Rustlang.Rustup")
    print("  Or download from https://rustup.rs/")
    print()
    print("  After install, restart terminal and re-run this script.")
    t["status"] = "BLOCKED"
    t["notes"] = "Rust not installed. Run: winget install Rustlang.Rustup"
    save_progress(prog)


# ===================================================================
# F1 — DPLL search (needs Rust)
# ===================================================================
def run_F1(prog, background=False):
    t = prog["FALSE_TRACK"]["F1_dpll_search"]
    ensure_f1_defaults(t)
    if t.get("blocker"):
        print(f"F1: BLOCKED — {t['blocker']}")
        print("  Run 'python railroad_false.py F6' first to check/install Rust.")
        return

    if t["status"] == "DONE" and t.get("result") == "COUNTEREXAMPLE_FOUND":
        print("F1: COUNTEREXAMPLE ALREADY FOUND — check logs!")
        return

    print(f"F1: Building and running orbit_anti255_dpll (Rust DPLL search)...")

    binary, ok = build_f1_binary(prog, t, background=background)
    if not ok:
        return

    print("  Build OK. Starting search...")
    t["status"] = "RUNNING"
    t["blocker"] = None
    save_progress(prog)

    start_n = (t.get("max_n_completed") or 1) + 1
    batch_sizes = int(t.get("batch_sizes", 20))
    max_n = min(start_n + batch_sizes - 1, 255)
    env = build_f1_env(prog, t, background=background)

    for n in range(start_n, max_n + 1):
        print(f"  anti255 n={n} ...", end=" ", flush=True)
        timeout_sec = min(60 + n * n * 2, 1800)
        try:
            result = subprocess.run(
                [binary, "anti255-n", str(n)],
                capture_output=True, text=True, timeout=timeout_sec,
                cwd=ROOT, env=env,
                creationflags=creation_flags(background)
            )
            output = result.stdout + "\n" + result.stderr
            log_result(f"F1_n{n}", output[:5000])

            if "FOUND" in output.upper() or "model" in output.lower():
                # Potential counterexample!
                print(f"*** POTENTIAL COUNTEREXAMPLE AT n={n}! ***")
                t["status"] = "DONE"
                t["result"] = "COUNTEREXAMPLE_FOUND"
                t["max_n_completed"] = n
                t["notes"] = f"COUNTEREXAMPLE at n={n}! Check logs/F1_n{n}.log"
                save_progress(prog)
                return
            else:
                print(f"exhausted")
                t["max_n_completed"] = n
                t["result"] = "NO_COUNTEREXAMPLE_SO_FAR"
                cap_label = "unbounded" if int(t.get("thread_cap", 0)) <= 0 else str(t["thread_cap"])
                t["notes"] = f"Completed through n={n} with no counterexample. Thread cap={cap_label}."
                save_progress(prog)

        except subprocess.TimeoutExpired:
            print(f"timeout ({timeout_sec}s)")
            t["max_n_completed"] = n - 1
            t["notes"] = f"Timeout at n={n} ({timeout_sec}s). Completed up to n={n-1}."
            save_progress(prog)
            break

    t["status"] = "PARTIAL"
    t["result"] = "NO_COUNTEREXAMPLE"
    cap_label = "unbounded" if int(t.get("thread_cap", 0)) <= 0 else str(t["thread_cap"])
    t["notes"] = f"No E677+¬E255 model found for n ≤ {t['max_n_completed']}. Thread cap={cap_label}."
    save_progress(prog)
    print(f"\n  F1 RESULT: No counterexample for n ≤ {t['max_n_completed']}")


def run_F1_BG(prog):
    run_F1(prog, background=True)


# ===================================================================
# Status display
# ===================================================================
def show_status(prog):
    print("=" * 70)
    print("  E677 ⊨_fin E255  —  FALSE TRACK STATUS")
    print("=" * 70)

    steps = prog["FALSE_TRACK"]
    order = ["F1_dpll_search", "F2_mace4_direct", "F3_fiber_extensions",
             "F4_construction_audit", "F5_mace4_open_pairs", "F6_install_rust"]

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
# Auto-picker
# ===================================================================
def next_step(prog):
    F = prog["FALSE_TRACK"]

    # F4 is quick and informative
    if F["F4_construction_audit"]["status"] in ("NOT_RUN", "NOT_STARTED"):
        return "F4"

    # F2 is the fastest counterexample search (no compilation)
    if F["F2_mace4_direct"]["status"] in ("NOT_RUN", "NOT_STARTED"):
        return "F2"

    # F6 to unblock F1
    if F["F6_install_rust"]["status"] not in ("DONE",):
        return "F6"

    # F1 if Rust is available
    if F["F1_dpll_search"]["status"] in ("NOT_STARTED",) and not F["F1_dpll_search"].get("blocker"):
        return "F1"

    # F3 for more coverage
    if F["F3_fiber_extensions"]["status"] in ("NOT_RUN", "NOT_STARTED", "PARTIAL"):
        return "F3"

    return None


# ===================================================================
# Main
# ===================================================================
RUNNERS = {
    "F1": run_F1,
    "F1-BG": run_F1_BG,
    "F2": run_F2,
    "F3": run_F3,
    "F4": run_F4,
    "F6": run_F6,
}


def run_all(prog):
    """Run all actionable steps in sequence until nothing is left."""
    print("\n" + "#" * 70)
    print("#  FALSE TRACK — CONTINUOUS MODE")
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
            for key, val in prog["FALSE_TRACK"].items():
                if isinstance(val, dict) and val.get("status") == "RUNNING":
                    val["status"] = "DONE"
                    val["result"] = f"ERROR: {e}"
                    val["notes"] = f"Failed with error: {e}"
            save_progress(prog)
        prog = load_progress()  # reload after each step
        show_status(prog)
    print(f"\n{'#'*70}")
    print(f"#  FALSE TRACK COMPLETE — {step_num} steps executed")
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

    step = next_step(prog)
    if step is None:
        print("All actionable FALSE-track steps are done or blocked.")
        show_status(prog)
        return

    print(f"Auto-selected next step: {step}\n")
    RUNNERS[step](prog)
    print()
    show_status(prog)


if __name__ == "__main__":
    main()
