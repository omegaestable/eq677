#![feature(explicit_tail_calls)]

#![allow(unused)] // heh
#![allow(private_interfaces)]
#![allow(irrefutable_let_patterns)]

mod magma;
pub use magma::*;

mod matrix;
pub use matrix::*;

mod eq_dpll;
pub use eq_dpll::*;

mod sym_dpll;
pub use sym_dpll::*;

mod tinv_dpll;
pub use tinv_dpll::*;

mod semitinv_dpll;
pub use semitinv_dpll::*;

mod c_dpll;
pub use c_dpll::*;

mod composite;
pub use composite::*;

mod db;
pub use db::*;

mod conj;
pub use conj::*;

mod parallel;
pub use parallel::*;

mod present;
pub use present::*;

mod search;
pub use search::*;

mod kb;
pub use kb::*;

mod twee;
pub use twee::*;

mod twee_sys;
pub use twee_sys::*;

mod timer;
pub use timer::*;

mod fo;
pub use fo::*;

mod analysis;
pub use analysis::*;

mod one_orbit;
pub use one_orbit::*;

mod one_orbit2;
pub use one_orbit2::*;

mod autom_search;
pub use autom_search::*;

mod load;
pub use load::*;

mod check;
pub use check::*;

mod prop_combo;
pub use prop_combo::*;

mod orbit_dpll;
pub use orbit_dpll::*;

mod enumerate;
pub use enumerate::*;

mod combine;
pub use combine::*;

mod uf;
pub use uf::*;

fn main() {
    setup_panic_hook();
    init_parallelism();
    let _timer = Timer::new();

    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(|s| s.as_str()) {
        Some("anti255") => {
            // Orbit-biased DPLL search for E677 ∧ ¬E255 models.
            // Optional second arg: starting size (default 0).
            let start: usize = args.get(2)
                .and_then(|s| s.parse().ok())
                .unwrap_or(0);
            for n in start.. {
                eprintln!("[orbit_anti255] n={}", n);
                orbit_anti255_run(n);
            }
        }
        Some("anti255-n") => {
            // Single size anti-255 search.
            let n: usize = args.get(2)
                .expect("usage: eq677 anti255-n <size>")
                .parse()
                .expect("size must be a number");
            eprintln!("[orbit_anti255] n={}", n);
            orbit_anti255_run(n);
        }
        Some("c-anti255") => {
            // c_dpll-based search for E677 ∧ ¬E255 models (partial-model composition).
            // Optional second arg: starting size (default 0).
            let start: usize = args.get(2)
                .and_then(|s| s.parse().ok())
                .unwrap_or(0);
            c_search_anti255(start);
        }
        Some("c-anti255-n") => {
            // Single size c_dpll anti-255 search.
            let n: usize = args.get(2)
                .expect("usage: eq677 c-anti255-n <size>")
                .parse()
                .expect("size must be a number");
            eprintln!("[c_dpll_anti255] n={}", n);
            c_run_anti255(n);
        }
        Some("eq-dpll") => {
            let n: usize = args.get(2)
                .expect("usage: eq677 eq-dpll <size>")
                .parse()
                .expect("size must be a number");
            eq_run(n);
        }
        _ => {
            one_orbit2_run();
        }
    }
}
