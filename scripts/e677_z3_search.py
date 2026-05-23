from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Sequence

from e677_api import MANIFEST_URL, configure_utf8_stdio, load_manifest as load_db_manifest

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


def e255_failures(table: Table) -> list[int]:
    return [x for x in range(len(table)) if not e255_at(table, x)]


def left_rows_are_permutations(table: Table) -> bool:
    order = len(table)
    expected = set(range(order))
    return all(set(row) == expected for row in table)


def right_cancellative(table: Table) -> bool:
    order = len(table)
    for col in range(order):
        values = {table[row][col] for row in range(order)}
        if len(values) != order:
            return False
    return True


def idempotent(table: Table) -> bool:
    return all(table[x][x] == x for x in range(len(table)))


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


def classify_size_commentary(comment: str) -> str:
    lowered = comment.lower()
    first_line = lowered.strip().splitlines()[0] if lowered.strip() else ""
    if (
        first_line.startswith("no magma")
        or first_line.startswith("no eq 677 magma")
        or first_line.startswith("no eq677 magma")
    ) and "currently known" not in first_line and "open" not in first_line:
        return "empty"
    if "open" in lowered or "currently known" in lowered or "no known" in lowered or "unknown" in lowered:
        return "open"
    return "note"


def format_int_list(values: Sequence[int], limit: int = 40) -> str:
    listed = list(values)
    if not listed:
        return "none"
    rendered = ", ".join(str(value) for value in listed[:limit])
    if len(listed) > limit:
        rendered += ", ..."
    return rendered


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


def phi10_mod(value: int, modulus: int) -> int:
    reduced = value % modulus
    return (pow(reduced, 4, modulus) - pow(reduced, 3, modulus) + pow(reduced, 2, modulus) - reduced + 1) % modulus


def phi10_roots_mod_prime(prime: int) -> list[int]:
    return [value for value in range(prime) if phi10_mod(value, prime) == 0]


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


def quadratic_residues_mod_prime(prime: int) -> set[int]:
    return {pow(value, 2, prime) for value in range(1, prime)}


def qr_piecewise_values(
    prime: int,
    qr_slope: int,
    nqr_slope: int,
    residues: set[int] | None = None,
) -> list[int]:
    residues = residues if residues is not None else quadratic_residues_mod_prime(prime)
    values = [0] * prime
    for difference in range(1, prime):
        slope = qr_slope if difference in residues else nqr_slope
        values[difference] = (slope * difference) % prime
    return values


def translation_table_from_values(values: Sequence[int]) -> Table:
    order = len(values)
    return [
        [(left + values[(right - left) % order]) % order for right in range(order)]
        for left in range(order)
    ]


def translation_e677_difference_failures(values: Sequence[int]) -> list[int]:
    order = len(values)
    failures: list[int] = []
    for difference in range(order):
        y_times_x = (difference + values[-difference % order]) % order
        yx_times_y = (y_times_x + values[(difference - y_times_x) % order]) % order
        inner = values[yx_times_y]
        result = (difference + values[(inner - difference) % order]) % order
        if result != 0:
            failures.append(difference)
    return failures


def frontier_hints(size: int) -> tuple[int, list[str]]:
    score = 0
    hints: list[str] = []
    if is_prime(size):
        score += 2
        roots = phi10_roots_mod_prime(size)
        if roots:
            hints.append(f"prime field linear Phi_10 roots {format_int_list(roots, 12)}")
        else:
            score += 1
            hints.append("prime field has no Phi_10 root; try QR/coset piecewise-linear search")
    if size % 20 in (1, 5):
        score += 3
        hints.append("Steiner S(2,5,n) congruence is admissible")
    if size > 5 and size % 5 == 0:
        score += 1
        hints.append("F_5-based bundle, pencil, or CRT-Steiner probe")
    if not is_prime(size) and size > 1:
        score += 1
        hints.append("composite size: product/fiber-bundle probe")
    return score, hints or ["generic bad-witness row-Latin search"]


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
    period4_external_cycle: str
    period4_external_lx_cycle_size: int | None
    period5_branch: str
    period5_s_branch: str
    lx_complement_cycles: tuple[int, ...] | None
    fixed_cells: tuple[tuple[int, int, int], ...]
    fixed_terms: tuple[tuple[str, int], ...]
    term_equalities: tuple[tuple[str, str], ...]
    term_inequalities: tuple[tuple[str, str], ...]
    timeout_ms: int
    require_bad_witness: bool
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


class TermParser:
    def __init__(self, search: E677Search, tokens: list[str]):  # type: ignore[name-defined]
        self.search = search
        self.tokens = tokens
        self.position = 0

    def has_remaining_tokens(self) -> bool:
        return self.position < len(self.tokens)

    def peek(self) -> str | None:
        if self.has_remaining_tokens():
            return self.tokens[self.position]
        return None

    def take(self) -> str:
        token = self.peek()
        if token is None:
            raise ValueError("unexpected end of term")
        self.position += 1
        return token

    def parse_expression(self) -> z3.ExprRef:
        parsed = self.parse_factor()
        while self.peek() == "*":
            self.take()
            parsed = self.search.mul(parsed, self.parse_factor())
        return parsed

    def parse_factor(self) -> z3.ExprRef:
        token = self.take()
        if token == "(":
            parsed = self.parse_expression()
            if self.take() != ")":
                raise ValueError("unbalanced parentheses in term")
            return parsed
        if token == ")" or token == "*":
            raise ValueError(f"unexpected token in term: {token!r}")
        if token.isdecimal():
            value = int(token)
            if value >= self.search.order:
                raise ValueError("numeric term labels must be less than --order")
            return self.search.as_expr(value)
        return self.search.named_term_expr(token)


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

    def add_fixed_cell_constraints(self) -> None:
        for row, col, value in self.config.fixed_cells:
            if row >= self.order or col >= self.order or value >= self.order:
                raise ValueError("fixed cell entries must be less than --order")
            self.add(self.mul(row, col) == self.as_expr(value), group="fixed_cells")

    def add_fixed_term_constraints(self) -> None:
        for term, value in self.config.fixed_terms:
            if value >= self.order:
                raise ValueError("fixed term values must be less than --order")
            self.add(self.term_expr(term) == self.as_expr(value), group="fixed_terms")

    def add_term_relation_constraints(self) -> None:
        for left, right in self.config.term_equalities:
            self.add(self.term_expr(left) == self.term_expr(right), group="term_equalities")
        for left, right in self.config.term_inequalities:
            self.add(self.term_expr(left) != self.term_expr(right), group="term_inequalities")

    def term_expr(self, term: str) -> z3.ExprRef:
        tokens = re.findall(r"\d+|[A-Za-z_][A-Za-z0-9_]*|[()*]", term)
        if not tokens or "".join(tokens) != re.sub(r"\s+", "", term):
            raise ValueError(f"could not parse term {term!r}")
        parser = TermParser(self, tokens)
        parsed = parser.parse_expression()
        if parser.has_remaining_tokens():
            raise ValueError(f"unexpected token in term {term!r}: {parser.peek()!r}")
        return parsed

    def named_term_expr(self, name: str) -> z3.ExprRef:
        witness = self.config.witness
        witness_expr = self.as_expr(witness)
        orbit_match = re.fullmatch(r"c(\d+)", name)
        if orbit_match:
            index = int(orbit_match.group(1))
            current = witness_expr
            for _ in range(index):
                current = self.mul(witness_expr, current)
            return current

        right_tail_match = re.fullmatch(r"rho(\d+)", name)
        if right_tail_match:
            index = int(right_tail_match.group(1))
            current = witness_expr
            for _ in range(index):
                current = self.mul(current, witness_expr)
            return current

        a_expr = self.mul(witness_expr, witness_expr)
        b_expr = self.mul(witness_expr, a_expr)
        c_expr = self.mul(witness_expr, b_expr)
        q_expr = self.mul(a_expr, witness_expr)
        p_expr = self.mul(witness_expr, q_expr)
        r_expr = self.mul(q_expr, witness_expr)

        named_terms = {
            "x": witness_expr,
            "a": a_expr,
            "b": b_expr,
            "c": c_expr,
            "q": q_expr,
            "p": p_expr,
            "g": r_expr,
            "r": r_expr,
            "s": self.mul(p_expr, witness_expr),
            "h": self.mul(r_expr, q_expr),
            "t": self.mul(q_expr, a_expr),
            "u": self.mul(witness_expr, r_expr),
        }
        if name not in named_terms:
            raise ValueError(f"unknown term name {name!r}")
        return named_terms[name]

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
            if self.config.lx_complement_cycles is not None:
                raise ValueError("L_x complement cycle constraints require --period")
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

    def add_lx_complement_cycle_constraints(self) -> None:
        cycles = self.config.lx_complement_cycles
        if cycles is None:
            return
        period = self.config.period
        if period is None:
            raise ValueError("L_x complement cycle constraints require --period")
        remaining = self.order - period
        if sum(cycles) != remaining:
            raise ValueError("L_x complement cycle sizes must sum to order - period")
        label = period
        for size in cycles:
            if size == 1:
                self.add(self.mul(0, label) == self.as_expr(label), group="lx_complement_cycles")
            else:
                for offset in range(size - 1):
                    self.add(
                        self.mul(0, label + offset) == self.as_expr(label + offset + 1),
                        group="lx_complement_cycles",
                    )
                self.add(self.mul(0, label + size - 1) == self.as_expr(label), group="lx_complement_cycles")
            for offset in range(size):
                node = label + offset
                next_node = label + ((offset + 1) % size)
                previous_node = label + ((offset - 1) % size)
                self.add(
                    self.mul(node, self.mul(next_node, 0)) == self.as_expr(previous_node),
                    group="lx_complement_cycle_recurrence",
                )
            label += size

    def add_period_orbit_derived_constraints(self) -> None:
        period = self.config.period
        if period is None:
            return
        x = 0
        for index in range(period):
            node = index
            next_node = (index + 1) % period
            next_next_node = (index + 2) % period
            node_x = self.mul(node, x)
            self.add(
                self.mul(node_x, self.mul(self.mul(node, node_x), node)) == self.as_expr(x),
                group="period_transformed_orbit_derived",
            )
            self.add(
                self.mul(next_next_node, x)
                == self.mul(node, self.mul(self.mul(next_node, node), next_node)),
                group="period_key_orbit_derived",
            )
            self.add(
                self.mul(self.mul(node, node_x), node)
                == self.mul(x, self.mul(self.mul(node_x, x), node_x)),
                group="period_uniform_u3_derived",
            )
        if self.config.require_bad_witness and self.config.add_bad_point_lemmas and period >= 4:
            q = period - 2
            g = self.mul(q, x)
            self.add(
                g != self.as_expr(period - 3),
                self.mul(x, g) != self.as_expr(q),
                group="period_bad_point_derived",
            )

    def add_period_four_gate(self) -> None:
        if self.config.period != 4:
            if self.config.branch != "any":
                raise ValueError("period-four branch constraints require --period 4")
            if self.config.period4_external_cycle != "any":
                raise ValueError("period-four external cycle constraints require --period 4 --branch external")
            if self.config.period4_external_lx_cycle_size is not None:
                raise ValueError("period-four external L_x cycle constraints require --period 4 --branch external")
            return
        if self.config.period4_external_lx_cycle_size is not None and self.config.branch != "external":
            raise ValueError("period-four external L_x cycle constraints require --branch external")
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
            if self.config.period4_external_cycle != "any":
                raise ValueError("period-four external cycle constraints require --branch external")
            self.add(r == self.as_expr(p), group="period4_branch_r_eq_p")
            self.add(qa == self.as_expr(q), group="period4_branch_r_eq_p_derived")
            qq = self.mul(q, q)
            self.add(s == self.mul(qq, q), s == self.mul(a, qq), group="period4_branch_r_eq_p_derived")
        elif self.config.branch == "external":
            self.add(r != self.as_expr(p), group="period4_branch_external")
            self.add(qa != r, group="period4_branch_external_derived")
            self.add(qa != self.as_expr(x), qa != self.as_expr(a), qa != self.as_expr(q), qa != self.as_expr(p), group="period4_branch_external_derived")
            self.add(self.mul(x, qa) == r, group="period4_branch_external_derived")
            xr = self.mul(x, r)
            x_xr = self.mul(x, xr)
            self.add(
                xr != self.as_expr(x),
                xr != self.as_expr(a),
                xr != self.as_expr(q),
                xr != self.as_expr(p),
                xr != r,
                group="period4_branch_external_derived",
            )
            self.add(s != self.as_expr(x), s != self.as_expr(a), s != self.as_expr(q), group="period4_branch_external_derived")
            self.add(h != self.as_expr(x), h != self.as_expr(p), h != r, group="period4_branch_external_derived")
            self.add(self.mul(r, self.mul(xr, x)) == qa, group="period4_external_recurrence")
            self.add(self.mul(xr, self.mul(x_xr, x)) == r, group="period4_external_recurrence")
            if self.config.symmetry_break_period4_external and self.order >= 5:
                self.add(r == self.as_expr(4), group="period4_external_symmetry_break")
                if self.order >= 6:
                    self.add(qa == self.as_expr(5), group="period4_external_symmetry_break")
            cycle_size = self.config.period4_external_lx_cycle_size
            if cycle_size is not None:
                if cycle_size < 2:
                    raise ValueError("period-four external L_x cycle size must be at least 2")
                if cycle_size > self.order - 4:
                    raise ValueError("period-four external L_x cycle size is too large for the carrier")
                if self.config.period4_external_cycle == "two-cycle" and cycle_size != 2:
                    raise ValueError("--period4-external-cycle two-cycle requires --period4-external-lx-cycle-size 2")
                if self.config.period4_external_cycle == "third" and cycle_size == 2:
                    raise ValueError("--period4-external-cycle third requires external L_x cycle size at least 3")
                self.add_period_four_external_lx_cycle(qa, r, xr, cycle_size)
            elif self.config.period4_external_cycle == "two-cycle":
                self.add(xr == qa, group="period4_external_two_cycle")
            elif self.config.period4_external_cycle == "third":
                self.add(xr != qa, group="period4_external_third_point")
                if self.config.symmetry_break_period4_external and self.order >= 7:
                    self.add(xr == self.as_expr(6), group="period4_external_third_point")

    def add_period_four_external_lx_cycle(
        self,
        t: z3.ExprRef,
        r: z3.ExprRef,
        u: z3.ExprRef,
        cycle_size: int,
    ) -> None:
        x = 0
        nodes = [t, r]
        if cycle_size == 2:
            self.add(u == t, group="period4_external_two_cycle")
        else:
            nodes.append(u)
            self.add(u != t, group="period4_external_third_point")
            if self.config.symmetry_break_period4_external and self.order >= 7:
                self.add(u == self.as_expr(6), group="period4_external_third_point")
            for offset in range(cycle_size - 3):
                next_node = self.mul(x, nodes[-1])
                nodes.append(next_node)
                if self.config.symmetry_break_period4_external:
                    self.add(next_node == self.as_expr(7 + offset), group="period4_external_lx_cycle_symmetry_break")
            self.add(z3.Distinct(nodes), group="period4_external_lx_cycle_size")
            self.add(self.mul(x, nodes[-1]) == t, group="period4_external_lx_cycle_size")
        for index, node in enumerate(nodes):
            previous_node = nodes[(index - 1) % cycle_size]
            next_node = nodes[(index + 1) % cycle_size]
            self.add(self.mul(node, self.mul(next_node, x)) == previous_node, group="period4_external_lx_cycle_recurrence")

    def add_period_five_gate(self) -> None:
        if self.config.period != 5:
            if self.config.period5_branch != "any":
                raise ValueError("period-five branch constraints require --period 5")
            if self.config.period5_s_branch != "any":
                raise ValueError("period-five s-branch constraints require --period 5 --period5-branch g=p")
            return
        x, a, b, q, p = 0, 1, 2, 3, 4
        g = self.mul(q, x)
        aq = self.mul(a, q)
        self.add(self.mul(a, x) == self.as_expr(q), group="period5_gate")
        self.add(self.mul(x, q) == self.as_expr(p), group="period5_gate")
        self.add(self.mul(x, p) == self.as_expr(x), group="period5_gate")
        self.add(self.mul(p, a) == self.as_expr(q), group="period5_gate")
        self.add(g == self.mul(a, self.mul(self.mul(b, a), b)), group="period5_derived")
        self.add(self.mul(q, self.mul(aq, a)) == self.as_expr(x), group="period5_derived")
        self.add(self.mul(aq, a) == self.mul(x, self.mul(g, q)), group="period5_derived")
        self.add(g != self.as_expr(x), group="period5_derived")
        if self.config.add_bad_point_lemmas:
            self.add(g != self.as_expr(b), group="period5_derived_bad_point")
        self.add_period_five_branch_constraints()

    def add_period_five_branch_constraints(self) -> None:
        x, a, b, q, p = 0, 1, 2, 3, 4
        g = self.mul(q, x)
        s = self.mul(p, x)
        aq = self.mul(a, q)
        qa = self.mul(q, a)
        qq = self.mul(q, q)
        qp = self.mul(q, p)
        pp = self.mul(p, p)
        bx = self.mul(b, x)

        branch = self.config.period5_branch
        if branch == "internal":
            self.add(z3.Or(g == self.as_expr(a), g == self.as_expr(q), g == self.as_expr(p)), group="period5_branch_internal")
        elif branch == "external":
            self.add(
                g != self.as_expr(x),
                g != self.as_expr(a),
                g != self.as_expr(b),
                g != self.as_expr(q),
                g != self.as_expr(p),
                group="period5_branch_external",
            )
        elif branch == "g=q":
            self.add(g == self.as_expr(q), group="period5_branch_g_eq_q")
            self.add(self.mul(b, q) == self.as_expr(a), group="period5_branch_g_eq_q")
            self.add(self.mul(aq, a) == self.mul(qq, q), group="period5_branch_g_eq_q_splitter")
            self.add(aq != qq, group="period5_branch_g_eq_q_splitter")
        elif branch == "g=a":
            self.add(g == self.as_expr(a), group="period5_branch_g_eq_a")
            self.add(self.mul(b, a) == self.as_expr(a), group="period5_branch_g_eq_a")
            self.add(self.mul(qa, q) == bx, group="period5_branch_g_eq_a_splitter")
            self.add(qa != self.as_expr(b), group="period5_branch_g_eq_a_splitter")
        elif branch == "g=p":
            self.add(g == self.as_expr(p), group="period5_branch_g_eq_p")
            self.add(self.mul(b, p) == self.as_expr(a), group="period5_branch_g_eq_p")
            self.add(self.mul(q, s) == self.as_expr(b), group="period5_branch_g_eq_p")
            self.add(s != self.as_expr(x), s != self.as_expr(q), group="period5_branch_g_eq_p")
        elif branch != "any":
            raise ValueError(f"unknown period-five branch {branch!r}")

        s_branch = self.config.period5_s_branch
        if s_branch == "any":
            return
        if branch != "g=p":
            raise ValueError("--period5-s-branch requires --period5-branch g=p")
        if s_branch == "internal":
            self.add(z3.Or(s == self.as_expr(a), s == self.as_expr(b), s == self.as_expr(p)), group="period5_s_branch_internal")
        elif s_branch == "external":
            self.add(
                s != self.as_expr(x),
                s != self.as_expr(a),
                s != self.as_expr(b),
                s != self.as_expr(q),
                s != self.as_expr(p),
                group="period5_s_branch_external",
            )
        elif s_branch == "s=a":
            self.add(s == self.as_expr(a), group="period5_s_branch_s_eq_a")
            self.add(qa == self.as_expr(b), group="period5_s_branch_s_eq_a")
            self.add(qp == bx, group="period5_s_branch_s_eq_a_splitter")
        elif s_branch == "s=b":
            self.add(s == self.as_expr(b), group="period5_s_branch_s_eq_b")
            self.add(self.mul(q, b) == self.as_expr(b), group="period5_s_branch_s_eq_b")
        elif s_branch == "s=p":
            self.add(s == self.as_expr(p), group="period5_s_branch_s_eq_p")
            self.add(qp == self.as_expr(b), group="period5_s_branch_s_eq_p")
            self.add(self.mul(b, q) == self.mul(pp, p), group="period5_s_branch_s_eq_p_splitter")
            self.add(qp != pp, group="period5_s_branch_s_eq_p_splitter")
        else:
            raise ValueError(f"unknown period-five s-branch {s_branch!r}")

    def add_period_six_gate(self) -> None:
        if self.config.period != 6:
            return
        x, a, b, c, q, p = 0, 1, 2, 3, 4, 5
        h = self.mul(c, x)
        g = self.mul(q, x)
        aq = self.mul(a, q)
        self.add(self.mul(a, x) == self.as_expr(q), group="period6_gate")
        self.add(self.mul(x, q) == self.as_expr(p), group="period6_gate")
        self.add(self.mul(x, p) == self.as_expr(x), group="period6_gate")
        self.add(self.mul(p, a) == self.as_expr(q), group="period6_gate")
        self.add(h == self.mul(a, self.mul(self.mul(b, a), b)), group="period6_derived")
        self.add(g == self.mul(b, self.mul(self.mul(c, b), c)), group="period6_derived")
        self.add(self.mul(q, self.mul(aq, a)) == self.as_expr(x), group="period6_derived")
        self.add(self.mul(aq, a) == self.mul(x, self.mul(g, q)), group="period6_derived")
        self.add(g != self.as_expr(x), group="period6_derived")

    def build(self) -> None:
        self.add_domain_constraints()
        if self.config.require_left_permutations:
            self.add_left_permutation_constraints()
        if self.config.require_label_injective:
            self.add_label_injective_constraints()
        self.add_e677_constraints()
        if self.config.add_derived_identities:
            self.add_derived_identity_constraints()
        if self.config.require_bad_witness:
            self.add_bad_witness()
        if self.config.require_bad_witness and self.config.add_bad_point_lemmas:
            self.add_bad_point_lemmas()
        if self.config.add_collision_splitter:
            self.add_collision_splitter_constraints()
        self.add_fixed_cell_constraints()
        self.add_fixed_term_constraints()
        self.add_term_relation_constraints()
        self.add_period_constraints()
        self.add_lx_complement_cycle_constraints()
        self.add_period_orbit_derived_constraints()
        if self.config.require_bad_witness:
            self.add_period_four_gate()
            self.add_period_five_gate()
            self.add_period_six_gate()

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
    sort_counter = 0

    def __init__(self, config: SearchConfig):
        self.config = config
        self.order = config.order
        self.solver = z3.Solver()
        if config.timeout_ms > 0:
            self.solver.set(timeout=config.timeout_ms)
        self.constraint_counts: Counter[str] = Counter()
        self.group_literals: dict[str, z3.BoolRef] = {}
        E677EnumSearch.sort_counter += 1
        sort_name = f"M_{E677EnumSearch.sort_counter}_{self.order}"
        self.sort, self.elements = z3.EnumSort(sort_name, [f"e{E677EnumSearch.sort_counter}_{index}" for index in range(self.order)])
        self.op = z3.Function(f"op_{E677EnumSearch.sort_counter}", self.sort, self.sort, self.sort)

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


def print_validation(
    table: Table,
    witness: int,
    *,
    show_table: bool = True,
    show_witness_summary: bool = True,
) -> None:
    ok, errors = check_table(table)
    if show_table:
        print(format_table(table))
        print()
    print(f"verified E677 and left permutations: {ok}")
    if errors:
        for error in errors:
            print(f"  {error}")
    failing = [x for x in range(len(table)) if not e255_at(table, x)]
    print(f"E255 failing witnesses: {failing}")
    print(f"right cancellative: {right_cancellative(table)}")
    print(f"idempotent: {idempotent(table)}")
    if show_witness_summary:
        print(witness_summary(table, witness))


def search_command(args: argparse.Namespace) -> int:
    config = search_config_from_args(args, period=args.period, branch=args.branch)
    search = make_search(config)
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


def existence_command(args: argparse.Namespace) -> int:
    config = search_config_from_args(args, period=args.period, branch="any", require_bad_witness=False)
    search = make_search(config)
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
        return 1 if result == z3.unsat else 2
    print_validation(table, args.witness)
    return 0


def search_config_from_args(
    args: argparse.Namespace,
    period: int | None,
    branch: str,
    period4_external_cycle: str | None = None,
    require_bad_witness: bool = True,
) -> SearchConfig:
    return SearchConfig(
        backend=args.backend,
        order=args.order,
        witness=getattr(args, "witness", 0),
        period=period,
        branch=branch,
        period4_external_cycle=period4_external_cycle or getattr(args, "period4_external_cycle", "any"),
        period4_external_lx_cycle_size=getattr(args, "period4_external_lx_cycle_size", None),
        period5_branch=getattr(args, "period5_branch", "any"),
        period5_s_branch=getattr(args, "period5_s_branch", "any"),
        lx_complement_cycles=getattr(args, "lx_complement_cycles", None),
        fixed_cells=tuple(getattr(args, "fix_cell", None) or ()),
        fixed_terms=tuple(getattr(args, "fix_term", None) or ()),
        term_equalities=tuple(getattr(args, "eq_term", None) or ()),
        term_inequalities=tuple(getattr(args, "neq_term", None) or ()),
        timeout_ms=args.timeout_ms,
        require_bad_witness=require_bad_witness,
        require_left_permutations=not getattr(args, "no_left_permutations", False),
        require_label_injective=not getattr(args, "no_label_injective", False),
        add_orbit_facts=not getattr(args, "no_orbit_facts", False),
        add_derived_identities=not getattr(args, "no_derived_identities", False),
        add_bad_point_lemmas=require_bad_witness and not getattr(args, "no_bad_point_lemmas", False),
        add_collision_splitter=not getattr(args, "no_collision_splitter", False),
        symmetry_break_bad_orbit=not getattr(args, "no_symmetry_break_bad_orbit", False),
        symmetry_break_period4_external=not getattr(args, "no_symmetry_break_period4_external", False),
        show_constraint_counts=getattr(args, "show_constraint_counts", False),
        track_groups=getattr(args, "track_groups", False),
        minimize_core=getattr(args, "minimize_core", False),
        core_check_timeout_ms=getattr(args, "core_check_timeout_ms", 5000),
    )


def make_search(config: SearchConfig) -> E677Search:
    search_class = E677EnumSearch if config.backend == "enum" else E677Search
    return search_class(config)


def sweep_command(args: argparse.Namespace) -> int:
    any_unknown = False
    periods: Sequence[int] = range(args.start_period, args.order + 1)
    if args.period5_branch != "any" or args.period5_s_branch != "any":
        periods = [5] if args.start_period <= 5 <= args.order else []
    for period in periods:
        branches = ["r=p", "external"] if period == 4 else ["any"]
        for branch in branches:
            label = f"period={period}" if branch == "any" else f"period={period}, branch={branch}"
            print(f"== {label} ==")
            cycle = args.period4_external_cycle if branch == "external" else "any"
            config = search_config_from_args(args, period=period, branch=branch, period4_external_cycle=cycle)
            search = make_search(config)
            result, table = search.run()
            print(f"result: {result}")
            if table is not None:
                print_validation(table, args.witness)
                return 1
            if result == z3.unknown:
                any_unknown = True
                print(f"reason: {search.solver.reason_unknown()}")
    return 2 if any_unknown else 0


def split_command(args: argparse.Namespace) -> int:
    split_terms: list[str] = args.split_term or []
    if not split_terms:
        raise ValueError("split requires --split-term")
    base_fixed_terms = list(args.fix_term or [])
    summary: Counter[str] = Counter()
    found_sat = False
    found_unknown = False

    def run_leaf(fixed_terms: list[tuple[str, int]], labels: list[str]) -> bool:
        nonlocal found_sat, found_unknown
        branch_args = argparse.Namespace(**vars(args))
        branch_args.fix_term = fixed_terms
        config = search_config_from_args(branch_args, period=args.period, branch=args.branch)
        search = make_search(config)
        result, table = search.run()
        summary[str(result)] += 1
        label = ", ".join(labels) if labels else "base"
        print(f"== {label} ==")
        print(f"result: {result}")
        if config.show_constraint_counts:
            print("constraint groups:")
            for group, count in search.constraint_counts.most_common():
                print(f"  {group}: {count}")
        if table is not None:
            found_sat = True
            print_validation(table, args.witness)
            return not args.continue_after_sat
        if result == z3.unknown:
            found_unknown = True
            print(f"reason: {search.solver.reason_unknown()}")
        return False

    def recurse(index: int, fixed_terms: list[tuple[str, int]], labels: list[str]) -> bool:
        if index == len(split_terms):
            return run_leaf(fixed_terms, labels)
        term = split_terms[index]
        for value in range(args.order):
            if recurse(index + 1, fixed_terms + [(term, value)], labels + [f"{term}={value}"]):
                return True
        return False

    recurse(0, base_fixed_terms, [f"{term}={value}" for term, value in base_fixed_terms])
    print("summary:")
    for result, count in summary.items():
        print(f"  {result}: {count}")
    if found_sat:
        return 1
    if found_unknown:
        return 2
    return 0


def calibrate_linear_command(args: argparse.Namespace) -> int:
    table = linear_table(args.prime, args.alpha, args.beta, args.const)
    print_validation(table, args.witness)
    return 0


def print_piecewise_pair(
    prime: int,
    qr_slope: int,
    nqr_slope: int,
    *,
    residues: set[int],
    validate_table: bool,
) -> bool:
    values = qr_piecewise_values(prime, qr_slope, nqr_slope, residues)
    failures = translation_e677_difference_failures(values)
    is_permutation = len(set(values)) == prime
    ok = is_permutation and not failures
    print(
        f"qr={qr_slope % prime} nqr={nqr_slope % prime} "
        f"perm={is_permutation} diff_e677_failures={len(failures)} "
        f"Phi_10=({phi10_mod(qr_slope, prime)}, {phi10_mod(nqr_slope, prime)})"
    )
    if failures:
        print(f"  first failing differences: {format_int_list(failures[:12], 12)}")
    if validate_table and ok:
        table = translation_table_from_values(values)
        table_ok, errors = check_table(table)
        print(f"  table_check={table_ok} e255_failures={e255_failures(table)} right_cancel={right_cancellative(table)}")
        if errors:
            for error in errors[:3]:
                print(f"    {error}")
        ok = table_ok
    return ok


def piecewise_prime_command(args: argparse.Namespace) -> int:
    prime = args.prime
    if not is_prime(prime):
        raise ValueError("--prime must be prime for QR/NQR piecewise search")
    explicit_pair = args.qr_slope is not None or args.nqr_slope is not None
    if explicit_pair and (args.qr_slope is None or args.nqr_slope is None):
        raise ValueError("provide both --qr-slope and --nqr-slope, or use --all-pairs")
    roots = phi10_roots_mod_prime(prime)
    residues = quadratic_residues_mod_prime(prime)
    print(f"prime: {prime}")
    print(f"Phi_10 roots: {format_int_list(roots, 20)}")

    if explicit_pair:
        table = translation_table_from_values(qr_piecewise_values(prime, args.qr_slope, args.nqr_slope, residues))
        print_piecewise_pair(prime, args.qr_slope, args.nqr_slope, residues=residues, validate_table=False)
        print_validation(
            table,
            args.witness,
            show_table=args.print_table,
            show_witness_summary=args.witness_summary,
        )
        ok, _errors = check_table(table)
        return 0 if ok and not e255_failures(table) else 1

    if not args.all_pairs:
        raise ValueError("provide slopes with --qr-slope/--nqr-slope or request enumeration with --all-pairs")

    matches: list[tuple[int, int]] = []
    for qr_slope in range(prime):
        for nqr_slope in range(prime):
            values = qr_piecewise_values(prime, qr_slope, nqr_slope, residues)
            if len(set(values)) != prime:
                continue
            if translation_e677_difference_failures(values):
                continue
            matches.append((qr_slope, nqr_slope))

    print(f"QR/NQR candidate pairs: {len(matches)}")
    for qr_slope, nqr_slope in matches[: args.limit]:
        print_piecewise_pair(prime, qr_slope, nqr_slope, residues=residues, validate_table=args.validate_found)
    if len(matches) > args.limit:
        print(f"... {len(matches) - args.limit} more pair(s) not printed")
    return 0 if matches else 1


def db_frontier_command(args: argparse.Namespace) -> int:
    manifest = load_db_manifest(args.manifest)
    magmas = manifest["magmas"]
    if args.max_size < args.min_size:
        raise ValueError("--max-size must be at least --min-size")

    by_size = Counter(int(record["size"]) for record in magmas)
    present_sizes = set(by_size)
    size_commentary = {
        int(item["size"]): str(item.get("comment", ""))
        for item in manifest.get("size_commentary", [])
        if isinstance(item, dict) and "size" in item
    }
    empty_sizes = sorted(
        size
        for size, comment in size_commentary.items()
        if classify_size_commentary(comment) == "empty"
    )
    open_commentary_sizes = sorted(
        size
        for size, comment in size_commentary.items()
        if classify_size_commentary(comment) == "open"
    )
    interval = range(args.min_size, args.max_size + 1)
    interval_empty = [size for size in interval if size in empty_sizes]
    interval_open_no_record = [
        size
        for size in interval
        if size not in present_sizes and size not in empty_sizes
    ]
    interval_open_commentary = [
        size
        for size in interval
        if size in open_commentary_sizes and size not in present_sizes
    ]
    check_sizes = sorted(set(interval_open_no_record + interval_open_commentary))
    frontier_hint_cache = {size: frontier_hints(size) for size in check_sizes}
    ranked_check_sizes = sorted(check_sizes, key=lambda size: (-frontier_hint_cache[size][0], size))

    e255_failures = [record for record in magmas if record.get("satisfies_255") is False]
    non_right_cancellative = [record for record in magmas if record.get("right_cancellative") is False]
    non_rc_by_size = Counter(int(record["size"]) for record in non_right_cancellative)
    interval_non_rc_sizes = sorted(size for size in non_rc_by_size if args.min_size <= size <= args.max_size)

    print(f"database records: {manifest.get('count', len(magmas))}")
    print(f"sizes with records: {format_int_list(sorted(present_sizes), args.list_limit)}")
    print(f"records marked not satisfying E255: {len(e255_failures)}")
    print(f"non-right-cancellative known positives: {len(non_right_cancellative)}")
    print()
    print("counterexample filter:")
    print("  a bad E255 witness has a right column missing x, hence a finite counterexample is non-right-cancellative")
    print("  right-cancellative database examples are calibration data, not plausible counterexample shapes")
    print()
    print(f"proved-empty sizes in {args.min_size}..{args.max_size}: {format_int_list(interval_empty, args.list_limit)}")
    print(f"open/no-record sizes in {args.min_size}..{args.max_size}: {format_int_list(check_sizes, args.list_limit)}")
    if ranked_check_sizes:
        print("pattern-ranked open/no-record sizes:")
        for size in ranked_check_sizes[: args.recommend]:
            print(f"  size {size}: {'; '.join(frontier_hint_cache[size][1])}")
    print(
        f"known non-right-cancellative sizes in {args.min_size}..{args.max_size}: "
        f"{format_int_list(interval_non_rc_sizes, args.list_limit)}"
    )
    if interval_non_rc_sizes:
        print("top non-right-cancellative known-positive sizes:")
        for size, count in non_rc_by_size.most_common(args.list_limit):
            if args.min_size <= size <= args.max_size:
                print(f"  size {size}: {count}")

    if e255_failures:
        print()
        print("urgent database records marked as E255 failures:")
        for record in sorted(e255_failures, key=lambda item: (int(item["size"]), str(item["canonical_hash"])))[: args.show_records]:
            print(f"  size {record['size']} hash {str(record['canonical_hash'])[:16]} url={record.get('url')}")

    if args.show_records and non_right_cancellative:
        print()
        print("non-right-cancellative examples to mine first:")
        selected = sorted(non_right_cancellative, key=lambda item: (int(item["size"]), str(item["canonical_hash"])))
        for record in selected[: args.show_records]:
            print(
                f"  size {record['size']} hash {str(record['canonical_hash'])[:16]} "
                f"idempotent={record.get('idempotent')} url={record.get('url')}"
            )

    print()
    print("recommended checks:")
    if e255_failures:
        record = sorted(e255_failures, key=lambda item: (int(item["size"]), str(item["canonical_hash"])))[0]
        print(
            "  verify the flagged record locally: "
            f"& .\\.venv\\Scripts\\python.exe scripts\\e677_db_analyze.py analyze --hash-prefix {str(record['canonical_hash'])[:12]}"
        )
    if check_sizes:
        for size in ranked_check_sizes[: args.recommend]:
            print(
                f"  size {size} existence: "
                f"& .\\.venv\\Scripts\\python.exe scripts\\e677_z3_search.py existence --order {size} "
                f"--timeout-ms {args.timeout_ms} --track-groups"
            )
            if is_prime(size):
                print(
                    f"  size {size} QR/NQR piecewise probe: "
                    f"& .\\.venv\\Scripts\\python.exe scripts\\e677_z3_search.py piecewise-prime --prime {size} "
                    "--all-pairs --validate-found"
                )
            print(
                f"  size {size} bad-witness sweep if existence is sat/unknown: "
                f"& .\\.venv\\Scripts\\python.exe scripts\\e677_z3_search.py sweep --order {size} "
                f"--timeout-ms {args.timeout_ms} --track-groups"
            )
    else:
        print("  no open/no-record size appears in the selected range")
    if interval_non_rc_sizes:
        size = interval_non_rc_sizes[0]
        print(
            "  mine nearest non-right-cancellative positives: "
            f"& .\\.venv\\Scripts\\python.exe scripts\\e677_db_analyze.py analyze --size {size} "
            "--limit 5 --cache-dir run_logs\\database_cache"
        )
    return 2 if e255_failures else 0


def selftest_command(_args: argparse.Namespace) -> int:
    args = argparse.Namespace(
        backend="enum",
        order=10,
        witness=0,
        period=None,
        branch="any",
        period4_external_cycle="any",
        period4_external_lx_cycle_size=None,
        period5_branch="any",
        period5_s_branch="any",
        lx_complement_cycles=None,
        fix_cell=None,
        fix_term=None,
        eq_term=[("rho3", "rho5")],
        neq_term=None,
        timeout_ms=0,
        no_left_permutations=False,
        no_label_injective=False,
        no_orbit_facts=False,
        no_derived_identities=False,
        no_bad_point_lemmas=False,
        no_collision_splitter=False,
        no_symmetry_break_bad_orbit=False,
        no_symmetry_break_period4_external=False,
        show_constraint_counts=False,
        track_groups=False,
        minimize_core=False,
        core_check_timeout_ms=0,
    )
    config = search_config_from_args(args, period=args.period, branch=args.branch)
    search = make_search(config)
    search.term_expr("rho5")
    assert ("rho3", "rho5") in config.term_equalities

    tail_search = make_search(config)
    tail_search.term_expr("rho5")

    assert is_prime(127)
    assert phi10_mod(4, 5) == 0
    assert frontier_hints(41)[0] > 0
    values = qr_piecewise_values(127, 58, 29)
    assert len(set(values)) == 127
    assert translation_e677_difference_failures(values) == []

    print("selftest ok")
    return 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return parsed


def positive_int_tuple(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(positive_int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a comma-separated list of positive integers") from exc
    if not parsed:
        raise argparse.ArgumentTypeError("must include at least one cycle size")
    return parsed


def fixed_cell(value: str) -> tuple[int, int, int]:
    parts = re.split(r"[,:]", value)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("must have the form row,col,value or row:col:value")
    try:
        row, col, cell_value = (int(part.strip()) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("row, col, and value must be integers") from exc
    if row < 0 or col < 0 or cell_value < 0:
        raise argparse.ArgumentTypeError("row, col, and value must be nonnegative")
    return row, col, cell_value


def fixed_term(value: str) -> tuple[str, int]:
    separator = ":" if ":" in value else "=" if "=" in value else None
    if separator is None:
        raise argparse.ArgumentTypeError("must have the form term:value or term=value")
    term, raw_value = value.rsplit(separator, 1)
    term = term.strip()
    if not term:
        raise argparse.ArgumentTypeError("term must not be empty")
    try:
        parsed_value = int(raw_value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("term value must be an integer") from exc
    if parsed_value < 0:
        raise argparse.ArgumentTypeError("term value must be nonnegative")
    return term, parsed_value


def term_equality(value: str) -> tuple[str, str]:
    if "!=" in value or "=" not in value:
        raise argparse.ArgumentTypeError("must have the form left=right")
    left, right = value.split("=", 1)
    left = left.strip()
    right = right.strip()
    if not left or not right:
        raise argparse.ArgumentTypeError("both sides of a term equality must be nonempty")
    return left, right


def term_inequality(value: str) -> tuple[str, str]:
    if "!=" not in value:
        raise argparse.ArgumentTypeError("must have the form left!=right")
    left, right = value.split("!=", 1)
    left = left.strip()
    right = right.strip()
    if not left or not right:
        raise argparse.ArgumentTypeError("both sides of a term inequality must be nonempty")
    return left, right


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
    search.add_argument(
        "--period5-branch",
        choices=["any", "internal", "external", "g=q", "g=a", "g=p"],
        default="any",
        help="period-five branch preset for g=q*x",
    )
    search.add_argument(
        "--period5-s-branch",
        choices=["any", "internal", "external", "s=a", "s=b", "s=p"],
        default="any",
        help="period-five g=p subbranch preset for s=p*x",
    )
    search.add_argument(
        "--period4-external-cycle",
        choices=["any", "two-cycle", "third"],
        default="any",
        help="split the period-four external L_x component by whether x*r=t=q*a",
    )
    search.add_argument(
        "--period4-external-lx-cycle-size",
        type=positive_int,
        help="fix the exact size of the external L_x cycle containing t=q*a in the period-four external branch",
    )
    search.add_argument(
        "--lx-complement-cycles",
        type=positive_int_tuple,
        help="fix the cycle sizes of L_x on labels outside the principal witness orbit, for example 3,2,1",
    )
    search.add_argument(
        "--fix-cell",
        action="append",
        type=fixed_cell,
        help="add a multiplication constraint row*col=value using row,col,value or row:col:value; can be repeated",
    )
    search.add_argument(
        "--fix-term",
        action="append",
        type=fixed_term,
        help="add a term constraint such as q*x:5, a*q=7, or (q*x)*q:3; can be repeated",
    )
    search.add_argument(
        "--eq-term",
        action="append",
        type=term_equality,
        help="add a term equality such as (a*q)*a=(q*q)*q; can be repeated",
    )
    search.add_argument(
        "--neq-term",
        action="append",
        type=term_inequality,
        help="add a term inequality such as a*q!=q*q; can be repeated",
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

    existence = subparsers.add_parser("existence", help="search for any finite E677 model, without a bad witness")
    existence.add_argument("--backend", choices=["enum", "array"], default="enum", help="Z3 encoding backend")
    existence.add_argument("--order", type=positive_int, required=True, help="finite carrier size")
    add_common_summary_args(existence)
    existence.add_argument("--period", type=positive_int, help="fix the diagnostic L_x orbit period for the witness label")
    existence.add_argument(
        "--lx-complement-cycles",
        type=positive_int_tuple,
        help="fix the cycle sizes of L_x on labels outside the chosen orbit, for example 3,2,1",
    )
    existence.add_argument(
        "--fix-cell",
        action="append",
        type=fixed_cell,
        help="add a multiplication constraint row*col=value using row,col,value or row:col:value; can be repeated",
    )
    existence.add_argument(
        "--fix-term",
        action="append",
        type=fixed_term,
        help="add a term constraint such as q*x:5, a*q=7, or (q*x)*q:3; can be repeated",
    )
    existence.add_argument(
        "--eq-term",
        action="append",
        type=term_equality,
        help="add a term equality such as (a*q)*a=(q*q)*q; can be repeated",
    )
    existence.add_argument(
        "--neq-term",
        action="append",
        type=term_inequality,
        help="add a term inequality such as a*q!=q*q; can be repeated",
    )
    existence.add_argument("--timeout-ms", type=int, default=30000, help="Z3 timeout in milliseconds; 0 means none")
    existence.add_argument("--no-left-permutations", action="store_true", help="do not add left-row permutation constraints")
    existence.add_argument("--no-label-injective", action="store_true", help="do not add row-label injectivity constraints")
    existence.add_argument("--no-orbit-facts", action="store_true", help="do not add trusted orbit recurrence facts")
    existence.add_argument("--no-derived-identities", action="store_true", help="do not add transformed/key identity constraints")
    existence.add_argument("--no-collision-splitter", action="store_true", help="do not add right-fiber splitter constraints")
    existence.add_argument("--show-constraint-counts", action="store_true", help="print added constraint groups")
    existence.add_argument("--track-groups", action="store_true", help="use group assumptions and print an UNSAT core")
    existence.add_argument("--minimize-core", action="store_true", help="greedily minimize the group UNSAT core")
    existence.add_argument(
        "--core-check-timeout-ms",
        type=int,
        default=5000,
        help="per-check timeout for greedy core minimization; 0 means no separate limit",
    )
    existence.set_defaults(func=existence_command)

    sweep = subparsers.add_parser("sweep", help="exhaustively check all witness periods for an order")
    sweep.add_argument("--backend", choices=["enum", "array"], default="enum", help="Z3 encoding backend")
    sweep.add_argument("--order", type=positive_int, required=True, help="finite carrier size")
    sweep.add_argument("--start-period", type=positive_int, default=4, help="first witness period to check")
    add_common_summary_args(sweep)
    sweep.add_argument("--timeout-ms", type=int, default=30000, help="Z3 timeout per case in milliseconds; 0 means none")
    sweep.add_argument(
        "--period4-external-cycle",
        choices=["any", "two-cycle", "third"],
        default="any",
        help="optional split for the period-four external L_x component",
    )
    sweep.add_argument(
        "--period5-branch",
        choices=["any", "internal", "external", "g=q", "g=a", "g=p"],
        default="any",
        help="period-five branch preset for g=q*x",
    )
    sweep.add_argument(
        "--period5-s-branch",
        choices=["any", "internal", "external", "s=a", "s=b", "s=p"],
        default="any",
        help="period-five g=p subbranch preset for s=p*x",
    )
    sweep.add_argument(
        "--period4-external-lx-cycle-size",
        type=positive_int,
        help="fix the exact size of the external L_x cycle containing t=q*a in the period-four external branch",
    )
    sweep.add_argument(
        "--lx-complement-cycles",
        type=positive_int_tuple,
        help="fix the cycle sizes of L_x on labels outside the principal witness orbit, for example 3,2,1",
    )
    sweep.add_argument(
        "--fix-cell",
        action="append",
        type=fixed_cell,
        help="add a multiplication constraint row*col=value using row,col,value or row:col:value; can be repeated",
    )
    sweep.add_argument(
        "--fix-term",
        action="append",
        type=fixed_term,
        help="add a term constraint such as q*x:5, a*q=7, or (q*x)*q:3; can be repeated",
    )
    sweep.add_argument(
        "--eq-term",
        action="append",
        type=term_equality,
        help="add a term equality such as (a*q)*a=(q*q)*q; can be repeated",
    )
    sweep.add_argument(
        "--neq-term",
        action="append",
        type=term_inequality,
        help="add a term inequality such as a*q!=q*q; can be repeated",
    )
    sweep.add_argument("--no-left-permutations", action="store_true", help="do not add left-row permutation constraints")
    sweep.add_argument("--no-label-injective", action="store_true", help="do not add row-label injectivity constraints")
    sweep.add_argument("--no-orbit-facts", action="store_true", help="do not add trusted orbit recurrence facts")
    sweep.add_argument("--no-derived-identities", action="store_true", help="do not add transformed/key identity constraints")
    sweep.add_argument("--no-bad-point-lemmas", action="store_true", help="do not add bad-witness consequences")
    sweep.add_argument("--no-collision-splitter", action="store_true", help="do not add right-fiber splitter constraints")
    sweep.add_argument(
        "--no-symmetry-break-bad-orbit",
        action="store_true",
        help="do not relabel the first bad L_x orbit points to 0,1,2,3 when possible",
    )
    sweep.add_argument(
        "--no-symmetry-break-period4-external",
        action="store_true",
        help="do not relabel period-four external branch points r=q*x and q*a",
    )
    sweep.add_argument("--show-constraint-counts", action="store_true", help="print added constraint groups")
    sweep.add_argument("--track-groups", action="store_true", help="use group assumptions and print an UNSAT core")
    sweep.add_argument("--minimize-core", action="store_true", help="greedily minimize the group UNSAT core")
    sweep.add_argument(
        "--core-check-timeout-ms",
        type=int,
        default=5000,
        help="per-check timeout for greedy core minimization; 0 means no separate limit",
    )
    sweep.set_defaults(func=sweep_command)

    split = subparsers.add_parser("split", help="branch a search over all values of one or more terms")
    split.add_argument("--backend", choices=["enum", "array"], default="enum", help="Z3 encoding backend")
    split.add_argument("--order", type=positive_int, required=True, help="finite carrier size")
    add_common_summary_args(split)
    split.add_argument("--period", type=positive_int, help="fix the witness L_x orbit period")
    split.add_argument(
        "--branch",
        choices=["any", "r=p", "external"],
        default="any",
        help="period-four gate branch to enforce",
    )
    split.add_argument(
        "--period5-branch",
        choices=["any", "internal", "external", "g=q", "g=a", "g=p"],
        default="any",
        help="period-five branch preset for g=q*x",
    )
    split.add_argument(
        "--period5-s-branch",
        choices=["any", "internal", "external", "s=a", "s=b", "s=p"],
        default="any",
        help="period-five g=p subbranch preset for s=p*x",
    )
    split.add_argument(
        "--period4-external-cycle",
        choices=["any", "two-cycle", "third"],
        default="any",
        help="split the period-four external L_x component by whether x*r=t=q*a",
    )
    split.add_argument(
        "--period4-external-lx-cycle-size",
        type=positive_int,
        help="fix the exact size of the external L_x cycle containing t=q*a in the period-four external branch",
    )
    split.add_argument(
        "--lx-complement-cycles",
        type=positive_int_tuple,
        help="fix the cycle sizes of L_x on labels outside the principal witness orbit, for example 3,2,1",
    )
    split.add_argument(
        "--fix-cell",
        action="append",
        type=fixed_cell,
        help="add a multiplication constraint row*col=value using row,col,value or row:col:value; can be repeated",
    )
    split.add_argument(
        "--fix-term",
        action="append",
        type=fixed_term,
        help="add a term constraint such as q*x:5, a*q=7, or (q*x)*q:3; can be repeated",
    )
    split.add_argument(
        "--eq-term",
        action="append",
        type=term_equality,
        help="add a term equality such as (a*q)*a=(q*q)*q; can be repeated",
    )
    split.add_argument(
        "--neq-term",
        action="append",
        type=term_inequality,
        help="add a term inequality such as a*q!=q*q; can be repeated",
    )
    split.add_argument(
        "--split-term",
        action="append",
        help="branch over all values of this term; can be repeated for nested splits",
    )
    split.add_argument(
        "--continue-after-sat",
        action="store_true",
        help="continue checking sibling branches after a satisfying table is found",
    )
    split.add_argument("--timeout-ms", type=int, default=30000, help="Z3 timeout per leaf in milliseconds; 0 means none")
    split.add_argument("--no-left-permutations", action="store_true", help="do not add left-row permutation constraints")
    split.add_argument("--no-label-injective", action="store_true", help="do not add row-label injectivity constraints")
    split.add_argument("--no-orbit-facts", action="store_true", help="do not add trusted orbit recurrence facts")
    split.add_argument("--no-derived-identities", action="store_true", help="do not add transformed/key identity constraints")
    split.add_argument("--no-bad-point-lemmas", action="store_true", help="do not add bad-witness consequences")
    split.add_argument("--no-collision-splitter", action="store_true", help="do not add right-fiber splitter constraints")
    split.add_argument(
        "--no-symmetry-break-bad-orbit",
        action="store_true",
        help="do not relabel the first bad L_x orbit points to 0,1,2,3 when possible",
    )
    split.add_argument(
        "--no-symmetry-break-period4-external",
        action="store_true",
        help="do not relabel period-four external branch points r=q*x and q*a",
    )
    split.add_argument("--show-constraint-counts", action="store_true", help="print added constraint groups")
    split.add_argument("--track-groups", action="store_true", help="use group assumptions and print an UNSAT core")
    split.add_argument("--minimize-core", action="store_true", help="greedily minimize the group UNSAT core")
    split.add_argument(
        "--core-check-timeout-ms",
        type=int,
        default=5000,
        help="per-check timeout for greedy core minimization; 0 means no separate limit",
    )
    split.set_defaults(func=split_command)

    calibrate = subparsers.add_parser("calibrate-linear", help="verify a linear model table")
    calibrate.add_argument("--prime", type=positive_int, default=5, help="field size, expected prime")
    calibrate.add_argument("--alpha", type=int, default=2, help="coefficient of x")
    calibrate.add_argument("--beta", type=int, default=-1, help="coefficient of y")
    calibrate.add_argument("--const", type=int, default=0, help="constant term")
    add_common_summary_args(calibrate)
    calibrate.set_defaults(func=calibrate_linear_command)

    piecewise = subparsers.add_parser("piecewise-prime", help="test QR/NQR translation-invariant prime templates")
    piecewise.add_argument("--prime", type=positive_int, required=True, help="prime carrier size")
    piecewise.add_argument("--qr-slope", type=int, help="multiplier used on nonzero quadratic residues")
    piecewise.add_argument("--nqr-slope", type=int, help="multiplier used on quadratic nonresidues")
    piecewise.add_argument("--all-pairs", action="store_true", help="enumerate all QR/NQR slope pairs")
    piecewise.add_argument("--limit", type=nonnegative_int, default=20, help="maximum candidate pairs to print")
    piecewise.add_argument("--validate-found", action="store_true", help="run full table checks on printed enumeration hits")
    piecewise.add_argument("--print-table", action="store_true", help="print the full table for an explicit slope pair")
    piecewise.add_argument("--witness-summary", action="store_true", help="print detailed witness diagnostics for an explicit slope pair")
    add_common_summary_args(piecewise)
    piecewise.set_defaults(func=piecewise_prime_command)

    frontier = subparsers.add_parser("db-frontier", help="use the public database manifest to choose next checks")
    frontier.add_argument("--manifest", default=MANIFEST_URL, help="manifest URL or local JSON path")
    frontier.add_argument("--min-size", type=positive_int, default=1, help="first size to report")
    frontier.add_argument("--max-size", type=positive_int, default=80, help="last size to report")
    frontier.add_argument("--recommend", type=nonnegative_int, default=6, help="number of open sizes to turn into commands")
    frontier.add_argument("--show-records", type=nonnegative_int, default=6, help="number of database records to print")
    frontier.add_argument("--list-limit", type=positive_int, default=40, help="maximum length of printed size lists")
    frontier.add_argument("--timeout-ms", type=int, default=120000, help="timeout to use in recommended sweep commands")
    frontier.set_defaults(func=db_frontier_command)

    selftest = subparsers.add_parser("selftest", help="run offline parser/config checks")
    selftest.set_defaults(func=selftest_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
