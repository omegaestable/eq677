% cascade-gap.p
% =============
% Goal: derive a contradiction from E677 + left-cancellativity + the hypothesis
% that d-injectivity fails, using the cascade argument and the L2b anchor.
%
% Setup:  We work in a FINITE E677-magma.  Suppose element 'a' has orbit
% period d >= 6.  The c-sequence is c_0=a, c_{k+1}=f(a,c_k), period d.
% The d-sequence is d_k = f(c_k, a).
%
% We assume:
%   1. E677 (two equivalent forms)
%   2. Left-cancellativity: f(x,y)=f(x,z) => y=z
%   3. L1 (provable): c_{k-1} = f(c_k, d_{k+1})   [indices mod d]
%   4. L2b (provable): f(c_{d-2}, a) = a            [anchor: d_{d-2} = a]
%   5. A d-sequence collision: d_i = d_j for some i != j  [NEGATION of E255]
%
% Target: derive FALSE (refutation), proving no such magma can exist.
%
% We instantiate with a concrete orbit period d=7 (smallest non-trivial case,
% since d in {1} union {>=6}).  c_0..c_6 are the orbit, d_0..d_6 the d-values.

% =========================================================================
% E677 (two equational axioms, universally quantified)
% =========================================================================
cnf(eq677_form1, axiom, X = f(Y, f(X, f(f(Y, X), Y)))).
cnf(eq677_form2, axiom, X = f(f(Y, X), f(f(Y, f(Y, X)), Y))).

% =========================================================================
% Left-cancellativity (functional: for any fixed first argument)
% We cannot state the full implication in CNF easily, so we provide it
% via a left-inverse function g: g(x, f(x, y)) = y.
% This is equivalent to left-cancellativity in the finite case.
% =========================================================================
cnf(left_cancel, axiom, g(X, f(X, Y)) = Y).

% =========================================================================
% Orbit structure for element a, period d=7.
% c_0 = a, c_{k+1} = f(a, c_k), c_7 = a (period).
% =========================================================================
cnf(c0_def, axiom, c0 = a).
cnf(c1_def, axiom, f(a, c0) = c1).
cnf(c2_def, axiom, f(a, c1) = c2).
cnf(c3_def, axiom, f(a, c2) = c3).
cnf(c4_def, axiom, f(a, c3) = c4).
cnf(c5_def, axiom, f(a, c4) = c5).
cnf(c6_def, axiom, f(a, c5) = c6).
cnf(c_period, axiom, f(a, c6) = a).

% All orbit elements are distinct.
cnf(dist_01, axiom, c0 != c1).
cnf(dist_02, axiom, c0 != c2).
cnf(dist_03, axiom, c0 != c3).
cnf(dist_04, axiom, c0 != c4).
cnf(dist_05, axiom, c0 != c5).
cnf(dist_06, axiom, c0 != c6).
cnf(dist_12, axiom, c1 != c2).
cnf(dist_13, axiom, c1 != c3).
cnf(dist_14, axiom, c1 != c4).
cnf(dist_15, axiom, c1 != c5).
cnf(dist_16, axiom, c1 != c6).
cnf(dist_23, axiom, c2 != c3).
cnf(dist_24, axiom, c2 != c4).
cnf(dist_25, axiom, c2 != c5).
cnf(dist_26, axiom, c2 != c6).
cnf(dist_34, axiom, c3 != c4).
cnf(dist_35, axiom, c3 != c5).
cnf(dist_36, axiom, c3 != c6).
cnf(dist_45, axiom, c4 != c5).
cnf(dist_46, axiom, c4 != c6).
cnf(dist_56, axiom, c5 != c6).

% =========================================================================
% d-sequence definitions: d_k = f(c_k, a)
% =========================================================================
cnf(d0_def, axiom, f(c0, a) = d0).
cnf(d1_def, axiom, f(c1, a) = d1).
cnf(d2_def, axiom, f(c2, a) = d2).
cnf(d3_def, axiom, f(c3, a) = d3).
cnf(d4_def, axiom, f(c4, a) = d4).
cnf(d5_def, axiom, f(c5, a) = d5).
cnf(d6_def, axiom, f(c6, a) = d6).

% =========================================================================
% L1 (key recurrence):  c_{k-1} = f(c_k, d_{k+1})   [indices mod 7]
% Provable from E677 + left-cancel.  We give all 7 instances.
% =========================================================================
cnf(l1_k0, axiom, f(c0, d1) = c6).
cnf(l1_k1, axiom, f(c1, d2) = c0).
cnf(l1_k2, axiom, f(c2, d3) = c1).
cnf(l1_k3, axiom, f(c3, d4) = c2).
cnf(l1_k4, axiom, f(c4, d5) = c3).
cnf(l1_k5, axiom, f(c5, d6) = c4).
cnf(l1_k6, axiom, f(c6, d0) = c5).

% =========================================================================
% L2b (anchor):  d_{d-2} = a, i.e., d_5 = a = c_0.
% Provable from L1 + squaring identity.
% =========================================================================
cnf(l2b_anchor, axiom, d5 = a).

% =========================================================================
% Squaring identity: c_{d-4} ∘ c_{d-4} = c_{d-5}
% For d=7: f(c3, c3) = c2.
% =========================================================================
cnf(squaring_id, axiom, f(c3, c3) = c2).

% =========================================================================
% COLLISION HYPOTHESIS (negation of E255 at element a):
% There exist i != j with d_i = d_j.
% We try the most constrained case first: collision at distance 1.
%
% Attempt 1: d_0 = d_1  (adjacent collision)
% If the prover refutes this, try other pairs.
% =========================================================================
cnf(collision, axiom, d0 = d1).

% =========================================================================
% The prover should derive FALSE from the above axioms.
% If it succeeds: this specific collision pattern is impossible under E677.
% If it fails/times out: the cascade argument alone does not close this case,
% and the gap is genuinely hard.
%
% To systematically cover all cases, run with each of the 21 possible
% collision pairs (d_i = d_j, 0 <= i < j <= 6).  If ALL 21 are refuted,
% then d-injectivity holds for d=7 and this approach generalizes.
% =========================================================================
