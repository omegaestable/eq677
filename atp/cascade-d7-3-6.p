% Auto-generated cascade-gap refutation for orbit period d=7.
% Target: show E677 + left-cancel + L1 + L2b + collision => FALSE.

% E677 (two equivalent forms).
cnf(eq677_1, axiom, X = f(Y, f(X, f(f(Y, X), Y)))).
cnf(eq677_2, axiom, X = f(f(Y, X), f(f(Y, f(Y, X)), Y))).

% Left-cancellativity via left-inverse function g.
cnf(left_cancel, axiom, g(X, f(X, Y)) = Y).

% Orbit of element a, period 7.
% c_0 = a, c_{k+1} = f(a, c_k), c_7 = a.
cnf(c0_def, axiom, c0 = a).
cnf(c1_def, axiom, f(a, c0) = c1).
cnf(c2_def, axiom, f(a, c1) = c2).
cnf(c3_def, axiom, f(a, c2) = c3).
cnf(c4_def, axiom, f(a, c3) = c4).
cnf(c5_def, axiom, f(a, c4) = c5).
cnf(c6_def, axiom, f(a, c5) = c6).
cnf(c_period, axiom, f(a, c6) = a).

% All orbit elements are distinct.
cnf(dist_0_1, axiom, c0 != c1).
cnf(dist_0_2, axiom, c0 != c2).
cnf(dist_0_3, axiom, c0 != c3).
cnf(dist_0_4, axiom, c0 != c4).
cnf(dist_0_5, axiom, c0 != c5).
cnf(dist_0_6, axiom, c0 != c6).
cnf(dist_1_2, axiom, c1 != c2).
cnf(dist_1_3, axiom, c1 != c3).
cnf(dist_1_4, axiom, c1 != c4).
cnf(dist_1_5, axiom, c1 != c5).
cnf(dist_1_6, axiom, c1 != c6).
cnf(dist_2_3, axiom, c2 != c3).
cnf(dist_2_4, axiom, c2 != c4).
cnf(dist_2_5, axiom, c2 != c5).
cnf(dist_2_6, axiom, c2 != c6).
cnf(dist_3_4, axiom, c3 != c4).
cnf(dist_3_5, axiom, c3 != c5).
cnf(dist_3_6, axiom, c3 != c6).
cnf(dist_4_5, axiom, c4 != c5).
cnf(dist_4_6, axiom, c4 != c6).
cnf(dist_5_6, axiom, c5 != c6).

% d-sequence: d_k = f(c_k, a).
cnf(d0_def, axiom, f(c0, a) = d0).
cnf(d1_def, axiom, f(c1, a) = d1).
cnf(d2_def, axiom, f(c2, a) = d2).
cnf(d3_def, axiom, f(c3, a) = d3).
cnf(d4_def, axiom, f(c4, a) = d4).
cnf(d5_def, axiom, f(c5, a) = d5).
cnf(d6_def, axiom, f(c6, a) = d6).

% L1 recurrence: c_{k-1} = f(c_k, d_{k+1})  [mod d].
cnf(l1_k0, axiom, f(c0, d1) = c6).
cnf(l1_k1, axiom, f(c1, d2) = a).
cnf(l1_k2, axiom, f(c2, d3) = c1).
cnf(l1_k3, axiom, f(c3, d4) = c2).
cnf(l1_k4, axiom, f(c4, d5) = c3).
cnf(l1_k5, axiom, f(c5, d6) = c4).
cnf(l1_k6, axiom, f(c6, d0) = c5).

% L2b anchor: d_{d-2} = a, i.e., d_5 = a.
cnf(l2b_anchor, axiom, d5 = a).

% Squaring identity: f(c_{d-4}, c_{d-4}) = c_{d-5}.
cnf(squaring_id, axiom, f(c3, c3) = c2).

% COLLISION HYPOTHESIS: d_3 = d_6.
cnf(collision, axiom, d3 = d6).

% The prover should derive FALSE (refutation).
