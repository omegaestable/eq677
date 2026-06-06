from __future__ import annotations

import argparse
from collections.abc import Sequence

from pysat.solvers import Solver

from e677_affine_color_sieve import (
    Op,
    e255_slope_chain,
    force_omega,
    inv_mod,
    label_name,
    labels_for,
    linear_base_satisfies_e677,
    slope_maps,
)


def full_linear_domain(q: int) -> list[Op]:
    return [(a, b, 0) for a in range(q) for b in range(1, q)]


def var_id(label_index: int, op_index: int, domain_size: int) -> int:
    return label_index * domain_size + op_index + 1


def exactly_one(clauses: list[list[int]], variables: Sequence[int]) -> None:
    clauses.append(list(variables))
    for i, left in enumerate(variables):
        for right in variables[i + 1 :]:
            clauses.append([-left, -right])


def build_solver(
    p: int,
    q: int,
    alpha: int,
    beta: int,
    domain: Sequence[Op],
    solver_name: str,
) -> tuple[Solver, dict[int, int], int]:
    labels = labels_for(p)
    label_pos = {label: index for index, label in enumerate(labels)}
    op_pos = {op: index for index, op in enumerate(domain)}
    mu_values, nu_values, omega_values = slope_maps(p, alpha, beta)
    d = len(domain)
    clauses: list[list[int]] = []

    for index in range(len(labels)):
        exactly_one(clauses, [var_id(index, op_index, d) for op_index in range(d)])

    for label in labels:
        l_pos = label_pos[label]
        m_pos = label_pos[mu_values[label]]
        n_pos = label_pos[nu_values[label]]
        w_pos = label_pos[omega_values[label]]
        for l_index, l_op in enumerate(domain):
            l_lit = -var_id(l_pos, l_index, d)
            for m_index, m_op in enumerate(domain):
                m_lit = -var_id(m_pos, m_index, d)
                for n_index, n_op in enumerate(domain):
                    forced = force_omega(q, l_op, m_op, n_op)
                    if forced is None:
                        clauses.append([l_lit, m_lit, -var_id(n_pos, n_index, d)])
                        continue
                    w_index = op_pos.get(forced)
                    if w_index is None:
                        clauses.append([l_lit, m_lit, -var_id(n_pos, n_index, d)])
                    else:
                        clauses.append([l_lit, m_lit, -var_id(n_pos, n_index, d), var_id(w_pos, w_index, d)])
    return Solver(name=solver_name, bootstrap_with=clauses), label_pos, len(clauses)


def model_assignment(
    model: Sequence[int],
    p: int,
    domain: Sequence[Op],
    label_pos: dict[int, int],
) -> dict[int, Op]:
    true_vars = {lit for lit in model if lit > 0}
    d = len(domain)
    out: dict[int, Op] = {}
    for label, index in label_pos.items():
        for op_index, op in enumerate(domain):
            if var_id(index, op_index, d) in true_vars:
                out[label] = op
                break
        else:
            raise RuntimeError(f"missing operation for label {label_name(label, p)}")
    return out


def e255_multiplier(q: int, assignment: dict[int, Op], chain: tuple[int, int, int]) -> int:
    one, second, bad = chain
    a_1, b_1, _ = assignment[one]
    a_2, b_2, _ = assignment[second]
    a_3, b_3, _ = assignment[bad]
    first = (a_1 + b_1) % q
    second_mult = (a_2 * first + b_2) % q
    return (a_3 * second_mult + b_3) % q


def constant_matrix(
    p: int,
    q: int,
    alpha: int,
    beta: int,
    assignment: dict[int, Op],
) -> list[list[int]]:
    labels = labels_for(p)
    label_pos = {label: index for index, label in enumerate(labels)}
    mu_values, nu_values, omega_values = slope_maps(p, alpha, beta)
    rows: list[list[int]] = []
    for label in labels:
        mu_label = mu_values[label]
        nu_label = nu_values[label]
        omega_label = omega_values[label]
        _, _, _ = assignment[label]
        a_m, _, _ = assignment[mu_label]
        _, b_n, _ = assignment[nu_label]
        _, b_w, _ = assignment[omega_label]
        row = [0] * len(labels)
        row[label_pos[label]] = (row[label_pos[label]] + b_w * b_n * a_m) % q
        row[label_pos[mu_label]] = (row[label_pos[mu_label]] + b_w * b_n) % q
        row[label_pos[nu_label]] = (row[label_pos[nu_label]] + b_w) % q
        row[label_pos[omega_label]] = (row[label_pos[omega_label]] + 1) % q
        rows.append(row)
    return rows


def rref(matrix: list[list[int]], q: int) -> tuple[list[list[int]], list[int]]:
    mat = [row[:] for row in matrix]
    if not mat:
        return mat, []
    rows = len(mat)
    cols = len(mat[0])
    pivots: list[int] = []
    r = 0
    for c in range(cols):
        pivot = next((i for i in range(r, rows) if mat[i][c] % q), None)
        if pivot is None:
            continue
        mat[r], mat[pivot] = mat[pivot], mat[r]
        inv = inv_mod(mat[r][c], q)
        mat[r] = [(value * inv) % q for value in mat[r]]
        for i in range(rows):
            if i != r and mat[i][c] % q:
                factor = mat[i][c] % q
                mat[i] = [(mat[i][j] - factor * mat[r][j]) % q for j in range(cols)]
        pivots.append(c)
        r += 1
        if r == rows:
            break
    return mat, pivots


def nullspace_basis(matrix: list[list[int]], q: int) -> list[list[int]]:
    reduced, pivots = rref(matrix, q)
    if not matrix:
        return []
    cols = len(matrix[0])
    pivot_set = set(pivots)
    basis: list[list[int]] = []
    for free_col in range(cols):
        if free_col in pivot_set:
            continue
        vector = [0] * cols
        vector[free_col] = 1
        for row_index, pivot_col in enumerate(pivots):
            vector[pivot_col] = (-reduced[row_index][free_col]) % q
        basis.append(vector)
    return basis


def e255_constant_functional(
    p: int,
    q: int,
    assignment: dict[int, Op],
    chain: tuple[int, int, int],
) -> list[int]:
    labels = labels_for(p)
    label_pos = {label: index for index, label in enumerate(labels)}
    one, second, bad = chain
    a_2, _, _ = assignment[second]
    a_3, _, _ = assignment[bad]
    functional = [0] * len(labels)
    functional[label_pos[one]] = (functional[label_pos[one]] + a_3 * a_2) % q
    functional[label_pos[second]] = (functional[label_pos[second]] + a_3) % q
    functional[label_pos[bad]] = (functional[label_pos[bad]] + 1) % q
    return functional


def constants_can_break_e255(
    p: int,
    q: int,
    alpha: int,
    beta: int,
    assignment: dict[int, Op],
    chain: tuple[int, int, int],
) -> tuple[bool, int]:
    matrix = constant_matrix(p, q, alpha, beta, assignment)
    basis = nullspace_basis(matrix, q)
    functional = e255_constant_functional(p, q, assignment, chain)
    for vector in basis:
        value = sum(a * b for a, b in zip(functional, vector, strict=True)) % q
        if value:
            return True, len(basis)
    return False, len(basis)


def block_assignment(
    solver: Solver,
    p: int,
    domain: Sequence[Op],
    label_pos: dict[int, int],
    assignment: dict[int, Op],
) -> None:
    op_pos = {op: index for index, op in enumerate(domain)}
    d = len(domain)
    solver.add_clause(
        [-var_id(label_pos[label], op_pos[assignment[label]], d) for label in labels_for(p)]
    )


def run(args: argparse.Namespace) -> int:
    if not linear_base_satisfies_e677(args.p, args.alpha, args.beta):
        raise SystemExit("selected base does not satisfy E677")
    domain = full_linear_domain(args.q)
    print(
        f"affine-sat start: p={args.p} q={args.q} A={args.alpha} B={args.beta} "
        f"labels={args.p + 1} domain={len(domain)} solver={args.solver}",
        flush=True,
    )
    solver, label_pos, clause_count = build_solver(args.p, args.q, args.alpha, args.beta, domain, args.solver)
    print(f"affine-sat cnf: vars={(args.p + 1) * len(domain)} clauses={clause_count}", flush=True)
    chain = e255_slope_chain(args.p, args.alpha, args.beta)
    models = 0
    linear_bad = 0
    constant_bad = 0
    max_nullity = 0
    example: dict[int, Op] | None = None
    while solver.solve():
        models += 1
        assignment = model_assignment(solver.get_model(), args.p, domain, label_pos)
        multiplier = e255_multiplier(args.q, assignment, chain)
        can_break_constants, nullity = constants_can_break_e255(
            args.p, args.q, args.alpha, args.beta, assignment, chain
        )
        max_nullity = max(max_nullity, nullity)
        if multiplier != 1:
            linear_bad += 1
            example = assignment
        if can_break_constants:
            constant_bad += 1
            example = assignment
        if args.show_models:
            rendered = " ".join(
                f"O_{label_name(label, args.p)}=({assignment[label][0]},{assignment[label][1]})"
                for label in labels_for(args.p)
            )
            print(
                f"model {models}: multiplier={multiplier} constants_bad={can_break_constants} "
                f"nullity={nullity} {rendered}"
            )
        if args.stop_on_bad and (multiplier != 1 or can_break_constants):
            break
        if args.max_models and models >= args.max_models:
            break
        block_assignment(solver, args.p, domain, label_pos, assignment)
    print(
        f"affine-sat done: models={models} linear_bad={linear_bad} "
        f"constant_bad={constant_bad} max_constant_nullity={max_nullity}"
    )
    if example is not None:
        for label in labels_for(args.p):
            print(f"  O_{label_name(label, args.p)}=({example[label][0]},{example[label][1]})")
    return 2 if linear_bad or constant_bad else 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exact SAT check for affine colored-slope coefficients.")
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--q", type=int, required=True)
    parser.add_argument("--alpha", type=int, required=True)
    parser.add_argument("--beta", type=int, required=True)
    parser.add_argument("--max-models", type=int, default=0)
    parser.add_argument("--show-models", action="store_true")
    parser.add_argument("--stop-on-bad", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--solver", default="cadical153")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
