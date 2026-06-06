from __future__ import annotations

import argparse
import time
from collections.abc import Iterable, Sequence

import z3

from e677_affine_color_sieve import (
    Op,
    e255_color_map,
    e255_slope_chain,
    force_omega,
    label_name,
    labels_for,
    linear_base_satisfies_e677,
    slope_maps,
)


def full_linear_domain(q: int) -> list[Op]:
    return [(a, b, 0) for a in range(q) for b in range(1, q)]


def color_bases(q: int) -> list[Op]:
    out: list[Op] = []
    for a, b, _ in full_linear_domain(q):
        left_coeff = (a + b * b * (a * a + b)) % q
        target_coeff = (a * b * (1 + b * b)) % q
        if left_coeff == 0 and target_coeff == 1:
            out.append((a, b, 0))
    return out


def build_table_solver(
    p: int,
    q: int,
    alpha: int,
    beta: int,
    domain: Sequence[Op],
) -> tuple[z3.Solver, dict[int, z3.IntNumRef], dict[Op, int]]:
    labels = labels_for(p)
    mu_values, nu_values, omega_values = slope_maps(p, alpha, beta)
    op_index = {op: index for index, op in enumerate(domain)}
    transition = z3.Function("transition", z3.IntSort(), z3.IntSort(), z3.IntSort(), z3.IntSort())
    solver = z3.Solver()
    variables = {label: z3.Int(f"x_{label}") for label in labels}
    for label in labels:
        solver.add(variables[label] >= 0, variables[label] < len(domain))
    for i, label_op in enumerate(domain):
        for j, mu_op in enumerate(domain):
            for k, nu_op in enumerate(domain):
                forced = force_omega(q, label_op, mu_op, nu_op)
                solver.add(transition(i, j, k) == op_index.get(forced, -1))
    for label in labels:
        solver.add(
            transition(variables[label], variables[mu_values[label]], variables[nu_values[label]])
            == variables[omega_values[label]]
        )
    return solver, variables, op_index


def iter_seed_keys(
    q: int,
    chain: tuple[int, int, int],
    family: str,
) -> Iterable[tuple[Op, Op, Op]]:
    domain = full_linear_domain(q)
    bases = color_bases(q)
    one, second, bad = chain
    seen: set[tuple[Op, Op, Op]] = set()

    def emit(seed: dict[int, Op]) -> Iterable[tuple[Op, Op, Op]]:
        key = tuple(seed[label] for label in chain)
        if key in seen:
            return
        seen.add(key)
        if e255_color_map(q, seed, chain)[0] != 1:
            yield key

    if family in {"one", "two"}:
        for base in bases:
            for mutate_label in chain:
                if family == "one":
                    for op in domain:
                        seed = {one: base, second: base, bad: base}
                        seed[mutate_label] = op
                        yield from emit(seed)
                else:
                    fixed_label = mutate_label
                    free = [label for label in chain if label != fixed_label]
                    for op0 in domain:
                        for op1 in domain:
                            seed = {fixed_label: base, free[0]: op0, free[1]: op1}
                            yield from emit(seed)
        return

    if family == "all":
        for op0 in domain:
            for op1 in domain:
                for op2 in domain:
                    seed = {one: op0, second: op1, bad: op2}
                    yield from emit(seed)
        return

    raise ValueError(f"unknown family {family!r}")


def run(args: argparse.Namespace) -> int:
    if not linear_base_satisfies_e677(args.p, args.alpha, args.beta):
        raise SystemExit("selected base does not satisfy E677")
    domain = full_linear_domain(args.q)
    chain = e255_slope_chain(args.p, args.alpha, args.beta)
    print(
        f"affine-z3-probe start: p={args.p} q={args.q} A={args.alpha} B={args.beta} "
        f"family={args.family} chain={chain} domain={len(domain)}",
        flush=True,
    )
    solver, variables, op_index = build_table_solver(args.p, args.q, args.alpha, args.beta, domain)
    solver.set(timeout=args.per_check_ms)
    one, second, bad = chain
    tested = 0
    skipped = 0
    unsat = 0
    unknown = 0
    start_time = time.time()
    for key in iter_seed_keys(args.q, chain, args.family):
        if skipped < args.start:
            skipped += 1
            continue
        if args.limit and tested >= args.limit:
            break
        solver.push()
        solver.add(
            variables[one] == op_index[key[0]],
            variables[second] == op_index[key[1]],
            variables[bad] == op_index[key[2]],
        )
        result = solver.check()
        solver.pop()
        tested += 1
        if result == z3.sat:
            print(f"SAT seed={key}", flush=True)
            model = solver.model()
            for label in labels_for(args.p):
                value = model.eval(variables[label], model_completion=True).as_long()
                print(f"  O_{label_name(label, args.p)}={domain[value]}", flush=True)
            return 2
        if result == z3.unsat:
            unsat += 1
        else:
            unknown += 1
            print(f"UNKNOWN seed={key}", flush=True)
            if args.stop_on_unknown:
                break
        if args.progress and tested % args.progress == 0:
            elapsed = time.time() - start_time
            print(
                f"progress tested={tested} skipped={skipped} unsat={unsat} "
                f"unknown={unknown} elapsed={elapsed:.1f}s",
                flush=True,
            )
    elapsed = time.time() - start_time
    print(
        f"affine-z3-probe done: tested={tested} skipped={skipped} unsat={unsat} "
        f"unknown={unknown} elapsed={elapsed:.1f}s",
        flush=True,
    )
    return 1 if unknown else 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Z3 fixed-seed probes for affine E677 color chains.")
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--q", type=int, required=True)
    parser.add_argument("--alpha", type=int, required=True)
    parser.add_argument("--beta", type=int, required=True)
    parser.add_argument("--family", choices=["one", "two", "all"], default="one")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--progress", type=int, default=250)
    parser.add_argument("--per-check-ms", type=int, default=15000)
    parser.add_argument("--stop-on-unknown", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
