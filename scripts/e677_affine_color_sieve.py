from __future__ import annotations

import argparse
import math
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product


INF_NAME = "inf"
Op = tuple[int, int, int]
Constraint = tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class Candidate:
    p: int
    q: int
    alpha: int
    beta: int
    chain: tuple[int, int, int]
    closure: int
    involved: int
    bad_involved: int
    color_bases: tuple[Op, ...]


@dataclass(slots=True)
class SearchResult:
    candidate: Candidate
    models: int = 0
    bad_models: int = 0
    best_failures: int = 0
    best_map: tuple[int, int] = (1, 0)
    best_assignment: dict[int, Op] | None = None
    nodes: int = 0
    seeds: int = 0
    timed_out: bool = False


def prime_values(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for value in range(2, int(limit**0.5) + 1):
        if sieve[value]:
            start = value * value
            sieve[start : limit + 1 : value] = b"\x00" * (((limit - start) // value) + 1)
    return [value for value in range(limit + 1) if sieve[value]]


def inv_mod(value: int, modulus: int) -> int:
    value %= modulus
    if value == 0:
        raise ZeroDivisionError("inverse of zero")
    return pow(value, -1, modulus)


def labels_for(prime: int) -> list[int]:
    return list(range(prime)) + [prime]


def label_name(label: int, prime: int) -> str:
    return INF_NAME if label == prime else str(label)


def linear_base_satisfies_e677(prime: int, alpha: int, beta: int) -> bool:
    return (
        (alpha + beta * beta * (alpha * alpha + beta)) % prime == 0
        and (alpha * beta * (1 + beta * beta)) % prime == 1
    )


def linear_bases_for_prime(prime: int) -> list[tuple[int, int]]:
    hits: list[tuple[int, int]] = []
    for beta in range(1, prime):
        denominator = beta * (1 + beta * beta)
        if denominator % prime == 0:
            continue
        alpha = inv_mod(denominator, prime)
        if linear_base_satisfies_e677(prime, alpha, beta):
            hits.append((alpha, beta))
    return hits


def e255_slope_chain(prime: int, alpha: int, beta: int) -> tuple[int, int, int]:
    first = 1 % prime
    second = (alpha + beta) % prime
    third = (alpha * second + beta) % prime
    return first, second, third


def slope_maps(prime: int, alpha: int, beta: int) -> tuple[list[int], list[int], list[int]]:
    infinity = prime
    linear = (alpha * alpha + beta) % prime
    mixed = (alpha * beta) % prime
    omega_linear = (beta * linear) % prime
    omega_const = (alpha * (1 + beta * beta)) % prime
    mu_values: list[int] = []
    nu_values: list[int] = []
    omega_values: list[int] = []
    for label in labels_for(prime):
        if label == infinity:
            mu_values.append(alpha % prime)
            nu_values.append(0 if linear != 0 else infinity)
            omega_values.append(infinity if omega_linear == 0 else inv_mod(omega_linear, prime))
            continue
        mu_values.append(infinity if label == 0 else (alpha + beta * inv_mod(label, prime)) % prime)
        nu_denominator = (linear * label + mixed) % prime
        omega_denominator = (omega_linear * label + omega_const) % prime
        nu_values.append(infinity if nu_denominator == 0 else inv_mod(nu_denominator, prime))
        omega_values.append(
            infinity if omega_denominator == 0 else (label * inv_mod(omega_denominator, prime)) % prime
        )
    return mu_values, nu_values, omega_values


def slope_closure(
    seeds: Iterable[int],
    mu_values: Sequence[int],
    nu_values: Sequence[int],
    omega_values: Sequence[int],
    depth: int,
) -> set[int]:
    closed = set(seeds)
    frontier = set(seeds)
    for _ in range(depth):
        next_frontier: set[int] = set()
        for label in frontier:
            for image in (mu_values[label], nu_values[label], omega_values[label]):
                if image not in closed:
                    closed.add(image)
                    next_frontier.add(image)
        frontier = next_frontier
        if not frontier:
            break
    return closed


def involved_lambdas(
    labels: Sequence[int],
    watched: set[int],
    mu_values: Sequence[int],
    nu_values: Sequence[int],
    omega_values: Sequence[int],
) -> set[int]:
    out: set[int] = set()
    for label in labels:
        if watched.intersection((label, mu_values[label], nu_values[label], omega_values[label])):
            out.add(label)
    return out


def force_omega(q: int, label_op: Op, mu_op: Op, nu_op: Op) -> Op | None:
    a_l, b_l, c_l = label_op
    a_m, b_m, c_m = mu_op
    a_n, b_n, c_n = nu_op
    u_i = (a_m * a_l + b_m) % q
    u_j = (a_m * b_l) % q
    u_c = (a_m * c_l + c_m) % q
    v_i = (b_n * u_i) % q
    v_j = (a_n + b_n * u_j) % q
    v_c = (b_n * u_c + c_n) % q
    if v_j == 0:
        return None
    b_w = inv_mod(v_j, q)
    return (-b_w * v_i) % q, b_w, (-b_w * v_c) % q


def force_mu(q: int, label_op: Op, nu_op: Op, omega_op: Op) -> Op | None:
    a_l, b_l, c_l = label_op
    a_n, b_n, c_n = nu_op
    a_w, b_w, c_w = omega_op
    a_m = (inv_mod(b_w, q) - a_n) * inv_mod(b_n * b_l, q)
    y_target = (-a_w * inv_mod(b_w * b_n, q)) % q
    b_m = (y_target - a_m * a_l) % q
    if b_m == 0:
        return None
    u_target = ((-c_w * inv_mod(b_w, q)) - c_n) * inv_mod(b_n, q)
    c_m = (u_target - a_m * c_l) % q
    return a_m % q, b_m, c_m


def force_label(q: int, mu_op: Op, nu_op: Op, omega_op: Op) -> Op | None:
    a_m, b_m, c_m = mu_op
    if a_m == 0:
        return None
    a_n, b_n, c_n = nu_op
    a_w, b_w, c_w = omega_op
    b_l = (inv_mod(b_w, q) - a_n) * inv_mod(b_n * a_m, q)
    b_l %= q
    if b_l == 0:
        return None
    y_target = (-a_w * inv_mod(b_w * b_n, q)) % q
    a_l = (y_target - b_m) * inv_mod(a_m, q)
    u_target = ((-c_w * inv_mod(b_w, q)) - c_n) * inv_mod(b_n, q)
    c_l = (u_target - c_m) * inv_mod(a_m, q)
    return a_l % q, b_l, c_l % q


def force_nu(q: int, label_op: Op, mu_op: Op, omega_op: Op) -> Op | None:
    a_l, b_l, c_l = label_op
    a_m, b_m, c_m = mu_op
    a_w, b_w, c_w = omega_op
    y_value = (a_m * a_l + b_m) % q
    if y_value == 0:
        return None
    b_n = (-a_w * inv_mod(b_w, q)) * inv_mod(y_value, q)
    b_n %= q
    if b_n == 0:
        return None
    x_value = (a_m * b_l) % q
    u_value = (a_m * c_l + c_m) % q
    a_n = (inv_mod(b_w, q) - b_n * x_value) % q
    c_n = (-c_w * inv_mod(b_w, q) - b_n * u_value) % q
    return a_n, b_n, c_n


def force_missing(
    q: int,
    label: int,
    mu_label: int,
    nu_label: int,
    omega_label: int,
    assignment: dict[int, Op],
) -> tuple[int, Op] | None:
    if len({label, mu_label, nu_label, omega_label}) < 4:
        if label in assignment and mu_label in assignment and nu_label in assignment and omega_label not in assignment:
            forced = force_omega(q, assignment[label], assignment[mu_label], assignment[nu_label])
            if forced is None:
                return None
            return omega_label, forced
        return None
    present = {
        label: assignment.get(label),
        mu_label: assignment.get(mu_label),
        nu_label: assignment.get(nu_label),
        omega_label: assignment.get(omega_label),
    }
    missing = [key for key, value in present.items() if value is None]
    if len(missing) != 1:
        return None
    missing_label = missing[0]
    label_op = present[label]
    mu_op = present[mu_label]
    nu_op = present[nu_label]
    omega_op = present[omega_label]
    forced: Op | None
    if missing_label == omega_label:
        assert label_op is not None and mu_op is not None and nu_op is not None
        forced = force_omega(q, label_op, mu_op, nu_op)
    elif missing_label == mu_label:
        assert label_op is not None and nu_op is not None and omega_op is not None
        forced = force_mu(q, label_op, nu_op, omega_op)
    elif missing_label == label:
        assert mu_op is not None and nu_op is not None and omega_op is not None
        forced = force_label(q, mu_op, nu_op, omega_op)
    elif missing_label == nu_label:
        assert label_op is not None and mu_op is not None and omega_op is not None
        forced = force_nu(q, label_op, mu_op, omega_op)
    else:
        raise AssertionError("unreachable missing label")
    if forced is None:
        return None
    return missing_label, forced


def propagate(q: int, constraints: Sequence[Constraint], assignment: dict[int, Op]) -> bool:
    changed = True
    while changed:
        changed = False
        for label, mu_label, nu_label, omega_label in constraints:
            if (
                label in assignment
                and mu_label in assignment
                and nu_label in assignment
                and omega_label in assignment
            ):
                forced = force_omega(q, assignment[label], assignment[mu_label], assignment[nu_label])
                if forced is None or assignment[omega_label] != forced:
                    return False
                continue
            forced_pair = force_missing(q, label, mu_label, nu_label, omega_label, assignment)
            if forced_pair is None:
                continue
            missing_label, forced = forced_pair
            old = assignment.get(missing_label)
            if old is not None and old != forced:
                return False
            if old is None:
                assignment[missing_label] = forced
                changed = True
    return True


def choose_label(
    ordered_labels: Sequence[int],
    constraints: Sequence[Constraint],
    assignment: dict[int, Op],
) -> int:
    best_label = next(label for label in ordered_labels if label not in assignment)
    best_score = -1
    for candidate in ordered_labels:
        if candidate in assignment:
            continue
        score = 0
        for label, mu_label, nu_label, omega_label in constraints:
            antecedents = (label, mu_label, nu_label)
            if candidate in antecedents:
                score += 3 * sum(item in assignment for item in antecedents)
            if candidate == omega_label:
                score += 1
        if score > best_score:
            best_score = score
            best_label = candidate
    return best_label


def e255_color_map(q: int, assignment: dict[int, Op], chain: tuple[int, int, int]) -> tuple[int, int]:
    one, second, bad = chain
    a_1, b_1, c_1 = assignment[one]
    a_2, b_2, c_2 = assignment[second]
    a_3, b_3, c_3 = assignment[bad]
    m_1 = (a_1 + b_1) % q
    k_1 = c_1 % q
    m_2 = (a_2 * m_1 + b_2) % q
    k_2 = (a_2 * k_1 + c_2) % q
    return (a_3 * m_2 + b_3) % q, (a_3 * k_2 + c_3) % q


def e255_failure_count(q: int, color_map: tuple[int, int]) -> int:
    multiplier, constant = color_map
    if multiplier == 1 and constant == 0:
        return 0
    if multiplier == 1:
        return q
    return q - 1


def structured_domain(q: int, constants: bool, full_domain_q: int) -> list[Op]:
    pairs: set[tuple[int, int]] = set()
    if q <= full_domain_q:
        pairs.update((a, b) for a in range(q) for b in range(1, q))
    bases = linear_bases_for_prime(q)
    pairs.update(bases)
    small = {0, 1, 2, 3, 4, 5, 6, q - 1, q - 2, q - 3}
    if q > 2:
        small.add(inv_mod(2, q))
    right_small = {1, 2, 3, q - 1, q - 2}
    for a in small:
        for b in right_small:
            if b % q:
                pairs.add((a % q, b % q))
    consts = range(q) if constants else (0,)
    out = [(a, b, c) for a, b in sorted(pairs) for c in consts]
    base_ops = [(a, b, 0) for a, b in bases]
    out.sort(key=lambda op: (op not in base_ops, op[2] != 0, op[0], op[1], op[2]))
    return out


def chain_seed_assignments(
    chain: tuple[int, int, int],
    domain: Sequence[Op],
    color_bases: Sequence[Op],
    limit: int,
    seed_domain_cap: int,
) -> list[dict[int, Op]]:
    labels = list(dict.fromkeys(chain))
    base_ops = list(color_bases) or list(domain[:1])
    seed_domain = list(domain[:seed_domain_cap])
    seeds: list[dict[int, Op]] = []
    seen: set[tuple[tuple[int, Op], ...]] = set()

    def add(seed: dict[int, Op]) -> None:
        if len(seeds) >= limit:
            return
        key = tuple(sorted(seed.items()))
        if key in seen:
            return
        seen.add(key)
        seeds.append(seed)

    for base in base_ops:
        add({label: base for label in labels})
        for label in labels:
            for op in seed_domain:
                seed = {item: base for item in labels}
                seed[label] = op
                add(seed)

    if len(seeds) < limit:
        cap = min(len(seed_domain), max(3, int(round(limit ** (1 / max(1, len(labels)))) + 1)))
        capped = seed_domain[:cap]
        for values in product(capped, repeat=len(labels)):
            add(dict(zip(labels, values, strict=True)))
            if len(seeds) >= limit:
                break
    return seeds


def ordered_labels_for_candidate(
    candidate: Candidate,
    mu_values: Sequence[int],
    nu_values: Sequence[int],
    omega_values: Sequence[int],
    depth: int,
) -> list[int]:
    labels = labels_for(candidate.p)
    closure = slope_closure(candidate.chain, mu_values, nu_values, omega_values, depth)
    ordered: list[int] = []
    for label in (*candidate.chain, *sorted(closure, key=lambda item: (item == candidate.p, item))):
        if label not in ordered:
            ordered.append(label)
    for label in labels:
        if label not in ordered:
            ordered.append(label)
    return ordered


def search_candidate(candidate: Candidate, args: argparse.Namespace) -> SearchResult:
    p, q = candidate.p, candidate.q
    labels = labels_for(p)
    mu_values, nu_values, omega_values = slope_maps(p, candidate.alpha, candidate.beta)
    constraints = tuple((label, mu_values[label], nu_values[label], omega_values[label]) for label in labels)
    ordered_labels = ordered_labels_for_candidate(candidate, mu_values, nu_values, omega_values, args.closure_depth)
    domain = structured_domain(q, args.constants, args.full_domain_q)
    seeds = chain_seed_assignments(
        candidate.chain,
        domain,
        candidate.color_bases,
        args.chain_seed_limit,
        args.seed_domain_cap,
    )
    fixed_seed: dict[int, Op] = {}
    if args.fix_op:
        for spec in args.fix_op:
            label_text, a_text, b_text, *rest = spec.split(":")
            label = candidate.p if label_text == INF_NAME else int(label_text)
            op = (int(a_text) % q, int(b_text) % q, int(rest[0]) % q if rest else 0)
            if label < 0 or label > candidate.p:
                raise SystemExit(f"fixed label {label_text!r} is outside this candidate")
            if op not in domain:
                raise SystemExit(f"fixed op {op} from {spec!r} is outside the active domain")
            old = fixed_seed.get(label)
            if old is not None and old != op:
                raise SystemExit(f"conflicting fixed ops for label {label_text!r}")
            fixed_seed[label] = op
        seeds = [fixed_seed]
    result = SearchResult(candidate=candidate, seeds=len(seeds))
    deadline = time.monotonic() + args.per_candidate_ms / 1000
    seen_models: set[tuple[tuple[int, Op], ...]] = set()

    def record_model(assignment: dict[int, Op]) -> bool:
        key = tuple(sorted(assignment.items()))
        if key in seen_models:
            return False
        seen_models.add(key)
        result.models += 1
        color_map = e255_color_map(q, assignment, candidate.chain)
        failures = e255_failure_count(q, color_map)
        if result.best_assignment is None or failures > result.best_failures:
            result.best_failures = failures
            result.best_map = color_map
            result.best_assignment = dict(assignment)
        if failures:
            result.bad_models += 1
            if args.stop_after_bad:
                return True
        return result.models >= args.model_budget > 0

    for base_op in candidate.color_bases:
        if any(base_op != op for op in fixed_seed.values()):
            continue
        uniform = {label: base_op for label in labels}
        if propagate(q, constraints, uniform) and record_model(uniform):
            return result

    def dfs(start_assignment: dict[int, Op]) -> bool:
        if time.monotonic() >= deadline:
            result.timed_out = True
            return True
        if args.node_budget and result.nodes >= args.node_budget:
            result.timed_out = True
            return True
        result.nodes += 1
        assignment = dict(start_assignment)
        if not propagate(q, constraints, assignment):
            return False
        if len(assignment) == len(labels):
            return record_model(assignment)
        label = choose_label(ordered_labels, constraints, assignment)
        for op in domain:
            child = dict(assignment)
            child[label] = op
            if dfs(child):
                return True
        return False

    for seed in seeds:
        if dfs(seed):
            break
    return result


def candidate_score(candidate: Candidate, prefer_large: bool) -> tuple[int, int, int, int]:
    order_term = -candidate.p * candidate.q if prefer_large else candidate.p * candidate.q
    return (candidate.closure, candidate.involved, candidate.bad_involved, order_term)


def build_candidates(args: argparse.Namespace) -> list[Candidate]:
    q_primes = [q for q in prime_values(args.max_q) if q >= args.min_q]
    if args.q:
        q_primes = [args.q]
    q_bases = {q: tuple((a, b, 0) for a, b in linear_bases_for_prime(q)) for q in q_primes}
    out: list[Candidate] = []
    for p in prime_values(args.max_p):
        if p < args.min_p:
            continue
        for alpha, beta in linear_bases_for_prime(p):
            labels = labels_for(p)
            mu_values, nu_values, omega_values = slope_maps(p, alpha, beta)
            chain = e255_slope_chain(p, alpha, beta)
            if not args.allow_degenerate_chain and len(set(chain)) < 3:
                continue
            closure = slope_closure(chain, mu_values, nu_values, omega_values, args.closure_depth)
            involved = involved_lambdas(labels, closure, mu_values, nu_values, omega_values)
            bad_involved = involved_lambdas(labels, {chain[2]}, mu_values, nu_values, omega_values)
            for q in q_primes:
                if args.min_order and p * q < args.min_order:
                    continue
                if args.max_order and p * q > args.max_order:
                    continue
                if args.require_color_base and not q_bases[q]:
                    continue
                out.append(
                    Candidate(
                        p=p,
                        q=q,
                        alpha=alpha,
                        beta=beta,
                        chain=chain,
                        closure=len(closure),
                        involved=len(involved),
                        bad_involved=len(bad_involved),
                        color_bases=q_bases[q],
                    )
                )
    out.sort(key=lambda item: candidate_score(item, args.prefer_large_order))
    return out[: args.candidate_limit if args.candidate_limit else None]


def format_op(op: Op) -> str:
    return f"({op[0]},{op[1]},{op[2]})"


def format_model(candidate: Candidate, assignment: dict[int, Op] | None) -> str:
    if assignment is None:
        return "none"
    pieces = []
    for label in dict.fromkeys(candidate.chain):
        pieces.append(f"O_{label_name(label, candidate.p)}={format_op(assignment[label])}")
    return " ".join(pieces)


def run(args: argparse.Namespace) -> int:
    candidates = build_candidates(args)
    print(
        "affine-sieve start: "
        f"candidates={len(candidates)} p=[{args.min_p},{args.max_p}] q=[{args.min_q},{args.max_q}] "
        f"min_order={args.min_order} max_order={args.max_order or 'none'} "
        f"constants={'yes' if args.constants else 'no'}"
    )
    results: list[SearchResult] = []
    for index, candidate in enumerate(candidates, start=1):
        result = search_candidate(candidate, args)
        results.append(result)
        if args.verbose or result.bad_models:
            print_result(index, result)
    results.sort(
        key=lambda item: (
            -item.best_failures,
            item.timed_out,
            item.candidate.closure,
            item.candidate.involved,
            -item.candidate.p * item.candidate.q,
        )
    )
    print("affine-sieve best:")
    for rank, result in enumerate(results[: args.top], start=1):
        print_result(rank, result, prefix="#")
    return 2 if any(result.bad_models for result in results) else 0


def print_result(rank: int, result: SearchResult, prefix: str = "cand") -> None:
    c = result.candidate
    print(
        f"{prefix}{rank:03d} order={c.p * c.q} p={c.p} q={c.q} A={c.alpha} B={c.beta} "
        f"chain=1->{c.chain[1]}->{c.chain[2]} closure={c.closure} involved={c.involved} "
        f"bad_involved={c.bad_involved} q_bases={len(c.color_bases)} "
        f"models={result.models} bad_models={result.bad_models} best_failures={result.best_failures} "
        f"e255_map=({result.best_map[0]},{result.best_map[1]}) "
        f"nodes={result.nodes} seeds={result.seeds} timeout={'yes' if result.timed_out else 'no'} "
        f"{format_model(c, result.best_assignment)}"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Theory-driven affine-color sieve for E677 colored-slope constructions."
    )
    parser.add_argument("--min-p", type=int, default=19)
    parser.add_argument("--max-p", type=int, default=1000)
    parser.add_argument("--min-q", type=int, default=7)
    parser.add_argument("--max-q", type=int, default=257)
    parser.add_argument("--q", type=int, default=0, help="restrict to one color prime")
    parser.add_argument("--min-order", type=int, default=0)
    parser.add_argument("--max-order", type=int, default=0)
    parser.add_argument("--closure-depth", type=int, default=3)
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--prefer-large-order", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--require-color-base", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow-degenerate-chain", action="store_true")
    parser.add_argument("--constants", action="store_true")
    parser.add_argument("--full-domain-q", type=int, default=13)
    parser.add_argument("--seed-domain-cap", type=int, default=48)
    parser.add_argument("--chain-seed-limit", type=int, default=4000)
    parser.add_argument("--per-candidate-ms", type=int, default=250)
    parser.add_argument("--node-budget", type=int, default=25000)
    parser.add_argument("--model-budget", type=int, default=50)
    parser.add_argument("--stop-after-bad", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--fix-op",
        action="append",
        default=[],
        help="force a slope operation as label:a:b[:c]; label may be inf",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
