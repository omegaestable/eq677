from __future__ import annotations

import argparse
from collections.abc import Sequence

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


AllowedTuple = tuple[int, int, int, int]


def full_linear_domain(q: int) -> list[Op]:
    return [(a, b, 0) for a in range(q) for b in range(1, q)]


def build_allowed_tuples(q: int, domain: Sequence[Op]) -> list[AllowedTuple]:
    op_pos = {op: index for index, op in enumerate(domain)}
    allowed: list[AllowedTuple] = []
    for l_index, l_op in enumerate(domain):
        for m_index, m_op in enumerate(domain):
            for n_index, n_op in enumerate(domain):
                forced = force_omega(q, l_op, m_op, n_op)
                if forced is None:
                    continue
                w_index = op_pos.get(forced)
                if w_index is not None:
                    allowed.append((l_index, m_index, n_index, w_index))
    return allowed


def tuple_matches_repeated_roles(roles: tuple[int, int, int, int], values: AllowedTuple) -> bool:
    return all(
        values[i] == values[j]
        for i in range(4)
        for j in range(i + 1, 4)
        if roles[i] == roles[j]
    )


def arc_consistent(
    domains: list[int],
    constraints: Sequence[tuple[int, int, int, int]],
    allowed: Sequence[AllowedTuple],
    bits: Sequence[int],
) -> bool:
    changed = True
    while changed:
        changed = False
        for roles in constraints:
            support = [0, 0, 0, 0]
            role_domains = [domains[role] for role in roles]
            for values in allowed:
                if not tuple_matches_repeated_roles(roles, values):
                    continue
                if all(role_domains[pos] & bits[values[pos]] for pos in range(4)):
                    for pos in range(4):
                        support[pos] |= bits[values[pos]]
            for pos, role in enumerate(roles):
                new_domain = domains[role] & support[pos]
                if new_domain == 0:
                    return False
                if new_domain != domains[role]:
                    domains[role] = new_domain
                    changed = True
    return True


def iter_bits(mask: int) -> list[int]:
    out: list[int] = []
    while mask:
        low = mask & -mask
        out.append(low.bit_length() - 1)
        mask ^= low
    return out


def choose_variable(domains: Sequence[int]) -> int | None:
    best_index: int | None = None
    best_size = 10**9
    for index, mask in enumerate(domains):
        size = mask.bit_count()
        if 1 < size < best_size:
            best_index = index
            best_size = size
    return best_index


def e255_multiplier(q: int, assignment: dict[int, Op], chain: tuple[int, int, int]) -> int:
    one, second, bad = chain
    a_1, b_1, _ = assignment[one]
    a_2, b_2, _ = assignment[second]
    a_3, b_3, _ = assignment[bad]
    first = (a_1 + b_1) % q
    second_mult = (a_2 * first + b_2) % q
    return (a_3 * second_mult + b_3) % q


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


def assignment_from_domains(
    p: int,
    domains: Sequence[int],
    domain: Sequence[Op],
    label_at_pos: Sequence[int],
) -> dict[int, Op]:
    out: dict[int, Op] = {}
    for index, mask in enumerate(domains):
        if mask.bit_count() != 1:
            raise RuntimeError("not a singleton assignment")
        out[label_at_pos[index]] = domain[mask.bit_length() - 1]
    return out


def solve(args: argparse.Namespace) -> int:
    if not linear_base_satisfies_e677(args.p, args.alpha, args.beta):
        raise SystemExit("selected base does not satisfy E677")
    labels = labels_for(args.p)
    label_pos = {label: index for index, label in enumerate(labels)}
    mu_values, nu_values, omega_values = slope_maps(args.p, args.alpha, args.beta)
    constraints = tuple(
        (label_pos[label], label_pos[mu_values[label]], label_pos[nu_values[label]], label_pos[omega_values[label]])
        for label in labels
    )
    chain = e255_slope_chain(args.p, args.alpha, args.beta)
    domain = full_linear_domain(args.q)
    bits = [1 << index for index in range(len(domain))]
    full_mask = (1 << len(domain)) - 1
    allowed = build_allowed_tuples(args.q, domain)
    print(
        f"affine-csp start: p={args.p} q={args.q} A={args.alpha} B={args.beta} "
        f"labels={len(labels)} domain={len(domain)} allowed={len(allowed)}",
        flush=True,
    )

    models = 0
    nodes = 0
    linear_bad = 0
    constant_bad = 0
    max_nullity = 0
    first_bad: dict[int, Op] | None = None

    def dfs(domains: list[int]) -> bool:
        nonlocal models, nodes, linear_bad, constant_bad, max_nullity, first_bad
        nodes += 1
        if args.node_limit and nodes > args.node_limit:
            return True
        domains = domains[:]
        if not arc_consistent(domains, constraints, allowed, bits):
            return False
        branch_var = choose_variable(domains)
        if branch_var is None:
            models += 1
            assignment = assignment_from_domains(args.p, domains, domain, labels)
            multiplier = e255_multiplier(args.q, assignment, chain)
            can_break_constants, nullity = constants_can_break_e255(
                args.p, args.q, args.alpha, args.beta, assignment, chain
            )
            max_nullity = max(max_nullity, nullity)
            if multiplier != 1:
                linear_bad += 1
                first_bad = assignment
            if can_break_constants:
                constant_bad += 1
                first_bad = assignment
            if args.show_models:
                rendered = " ".join(
                    f"O_{label_name(label, args.p)}=({assignment[label][0]},{assignment[label][1]})"
                    for label in labels
                )
                print(
                    f"model {models}: multiplier={multiplier} constants_bad={can_break_constants} "
                    f"nullity={nullity} {rendered}",
                    flush=True,
                )
            return bool(args.stop_on_bad and (multiplier != 1 or can_break_constants))

        values = iter_bits(domains[branch_var])
        for value in values:
            child = domains[:]
            child[branch_var] = bits[value]
            if dfs(child):
                return True
        return False

    dfs([full_mask] * len(labels))
    print(
        f"affine-csp done: models={models} nodes={nodes} linear_bad={linear_bad} "
        f"constant_bad={constant_bad} max_constant_nullity={max_nullity}",
        flush=True,
    )
    if first_bad is not None:
        for label in labels:
            print(f"  O_{label_name(label, args.p)}=({first_bad[label][0]},{first_bad[label][1]})")
    return 2 if linear_bad or constant_bad else 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exact bitset CSP for affine colored-slope coefficients.")
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--q", type=int, required=True)
    parser.add_argument("--alpha", type=int, required=True)
    parser.add_argument("--beta", type=int, required=True)
    parser.add_argument("--node-limit", type=int, default=0)
    parser.add_argument("--show-models", action="store_true")
    parser.add_argument("--stop-on-bad", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    return solve(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
