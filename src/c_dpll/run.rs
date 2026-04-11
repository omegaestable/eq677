use crate::c_dpll::*;

use std::sync::atomic::{AtomicUsize, Ordering};

const USE_COUNTER: bool = false;

fn threading_depth(n: E) -> E { n + 1 }

static RUNS_STARTED: AtomicUsize = AtomicUsize::new(0);
static RUNS_FINISHED: AtomicUsize = AtomicUsize::new(0);

pub fn c_run(n: usize, automs: Vec<Vec<E>>) {
    let models = split_models(build_ctxt(n, automs));
    into_par_for_each(models, |mut ctxt| {
        prerun(0, &mut ctxt);
    });
}

// Completes a partial magma.
pub fn c_complete(mpart: &MatrixMagma) {
    let n = mpart.n;
    let mut ctxt = build_ctxt(n, Vec::new());
    ctxt.nonfresh = n as _;
    for x in 0..n {
        for y in 0..n {
            let z = mpart.f(x, y);
            if z != usize::MAX {
                if prove_triple(x as E, y as E, z as E, &mut ctxt).is_err() { return }
            }
        }
    }
    if propagate(&mut ctxt).is_err() { return }

    prerun(0, &mut ctxt);
}

// Completes a partial magma, will try to extend if not possible.
pub fn c_complete_extended(m: &MatrixMagma) {
    for nn in m.n..m.n+30 {
        dbg!(nn);
        let mut m2 = MatrixMagma::undefined(nn);
        for x in 0..m.n {
            for y in 0..m.n {
                m2.set_f(x, y, m.f(x, y));
            }
        }
        c_complete(&m2);
    }
}

pub fn c_search() {
    for i in 0.. {
        c_run(i, Vec::new());
    }
}

pub fn c_run_anti255(n: usize) {
    let mut models = split_models(build_ctxt(n, Vec::new()));
    for m in &mut models {
        m.anti255_only = true;
    }
    into_par_for_each(models, |mut ctxt| {
        prerun(0, &mut ctxt);
    });
}

pub fn c_search_anti255(start: usize) {
    for n in start.. {
        eprintln!("[c_dpll_anti255] n={}", n);
        c_run_anti255(n);
    }
}

fn inc_counter(ctr: &AtomicUsize) {
    if !USE_COUNTER { return }

    let t = PRINT_MUTEX.lock().unwrap();
    ctr.fetch_add(1, Ordering::SeqCst);

    let started = RUNS_STARTED.load(Ordering::SeqCst);
    let finished = RUNS_FINISHED.load(Ordering::SeqCst);

    let running = started - finished;
    println!("running: {running}, finished: {finished}");
}

fn prerun(depth: E, ctxt: &mut Ctxt) {
    // No need to have a trail, we won't backtrack in the prerun.
    ctxt.trail.clear();

    if depth >= threading_depth(ctxt.n) {
        inc_counter(&RUNS_STARTED);

        main_branch(ctxt);

        inc_counter(&RUNS_FINISHED);
        return;
    }

    let Some((x, y)) = select_p(ctxt) else {
        submit_model(ctxt);
        return;
    };

    defresh(x, ctxt);
    defresh(y, ctxt);

    let count = ctxt.n.min(ctxt.nonfresh+1);
    range_for_each(count, |e| {
        if ctxt.classes_xz[idx(x, e, ctxt.n)].value != E::MAX { return }
        let c = &mut ctxt.clone();

        if prove_triple(x, y, e, c).is_err() { return }
        if propagate(c).is_err() { return }

        defresh(e, c);
        prerun(depth+1, c);
    });
}

fn score_c(c: CXY) -> i32 {
    match c {
        CXY::C11(..) => C11_SCORE,
        CXY::C12(..) => C12_SCORE,
        CXY::C21(..) => C21_SCORE,
        CXY::C22(..) => C22_SCORE,
    }
}

fn pos_score(x: E, y: E, ctxt: &Ctxt) -> i32 {
    let xi = x as i32;
    let yi = y as i32;
    let ni = ctxt.n as i32;
    ni * ni - xi * ni - yi
}

pub fn compute_base_score(x: E, y: E, ctxt: &Ctxt) -> i32 {
    let class = &ctxt.classes_xy[idx(x, y, ctxt.n)];
    let cs_score = class.cs.iter().map(|c| score_c(*c)).sum::<i32>();
    let x0_score = X0_SCORE * (x == 0) as i32;
    let pos_score = pos_score(x, y, ctxt);

    cs_score + x0_score + pos_score
}

// returns None if we are done.
fn select_p(ctxt: &Ctxt) -> Option<(E, E)> {
    // Should hold here:
    // check_score(ctxt);

    let mut best = (E::MAX, E::MAX);
    let mut best_score = -1;

    for x in 0..ctxt.n {
        let chosen_score = CHOSEN_SCORE * ctxt.chosen_per_row[x as usize] as i32;
        for y in 0..ctxt.n {
            let class = &ctxt.classes_xy[idx(x, y, ctxt.n)];
            let score = class.score + chosen_score;
            if (class.value == E::MAX) & (score > best_score) {
                best = (x, y);
                best_score = score;
            }
        }
    }

    if best_score == -1 { None }
    else { Some(best) }
}

fn submit_model(ctxt: &Ctxt) {
    if ctxt.anti255_only {
        let m = ctxt.matrix();
        if m.is255() { return; }
        present_model(ctxt.n as usize, "c_dpll_anti255", |x, y| {
            let i = idx(x as E, y as E, ctxt.n);
            ctxt.classes_xy[i].value as usize
        });
    } else {
        present_model(ctxt.n as usize, "c_dpll", |x, y| {
            let i = idx(x as E, y as E, ctxt.n);
            ctxt.classes_xy[i].value as usize
        });
    }
}

pub fn defresh(e: E, ctxt: &mut Ctxt) {
    if e >= ctxt.nonfresh {
        // assert!(e == ctxt.nonfresh);
        ctxt.nonfresh += 1;
        ctxt.trail.push(TrailEvent::Defresh);
    }
}

fn main_branch(ctxt: &mut Ctxt) {
    let Some((x, y)) = select_p(ctxt) else {
        submit_model(ctxt);
        become main_backtrack(ctxt);
    };

    defresh(x, ctxt);
    defresh(y, ctxt);

    if branch_options(x, y, 0, ctxt).is_ok() { become main_propagate(ctxt); }
    else { become main_backtrack(ctxt); }
}

// e is the next thing to try. If that doesn't work, we iterate from there.
fn branch_options(x: E, y: E, mut e: E, ctxt: &mut Ctxt) -> Result<(), ()> {
    let count = ctxt.n.min(ctxt.nonfresh+1);
    loop {
        if e >= count { return Err(()) }
        if ctxt.classes_xz[idx(x, e, ctxt.n)].value == E::MAX { break }
        e += 1;
    }
    ctxt.trail.push(TrailEvent::Decision(x, y, e));
    ctxt.chosen_per_row[x as usize] += 1;
    prove_triple(x, y, e, ctxt)?;

    // note: This defresh has to be after the decision point!
    // Otherwise it won't get re-freshed on backtracking.
    defresh(e, ctxt);

    Ok(())
}

fn main_backtrack(ctxt: &mut Ctxt) {
    ctxt.propagate_queue.clear();

    loop {
        let Some(event) = ctxt.trail.pop() else { return };
        match event {
            TrailEvent::Decision(x, y, e) => {
                ctxt.chosen_per_row[x as usize] -= 1;
                if branch_options(x, y, e+1, ctxt).is_ok() { become main_propagate(ctxt); }
            },
            TrailEvent::DefineClass(x, y) => {
                let z = std::mem::replace(&mut ctxt.classes_xy[idx(x, y, ctxt.n)].value, E::MAX);
                ctxt.classes_xz[idx(x, z, ctxt.n)].value = E::MAX;
                if y == z {
                    ctxt.yxx[y as usize] = E::MAX;
                }
            },
            TrailEvent::PushCXY(x, y) => {
                let class = &mut ctxt.classes_xy[idx(x, y, ctxt.n)];
                let c = class.cs.pop().unwrap();
                class.score -= score_c(c);
            }
            TrailEvent::PushCXZ(x, z) => {
                ctxt.classes_xz[idx(x, z, ctxt.n)].cs.pop().unwrap();
            }
            TrailEvent::Defresh => {
                ctxt.nonfresh -= 1;
            }
        }
    }
}

pub fn main_propagate(ctxt: &mut Ctxt) {
    match propagate(ctxt) {
        Ok(()) => become main_branch(ctxt),
        Err(()) => become main_backtrack(ctxt),
    }
}

pub fn prove_triple(x: E, y: E, z: E, ctxt: &mut Ctxt) -> Result<(), ()> {
    prove_triple_impl(x, y, z, ctxt)?;
    for g in ctxt.forced_automs.clone() {
        let (mut x, mut y, mut z) = (x, y, z);
        for _ in 0..ctxt.n {
            x = g[x as usize];
            y = g[y as usize];
            z = g[z as usize];
            prove_triple_impl(x, y, z, ctxt)?;
        }
    }
    Ok(())
}

pub fn prove_triple_impl(x: E, y: E, z: E, ctxt: &mut Ctxt) -> Result<(), ()> {
    let xy_ref = &mut ctxt.classes_xy[idx(x, y, ctxt.n)].value;
    let xy = *xy_ref;
    if xy == z { return Ok(()) }
    if xy != E::MAX { return Err(()) }

    let xz_ref = &mut ctxt.classes_xz[idx(x, z, ctxt.n)].value;
    if *xz_ref != E::MAX { return Err(()); }

    if y == z {
        if ctxt.yxx[z as usize] != E::MAX { return Err(()); }
        ctxt.yxx[z as usize] = x;
    }

    *xy_ref = z;
    *xz_ref = y;
    ctxt.trail.push(TrailEvent::DefineClass(x, y));
    ctxt.propagate_queue.push((x, y, z));
    Ok(())
}

pub fn propagate(ctxt: &mut Ctxt) -> Result<(), ()> {
    while let Some((x, y, z)) = ctxt.propagate_queue.pop() {
        // spawn constraints!
        let (a, b, ba) = (y, x, z);
        visit_c11(a, b, ba, ctxt)?;
        visit_c21(a, b, ba, ctxt)?;

        let i = idx(x, y, ctxt.n);
        let len = ctxt.classes_xy[i].cs.len();
        for j in 0..len {
            let c = ctxt.classes_xy[i].cs[j];
            progress_c(c, x, y, z, ctxt)?;
        }

        let i = idx(x, z, ctxt.n);
        let len = ctxt.classes_xz[i].cs.len();
        for j in 0..len {
            let CXZ(a,b) = ctxt.classes_xz[i].cs[j];
            // z = x*(a*b).
            prove_triple(a, b, y, ctxt)?;
        }
    }

    Ok(())
}

fn check_score(ctxt: &Ctxt) {
    for x in 0..ctxt.n {
        for y in 0..ctxt.n {
            let actual = compute_base_score(x, y, ctxt);
            let stored = ctxt.classes_xy[idx(x, y, ctxt.n)].score;
            assert_eq!(actual, stored);
        }
    }
}
