use crate::*;
use rayon::prelude::*;
use std::backtrace::Backtrace;
use std::sync::Once;
use std::sync::atomic::{AtomicU64, Ordering};

// This flag allows me to turn off multi-thrading globally.
// Useful for flamegraphs and deterministic debugging.
const PAR: bool = !cfg!(feature = "flamegraph");
static INIT_RAYON: Once = Once::new();

// Sleep injected between parallel work units for thermal throttling.
// Set by --sleep-ms <n> CLI flag before init_parallelism() is called.
pub static SLEEP_MS: AtomicU64 = AtomicU64::new(0);

pub fn maybe_sleep() {
    let ms = SLEEP_MS.load(Ordering::Relaxed);
    if ms > 0 {
        std::thread::sleep(std::time::Duration::from_millis(ms));
    }
}

// Call this inside tight inner loops to provide genuine duty-cycle throttling.
// Sleeps for SLEEP_MS every 100 calls per thread.
pub fn throttle_point() {
    let ms = SLEEP_MS.load(Ordering::Relaxed);
    if ms == 0 { return; }
    thread_local! {
        static CTR: std::cell::Cell<u32> = std::cell::Cell::new(0);
    }
    CTR.with(|c| {
        let v = c.get() + 1;
        if v >= 100 {
            c.set(0);
            std::thread::sleep(std::time::Duration::from_millis(ms));
        } else {
            c.set(v);
        }
    });
}

pub fn init_parallelism() {
    if !PAR {
        return;
    }

    INIT_RAYON.call_once(|| {
        let thread_count = std::env::var("EQ677_RAYON_THREADS")
            .ok()
            .or_else(|| std::env::var("RAYON_NUM_THREADS").ok())
            .and_then(|s| s.parse::<usize>().ok())
            .filter(|&n| n > 0);

        let mut builder = rayon::ThreadPoolBuilder::new();
        if let Some(n) = thread_count {
            builder = builder.num_threads(n);
            eprintln!("[parallel] rayon threads={n}");
        }
        let _ = builder.build_global();
    });
}

pub fn par_for_each<T>(x: &[T], f: impl Fn(&T) + Send + Sync) where T: Send + Sync + 'static {
    if PAR {
        x.par_iter().for_each(f);
    } else {
        x.iter().for_each(f);
    }
}

pub fn into_par_for_each<T>(x: Vec<T>, f: impl Fn(T) + Send + Sync) where T: Send {
    if PAR {
        x.into_par_iter().for_each(f);
    } else {
        x.into_iter().for_each(f);
    }
}

pub fn range_for_each(n: u8, f: impl Fn(u8) + Send + Sync) {
    if PAR {
        (0..n).into_par_iter().for_each(f);
    } else {
        for x in 0..n { f(x); }
    }
}

// This allows panic propagation even through rayon threads.
pub fn setup_panic_hook() {
    init_parallelism();
    std::panic::set_hook(Box::new(|info| {
        eprintln!("panic: {info}");
        // eprintln!("backtrace:\n{}", Backtrace::force_capture());
        std::process::abort(); // kill immediately
    }));
}
