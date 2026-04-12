use crate::*;

// Orbit-biased anti-E255 DPLL search.
//
// This is the "orbit-d collision" search family: it searches for finite
// E677-satisfying magmas in which d-injectivity FAILS — i.e., a magma
// that witnesses the gap in the L3 proof attempt (see proof_candidates.py).
//
// Architecture: reuses the eq_dpll constraint graph (full E677 constraints on
// an n×n table) but with two modifications baked into the context:
//
//  * orbit_bias = true  — scores cells (x, 0) and (0, x) very highly so the
//    L_0 orbit and d-sequence  d_k = f(c_k, 0)  are committed before
//    unrelated off-orbit cells.  Once d-sequence values are fixed, the
//    E677 propagation engine can detect and prune infeasible collision setups
//    earlier than in the generic eq_dpll order.
//
//  * anti255_only = true — at submit_model, the completed table is checked
//    for E255; only tables where E255 fails are reported.
//
// Search order: we iterate n = 0, 1, 2, ...  For each n, the split_models
// optimisation creates two branches: the non-idempotent seed (f(0,0)=1)
// and the all-idempotent seed (f(i,i)=i).  The all-idempotent branch has
// trivial orbits of period 1 and will quickly terminate as UNSAT (no
// anti-255 witnesses exist there).  The non-idempotent branch is where the
// interesting search happens.

pub fn orbit_anti255_run(n: usize) {
    let ctxt = build_orbit_anti255_ctxt(n);
    let models = split_eq_models(ctxt);
    // maybe_sleep() here throttles between the top-level split branches only,
    // not recursively inside the tree. This is the right granularity for --sleep-ms.
    into_par_for_each(models, |ctxt| {
        mainloop(ctxt);
        maybe_sleep();
    });
}

pub fn orbit_anti255_search() {
    for n in 0.. {
        eprintln!("[orbit_anti255] n={}", n);
        orbit_anti255_run(n);
    }
}
