from __future__ import annotations

import argparse
import itertools
import math
import random
import time
from collections.abc import Iterable, Sequence


Table = list[list[int]]


def operation(table: Table, left: int, right: int) -> int:
    return table[left][right]


def e677_at(table: Table, target: int, parameter: int) -> bool:
    first = operation(table, parameter, target)
    second = operation(table, first, parameter)
    third = operation(table, target, second)
    return operation(table, parameter, third) == target


def e255_at(table: Table, element: int) -> bool:
    first = operation(table, element, element)
    second = operation(table, first, element)
    return operation(table, second, element) == element


def e255_failures(table: Table) -> list[int]:
    return [element for element in range(len(table)) if not e255_at(table, element)]


def check_e677(table: Table) -> bool:
    order = len(table)
    for target in range(order):
        for parameter in range(order):
            if not e677_at(table, target, parameter):
                return False
    return True


def left_rows_are_permutations(table: Table) -> bool:
    expected = list(range(len(table)))
    return all(sorted(row) == expected for row in table)


def right_cancellative(table: Table) -> bool:
    order = len(table)
    expected = list(range(order))
    for right in range(order):
        column = [table[left][right] for left in range(order)]
        if sorted(column) != expected:
            return False
    return True


def format_values(values: Sequence[int], limit: int = 30) -> str:
    rendered = ",".join(str(value) for value in values[:limit])
    if len(values) > limit:
        rendered += ",..."
    return rendered


def print_table(table: Table) -> None:
    width = max(1, len(str(len(table) - 1)))
    for row in table:
        print(" ".join(f"{value:{width}d}" for value in row))


def maybe_report_hit(
    family: str,
    details: str,
    table: Table,
    args: argparse.Namespace,
) -> bool:
    failures = e255_failures(table)
    is_bad = bool(failures)
    print(
        f"{family}: {details} e255_failures={format_values(failures) if failures else 'none'} "
        f"right_cancellative={right_cancellative(table)}"
    )
    if args.show_table or (is_bad and args.show_bad_table):
        print_table(table)
    return is_bad


def affine_table(modulus: int, alpha: int, beta: int, constant: int) -> Table:
    return [
        [((alpha * left) + (beta * right) + constant) % modulus for right in range(modulus)]
        for left in range(modulus)
    ]


def scan_affine(args: argparse.Namespace) -> int:
    hits = 0
    checked = 0
    for modulus in range(2, args.max_order + 1):
        for alpha in range(modulus):
            for beta in range(modulus):
                if args.left_latin and math.gcd(beta, modulus) != 1:
                    continue
                for constant in range(modulus):
                    checked += 1
                    table = affine_table(modulus, alpha, beta, constant)
                    if args.left_latin and not left_rows_are_permutations(table):
                        continue
                    if not check_e677(table):
                        continue
                    hits += 1
                    is_bad = maybe_report_hit(
                        "affine",
                        f"modulus={modulus} alpha={alpha} beta={beta} constant={constant}",
                        table,
                        args,
                    )
                    if is_bad and args.stop_on_bad:
                        return 2
                    if args.max_hits and hits >= args.max_hits:
                        print(f"stopped after max_hits={args.max_hits}; checked={checked}")
                        return 0
    print(f"affine scan complete: checked={checked} hits={hits}")
    return 0


def translation_table(values: Sequence[int]) -> Table:
    modulus = len(values)
    return [
        [(left + values[(right - left) % modulus]) % modulus for right in range(modulus)]
        for left in range(modulus)
    ]


def translation_e677_failures(values: Sequence[int]) -> list[int]:
    modulus = len(values)
    failures: list[int] = []
    for parameter in range(modulus):
        first = (parameter + values[-parameter % modulus]) % modulus
        second = (first + values[(parameter - first) % modulus]) % modulus
        third = values[second]
        result = (parameter + values[(third - parameter) % modulus]) % modulus
        if result != 0:
            failures.append(parameter)
    return failures


def translation_e255_fails(values: Sequence[int]) -> bool:
    modulus = len(values)
    first = values[0] % modulus
    second = (first + values[-first % modulus]) % modulus
    third = (second + values[-second % modulus]) % modulus
    return third != 0


def iter_translation_values(args: argparse.Namespace) -> Iterable[tuple[int, ...]]:
    for modulus in range(2, args.max_order + 1):
        if args.exhaustive_order and modulus <= args.exhaustive_order:
            for values in itertools.permutations(range(modulus)):
                if args.fix_zero and values[0] != 0:
                    continue
                yield values
            continue

        sampler = random.Random(args.seed + modulus)
        base = list(range(modulus))
        for _ in range(args.samples_per_order):
            sampler.shuffle(base)
            if args.fix_zero:
                zero_index = base.index(0)
                base[0], base[zero_index] = base[zero_index], base[0]
            yield tuple(base)


def scan_translation(args: argparse.Namespace) -> int:
    hits = 0
    bad_hits = 0
    checked = 0
    for values in iter_translation_values(args):
        checked += 1
        if translation_e677_failures(values):
            continue
        table = translation_table(values)
        hits += 1
        if translation_e255_fails(values):
            bad_hits += 1
        is_bad = maybe_report_hit(
            "translation",
            f"modulus={len(values)} values={format_values(values)}",
            table,
            args,
        )
        if is_bad and args.stop_on_bad:
            return 2
        if args.max_hits and hits >= args.max_hits:
            print(f"stopped after max_hits={args.max_hits}; checked={checked} bad_hits={bad_hits}")
            return 0
    print(f"translation scan complete: checked={checked} hits={hits} bad_hits={bad_hits}")
    return 0


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def prime_values(max_prime: int) -> list[int]:
    return [candidate for candidate in range(2, max_prime + 1) if is_prime(candidate)]


def primitive_root(prime: int) -> int:
    factors: set[int] = set()
    remaining = prime - 1
    divisor = 2
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            factors.add(divisor)
            while remaining % divisor == 0:
                remaining //= divisor
        divisor += 1
    if remaining > 1:
        factors.add(remaining)
    for candidate in range(2, prime):
        if all(pow(candidate, (prime - 1) // factor, prime) != 1 for factor in factors):
            return candidate
    raise ValueError(f"no primitive root found for prime {prime}")


def coset_indices(prime: int, index: int) -> list[int]:
    generator = primitive_root(prime)
    indices = [0] * prime
    current = 1
    for exponent in range(prime - 1):
        indices[current] = exponent % index
        current = (current * generator) % prime
    return indices


def coset_translation_values(prime: int, index: int, zero_value: int, slopes: Sequence[int]) -> tuple[int, ...]:
    indices = coset_indices(prime, index)
    values = [zero_value % prime]
    for difference in range(1, prime):
        values.append((slopes[indices[difference]] * difference) % prime)
    return tuple(values)


def scan_coset_translation(args: argparse.Namespace) -> int:
    if not is_prime(args.prime):
        raise SystemExit("--prime must be prime")
    if (args.prime - 1) % args.index != 0:
        raise SystemExit("--index must divide prime - 1")

    hits = 0
    checked = 0
    zero_values = [args.zero_value] if args.zero_value is not None else range(args.prime)
    nonzero_values = range(1, args.prime)
    for zero_value in zero_values:
        for slopes in itertools.product(nonzero_values, repeat=args.index):
            checked += 1
            if args.max_candidates and checked > args.max_candidates:
                print(f"candidate limit reached: checked={checked - 1} hits={hits}")
                return 0
            values = coset_translation_values(args.prime, args.index, zero_value, slopes)
            if len(set(values)) != args.prime:
                continue
            if translation_e677_failures(values):
                continue
            table = translation_table(values)
            hits += 1
            is_bad = maybe_report_hit(
                "coset-translation",
                f"prime={args.prime} index={args.index} zero={zero_value} slopes={format_values(slopes)}",
                table,
                args,
            )
            if is_bad and args.stop_on_bad:
                return 2
            if args.max_hits and hits >= args.max_hits:
                print(f"stopped after max_hits={args.max_hits}; checked={checked}")
                return 0
    print(f"coset-translation scan complete: checked={checked} hits={hits}")
    return 0


def polynomial_values(prime: int, coefficients: Sequence[int]) -> tuple[int, ...]:
    values: list[int] = []
    for point in range(prime):
        total = 0
        power = 1
        for coefficient in coefficients:
            total = (total + coefficient * power) % prime
            power = (power * point) % prime
        values.append(total)
    return tuple(values)


def scan_polynomial_translation(args: argparse.Namespace) -> int:
    hits = 0
    checked = 0
    for prime in prime_values(args.max_prime):
        if prime < args.min_prime:
            continue
        coefficient_ranges: list[Iterable[int]] = []
        if args.zero_value is None:
            coefficient_ranges.append(range(prime))
        else:
            coefficient_ranges.append([args.zero_value % prime])
        coefficient_ranges.extend(range(prime) for _ in range(args.degree))
        for coefficients in itertools.product(*coefficient_ranges):
            checked += 1
            if args.max_candidates and checked > args.max_candidates:
                print(f"candidate limit reached: checked={checked - 1} hits={hits}")
                return 0
            values = polynomial_values(prime, coefficients)
            if len(set(values)) != prime:
                continue
            if translation_e677_failures(values):
                continue
            table = translation_table(values)
            hits += 1
            is_bad = maybe_report_hit(
                "polynomial-translation",
                f"prime={prime} degree={args.degree} coeffs={format_values(coefficients)}",
                table,
                args,
            )
            if is_bad and args.stop_on_bad:
                return 2
            if args.max_hits and hits >= args.max_hits:
                print(f"stopped after max_hits={args.max_hits}; checked={checked}")
                return 0
    print(f"polynomial-translation scan complete: checked={checked} hits={hits}")
    return 0


def linear_base_satisfies_e677(prime: int, alpha: int, beta: int) -> bool:
    left_coeff = (alpha + beta * beta * (alpha * alpha + beta)) % prime
    target_coeff = (alpha * beta * (1 + beta * beta)) % prime
    return left_coeff == 0 and target_coeff == 1


def linear_base_e255_coefficient(prime: int, alpha: int, beta: int) -> int:
    coefficient = 1
    for _ in range(3):
        coefficient = (alpha * coefficient + beta) % prime
    return coefficient


def inverse_mod(value: int, modulus: int) -> int:
    reduced = value % modulus
    if reduced == 0:
        raise ZeroDivisionError("inverse of zero")
    return pow(reduced, -1, modulus)


def labels_for(prime: int) -> list[int]:
    return list(range(prime)) + [prime]


def label_name(label: int, prime: int) -> str:
    return "inf" if label == prime else str(label)


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
            omega_values.append(infinity if omega_linear == 0 else inverse_mod(omega_linear, prime))
            continue
        if label == 0:
            mu_values.append(infinity)
        else:
            mu_values.append((alpha + beta * inverse_mod(label, prime)) % prime)
        nu_denominator = (linear * label + mixed) % prime
        nu_values.append(infinity if nu_denominator == 0 else inverse_mod(nu_denominator, prime))
        omega_denominator = (omega_linear * label + omega_const) % prime
        omega_values.append(infinity if omega_denominator == 0 else (label * inverse_mod(omega_denominator, prime)) % prime)
    return mu_values, nu_values, omega_values


def e255_slope_chain(prime: int, alpha: int, beta: int) -> tuple[int, int, int]:
    first = 1 % prime
    second = (alpha + beta) % prime
    third = (alpha * second + beta) % prime
    return first, second, third


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


def involved_identity_lambdas(
    labels: Sequence[int],
    watched: set[int],
    mu_values: Sequence[int],
    nu_values: Sequence[int],
    omega_values: Sequence[int],
) -> set[int]:
    involved: set[int] = set()
    for label in labels:
        if watched.intersection((label, mu_values[label], nu_values[label], omega_values[label])):
            involved.add(label)
    return involved


def scan_colored_candidates(args: argparse.Namespace) -> int:
    q_values = [value for value in prime_values(args.max_q) if value >= args.min_q]
    if args.q:
        q_values = [args.q]
    records: list[tuple[int, dict[str, object]]] = []
    for prime in prime_values(args.max_prime):
        if prime < args.min_prime:
            continue
        for alpha in range(prime):
            for beta in range(1, prime):
                if not linear_base_satisfies_e677(prime, alpha, beta):
                    continue
                labels = labels_for(prime)
                mu_values, nu_values, omega_values = slope_maps(prime, alpha, beta)
                first_slope, second_slope, bad_slope = e255_slope_chain(prime, alpha, beta)
                chain = (first_slope, second_slope, bad_slope)
                distinct_chain = len(set(chain))
                if not args.allow_degenerate_chain and distinct_chain < 3:
                    continue
                closure = slope_closure(chain, mu_values, nu_values, omega_values, args.closure_depth)
                involved = involved_identity_lambdas(labels, closure, mu_values, nu_values, omega_values)
                bad_involved = involved_identity_lambdas(labels, {bad_slope}, mu_values, nu_values, omega_values)
                finite_closure = len([label for label in closure if label != prime])
                for color_prime in q_values:
                    if args.max_order and prime * color_prime > args.max_order:
                        continue
                    if args.min_order and prime * color_prime < args.min_order:
                        continue
                    c3_seed_valid = color_prime > 3 and math.gcd(3, color_prime) == 1
                    bad_diagonal_points = color_prime - 1 if color_prime > 2 else 0
                    score = (
                        prime * color_prime
                        + 7 * len(closure)
                        + 3 * len(involved)
                        + 2 * len(bad_involved)
                        - 5 * distinct_chain
                        - (3 if c3_seed_valid else 0)
                    )
                    records.append((score, {
                        "p": prime,
                        "q": color_prime,
                        "alpha": alpha,
                        "beta": beta,
                        "s1": second_slope,
                        "bad": bad_slope,
                        "chain": chain,
                        "closure": len(closure),
                        "finite_closure": finite_closure,
                        "involved": len(involved),
                        "bad_involved": len(bad_involved),
                        "c3_seed_valid": c3_seed_valid,
                        "bad_diagonal_points": bad_diagonal_points,
                    }))
    records.sort(key=lambda item: item[0])
    for rank, (score, record) in enumerate(records[:args.top], start=1):
        p = int(record["p"])
        q = int(record["q"])
        alpha = int(record["alpha"])
        beta = int(record["beta"])
        bad = int(record["bad"])
        print(
            f"#{rank:03d} score={score} order={p*q} p={p} q={q} A={alpha} B={beta} "
            f"chain=1->{record['s1']}->{bad} closure={record['closure']} "
            f"involved={record['involved']} bad_involved={record['bad_involved']} "
            f"c3_seed={'yes' if record['c3_seed_valid'] else 'no'} "
            f"bad_diag={record['bad_diagonal_points']}"
        )
        if args.show_commands:
            print(
                "  stats: & .\\.venv\\Scripts\\python.exe .\\explore_colored_magma.py "
                f"--config custom --p {p} --q {q} --A {alpha} --B {beta} --bad-slope {bad} --mode stats"
            )
            if q == 7:
                print(
                    "  deep:  & .\\.venv\\Scripts\\python.exe .\\explore_colored_magma.py "
                    f"--config custom --p {p} --q {q} --A {alpha} --B {beta} --bad-slope {bad} "
                    "--mode deep --solver cadical --default-branch none --propagate-branches --progress-conflicts 50000 --out custom_solution.json"
                )
    print(f"colored-candidates complete: candidates={len(records)} shown={min(args.top, len(records))}")
    return 0


def slope_of_pair(prime: int, left_base: int, right_base: int) -> int:
    if right_base % prime == 0:
        if left_base % prime == 0:
            raise ValueError("zero pair has no projective slope")
        return prime
    return (left_base * inverse_mod(right_base, prime)) % prime


def affine_color_matrix(modulus: int, left_coeff: int, right_coeff: int, constant: int) -> Table:
    return [
        [((left_coeff * left) + (right_coeff * right) + constant) % modulus for right in range(modulus)]
        for left in range(modulus)
    ]


def colored_operation(
    prime: int,
    color_modulus: int,
    alpha: int,
    beta: int,
    slope_operations: dict[int, Table],
    zero_operation: Table,
    left: tuple[int, int],
    right: tuple[int, int],
) -> tuple[int, int]:
    left_base, left_color = left
    right_base, right_color = right
    out_base = (alpha * left_base + beta * right_base) % prime
    if left_base % prime == 0 and right_base % prime == 0:
        out_color = zero_operation[left_color][right_color]
    else:
        label = slope_of_pair(prime, left_base, right_base)
        out_color = slope_operations[label][left_color][right_color]
    return out_base, out_color


def colored_e677_ok(
    prime: int,
    color_modulus: int,
    alpha: int,
    beta: int,
    slope_operations: dict[int, Table],
    zero_operation: Table,
) -> bool:
    elements = [(base, color) for base in range(prime) for color in range(color_modulus)]
    for target in elements:
        for parameter in elements:
            first = colored_operation(prime, color_modulus, alpha, beta, slope_operations, zero_operation, parameter, target)
            second = colored_operation(prime, color_modulus, alpha, beta, slope_operations, zero_operation, first, parameter)
            third = colored_operation(prime, color_modulus, alpha, beta, slope_operations, zero_operation, target, second)
            if colored_operation(prime, color_modulus, alpha, beta, slope_operations, zero_operation, parameter, third) != target:
                return False
    return True


def colored_e255_failures(
    prime: int,
    color_modulus: int,
    alpha: int,
    beta: int,
    slope_operations: dict[int, Table],
    zero_operation: Table,
) -> list[tuple[int, int]]:
    failures: list[tuple[int, int]] = []
    elements = [(base, color) for base in range(prime) for color in range(color_modulus)]
    for element in elements:
        first = colored_operation(prime, color_modulus, alpha, beta, slope_operations, zero_operation, element, element)
        second = colored_operation(prime, color_modulus, alpha, beta, slope_operations, zero_operation, first, element)
        third = colored_operation(prime, color_modulus, alpha, beta, slope_operations, zero_operation, second, element)
        if third != element:
            failures.append(element)
    return failures


def affine_color_operations_from_assignment(
    color_modulus: int,
    assignment: dict[int, tuple[int, int, int]],
) -> dict[int, Table]:
    return {
        label: affine_color_matrix(color_modulus, left_coeff, right_coeff, constant)
        for label, (left_coeff, right_coeff, constant) in assignment.items()
    }


def scan_affine_zero_operations(
    prime: int,
    color_modulus: int,
    alpha: int,
    beta: int,
    slope_operations: dict[int, Table],
    args: argparse.Namespace,
) -> tuple[int, int]:
    full_hits = 0
    bad_hits = 0
    for left_coeff in range(color_modulus):
        for right_coeff in range(color_modulus):
            if math.gcd(right_coeff, color_modulus) != 1:
                continue
            for constant in range(color_modulus):
                zero_operation = affine_color_matrix(color_modulus, left_coeff, right_coeff, constant)
                if not colored_e677_ok(prime, color_modulus, alpha, beta, slope_operations, zero_operation):
                    continue
                full_hits += 1
                failures = colored_e255_failures(
                    prime, color_modulus, alpha, beta, slope_operations, zero_operation
                )
                if failures:
                    bad_hits += 1
                print(
                    "affine-colors full-hit: "
                    f"prime={prime} q={color_modulus} alpha={alpha} beta={beta} "
                    f"zero=({left_coeff},{right_coeff},{constant}) "
                    f"e255_failures={format_values([b * color_modulus + c for b, c in failures]) if failures else 'none'}"
                )
                if args.stop_on_bad and failures:
                    return full_hits, bad_hits
                if args.max_full_hits and full_hits >= args.max_full_hits:
                    return full_hits, bad_hits
    return full_hits, bad_hits


def forced_affine_color(
    color_modulus: int,
    label_op: tuple[int, int, int],
    mu_op: tuple[int, int, int],
    nu_op: tuple[int, int, int],
) -> tuple[int, int, int] | None:
    a_l, b_l, c_l = label_op
    a_m, b_m, c_m = mu_op
    a_n, b_n, c_n = nu_op
    u_i = (a_m * a_l + b_m) % color_modulus
    u_j = (a_m * b_l) % color_modulus
    u_c = (a_m * c_l + c_m) % color_modulus
    v_i = (b_n * u_i) % color_modulus
    v_j = (a_n + b_n * u_j) % color_modulus
    v_c = (b_n * u_c + c_n) % color_modulus
    if v_j == 0:
        return None
    b_w = inverse_mod(v_j, color_modulus)
    a_w = (-b_w * v_i) % color_modulus
    c_w = (-b_w * v_c) % color_modulus
    return a_w, b_w, c_w


def propagate_affine_assignment(
    color_modulus: int,
    constraints: Sequence[tuple[int, int, int, int]],
    assignment: dict[int, tuple[int, int, int]],
) -> bool:
    changed = True
    while changed:
        changed = False
        for label, mu_label, nu_label, omega_label in constraints:
            if label not in assignment or mu_label not in assignment or nu_label not in assignment:
                continue
            forced = forced_affine_color(
                color_modulus,
                assignment[label],
                assignment[mu_label],
                assignment[nu_label],
            )
            if forced is None:
                return False
            old = assignment.get(omega_label)
            if old is None:
                assignment[omega_label] = forced
                changed = True
            elif old != forced:
                return False
    return True


def choose_affine_label(
    labels: Sequence[int],
    constraints: Sequence[tuple[int, int, int, int]],
    assignment: dict[int, tuple[int, int, int]],
) -> int:
    best_label = next(label for label in labels if label not in assignment)
    best_score = -1
    for candidate in labels:
        if candidate in assignment:
            continue
        score = 0
        for label, mu_label, nu_label, omega_label in constraints:
            antecedents = (label, mu_label, nu_label)
            if candidate in antecedents:
                score += sum(1 for item in antecedents if item in assignment)
            if candidate == omega_label:
                score += 1
        if score > best_score:
            best_score = score
            best_label = candidate
    return best_label


def iter_affine_color_assignments(
    labels: Sequence[int],
    color_modulus: int,
    domain: Sequence[tuple[int, int, int]],
    constraints: Sequence[tuple[int, int, int, int]],
    args: argparse.Namespace,
) -> Iterable[tuple[dict[int, tuple[int, int, int]], int, bool]]:
    start = time.time()
    nodes = 0
    timed_out = False

    def search(assignment: dict[int, tuple[int, int, int]]) -> Iterable[dict[int, tuple[int, int, int]]]:
        nonlocal nodes, timed_out
        if timed_out:
            return
        if args.timeout_ms > 0 and (time.time() - start) * 1000 >= args.timeout_ms:
            timed_out = True
            return
        nodes += 1
        if args.max_nodes and nodes > args.max_nodes:
            timed_out = True
            return
        assignment = dict(assignment)
        if not propagate_affine_assignment(color_modulus, constraints, assignment):
            return
        if len(assignment) == len(labels):
            yield assignment
            return
        label = choose_affine_label(labels, constraints, assignment)
        for value in domain:
            child = dict(assignment)
            child[label] = value
            yield from search(child)

    yielded = 0
    for solution in search({}):
        yielded += 1
        yield solution, nodes, timed_out
        if args.max_models and yielded >= args.max_models:
            return
    yield {}, nodes, timed_out


def scan_affine_colors(args: argparse.Namespace) -> int:
    if not is_prime(args.prime):
        raise SystemExit("--prime must be prime")
    if not is_prime(args.q):
        raise SystemExit("--q must be prime for affine color scans")
    if not linear_base_satisfies_e677(args.prime, args.alpha, args.beta):
        raise SystemExit("the selected prime-field base does not satisfy E677")

    prime = args.prime
    color_modulus = args.q
    labels = labels_for(prime)
    mu_values, nu_values, omega_values = slope_maps(prime, args.alpha, args.beta)

    constants = range(color_modulus) if args.constants else [0]
    domain = [
        (left_coeff, right_coeff, constant)
        for left_coeff in range(color_modulus)
        for right_coeff in range(1, color_modulus)
        for constant in constants
    ]
    constraints = [
        (label, mu_values[label], nu_values[label], omega_values[label])
        for label in labels
    ]

    slope_models = 0
    full_hits = 0
    bad_hits = 0
    last_nodes = 0
    timed_out = False
    seen_assignment_keys: set[tuple[tuple[int, tuple[int, int, int]], ...]] = set()

    def assignment_key(assignment: dict[int, tuple[int, int, int]]) -> tuple[tuple[int, tuple[int, int, int]], ...]:
        return tuple(sorted(assignment.items()))

    def process_assignment(assignment: dict[int, tuple[int, int, int]]) -> bool:
        nonlocal slope_models, full_hits, bad_hits
        key = assignment_key(assignment)
        if key in seen_assignment_keys:
            return False
        seen_assignment_keys.add(key)
        slope_models += 1
        if args.show_slope_model:
            rendered = " ".join(
                f"O_{label_name(label, prime)}={assignment[label]}" for label in labels
            )
            print(f"affine-colors slope-model {slope_models}: {rendered}")

        slope_operations = affine_color_operations_from_assignment(color_modulus, assignment)
        model_full_hits, model_bad_hits = scan_affine_zero_operations(
            prime, color_modulus, args.alpha, args.beta, slope_operations, args
        )
        full_hits += model_full_hits
        bad_hits += model_bad_hits
        return bool(args.stop_on_bad and model_bad_hits) or bool(args.max_full_hits and full_hits >= args.max_full_hits)

    if args.uniform_first:
        for value in domain:
            assignment = {label: value for label in labels}
            if not propagate_affine_assignment(color_modulus, constraints, assignment):
                continue
            if process_assignment(assignment):
                print(
                    f"affine-colors scan complete: slope_models={slope_models} "
                    f"full_hits={full_hits} bad_hits={bad_hits} nodes={last_nodes} timed_out={timed_out}"
                )
                return 2 if bad_hits else 0
            if args.max_models and slope_models >= args.max_models:
                print(
                    f"affine-colors scan complete: slope_models={slope_models} "
                    f"full_hits={full_hits} bad_hits={bad_hits} nodes={last_nodes} timed_out={timed_out}"
                )
                return 2 if bad_hits else 0
        if args.uniform_only:
            print(
                f"affine-colors scan complete: slope_models={slope_models} "
                f"full_hits={full_hits} bad_hits={bad_hits} nodes={last_nodes} timed_out={timed_out}"
            )
            return 2 if bad_hits else 0

    for assignment, nodes, timed_out in iter_affine_color_assignments(
        labels, color_modulus, domain, constraints, args
    ):
        last_nodes = nodes
        if not assignment:
            break
        if process_assignment(assignment):
            print(
                f"affine-colors scan complete: slope_models={slope_models} "
                f"full_hits={full_hits} bad_hits={bad_hits} nodes={last_nodes} timed_out={timed_out}"
            )
            return 2 if bad_hits else 0
        if args.max_models and slope_models >= args.max_models:
            break

    print(
        f"affine-colors scan complete: slope_models={slope_models} "
        f"full_hits={full_hits} bad_hits={bad_hits} nodes={last_nodes} timed_out={timed_out}"
    )
    return 2 if bad_hits else 0


def scan_linear_bases(args: argparse.Namespace) -> int:
    hits = 0
    for prime in prime_values(args.max_prime):
        if prime < args.min_prime:
            continue
        for alpha in range(prime):
            for beta in range(1, prime):
                if not linear_base_satisfies_e677(prime, alpha, beta):
                    continue
                hits += 1
                coefficient = linear_base_e255_coefficient(prime, alpha, beta)
                print(
                    f"linear-base: prime={prime} alpha={alpha} beta={beta} "
                    f"base_e255={'yes' if coefficient == 1 else 'no'} e255_coeff={coefficient}"
                )
                if args.show_maps:
                    mu_values, nu_values, omega_values = slope_maps(prime, alpha, beta)
                    for label in labels_for(prime):
                        print(
                            f"  lambda={label_name(label, prime):>3} "
                            f"mu={label_name(mu_values[label], prime):>3} "
                            f"nu={label_name(nu_values[label], prime):>3} "
                            f"omega={label_name(omega_values[label], prime):>3}"
                        )
                if args.max_hits and hits >= args.max_hits:
                    print(f"stopped after max_hits={args.max_hits}")
                    return 0
    print(f"linear-base scan complete: hits={hits}")
    return 0


def add_common_hit_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-hits", type=int, default=0, help="stop after this many E677 hits; 0 means no limit")
    parser.add_argument("--stop-on-bad", action="store_true", help="stop immediately if an E677 hit violates E255")
    parser.add_argument("--show-table", action="store_true", help="print every E677 hit table")
    parser.add_argument("--show-bad-table", action="store_true", help="print the table for any E677 hit violating E255")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Explore explicit algebraic construction families for finite E677 magmas."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    affine = subparsers.add_parser("affine", help="scan laws left*right = alpha*left + beta*right + constant mod n")
    affine.add_argument("--max-order", type=int, default=40)
    affine.add_argument("--left-latin", action=argparse.BooleanOptionalAction, default=True)
    add_common_hit_options(affine)
    affine.set_defaults(func=scan_affine)

    translation = subparsers.add_parser("translation", help="scan laws left*right = left + f(right-left) mod n")
    translation.add_argument("--max-order", type=int, default=8)
    translation.add_argument("--exhaustive-order", type=int, default=8, help="exhaust permutations through this order")
    translation.add_argument("--samples-per-order", type=int, default=2000, help="random samples above exhaustive order")
    translation.add_argument("--seed", type=int, default=677)
    translation.add_argument("--fix-zero", action="store_true", help="only use f(0)=0, the idempotent subfamily")
    add_common_hit_options(translation)
    translation.set_defaults(func=scan_translation)

    coset = subparsers.add_parser("coset-translation", help="scan prime-field coset-piecewise translation laws")
    coset.add_argument("--prime", type=int, required=True)
    coset.add_argument("--index", type=int, default=2, help="multiplicative coset index; must divide prime - 1")
    coset.add_argument("--zero-value", type=int, default=None, help="fix f(0); omit to scan all values")
    coset.add_argument("--max-candidates", type=int, default=250000)
    add_common_hit_options(coset)
    coset.set_defaults(func=scan_coset_translation)

    polynomial = subparsers.add_parser(
        "polynomial-translation",
        help="scan prime-field translation laws from polynomial permutations",
    )
    polynomial.add_argument("--min-prime", type=int, default=3)
    polynomial.add_argument("--max-prime", type=int, default=17)
    polynomial.add_argument("--degree", type=int, default=3)
    polynomial.add_argument("--zero-value", type=int, default=None, help="fix f(0), i.e. the constant coefficient")
    polynomial.add_argument("--max-candidates", type=int, default=250000)
    add_common_hit_options(polynomial)
    polynomial.set_defaults(func=scan_polynomial_translation)

    affine_colors = subparsers.add_parser(
        "affine-colors",
        help="solve affine color operations over F_q on a prime-field linear base",
    )
    affine_colors.add_argument("--prime", type=int, required=True)
    affine_colors.add_argument("--q", type=int, required=True)
    affine_colors.add_argument("--alpha", type=int, required=True)
    affine_colors.add_argument("--beta", type=int, required=True)
    affine_colors.add_argument("--constants", action=argparse.BooleanOptionalAction, default=True)
    affine_colors.add_argument("--timeout-ms", type=int, default=10000)
    affine_colors.add_argument("--max-nodes", type=int, default=200000, help="backtracking node budget; 0 means unlimited")
    affine_colors.add_argument("--max-models", type=int, default=20, help="slope-color models to enumerate; 0 means unlimited")
    affine_colors.add_argument("--max-full-hits", type=int, default=20, help="verified full colored magmas to print; 0 means unlimited")
    affine_colors.add_argument("--uniform-first", action=argparse.BooleanOptionalAction, default=True)
    affine_colors.add_argument("--uniform-only", action="store_true", help="only test uniform slope-color operations")
    affine_colors.add_argument("--show-slope-model", action="store_true")
    affine_colors.add_argument("--stop-on-bad", action="store_true", help="stop immediately if a verified full hit violates E255")
    affine_colors.set_defaults(func=scan_affine_colors)

    colored_candidates = subparsers.add_parser(
        "colored-candidates",
        help="rank F_p x F_q colored-slope parameter choices before SAT search",
    )
    colored_candidates.add_argument("--min-prime", type=int, default=5)
    colored_candidates.add_argument("--max-prime", type=int, default=200)
    colored_candidates.add_argument("--min-q", type=int, default=5)
    colored_candidates.add_argument("--max-q", type=int, default=19)
    colored_candidates.add_argument("--q", type=int, default=0, help="restrict to one color field size")
    colored_candidates.add_argument("--min-order", type=int, default=0)
    colored_candidates.add_argument("--max-order", type=int, default=0)
    colored_candidates.add_argument("--closure-depth", type=int, default=2)
    colored_candidates.add_argument("--top", type=int, default=40)
    colored_candidates.add_argument("--allow-degenerate-chain", action="store_true")
    colored_candidates.add_argument("--show-commands", action="store_true")
    colored_candidates.set_defaults(func=scan_colored_candidates)

    bases = subparsers.add_parser("linear-bases", help="list prime-field linear bases usable for colored-slope probes")
    bases.add_argument("--min-prime", type=int, default=3)
    bases.add_argument("--max-prime", type=int, default=200)
    bases.add_argument("--max-hits", type=int, default=0)
    bases.add_argument("--show-maps", action="store_true")
    bases.set_defaults(func=scan_linear_bases)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())