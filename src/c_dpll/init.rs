use crate::c_dpll::*;

pub fn build_ctxt(n: usize, automs: Vec<Vec<E>>) -> Ctxt {
    let class_xy = ClassXY {
        value: E::MAX,
        cs: SmallVec::new(),
        score: -1,
    };
    let class_xz = ClassXZ {
        value: E::MAX,
        cs: SmallVec::new(),
    };
    let mut ctxt = Ctxt {
        trail: Vec::new(),
        n: n as E,
        classes_xz: std::iter::repeat(class_xz)
            .take(n*n)
            .collect(),
        classes_xy: std::iter::repeat(class_xy)
            .take(n*n)
            .collect(),
        nonfresh: if automs.is_empty() { 0 } else { n as E },
        propagate_queue: Vec::new(),
        chosen_per_row: std::iter::repeat(0).take(n).collect(),
        yxx: std::iter::repeat(E::MAX).take(n).collect(),
        forced_automs: automs,
        anti255_only: false,
    };
    for x in 0..ctxt.n {
        for y in 0..ctxt.n {
            ctxt.classes_xy[idx(x, y, ctxt.n)].score = compute_base_score(x, y, &ctxt);
        }
    }
    ctxt
}
