from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Sequence

try:
    import z3  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - exercised by users without z3
    raise SystemExit("z3-solver is required; use the repository virtualenv") from exc


Table = list[list[int]]


def left_div(table: Table, left: int, value: int) -> int | None:
    for candidate, product in enumerate(table[left]):
        if product == value:
            return candidate
    return None


def e677_at(table: Table, x: int, y: int) -> bool:
    return table[y][table[x][table[table[y][x]][y]]] == x


def e255_at(table: Table, x: int) -> bool:
    return table[table[table[x][x]][x]][x] == x


def left_rows_are_permutations(table: Table) -> bool:
    order = len(table)
    expected = set(range(order))
    return all(set(row) == expected for row in table)


def check_table(table: Table) -> tuple[bool, list[str]]:
    order = len(table)
    errors: list[str] = []
    if not left_rows_are_permutations(table):
        errors.append("some left row is not a permutation")
    for x in range(order):
        for y in range(order):
            if not e677_at(table, x, y):
                errors.append(f"E677 fails at x={x}, y={y}")
                return False, errors
    return not errors, errors


def orbit_under_left(table: Table, x: int) -> list[int]:
    current = x
    orbit: list[int] = []
    for _ in range(len(table) + 1):
        orbit.append(current)
        current = table[x][current]
        if current == x:
            return orbit
    raise ValueError(f"left orbit of {x} did not return within the table")


def cycle_decomposition(mapping: list[int]) -> list[list[int]]:
    seen: set[int] = set()
    cycles: list[list[int]] = []
    for start in range(len(mapping)):
        if start in seen:
            continue
        current = start
        cycle: list[int] = []
        while current not in seen:
            seen.add(current)
            cycle.append(current)
            current = mapping[current]
        cycles.append(cycle)
    return cycles


def right_fibers(table: Table, x: int) -> dict[int, list[int]]:
    fibers: dict[int, list[int]] = defaultdict(list)
    for y in range(len(table)):
        fibers[table[y][x]].append(y)
    return dict(fibers)


def format_table(table: Table) -> str:
    width = max(1, len(str(len(table) - 1)))
    rows = [" ".join(f"{value:{width}d}" for value in row) for row in table]
    return "\n".join(rows)


def linear_table(prime: int, alpha: int, beta: int, const: int) -> Table:
    return [
        [((alpha * x) + (beta * y) + const) % prime for y in range(prime)]
        for x in range(prime)
    ]


def witness_summary(table: Table, x: int, max_fibers: int = 4) -> str:
    a = table[x][x]
    q = table[a][x]
    p = left_div(table, x, x)
    r = table[q][x]
    h = table[r][q]
    orbit = orbit_under_left(table, x)
    h_map = [table[table[x][t]][x] for t in range(len(table))]
    f_map = [table[x][table[t][x]] for t in range(len(table))]

    lines = [
        f"witness x={x}",
        f"  orbit under L_x: {orbit} (period {len(orbit)})",
        f"  a=x*x={a}, q=(x*x)*x={q}, p=x\\x={p}",
        f"  r=q*x={r}, h=(q*x)*q={h}",
        f"  E255 at x: {e255_at(table, x)}",
        f"  H_x cycles: {cycle_decomposition(h_map)}",
        f"  F_x cycles: {cycle_decomposition(f_map)}",
    ]

    collided = [(value, fiber) for value, fiber in right_fibers(table, x).items() if len(fiber) > 1]
    if collided:
        lines.append("  right collisions in column x:")
        for value, fiber in collided[:max_fibers]:
            quotient = left_div(table, value, x)
            splitters = [table[y][value] for y in fiber]
            rectangles = [table[table[y][value]][y] == quotient for y in fiber]
            lines.append(
                f"    value {value}: fiber={fiber}, splitters={splitters}, "
                f"r\\x={quotient}, rectangles={rectangles}"
            )
    else:
        lines.append("  no right collision in column x")
    return "\n".join(lines)


@dataclass
class SearchConfig:
    backend: str
    order: int
    witness: int
    period: int | None
    branch: str
    timeout_ms: int
    require_left_permutations: bool
    require_label_injective: bool
    add_orbit_facts: bool
    add_derived_identities: bool
    add_bad_point_lemmas: bool
    add_collision_splitter: bool
    symmetry_break_bad_orbit: bool
    symmetry_break_period4_external: bool
    show_constraint_counts: bool
    track_groups: bool
    minimize_core: bool
    core_check_timeout_ms: int


class E677Search:
    def __init__(self, config: SearchConfig):
        self.config = config
        self.order = config.order
        self.solver = z3.Solver()
        if config.timeout_ms > 0:
            self.solver.set(timeout=config.timeout_ms)
        self.constraint_counts: Counter[str] = Counter()
        self.group_literals: dict[str, z3.BoolRef] = {}
        self.cells = [
            [z3.Int(f"m_{row}_{col}") for col in range(self.order)]
            for row in range(self.order)
        ]
        op_array = z3.K(z3.IntSort(), z3.IntVal(0))
        for row in range(self.order):
            for col in range(self.order):
                op_array = z3.Store(op_array, row * self.order + col, self.cells[row][col])
        self.op_array = op_array

    def add(self, *constraints: z3.BoolRef, group: str) -> None:
        if self.config.track_groups:
            literal = self.group_literals.setdefault(group, z3.Bool(f"use_{group}"))
        else:
            literal = None
        for constraint in constraints:
            if literal is None:
                self.solver.add(constraint)
            else:
                self.solver.add(z3.Implies(literal, constraint))
            self.constraint_counts[group] += 1

    def as_expr(self, value: int | z3.ArithRef) -> z3.ArithRef:
        if isinstance(value, int):
            return z3.IntVal(value)
        return value

    def mul(self, left: int | z3.ArithRef, right: int | z3.ArithRef) -> z3.ArithRef:
        left_expr = self.as_expr(left)
        right_expr = self.as_expr(right)
        return z3.Select(self.op_array, left_expr * self.order + right_expr)

    def add_domain_constraints(self) -> None:
        for row in self.cells:
            for cell in row:
                self.add(cell >= 0, cell < self.order, group="domain")

    def add_left_permutation_constraints(self) -> None:
        for row in range(self.order):
            self.add(z3.Distinct([self.mul(row, col) for col in range(self.order)]), group="left_rows_permutations")

    def add_label_injective_constraints(self) -> None:
        for first in range(self.order):
            for second in range(first + 1, self.order):
                self.add(
                    z3.Or([self.mul(first, col) != self.mul(second, col) for col in range(self.order)]),
                    group="label_injective",
                )

    def add_e677_constraints(self) -> None:
        for x in range(self.order):
            for y in range(self.order):
                self.add(self.mul(y, self.mul(x, self.mul(self.mul(y, x), y))) == self.as_expr(x), group="e677")

    def add_derived_identity_constraints(self) -> None:
        for y in range(self.order):
            for z in range(self.order):
                yz = self.mul(y, z)
                y_yz = self.mul(y, yz)
                self.add(self.mul(yz, self.mul(y_yz, y)) == self.as_expr(z), group="transformed_identity")
                self.add(
                    self.mul(y_yz, y) == self.mul(z, self.mul(self.mul(yz, z), yz)),
                    group="key_identity",
                )

    def add_bad_point_lemmas(self) -> None:
        x = self.config.witness
        c1 = self.mul(x, x)
        c2 = self.mul(x, c1)
        c3 = self.mul(x, c2)
        q = self.mul(c1, x)
        r = self.mul(q, x)
        p = self.mul(x, q)
        h = self.mul(r, q)
        lemma_l = self.mul(self.mul(c1, q), c1)

        self.add(z3.Distinct(self.as_expr(x), c1, c2, c3), group="bad_orbit_period_ge_4")
        if self.config.symmetry_break_bad_orbit and self.config.period is None and x == 0 and self.order >= 4:
            self.add(c1 == self.as_expr(1), c2 == self.as_expr(2), c3 == self.as_expr(3), group="bad_orbit_symmetry_break")

        for y in range(self.order):
            self.add(self.mul(y, x) != self.as_expr(x), group="bad_column_misses_x")

        right_collisions = [
            self.mul(first, x) == self.mul(second, x)
            for first in range(self.order)
            for second in range(first + 1, self.order)
        ]
        self.add(z3.Or(right_collisions) if right_collisions else z3.BoolVal(False), group="bad_column_collision")

        for t in range(self.order):
            self.add(self.mul(self.mul(x, t), x) != self.as_expr(t), group="bad_H_fixed_point_free")
            self.add(self.mul(x, self.mul(t, x)) != self.as_expr(t), group="bad_F_fixed_point_free")

        self.add(h != self.as_expr(p), lemma_l != self.as_expr(x), self.mul(x, h) != self.as_expr(x), group="bad_equivalent_targets_fail")

    def add_collision_splitter_constraints(self) -> None:
        for z in range(self.order):
            for first in range(self.order):
                for second in range(first + 1, self.order):
                    first_value = self.mul(first, z)
                    second_value = self.mul(second, z)
                    first_splitter = self.mul(first, first_value)
                    second_splitter = self.mul(second, second_value)
                    self.add(
                        z3.Implies(first_value == second_value, first_splitter != second_splitter),
                        group="right_fiber_splitter_injective",
                    )

    def add_bad_witness(self) -> None:
        x = self.config.witness
        c1 = self.mul(x, x)
        q = self.mul(c1, x)
        self.add(self.mul(q, x) != self.as_expr(x), group="bad_witness")

    def add_period_constraints(self) -> None:
        period = self.config.period
        if period is None:
            return
        if self.config.witness != 0:
            raise ValueError("period symmetry breaking currently requires --witness 0")
        if period < 1 or period > self.order:
            raise ValueError("period must satisfy 1 <= period <= order")
        for value in range(period - 1):
            self.add(self.mul(0, value) == self.as_expr(value + 1), group="period_orbit")
        self.add(self.mul(0, period - 1) == self.as_expr(0), group="period_orbit")

        if not self.config.add_orbit_facts:
            return
        if period >= 2:
            self.add(self.mul(1, 0) == self.as_expr(period - 2), group="orbit_facts")
        for k in range(period):
            c_prev = (k - 1) % period
            c_k = k
            c_next = (k + 1) % period
            self.add(self.mul(c_k, self.mul(c_next, 0)) == self.as_expr(c_prev), group="orbit_facts")

    def add_period_four_gate(self) -> None:
        if self.config.period != 4:
            if self.config.branch != "any":
                raise ValueError("period-four branch constraints require --period 4")
            return
        x, a, q, p = 0, 1, 2, 3
        r = self.mul(q, x)
        s = self.mul(p, x)
        h = self.mul(r, q)
        qa = self.mul(q, a)
        self.add(self.mul(x, a) == self.as_expr(q), group="period4_gate")
        self.add(self.mul(a, x) == self.as_expr(q), group="period4_gate")
        self.add(self.mul(a, r) == self.as_expr(x), group="period4_gate")
        self.add(self.mul(x, q) == self.as_expr(p), group="period4_gate")
        self.add(self.mul(p, a) == self.as_expr(q), group="period4_gate")
        self.add(r != self.as_expr(x), r != self.as_expr(a), r != self.as_expr(q), group="period4_gate")
        self.add(self.mul(q, s) == self.as_expr(a), group="period4_derived")
        self.add(self.mul(self.mul(p, q), p) == s, group="period4_derived")
        self.add(self.mul(a, h) == r, group="period4_derived")
        if self.config.branch == "r=p":
            self.add(r == self.as_expr(p), group="period4_branch_r_eq_p")
            self.add(qa == self.as_expr(q), group="period4_branch_r_eq_p_derived")
        elif self.config.branch == "external":
            self.add(r != self.as_expr(p), group="period4_branch_external")
            self.add(qa != r, group="period4_branch_external_derived")
            self.add(qa != self.as_expr(x), qa != self.as_expr(a), qa != self.as_expr(q), qa != self.as_expr(p), group="period4_branch_external_derived")
            self.add(self.mul(x, qa) == r, group="period4_branch_external_derived")
            if self.config.symmetry_break_period4_external and self.order >= 5:
                self.add(r == self.as_expr(4), group="period4_external_symmetry_break")
                if self.order >= 6:
                    self.add(qa == self.as_expr(5), group="period4_external_symmetry_break")

    def build(self) -> None:
        self.add_domain_constraints()
        if self.config.require_left_permutations:
            self.add_left_permutation_constraints()
        if self.config.require_label_injective:
            self.add_label_injective_constraints()
        self.add_e677_constraints()
        if self.config.add_derived_identities:
            self.add_derived_identity_constraints()
        self.add_bad_witness()
        if self.config.add_bad_point_lemmas:
            self.add_bad_point_lemmas()
        if self.config.add_collision_splitter:
            self.add_collision_splitter_constraints()
        self.add_period_constraints()
        self.add_period_four_gate()

    def extract_table(self, model: z3.ModelRef) -> Table:
        return [
            [model.eval(self.cells[row][col], model_completion=True).as_long() for col in range(self.order)]
            for row in range(self.order)
        ]

    def run(self) -> tuple[z3.CheckSatResult, Table | None]:
        self.build()
        if self.config.track_groups:
            result = self.solver.check(*self.group_literals.values())
        else:
            result = self.solver.check()
        if result != z3.sat:
            return result, None
        return result, self.extract_table(self.solver.model())

    def group_unsat_core(self) -> list[str]:
        literal_to_group = {literal: group for group, literal in self.group_literals.items()}
        return [literal_to_group[literal] for literal in self.solver.unsat_core()]

    def minimized_group_unsat_core(self) -> list[str]:
        groups = self.group_unsat_core()
        kept = list(groups)
        if self.config.core_check_timeout_ms > 0:
            self.solver.set(timeout=self.config.core_check_timeout_ms)
        for group in groups:
            trial = [candidate for candidate in kept if candidate != group]
            assumptions = [self.group_literals[candidate] for candidate in trial]
            if self.solver.check(*assumptions) == z3.unsat:
                kept = trial
        return kept


class E677EnumSearch(E677Search):
    def __init__(self, config: SearchConfig):
        self.config = config
        self.order = config.order
        self.solver = z3.Solver()
        if config.timeout_ms > 0:
            self.solver.set(timeout=config.timeout_ms)
        self.constraint_counts: Counter[str] = Counter()
        self.group_literals: dict[str, z3.BoolRef] = {}
        self.sort, self.elements = z3.EnumSort("M", [f"e{index}" for index in range(self.order)])
        self.op = z3.Function("op", self.sort, self.sort, self.sort)

    def add_domain_constraints(self) -> None:
        return

    def as_expr(self, value: int | z3.ExprRef) -> z3.ExprRef:
        if isinstance(value, int):
            return self.elements[value]
        return value

    def mul(self, left: int | z3.ExprRef, right: int | z3.ExprRef) -> z3.ExprRef:
        return self.op(self.as_expr(left), self.as_expr(right))

    def extract_table(self, model: z3.ModelRef) -> Table:
        table: Table = []
        for row in range(self.order):
            values: list[int] = []
            for col in range(self.order):
                product = model.eval(self.mul(row, col), model_completion=True)
                for index, element in enumerate(self.elements):
                    if product.eq(element):
                        values.append(index)
                        break
                else:
                    raise ValueError(f"could not decode enum product {product}")
            table.append(values)
        return table

    def run(self) -> tuple[z3.CheckSatResult, Table | None]:
        self.build()
        if self.config.track_groups:
            result = self.solver.check(*self.group_literals.values())
        else:
            result = self.solver.check()
        if result != z3.sat:
            return result, None
        return result, self.extract_table(self.solver.model())

    def group_unsat_core(self) -> list[str]:
        literal_to_group = {literal: group for group, literal in self.group_literals.items()}
        return [literal_to_group[literal] for literal in self.solver.unsat_core()]

    def minimized_group_unsat_core(self) -> list[str]:
        groups = self.group_unsat_core()
        kept = list(groups)
        if self.config.core_check_timeout_ms > 0:
            self.solver.set(timeout=self.config.core_check_timeout_ms)
        for group in groups:
            trial = [candidate for candidate in kept if candidate != group]
            assumptions = [self.group_literals[candidate] for candidate in trial]
            if self.solver.check(*assumptions) == z3.unsat:
                kept = trial
        return kept


def print_validation(table: Table, witness: int) -> None:
    ok, errors = check_table(table)
    print(format_table(table))
    print()
    print(f"verified E677 and left permutations: {ok}")
    if errors:
        for error in errors:
            print(f"  {error}")
    failing = [x for x in range(len(table)) if not e255_at(table, x)]
    print(f"E255 failing witnesses: {failing}")
    print(witness_summary(table, witness))


def search_command(args: argparse.Namespace) -> int:
    config = SearchConfig(
        backend=args.backend,
        order=args.order,
        witness=args.witness,
        period=args.period,
        branch=args.branch,
        timeout_ms=args.timeout_ms,
        require_left_permutations=not args.no_left_permutations,
        require_label_injective=not args.no_label_injective,
        add_orbit_facts=not args.no_orbit_facts,
        add_derived_identities=not args.no_derived_identities,
        add_bad_point_lemmas=not args.no_bad_point_lemmas,
        add_collision_splitter=not args.no_collision_splitter,
        symmetry_break_bad_orbit=not args.no_symmetry_break_bad_orbit,
        symmetry_break_period4_external=not args.no_symmetry_break_period4_external,
        show_constraint_counts=args.show_constraint_counts,
        track_groups=args.track_groups,
        minimize_core=args.minimize_core,
        core_check_timeout_ms=args.core_check_timeout_ms,
    )
    search_class = E677EnumSearch if config.backend == "enum" else E677Search
    search = search_class(config)
    result, table = search.run()
    print(f"result: {result}")
    if config.show_constraint_counts:
        print("constraint groups:")
        for group, count in search.constraint_counts.most_common():
            print(f"  {group}: {count}")
    if table is None:
        if result == z3.unsat and config.track_groups:
            core = search.minimized_group_unsat_core() if config.minimize_core else search.group_unsat_core()
            label = "minimized unsat core groups" if config.minimize_core else "unsat core groups"
            print(f"{label}:")
            for group in core:
                print(f"  {group}")
        if result == z3.unknown:
            print(f"reason: {search.solver.reason_unknown()}")
        return 0 if result == z3.unsat else 2
    print_validation(table, args.witness)
    return 0


def calibrate_linear_command(args: argparse.Namespace) -> int:
    table = linear_table(args.prime, args.alpha, args.beta, args.const)
    print_validation(table, args.witness)
    return 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def add_common_summary_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--witness", type=int, default=0, help="witness element for diagnostics")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Proof-directed finite searches for E677 vs E255")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="search for a finite E677 model failing E255")
    search.add_argument("--backend", choices=["enum", "array"], default="enum", help="Z3 encoding backend")
    search.add_argument("--order", type=positive_int, required=True, help="finite carrier size")
    add_common_summary_args(search)
    search.add_argument("--period", type=positive_int, help="fix the witness L_x orbit period")
    search.add_argument(
        "--branch",
        choices=["any", "r=p", "external"],
        default="any",
        help="period-four gate branch to enforce",
    )
    search.add_argument("--timeout-ms", type=int, default=30000, help="Z3 timeout in milliseconds; 0 means none")
    search.add_argument("--no-left-permutations", action="store_true", help="do not add left-row permutation constraints")
    search.add_argument("--no-label-injective", action="store_true", help="do not add row-label injectivity constraints")
    search.add_argument("--no-orbit-facts", action="store_true", help="do not add trusted orbit recurrence facts")
    search.add_argument("--no-derived-identities", action="store_true", help="do not add transformed/key identity constraints")
    search.add_argument("--no-bad-point-lemmas", action="store_true", help="do not add bad-witness consequences")
    search.add_argument("--no-collision-splitter", action="store_true", help="do not add right-fiber splitter constraints")
    search.add_argument(
        "--no-symmetry-break-bad-orbit",
        action="store_true",
        help="do not relabel the first bad L_x orbit points to 0,1,2,3 when possible",
    )
    search.add_argument(
        "--no-symmetry-break-period4-external",
        action="store_true",
        help="do not relabel period-four external branch points r=q*x and q*a",
    )
    search.add_argument("--show-constraint-counts", action="store_true", help="print added constraint groups")
    search.add_argument("--track-groups", action="store_true", help="use group assumptions and print an UNSAT core")
    search.add_argument("--minimize-core", action="store_true", help="greedily minimize the group UNSAT core")
    search.add_argument(
        "--core-check-timeout-ms",
        type=int,
        default=5000,
        help="per-check timeout for greedy core minimization; 0 means no separate limit",
    )
    search.set_defaults(func=search_command)

    calibrate = subparsers.add_parser("calibrate-linear", help="verify a linear model table")
    calibrate.add_argument("--prime", type=positive_int, default=5, help="field size, expected prime")
    calibrate.add_argument("--alpha", type=int, default=2, help="coefficient of x")
    calibrate.add_argument("--beta", type=int, default=-1, help="coefficient of y")
    calibrate.add_argument("--const", type=int, default=0, help="constant term")
    add_common_summary_args(calibrate)
    calibrate.set_defaults(func=calibrate_linear_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())