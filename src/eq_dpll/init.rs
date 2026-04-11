use crate::eq_dpll::*;

pub(crate) fn build_ctxt(n: usize) -> Ctxt {
    let mut ctxt = Ctxt::default();
    ctxt.n = n;
    ctxt.fresh = vec![true; n];
    ctxt.table = vec![ElemId::MAX; n*n];
    ctxt.pos_terms = vec![Vec::new(); n*n];
    add_constraints(&mut ctxt);
    ctxt
}

/// Build a context configured for orbit-biased anti-255 search.
/// Sets orbit_bias=true so cells (x,0) and (0,x) are prioritised by the
/// scorer, wiring up the L_0 orbit and d-sequence before unrelated cells.
/// Sets anti255_only=true so only models where E255 fails are emitted.
pub(crate) fn build_ctxt_orbit_anti255(n: usize) -> Ctxt {
    let mut ctxt = build_ctxt(n);
    ctxt.anti255_only = true;
    ctxt.orbit_bias = true;
    ctxt
}

fn add_constraints(ctxt: &mut Ctxt) {
    let n = ctxt.n;
    let mut xs = Vec::new();
    for x_id in 0..n {
        xs.push(build_elem(x_id, ctxt));
    }
    for x_id in 0..n {
        for y_id in 0..n {
            let x = xs[x_id];
            let y = xs[y_id];
            let yx = build_f(y, x, ctxt);

            let t = build_f(yx, y, ctxt);
            let t = build_f(x, t, ctxt);
            let t = build_f(y, t, ctxt);
            build_assert(x_id, t, ctxt);

            let t = build_f(y, yx, ctxt);
            let t = build_f(t, y, ctxt);
            let t = build_f(yx, t, ctxt);
            build_assert(x_id, t, ctxt);
        }
    }
}

fn build_elem(e: ElemId, ctxt: &mut Ctxt) -> TermId {
    ctxt.classes.push(Class {
        node: Node::Elem(e),
        parents: SmallVec::new(),
        value: Some(e),
    });
    TermId(ctxt.classes.len() - 1)
}

fn build_f(l: TermId, r: TermId, ctxt: &mut Ctxt) -> TermId {
    ctxt.classes.push(Class {
        node: Node::F(l, r),
        parents: SmallVec::new(),
        value: None,
    });
    let out = TermId(ctxt.classes.len() - 1);
    ctxt.classes[l.0].parents.push(out);
    if l != r {
        ctxt.classes[r.0].parents.push(out);
    }

    if let (Node::Elem(l), Node::Elem(r)) = (&ctxt.classes[l.0].node, &ctxt.classes[r.0].node) {
        ctxt.pos_terms[idx((*l, *r), ctxt.n)].push(out);
    }

    out
}

fn build_assert(l: ElemId, r: TermId, ctxt: &mut Ctxt) {
    ctxt.classes.push(Class {
        node: Node::AssertEq(l, r),
        parents: SmallVec::new(),
        value: None,
    });
    let out = TermId(ctxt.classes.len() - 1);
    ctxt.classes[r.0].parents.push(out);
}
