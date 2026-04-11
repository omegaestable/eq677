use crate::*;

#[test]
fn test_db_conj() {
    for (_, m) in db() {
        conj(&m);
    }
}

#[test]
fn test_db_orbit_analysis() {
    for (name, m) in db() {
        println!("=== Model {}/{} (n={}) ===", name.0, name.1, m.n);
        orbit_report(&m);
    }
}

#[test]
fn test_db_component_analysis() {
    for (name, m) in db() {
        if m.n > 50 { continue } // skip large models for perf
        println!("=== Model {}/{} (n={}) ===", name.0, name.1, m.n);
        component_report(&m);
    }
}

pub fn conj(m: &MatrixMagma) {
    assert!(m.is677());
    assert!(m.is255());
    assert!(m.is_left_cancellative());

    conj_diag_orbit_size(m);
    conj_bijective_or_constant(m);
    conj_singleton_cycle(m);
    conj_2_orbit(m);
    conj_orbit_injective(m);
    conj_orbit_squaring(m);

    // false_conj_unique_cycle_size(m);
    // false_conj_cycle_size(m);
    // false_conj_cycles_summary(m);
    // false_conj_cycles_divide_n(m);
    // false_conj_not_rigid(m);
    // false_conj_cycle2(m);
    // false_conj_d_bij(m);
    // false_conj_right_cancellative(m);
    // false_conj_exists_idempotence(m);
    // false_conj_tinv_or_semitinv(m);
}

// Conjectures:

fn bij_to_cycles(n: usize, bij: impl Fn(usize) -> usize) -> Vec<Vec<usize>> {
    let mut out = Vec::new();

    let mut seen = vec![false; n];
    for mut i in 0..n {
        if seen[i] { continue }

        let mut current = vec![i];

        loop {
            seen[i] = true;
            i = bij(i);
            if seen[i] {
                out.push(std::mem::take(&mut current));
                break
            } else {
                current.push(i);
            }
        }
    }
    out
}

fn false_conj_tinv_or_semitinv(m: &MatrixMagma) {
    if m.n < 2 || m.n > 50 /* for perf */ { return }

    let grp = m.autom_group();
    for perm in grp {
        let c = bij_to_cycles(m.n, |i| perm[i]);
        if c.iter().any(|cyc| cyc.len() >= m.n-1) { return }
    }
    assert!(false);
}

fn false_conj_d_bij(m: &MatrixMagma) {
    if m.n == 496 { return }

    // claim: for any x, {f(f(y,x),y) | y in M} = M.
    let n = m.n;
    for x in 0..n {
        let mut opts = vec![false; n];
        for y in 0..n {
            let z = m.f(m.f(y, x), y);
            opts[z] = true;
        }
        assert!(opts.iter().all(|x| *x));
    }
}

fn conj_2_orbit(m: &MatrixMagma) {
    if m.n > 40 { return } // for performance

    if !is_prime(m.n) { return }

    let grp = m.autom_group();
    let orbits = orbits(&grp);
    let mut orbit_sizes = vec![0; m.n];
    for x in 0..m.n {
       orbit_sizes[orbits[x]] += 1;
    }
    orbit_sizes.sort();
    orbit_sizes.reverse();

    // either all in one orbit
    if orbit_sizes[0] == m.n { return }

    // or one singleton element.
    assert_eq!(orbit_sizes[0], m.n - 1);
    assert_eq!(orbit_sizes[1], 1);
    assert!(orbit_sizes[2..].iter().all(|x| *x == 0));
}

fn false_conj_autom(m: &MatrixMagma) {
    let expected = match m.n {
        0 => return,
        1 => 1,
        5 => 20,
        7 => 6,
        9 => 8,
        11 => 110,
        13 => 12,
        19 => 18,
        25 => return, // sometimes 500, sometimes 12000
        31 => return, // sometimes 30, sometimes 930
        // ...
        _ => return,
    };
    let real = m.autom_group().len();
    assert_eq!(expected, real);
}

fn false_conj_one_orbit(m: &MatrixMagma) {
    if m.n % 7 == 0 { return }
    let grp = m.autom_group();
    let orbits = orbits(&grp);
    if orbits.iter().any(|x| *x != 0) {
        println!("wrong:");
        m.cycle_dump();
        dbg!(&orbits);
        assert!(false);
    }
}

// conj_cycles_summary is a stronger version of this.
fn false_conj_cycles_divide_n(m: &MatrixMagma) {
    if m.n % 7 == 0 { return } // Why %7?

    let mut s = 0;
    for x in 0..m.n {
        for z in 0..m.n {
            s += (c_mini(m, x, z) == z) as usize;
        }
    }
    assert!(s % m.n == 0);
}

fn false_conj_cycles_summary(m: &MatrixMagma) {
    if m.n % 7 == 0 { return } // Why %7?

    let a = c_summary(m, 0);
    for x in 1..m.n {
        let b = c_summary(m, x);
        assert_eq!(a, b);
    }
}

// This property seems often true, but not always true.
fn false_conj_unique_cycle_size(m: &MatrixMagma) {
    if !is_prime(m.n) { return }

    let mut out = Vec::new();
    for x in 0..m.n {
        out.extend(c_summary(m, x));
    }
    out.sort();
    out.retain(|x| *x >= 3);
    out.dedup();
    assert!(out.len() <= 1);
}

// Falsified conjectures:

pub fn is_prime(n: usize) -> bool {
    if n < 2 { return false }

    for i in 2.. {
        if n%i == 0 { return false }
        if i*i > n { break }
    }
    true
}

fn false_conj_not_rigid(m: &MatrixMagma) {
    if m.n < 2 { return }

    // for performance
    if m.n > 80 { return }

    if m.autom_stats().grpsize() <= 1.5 {
        m.dump();
        panic!();
    }
}

// Note: This is equivalent to 255, as you can see here:
// https://teorth.github.io/equational_theories/blueprint/677-chapter.html
fn conj_singleton_cycle(m: &MatrixMagma) {
    if m.n == 0 { return }

    for x in 0..m.n {
        assert!((0..m.n).any(|y| m.f(y, x) == x));
    }
}

fn conj_bijective_or_constant(m: &MatrixMagma) {
    // only applies to primitive models.
    // if decompose(&m).len() > 0 { return }

    // This is a much cheaper check though:
    if !is_prime(m.n) { return }

    assert!(m.is_diag_bijective() || m.is_diag_constant());
}

fn false_conj_exists_idempotence(m: &MatrixMagma) {
    if m.n == 0 { return }

    for x in 0..m.n {
        if m.f(x, x) == x { return }
    }
    assert!(false);
}

fn false_conj_odd(m: &MatrixMagma) {
    assert!(m.n % 2 == 1 || m.n == 0);
}

fn false_conj_right_cancellative(m: &MatrixMagma) {
    if m.n == 496 { return }

    assert!(m.is_right_cancellative());
}

fn conj_diag_orbit_size(m: &MatrixMagma) {
    if !m.is_diag_bijective() { return }

    for x in 0..m.n {
        let mut y = x;
        let mut i = 0;
        // i is the smallest positive number, s.t. S^i x = x, where S x = x*x
        loop {
            y = m.f(y, y);
            i += 1;
            if x == y { break }
        }
        // Known values: 1, 3, 4, 5, 6, 7, 12, 18.
        // We know that 2 is impossible. 0*0 = 1 /\ 1*1 = 0 -> 0=1.
        assert!(i != 8);
    }
}

fn false_conj_cycle_size(m: &MatrixMagma) {
    for x in 0..m.n {
        for z in 0..m.n {
            let i = c(m, x, z);
            // Known values for i:
            // assert!(i == 1 || i == 2 || i == 4 || i == 5 || i == 6 || i == 7 || i == 8 || i == 9
            //     || i == 10 || i == 12 || i == 14 || i == 15 || i == 18
            //     || i == 21 || i == 36 || i == 42 || i == 48 || i == 49);
        }
    }
}

fn false_conj_cycle2(m: &MatrixMagma) {
    for x in 0..m.n {
        for y in 0..m.n {
            let a = m.f(x, y);
            if a == y { continue }

            let a = m.f(x, a);
            let a = m.f(x, a);
            assert!(a != y);
        }
    }
}

// Helpers:

// returns how often I need to left-multiply x onto z, until it becomes z again.
fn c(m: &MatrixMagma, x: usize, z: usize) -> u32 {
    let mut zz = z;
    let mut i = 0;
    loop {
        zz = m.f(x, zz);
        i += 1;
        if z == zz { break }
    }
    i
}

// Finds the minimal (i.e. canonical) element from the C(x, z) cycle.
fn c_mini(m: &MatrixMagma, x: usize, z: usize) -> usize {
    let mut zz = z;
    let mut mini = z;

    loop {
        zz = m.f(x, zz);
        if z == zz { break }
        if zz < mini { mini = zz; }
    }
    mini
}

fn c_summary(m: &MatrixMagma, x: usize) -> Vec<u32> {
    let mut v = Vec::new();
    for z in 0..m.n {
        // We only consider the representatives of each cycle!
        if c_mini(m, x, z) == z {
            v.push(c(m, x, z));
        }
    }
    v.sort();
    v
}

// 255 is equivalent to this function always returning 1 or 3.
fn right_cycle(m: &MatrixMagma, x: usize) -> usize {
    let mut a = x;
    let mut c = 0;
    loop {
        a = m.f(a, x);
        c += 1;
        if a == x { break }
    }
    c
}

// McKenna orbit analysis:
// For element x, define:
//   c_0 = x, c_{k+1} = x ◇ c_k  (i.e., c_k = L_x^k(x))
//   d_k = c_k ◇ x
// The orbit period d is the smallest positive k with c_k = x.
// E255 is equivalent to: for all x, the map k ↦ d_k is injective on Z/dZ.
// Known identity from E677: c_{d-4} ◇ c_{d-4} = c_{d-5} (for d >= 5).

/// Returns the orbit sequence [c_0, c_1, ..., c_{d-1}] where c_k = L_x^k(x).
pub fn orbit_c_seq(m: &MatrixMagma, x: usize) -> Vec<usize> {
    let mut seq = vec![x];
    let mut cur = x;
    loop {
        cur = m.f(x, cur);
        if cur == x { break }
        seq.push(cur);
    }
    seq
}

/// Returns the d-sequence [d_0, d_1, ..., d_{d-1}] where d_k = c_k ◇ x.
pub fn orbit_d_seq(m: &MatrixMagma, x: usize) -> Vec<usize> {
    orbit_c_seq(m, x).iter().map(|&ck| m.f(ck, x)).collect()
}

/// Check if the d-sequence is injective (equivalent to E255).
fn orbit_d_injective(m: &MatrixMagma, x: usize) -> bool {
    let d_seq = orbit_d_seq(m, x);
    let mut seen = vec![false; m.n];
    for &dk in &d_seq {
        if seen[dk] { return false }
        seen[dk] = true;
    }
    true
}

/// Verify the squaring identity: c_{d-4} ◇ c_{d-4} = c_{d-5} for d >= 5.
fn orbit_squaring_identity(m: &MatrixMagma, x: usize) -> bool {
    let c_seq = orbit_c_seq(m, x);
    let d = c_seq.len();
    if d < 5 { return true }
    let c_dm4 = c_seq[d - 4];
    let c_dm5 = c_seq[d - 5];
    m.f(c_dm4, c_dm4) == c_dm5
}

/// Assert orbit d-injectivity for all elements (conjecture equivalent to E255).
fn conj_orbit_injective(m: &MatrixMagma) {
    for x in 0..m.n {
        assert!(orbit_d_injective(m, x),
            "orbit d-sequence not injective for x={} in model of size {}", x, m.n);
    }
}

/// Assert squaring identity for all elements.
fn conj_orbit_squaring(m: &MatrixMagma) {
    for x in 0..m.n {
        assert!(orbit_squaring_identity(m, x),
            "squaring identity failed for x={} in model of size {}", x, m.n);
    }
}

/// Print detailed orbit analysis report for a magma.
pub fn orbit_report(m: &MatrixMagma) {
    let mut orbit_periods: Vec<usize> = Vec::new();
    let mut all_d_inj = true;
    let mut all_sq_ok = true;

    for x in 0..m.n {
        let c_seq = orbit_c_seq(m, x);
        let d = c_seq.len();
        let d_inj = orbit_d_injective(m, x);
        let sq_ok = orbit_squaring_identity(m, x);

        orbit_periods.push(d);
        all_d_inj &= d_inj;
        all_sq_ok &= sq_ok;

        if !d_inj || !sq_ok || m.n <= 31 {
            let d_seq = orbit_d_seq(m, x);
            println!("  x={}: period={}, d_inj={}, sq_ok={}", x, d, d_inj, sq_ok);
            if d <= 40 {
                println!("    c: {:?}", c_seq);
                println!("    d: {:?}", d_seq);
            }
        }
    }

    orbit_periods.sort();
    orbit_periods.dedup();
    println!("  orbit_periods={:?} d_inj={} sq_ok={}", orbit_periods, all_d_inj, all_sq_ok);
}

// Component structure analysis:
// Analyze L_x permutation cycle types, squaring map, and interaction structure.

/// Returns the cycle type (sorted cycle lengths) of the permutation L_x.
fn lx_cycle_type(m: &MatrixMagma, x: usize) -> Vec<usize> {
    let cycles = bij_to_cycles(m.n, |z| m.f(x, z));
    let mut lengths: Vec<usize> = cycles.iter().map(|c| c.len()).collect();
    lengths.sort();
    lengths
}

/// Returns the cycle structure of the squaring map S: x → x◇x.
fn squaring_map_cycles(m: &MatrixMagma) -> Vec<Vec<usize>> {
    bij_to_cycles(m.n, |x| m.f(x, x))
}

/// Print component structure report for a magma.
pub fn component_report(m: &MatrixMagma) {
    println!("Component structure for size {} model:", m.n);

    // 1. Classify L_x by cycle type
    let mut type_groups: std::collections::BTreeMap<Vec<usize>, Vec<usize>> = std::collections::BTreeMap::new();
    for x in 0..m.n {
        let ct = lx_cycle_type(m, x);
        type_groups.entry(ct).or_default().push(x);
    }
    println!("  L_x cycle type classes:");
    for (ct, elems) in &type_groups {
        println!("    {:?} => {} elements: {:?}", ct, elems.len(),
            if elems.len() <= 20 { format!("{:?}", elems) } else { format!("[{}, ..., {}]", elems[0], elems[elems.len()-1]) });
    }

    // 2. Squaring map S(x) = x◦x
    if m.is_diag_bijective() {
        let sq_cycles = squaring_map_cycles(m);
        let mut sq_lengths: Vec<usize> = sq_cycles.iter().map(|c| c.len()).collect();
        sq_lengths.sort();
        println!("  squaring map (bijective): cycle_type={:?}", sq_lengths);
        let fixed: Vec<usize> = (0..m.n).filter(|&x| m.f(x, x) == x).collect();
        if !fixed.is_empty() {
            println!("  idempotent elements: {:?}", fixed);
        }
    } else {
        let image_size = {
            let mut img = vec![false; m.n];
            for x in 0..m.n { img[m.f(x, x)] = true; }
            img.iter().filter(|&&b| b).count()
        };
        println!("  squaring map: non-bijective, image_size={}", image_size);
    }

    // 3. Check pairwise commutativity of L_x
    let mut commuting_pairs = 0usize;
    let total_pairs = m.n * (m.n - 1) / 2;
    for x in 0..m.n {
        for y in (x+1)..m.n {
            let all_commute = (0..m.n).all(|z| m.f(x, m.f(y, z)) == m.f(y, m.f(x, z)));
            if all_commute { commuting_pairs += 1; }
        }
    }
    println!("  L_x commutativity: {}/{} pairs commute", commuting_pairs, total_pairs);
}

impl MatrixMagma {
    pub fn is_left_cancellative(&self) -> bool {
        for a in 0..self.n {
            for b in 0..self.n {
                for c in 0..self.n {
                    // a*b = a*c -> b = c.
                    if b != c && self.f(a, b) == self.f(a, c) { return false }
                }
            }
        }
        true
    }

    pub fn is_right_cancellative(&self) -> bool {
        for a in 0..self.n {
            for b in 0..self.n {
                for c in 0..self.n {
                    // b*a = c*a -> b = c
                    if b != c && self.f(b, a) == self.f(c, a) { return false }
                }
            }
        }
        true
    }

    pub fn is_diag_constant(&self) -> bool {
        for x in 0..self.n {
            for y in 0..self.n {
                if self.f(x, x) != self.f(y, y) { return false }
            }
        }
        true
    }

    pub fn is_diag_bijective(&self) -> bool {
        for x in 0..self.n {
            for y in 0..self.n {
                if x == y { continue }
                if self.f(x, x) == self.f(y, y) { return false }
            }
        }
        true
    }

    pub fn is_idempotent(&self) -> bool {
        for x in 0..self.n {
            if x != self.f(x, x) { return false }
        }
        true
    }

    // For tinv models, this is equivalent to h=h⁻¹.
    pub fn is_double_left_inverse(&self) -> bool {
        for x in 0..self.n {
            for y in 0..self.n {
                if self.f(x, self.f(x, y)) != y { return false }
            }
        }
        true
    }

    pub fn is_double_right_inverse(&self) -> bool {
        for x in 0..self.n {
            for y in 0..self.n {
                if self.f(self.f(y, x), x) != y { return false }
            }
        }
        true
    }
}
