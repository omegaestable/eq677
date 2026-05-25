#!/usr/bin/env python3
"""
Search/prune finite colored-slope magmas for the identity

    x = y * (x * ((y * x) * y))

in the construction M = F_p x F_q with

    (y,i) * (x,j) = (A*y + B*x, O_[y:x](i,j))

for (y,x) != (0,0), and a separate bullet operation at (0,0).

The primary target encoded here is:
    p=19, q=7, A=7, B=4, bad slope 5,
    O_5 = C_3,
    O_4(u,v)=u+2v, O_12(u,v)=6u+2v.

The script has four intended uses:
    1. run pruned UNSAT sweeps for tempting subfamilies;
    2. run the remaining SAT instance with the same pruning and dump any model found;
    3. split the residual SAT instance into exhaustive branches for deep runs;
    4. export branch CNFs for external/native SAT solvers.

Dependencies:
    pip install python-sat[pblib,aiger]
The execution environment used for this file already has python-sat installed.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from pysat.formula import IDPool
from pysat.solvers import Cadical195, Glucose42, Kissat404, MapleChrono, Minisat22


INF_NAME = "inf"


@dataclass(frozen=True)
class Config:
    name: str
    p: int
    q: int
    A: int
    B: int
    bad: int
    seed_primary: bool = False


@dataclass(frozen=True)
class ProgressLogger:
    enabled: bool = True

    def log(self, message: str) -> None:
        if self.enabled:
            print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def progress_logger_from_args(args: argparse.Namespace) -> ProgressLogger:
    return ProgressLogger(enabled=not args.quiet)


def format_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remainder = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{remainder:02d}s"
    return f"{minutes}m{remainder:02d}s"


def stats_summary(stats: Dict[str, int]) -> str:
    if not stats:
        return "{}"
    preferred_keys = ("conflicts", "decisions", "propagations", "restarts")
    parts = [f"{key}={stats[key]}" for key in preferred_keys if key in stats]
    if not parts:
        parts = [f"{key}={value}" for key, value in sorted(stats.items())]
    return "{" + ", ".join(parts) + "}"


def selected_branch_count(total: int, branch_mod: int, branch_index: int) -> int:
    if branch_index >= total:
        return 0
    return ((total - 1 - branch_index) // branch_mod) + 1


def eta_text(done: int, total: int, elapsed: float) -> str:
    if done <= 0 or total <= done or elapsed <= 0:
        return "eta=unknown"
    remaining = total - done
    return f"eta={format_seconds(elapsed * remaining / done)}"


def inv_mod(a: int, p: int) -> int:
    a %= p
    if a == 0:
        raise ZeroDivisionError("inverse of zero")
    return pow(a, -1, p)


def labels_for(p: int) -> List[int]:
    return list(range(p)) + [p]  # p denotes infinity


def label_name(a: int, p: int) -> str:
    return INF_NAME if a == p else str(a)


def parse_label(text: str, p: int) -> int:
    if text == INF_NAME:
        return p
    value = int(text)
    if value < 0 or value > p:
        raise ValueError(f"label {text!r} is outside 0..{p} or {INF_NAME}")
    return value


def parse_cell(text: str, cfg: Config) -> Tuple[int, int, int]:
    parts = text.split(":")
    if len(parts) != 3:
        raise ValueError(f"expected CELL as slope:row:col, got {text!r}")
    a = parse_label(parts[0], cfg.p)
    i = int(parts[1])
    j = int(parts[2])
    if not (0 <= i < cfg.q and 0 <= j < cfg.q):
        raise ValueError(f"cell indices in {text!r} are outside 0..{cfg.q - 1}")
    return a, i, j


def parse_assume_cell(text: str, cfg: Config) -> Tuple[int, int, int, int]:
    parts = text.split(":")
    if len(parts) != 4:
        raise ValueError(f"expected ASSUMPTION as slope:row:col:value, got {text!r}")
    a, i, j = parse_cell(":".join(parts[:3]), cfg)
    value = int(parts[3])
    if not 0 <= value < cfg.q:
        raise ValueError(f"assumption value in {text!r} is outside 0..{cfg.q - 1}")
    return a, i, j, value


def parse_branch_cell(text: str, cfg: Config) -> Tuple[Tuple[int, int, int], List[int]]:
    if "=" in text:
        cell_text, values_text = text.split("=", 1)
        values = [int(v) for v in values_text.split(",") if v != ""]
    else:
        cell_text = text
        values = list(range(cfg.q))
    for value in values:
        if not 0 <= value < cfg.q:
            raise ValueError(f"branch value {value} in {text!r} is outside 0..{cfg.q - 1}")
    return parse_cell(cell_text, cfg), values


def parse_row(text: str, cfg: Config) -> Tuple[int, int]:
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"expected ROW as slope:row, got {text!r}")
    a = parse_label(parts[0], cfg.p)
    i = int(parts[1])
    if not 0 <= i < cfg.q:
        raise ValueError(f"row index in {text!r} is outside 0..{cfg.q - 1}")
    return a, i


def cell_desc(cfg: Config, a: int, i: int, j: int, value: int) -> str:
    return f"O_{label_name(a, cfg.p)}[{i},{j}]={value}"


def row_desc(cfg: Config, a: int, i: int, perm: Sequence[int]) -> str:
    return f"O_{label_name(a, cfg.p)}[{i},*]={''.join(map(str, perm))}"


def column_desc(cfg: Config, a: int, j: int, perm: Sequence[int]) -> str:
    return f"O_{label_name(a, cfg.p)}[*,{j}]={''.join(map(str, perm))}"


def slope_maps(p: int, A: int, B: int) -> Tuple[List[int], List[int], List[int]]:
    """Return mu, nu, omega for y*x = A*y+B*x over F_p.

    For finite lambda = y/x:
      mu    = (A*lambda+B)/lambda = A+B/lambda
      nu    = 1/((A^2+B)*lambda+A*B)
      omega = lambda/(B*(A^2+B)*lambda + A*(1+B^2))

    Infinity is represented by p.
    """
    INF = p
    labels = labels_for(p)
    C = (A * A + B) % p
    D = (A * B) % p
    E = (B * C) % p
    F = (A * (1 + B * B)) % p
    mu: List[int] = []
    nu: List[int] = []
    omega: List[int] = []
    for lam in labels:
        if lam == INF:
            # y=1, x=0
            mu.append(A % p)
            nu.append(0 if C != 0 else INF)
            omega.append(INF if E == 0 else inv_mod(E, p))
        else:
            if lam == 0:
                mu.append(INF)
            else:
                mu.append((A + B * inv_mod(lam, p)) % p)
            den = (C * lam + D) % p
            nu.append(INF if den == 0 else inv_mod(den, p))
            den2 = (E * lam + F) % p
            omega.append(INF if den2 == 0 else (lam * inv_mod(den2, p)) % p)
    return mu, nu, omega


def base_ok(cfg: Config) -> bool:
    p, A, B = cfg.p, cfg.A % cfg.p, cfg.B % cfg.p
    for x in range(p):
        for y in range(p):
            yx = (A * y + B * x) % p
            z = (A * yx + B * y) % p
            w = (A * x + B * z) % p
            out = (A * y + B * w) % p
            if out != x:
                return False
    return True


def c3_row(q: int, i: int) -> Tuple[int, ...]:
    return tuple((3 * j) % q if i == 0 else (j + i) % q for j in range(q))


def bullet(q: int, i: int, j: int) -> int:
    if q != 7:
        # The script only uses the provided good bullet for q=7.
        raise ValueError("bullet is only configured for q=7")
    return (4 * i + 3 * j) % q


class CNFBuilder:
    def __init__(
        self,
        cfg: Config,
        strong_primary_prunes: bool = True,
        progress: Optional[ProgressLogger] = None,
    ) -> None:
        self.cfg = cfg
        self.p = cfg.p
        self.q = cfg.q
        self.labels = labels_for(cfg.p)
        self.mu, self.nu, self.omega = slope_maps(cfg.p, cfg.A, cfg.B)
        self.vpool = IDPool()
        self.clauses: List[List[int]] = []
        self.fixed: Dict[Tuple[int, int, int], int] = {}
        self.strong_primary_prunes = strong_primary_prunes
        self.progress = progress or ProgressLogger(enabled=False)

    def X(self, a: int, i: int, j: int, v: int) -> int:
        return self.vpool.id(("X", a, i, j, v))

    def add(self, clause: Sequence[int]) -> None:
        self.clauses.append(list(clause))

    def exactly_one(self, lits: Sequence[int]) -> None:
        lits = list(lits)
        self.add(lits)
        for r in range(len(lits)):
            for s in range(r + 1, len(lits)):
                self.add([-lits[r], -lits[s]])

    def fix(self, a: int, i: int, j: int, value: int) -> None:
        value %= self.q
        key = (a, i, j)
        old = self.fixed.get(key)
        if old is not None and old != value:
            raise ValueError(f"conflicting fixed cell {key}: {old} vs {value}")
        self.fixed[key] = value

    def apply_seed(self) -> None:
        self.progress.log("CNF seed: fixing the bad slope operation")
        q = self.q
        # Critical bad slope is always C_3.
        for i in range(q):
            for j in range(q):
                self.fix(self.cfg.bad, i, j, c3_row(q, i)[j])

        # Primary fixed seed O_4 and O_12.
        if self.cfg.seed_primary:
            self.progress.log("CNF seed: fixing primary O_4 and O_12 operations")
            for i in range(q):
                for j in range(q):
                    self.fix(4, i, j, i + 2 * j)
                    self.fix(12, i, j, 6 * i + 2 * j)
        self.progress.log(f"CNF seed complete: fixed_cells={len(self.fixed)}")

    def add_cell_and_row_constraints(self) -> None:
        q = self.q
        for label_index, a in enumerate(self.labels, start=1):
            self.progress.log(
                f"CNF cell constraints: O_{label_name(a, self.p)} "
                f"({label_index}/{len(self.labels)})"
            )
            for i in range(q):
                for j in range(q):
                    if (a, i, j) in self.fixed:
                        vv = self.fixed[(a, i, j)]
                        self.add([self.X(a, i, j, vv)])
                        for v in range(q):
                            if v != vv:
                                self.add([-self.X(a, i, j, v)])
                    else:
                        self.exactly_one([self.X(a, i, j, v) for v in range(q)])

        # Row-permutation condition: for every operation row, each value appears once.
        for label_index, a in enumerate(self.labels, start=1):
            self.progress.log(
                f"CNF row permutations: O_{label_name(a, self.p)} "
                f"({label_index}/{len(self.labels)})"
            )
            for i in range(q):
                for v in range(q):
                    self.exactly_one([self.X(a, i, j, v) for j in range(q)])

    def add_identity_constraints(self) -> None:
        q = self.q
        clauses_per_slope = q ** 5
        for label_index, lam in enumerate(self.labels, start=1):
            m = self.mu[lam]
            n = self.nu[lam]
            w = self.omega[lam]
            before = len(self.clauses)
            self.progress.log(
                f"CNF identity: lambda={label_name(lam, self.p)} "
                f"({label_index}/{len(self.labels)}), "
                f"mu={label_name(m, self.p)}, nu={label_name(n, self.p)}, "
                f"omega={label_name(w, self.p)}, adding {clauses_per_slope} clauses"
            )
            for i in range(q):
                for j in range(q):
                    for t in range(q):
                        for u in range(q):
                            for v in range(q):
                                self.add([
                                    -self.X(lam, i, j, t),
                                    -self.X(m, t, i, u),
                                    -self.X(n, j, u, v),
                                    self.X(w, i, v, j),
                                ])
            self.progress.log(
                f"CNF identity: lambda={label_name(lam, self.p)} complete, "
                f"clauses_added={len(self.clauses) - before}, total_clauses={len(self.clauses)}"
            )

    def add_primary_prunes(self) -> None:
        """Extra implications valid for the primary seed.

        These are not assumptions. They are consequences of the fixed O_4 and O_12.

        lambda=1 gives
            O_11(O_1(i,j), i) = 2(i-j).
        Hence each column of O_11 is a permutation, and O_1 is determined by
        those columns.

        lambda=12 gives
            O_18(j, O_1(6i+2j, i)) = 4(j-i).
        """
        if not self.cfg.seed_primary or self.cfg.p != 19 or self.cfg.q != 7:
            self.progress.log("CNF primary prunes: skipped for this config")
            return
        before = len(self.clauses)
        self.progress.log("CNF primary prunes: adding lambda=1 and lambda=12 consequences")
        q = self.q
        # lambda=1 equivalence.
        for i in range(q):
            for j in range(q):
                val = (2 * (i - j)) % q
                for r in range(q):
                    self.add([-self.X(1, i, j, r), self.X(11, r, i, val)])
                    self.add([-self.X(11, r, i, val), self.X(1, i, j, r)])

        # Columns of O_11 are permutations.
        for i in range(q):
            for v in range(q):
                self.exactly_one([self.X(11, r, i, v) for r in range(q)])

        # lambda=12 implications. The converse is also safe because for fixed
        # row j and rhs, i is unique.
        for i in range(q):
            for j in range(q):
                row = (6 * i + 2 * j) % q
                rhs = (4 * (j - i)) % q
                for u in range(q):
                    self.add([-self.X(1, row, i, u), self.X(18, j, u, rhs)])
                    self.add([-self.X(18, j, u, rhs), self.X(1, row, i, u)])
        self.progress.log(
            f"CNF primary prunes complete: clauses_added={len(self.clauses) - before}, "
            f"total_clauses={len(self.clauses)}"
        )

    def build(self) -> Tuple[List[List[int]], IDPool]:
        build_start = time.time()
        self.progress.log(
            f"CNF build started: config={self.cfg.name}, p={self.p}, q={self.q}, "
            f"strong_primary_prunes={self.strong_primary_prunes}"
        )
        self.apply_seed()
        before = len(self.clauses)
        self.add_cell_and_row_constraints()
        self.progress.log(
            f"CNF cell/row constraints complete: clauses_added={len(self.clauses) - before}, "
            f"total_clauses={len(self.clauses)}, vars={self.vpool.top}"
        )
        before = len(self.clauses)
        self.add_identity_constraints()
        self.progress.log(
            f"CNF identity constraints complete: clauses_added={len(self.clauses) - before}, "
            f"total_clauses={len(self.clauses)}, vars={self.vpool.top}"
        )
        if self.strong_primary_prunes:
            self.add_primary_prunes()
        else:
            self.progress.log("CNF primary prunes: disabled by --no-strong-prunes")
        self.progress.log(
            f"CNF build finished in {format_seconds(time.time() - build_start)}: "
            f"vars={self.vpool.top}, clauses={len(self.clauses)}"
        )
        return self.clauses, self.vpool


def solver_class(name: str):
    table = {
        "cadical": Cadical195,
        "glucose": Glucose42,
        "kissat": Kissat404,
        "maple": MapleChrono,
        "minisat": Minisat22,
    }
    try:
        return table[name]
    except KeyError as exc:
        raise SystemExit(f"unknown solver {name!r}; choose one of {sorted(table)}") from exc


def solver_stats(solver) -> Dict[str, int]:
    if not hasattr(solver, "accum_stats"):
        return {}
    try:
        return dict(solver.accum_stats())
    except Exception:
        return {}


def solver_supports_limited(solver) -> bool:
    return hasattr(solver, "conf_budget") and hasattr(solver, "solve_limited")


def solve_with_progress(
    solver,
    assumptions: Sequence[int],
    args: argparse.Namespace,
    progress: ProgressLogger,
    label: str,
):
    assumption_list = list(assumptions)
    hard_conflict_budget = args.conflicts

    if hard_conflict_budget:
        if solver_supports_limited(solver):
            progress.log(
                f"{label}: solve_limited starts with hard conflict_budget={hard_conflict_budget}, "
                f"assumptions={len(assumption_list)}"
            )
            solver.conf_budget(hard_conflict_budget)
            result = solver.solve_limited(assumptions=assumption_list, expect_interrupt=True)
            progress.log(f"{label}: solve_limited returned {result}, stats={stats_summary(solver_stats(solver))}")
            return result

        progress.log(
            f"{label}: solver does not expose solve_limited; ignoring --conflicts and running blocking solve"
        )
        return solver.solve(assumptions=assumption_list)

    if args.progress_conflicts and solver_supports_limited(solver):
        chunk_conflicts = args.progress_conflicts
        progress.log(
            f"{label}: solving in chunks of {chunk_conflicts} conflicts, "
            f"assumptions={len(assumption_list)}"
        )
        start = time.time()
        last_report = start
        chunks = 0
        while True:
            solver.conf_budget(chunk_conflicts)
            result = solver.solve_limited(assumptions=assumption_list, expect_interrupt=True)
            chunks += 1
            now = time.time()
            if result is not None:
                progress.log(
                    f"{label}: solver returned {result} after {chunks} chunk(s), "
                    f"elapsed={format_seconds(now - start)}, stats={stats_summary(solver_stats(solver))}"
                )
                return result

            if args.progress_every <= 0 or chunks == 1 or now - last_report >= args.progress_every:
                progress.log(
                    f"{label}: still searching after {chunks} chunk(s), "
                    f"elapsed={format_seconds(now - start)}, stats={stats_summary(solver_stats(solver))}"
                )
                last_report = now

    progress.log(
        f"{label}: blocking solve starts, assumptions={len(assumption_list)}; "
        "no in-solve progress will be available"
    )
    result = solver.solve(assumptions=assumption_list)
    progress.log(f"{label}: blocking solve returned {result}, stats={stats_summary(solver_stats(solver))}")
    return result


def base_assumptions(cfg: Config, builder: CNFBuilder, args: argparse.Namespace) -> List[int]:
    assumptions: List[int] = []

    if args.symbreak_o11_00 is not None:
        if not cfg.seed_primary or cfg.q != 7:
            raise SystemExit("O11 symmetry break only applies to the primary q=7 seed")
        assumptions.append(builder.X(11, 0, 0, args.symbreak_o11_00))

    for spec in args.assume_cell or []:
        try:
            a, i, j, value = parse_assume_cell(spec, cfg)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        assumptions.append(builder.X(a, i, j, value))

    return assumptions


def assumption_descriptions(cfg: Config, args: argparse.Namespace) -> List[str]:
    desc: List[str] = []
    if args.symbreak_o11_00 is not None:
        desc.append(cell_desc(cfg, 11, 0, 0, args.symbreak_o11_00))
    for spec in args.assume_cell or []:
        a, i, j, value = parse_assume_cell(spec, cfg)
        desc.append(cell_desc(cfg, a, i, j, value))
    return desc


def matrix_from_model(cfg: Config, builder: CNFBuilder, model: Iterable[int]) -> Dict[int, List[List[int]]]:
    q = cfg.q
    positive = {lit for lit in model if lit > 0}
    O: Dict[int, List[List[int]]] = {}
    for a in labels_for(cfg.p):
        mat: List[List[int]] = []
        for i in range(q):
            row: List[int] = []
            for j in range(q):
                vals = [v for v in range(q) if builder.X(a, i, j, v) in positive]
                if len(vals) != 1:
                    raise RuntimeError(f"bad decoded cell O_{label_name(a,cfg.p)}[{i},{j}] -> {vals}")
                row.append(vals[0])
            mat.append(row)
        O[a] = mat
    return O


def slope_of_pair(p: int, y: int, x: int) -> int:
    if x % p == 0:
        if y % p == 0:
            raise ValueError("zero pair has no projective slope")
        return p
    return (y * inv_mod(x, p)) % p


def op_M(cfg: Config, O: Dict[int, List[List[int]]], left: Tuple[int, int], right: Tuple[int, int]) -> Tuple[int, int]:
    y, i = left
    x, j = right
    z = (cfg.A * y + cfg.B * x) % cfg.p
    if y % cfg.p == 0 and x % cfg.p == 0:
        color = bullet(cfg.q, i, j)
    else:
        lam = slope_of_pair(cfg.p, y, x)
        color = O[lam][i][j]
    return z, color


def verify_solution(cfg: Config, O: Dict[int, List[List[int]]], verbose: bool = True) -> Tuple[bool, Optional[Tuple[int, int]]]:
    q = cfg.q
    # Row-permutation check.
    for a, mat in O.items():
        for i, row in enumerate(mat):
            if sorted(row) != list(range(q)):
                if verbose:
                    print(f"row is not a permutation: O_{label_name(a,cfg.p)} row {i}: {row}")
                return False, None

    # Slope identity check.
    mu, nu, omega = slope_maps(cfg.p, cfg.A, cfg.B)
    for lam in labels_for(cfg.p):
        for i in range(q):
            for j in range(q):
                t = O[lam][i][j]
                u = O[mu[lam]][t][i]
                v = O[nu[lam]][j][u]
                out = O[omega[lam]][i][v]
                if out != j:
                    if verbose:
                        print("slope identity fails", lam, i, j, "got", out)
                    return False, None

    # Full magma identity, including the bullet fiber.
    elems = [(x, c) for x in range(cfg.p) for c in range(q)]
    for X in elems:
        for Y in elems:
            a = op_M(cfg, O, Y, X)
            b = op_M(cfg, O, a, Y)
            c = op_M(cfg, O, X, b)
            d = op_M(cfg, O, Y, c)
            if d != X:
                if verbose:
                    print("full identity fails", X, Y, "got", d)
                return False, None

    bad_witness: Optional[Tuple[int, int]] = None
    for X in elems:
        t1 = op_M(cfg, O, X, X)
        t2 = op_M(cfg, O, t1, X)
        t3 = op_M(cfg, O, t2, X)
        if t3 != X:
            bad_witness = X
            break

    if verbose:
        print("verified slope identity and full magma identity")
        if bad_witness is None:
            print("no fourth-power failure found")
        else:
            print("fourth-power failure witness:", bad_witness)
    return bad_witness is not None, bad_witness


def dump_solution(cfg: Config, O: Dict[int, List[List[int]]], path: str) -> None:
    data = {
        "config": cfg.__dict__,
        "operations": {label_name(a, cfg.p): mat for a, mat in O.items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def print_operations(cfg: Config, O: Dict[int, List[List[int]]]) -> None:
    for a in labels_for(cfg.p):
        print(f"O_{label_name(a, cfg.p)} =")
        for row in O[a]:
            print(" ".join(map(str, row)))


def affine_o11_projection_assumptions(builder: CNFBuilder, a: int, b: int, c: int) -> List[int]:
    """Assumptions for a pruned primary subfamily.

    O_11(row,col) = a*row + b*col + c, with a,b != 0.
    lambda=1 then forces O_1.  Also set O_6(u,v)=v and force O_14
    from lambda=6.  This is exactly the tempting projection-side repair family.
    """
    q = builder.q
    ia = inv_mod(a, q)
    ib = inv_mod(b, q)
    ass: List[int] = []
    for i in range(q):
        for j in range(q):
            ass.append(builder.X(11, i, j, (a * i + b * j + c) % q))
            forced_o1 = (ia * ((2 - b) * i - 2 * j - c)) % q
            ass.append(builder.X(1, i, j, forced_o1))
            ass.append(builder.X(6, i, j, j))
            # O_14(row=k, col=ii) forced by lambda=6.
            k, ii = i, j
            if k == 0:
                val = (5 * ib * (-a * ii - c)) % q
            else:
                val = (ib * (k - a * ii - c) - k) % q
            ass.append(builder.X(14, i, j, val))
    return ass


def run_affine_o11_projection_sweep(cfg: Config, args: argparse.Namespace) -> int:
    if not cfg.seed_primary or cfg.q != 7:
        raise SystemExit("the affine O11 projection sweep is only implemented for the primary q=7 seed")
    progress = progress_logger_from_args(args)
    builder = CNFBuilder(cfg, strong_primary_prunes=True, progress=progress)
    clauses, _ = builder.build()
    S = solver_class(args.solver)
    print(f"CNF: vars={builder.vpool.top} clauses={len(clauses)}")
    print("Sweeping 252 cases: O_11 affine, O_6(u,v)=v, O_14 forced by lambda=6")
    start = time.time()
    with S(bootstrap_with=clauses) as solver:
        count = 0
        for a in range(1, cfg.q):
            for b in range(1, cfg.q):
                for c in range(cfg.q):
                    count += 1
                    ass = affine_o11_projection_assumptions(builder, a, b, c)
                    progress.log(f"sweep case {count}/252 starts: a={a} b={b} c={c}")
                    sat = solve_with_progress(solver, ass, args, progress, f"sweep case {count}/252")
                    dt = time.time() - start
                    print(
                        f"case {count:3d}: a={a} b={b} c={c} -> {sat}   "
                        f"elapsed={dt:.2f}s {eta_text(count, 252, dt)}"
                    )
                    if sat:
                        O = matrix_from_model(cfg, builder, solver.get_model())
                        ok, witness = verify_solution(cfg, O, verbose=True)
                        print_operations(cfg, O)
                        if args.out:
                            dump_solution(cfg, O, args.out)
                        return 0 if ok and witness else 2
    print("No model in this pruned subfamily.")
    return 1


BranchChoice = Tuple[str, List[int], Dict[str, object]]


def branch_choice_groups(cfg: Config, builder: CNFBuilder, args: argparse.Namespace) -> List[List[BranchChoice]]:
    groups: List[List[BranchChoice]] = []

    branch_cells = list(args.branch_cell or [])
    if not branch_cells and not args.branch_row and not args.branch_o11_column and args.symbreak_o11_00 is None:
        if cfg.seed_primary and cfg.q == 7:
            if args.primary_o11_symmetry:
                branch_cells.append("11:0:0=0,1")
            else:
                branch_cells.append("11:0:0")

    for spec in branch_cells:
        try:
            (a, i, j), values = parse_branch_cell(spec, cfg)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        group: List[BranchChoice] = []
        for value in values:
            group.append((
                cell_desc(cfg, a, i, j, value),
                [builder.X(a, i, j, value)],
                {"kind": "cell", "slope": label_name(a, cfg.p), "row": i, "col": j, "value": value},
            ))
        groups.append(group)

    for spec in args.branch_row or []:
        try:
            a, i = parse_row(spec, cfg)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        group = []
        for perm in itertools.permutations(range(cfg.q)):
            group.append((
                row_desc(cfg, a, i, perm),
                [builder.X(a, i, j, perm[j]) for j in range(cfg.q)],
                {"kind": "row", "slope": label_name(a, cfg.p), "row": i, "values": list(perm)},
            ))
        groups.append(group)

    for spec in args.branch_o11_column or []:
        if not cfg.seed_primary or cfg.q != 7:
            raise SystemExit("--branch-o11-column is only justified for the primary q=7 seed")
        j = int(spec)
        if not 0 <= j < cfg.q:
            raise SystemExit(f"O11 column index {j} is outside 0..{cfg.q - 1}")
        group = []
        for perm in itertools.permutations(range(cfg.q)):
            if args.primary_o11_symmetry and j == 0 and perm[0] not in (0, 1):
                continue
            group.append((
                column_desc(cfg, 11, j, perm),
                [builder.X(11, i, j, perm[i]) for i in range(cfg.q)],
                {"kind": "o11-column", "slope": "11", "col": j, "values": list(perm)},
            ))
        groups.append(group)

    return groups


def combined_branch_choices(groups: Sequence[Sequence[BranchChoice]]) -> Iterable[Tuple[str, List[int], List[Dict[str, object]]]]:
    if not groups:
        yield "unbranched", [], []
        return
    for choices in itertools.product(*groups):
        descriptions: List[str] = []
        assumptions: List[int] = []
        details: List[Dict[str, object]] = []
        for description, lits, detail in choices:
            descriptions.append(description)
            assumptions.extend(lits)
            details.append(detail)
        yield "; ".join(descriptions), assumptions, details


def branch_count(groups: Sequence[Sequence[BranchChoice]]) -> int:
    total = 1
    for group in groups:
        total *= len(group)
    return total


def load_completed_branches(path: Path) -> set[str]:
    if not path.exists():
        return set()
    completed: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("status") in {"sat", "unsat", "bad-model", "verified-sat"} and isinstance(rec.get("branch"), str):
                completed.add(rec["branch"])
    return completed


def default_deep_log_path(cfg: Config, args: argparse.Namespace) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    name = f"{cfg.name}_{args.solver}_{stamp}.jsonl"
    return Path("run_logs") / "colored_magma" / name


def solution_path_for_branch(path: Optional[str], branch_no: int, total: int) -> Optional[str]:
    if not path:
        return None
    if total <= 1:
        return path
    p = Path(path)
    return str(p.with_name(f"{p.stem}.branch{branch_no}{p.suffix}"))


def append_jsonl(path: Path, record: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def run_deep_sat(cfg: Config, args: argparse.Namespace) -> int:
    if args.branch_mod < 1:
        raise SystemExit("--branch-mod must be positive")
    if args.branch_index < 0 or args.branch_index >= args.branch_mod:
        raise SystemExit("--branch-index must satisfy 0 <= index < mod")

    progress = progress_logger_from_args(args)
    builder = CNFBuilder(cfg, strong_primary_prunes=not args.no_strong_prunes, progress=progress)
    clauses, _ = builder.build()
    base = base_assumptions(cfg, builder, args)
    groups = branch_choice_groups(cfg, builder, args)
    total = branch_count(groups)
    selected_total = selected_branch_count(total, args.branch_mod, args.branch_index)
    log_path = Path(args.log) if args.log else default_deep_log_path(cfg, args)
    completed = load_completed_branches(log_path) if args.resume else set()

    print(f"Config: {cfg}")
    print(f"base identity: {base_ok(cfg)}")
    print(f"CNF: vars={builder.vpool.top} clauses={len(clauses)} base_assumptions={len(base)}")
    print(f"Branch groups: {[len(group) for group in groups] or [1]} total={total}")
    print(f"Shard: index={args.branch_index} mod={args.branch_mod}")
    print(f"Selected local branches: {selected_total}")
    if args.max_branches:
        print(f"Max local solves this run: {args.max_branches}")
    print(f"Log: {log_path}")
    if args.resume:
        print(f"Resume: loaded {len(completed)} completed branch record(s)")
    if args.primary_o11_symmetry and cfg.seed_primary:
        print("Using primary color-scalar symmetry: O_11(0,0)=0 or normalized to 1.")
    for desc in assumption_descriptions(cfg, args):
        print(f"Base assumption: {desc}")

    if args.dry_run:
        shown = 0
        for branch_no, (description, _, _) in enumerate(combined_branch_choices(groups), start=1):
            if (branch_no - 1) % args.branch_mod != args.branch_index:
                continue
            print(f"branch {branch_no}/{total} local={shown + 1}/{selected_total}: {description}")
            shown += 1
            if args.max_branches and shown >= args.max_branches:
                break
        return 0

    unknown = 0
    solved = 0
    skipped = 0
    S = solver_class(args.solver)
    run_start = time.time()
    local_seen = 0
    progress.log(f"creating solver {args.solver} with {len(clauses)} clauses")
    with S(bootstrap_with=clauses) as solver:
        for branch_no, (description, branch_assumptions, details) in enumerate(combined_branch_choices(groups), start=1):
            if (branch_no - 1) % args.branch_mod != args.branch_index:
                continue
            local_seen += 1
            if description in completed:
                skipped += 1
                if skipped <= 5 or skipped % 100 == 0:
                    elapsed = time.time() - run_start
                    progress.log(
                        f"branch {branch_no}/{total} local={local_seen}/{selected_total}: skipped from resume; "
                        f"processed={solved + unknown + skipped}/{selected_total}, "
                        f"elapsed={format_seconds(elapsed)} {eta_text(solved + unknown + skipped, selected_total, elapsed)}"
                    )
                continue
            if args.max_branches and solved + unknown >= args.max_branches:
                break

            assumptions = base + branch_assumptions
            progress.log(
                f"branch {branch_no}/{total} local={local_seen}/{selected_total} starts: "
                f"{description}; assumptions={len(assumptions)}"
            )
            start = time.time()
            sat = solve_with_progress(solver, assumptions, args, progress, f"branch {branch_no}/{total}")
            elapsed = time.time() - start
            status = "unknown" if sat is None else "sat" if sat else "unsat"
            stats = solver_stats(solver)
            print(
                f"branch {branch_no}/{total}: {description} -> {status} "
                f"elapsed={elapsed:.2f}s stats={stats}"
            )
            append_jsonl(log_path, {
                "branch": description,
                "branch_no": branch_no,
                "total_branches": total,
                "details": details,
                "status": status,
                "elapsed_seconds": elapsed,
                "solver": args.solver,
                "conflict_budget": args.conflicts,
                "stats": stats,
            })

            if sat is None:
                unknown += 1
            else:
                solved += 1
            processed = solved + unknown + skipped
            run_elapsed = time.time() - run_start
            progress.log(
                f"deep progress: processed={processed}/{selected_total}, solved={solved}, "
                f"unknown={unknown}, skipped={skipped}, elapsed={format_seconds(run_elapsed)} "
                f"{eta_text(processed, selected_total, run_elapsed)}"
            )
            if sat is None:
                continue
            if sat is False:
                continue

            O = matrix_from_model(cfg, builder, solver.get_model())
            ok, witness = verify_solution(cfg, O, verbose=True)
            print_operations(cfg, O)
            out_path = solution_path_for_branch(args.out, branch_no, total)
            if out_path:
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                dump_solution(cfg, O, out_path)
                print(f"wrote {out_path}")
            append_jsonl(log_path, {
                "branch": description,
                "branch_no": branch_no,
                "status": "verified-sat" if ok and witness else "bad-model",
                "witness": list(witness) if witness is not None else None,
            })
            return 0 if ok and witness else 2

    print(
        f"Deep run finished in {time.time() - run_start:.2f}s: "
        f"solved={solved} unknown={unknown} skipped={skipped}"
    )
    if unknown:
        return 3
    return 1


def write_dimacs(path: Path, clauses: Sequence[Sequence[int]], vars_top: int,
                 assumptions: Sequence[int], comments: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_clauses = len(clauses) + len(assumptions)
    with path.open("w", encoding="utf-8") as f:
        for comment in comments:
            f.write(f"c {comment}\n")
        f.write(f"p cnf {vars_top} {total_clauses}\n")
        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")
        for lit in assumptions:
            f.write(f"{lit} 0\n")


def run_dimacs_export(cfg: Config, args: argparse.Namespace) -> int:
    progress = progress_logger_from_args(args)
    builder = CNFBuilder(cfg, strong_primary_prunes=not args.no_strong_prunes, progress=progress)
    clauses, _ = builder.build()
    assumptions = base_assumptions(cfg, builder, args)
    out = Path(args.cnf_out or "colored_magma.cnf")
    comments = [
        f"config={cfg}",
        f"base_identity={base_ok(cfg)}",
        f"vars={builder.vpool.top}",
        f"clauses_without_assumptions={len(clauses)}",
    ]
    for desc in assumption_descriptions(cfg, args):
        comments.append(f"assumption {desc}")
    progress.log(f"DIMACS export: writing {out}")
    write_dimacs(out, clauses, builder.vpool.top, assumptions, comments)
    print(f"wrote {out} with vars={builder.vpool.top} clauses={len(clauses) + len(assumptions)}")
    return 0


def run_full_sat(cfg: Config, args: argparse.Namespace) -> int:
    progress = progress_logger_from_args(args)
    builder = CNFBuilder(cfg, strong_primary_prunes=not args.no_strong_prunes, progress=progress)
    clauses, _ = builder.build()
    assumptions = base_assumptions(cfg, builder, args)

    S = solver_class(args.solver)
    print(f"Config: {cfg}")
    print(f"base identity: {base_ok(cfg)}")
    print(f"CNF: vars={builder.vpool.top} clauses={len(clauses)} assumptions={len(assumptions)}")
    for desc in assumption_descriptions(cfg, args):
        print(f"Assumption: {desc}")
    start = time.time()
    progress.log(f"creating solver {args.solver} with {len(clauses)} clauses")
    with S(bootstrap_with=clauses) as solver:
        sat = solve_with_progress(solver, assumptions, args, progress, "full solve")
        elapsed = time.time() - start
        print(f"SAT result: {sat}   elapsed={elapsed:.2f}s stats={solver_stats(solver)}")
        if sat is None:
            print("Search stopped by the configured conflict budget.")
            return 3
        if sat is False:
            print("UNSAT under the selected assumptions/prunes.")
            return 1
        O = matrix_from_model(cfg, builder, solver.get_model())
        ok, witness = verify_solution(cfg, O, verbose=True)
        print_operations(cfg, O)
        if args.out:
            dump_solution(cfg, O, args.out)
            print(f"wrote {args.out}")
        return 0 if ok and witness else 2


def config_from_name(name: str) -> Config:
    if name == "primary":
        return Config(name="primary", p=19, q=7, A=7, B=4, bad=5, seed_primary=True)
    if name == "backup1":
        return Config(name="backup1", p=19, q=7, A=7, B=3, bad=16, seed_primary=False)
    if name == "backup2q7":
        return Config(name="backup2q7", p=31, q=7, A=5, B=9, bad=17, seed_primary=False)
    raise SystemExit("unknown config; choose primary, backup1, or backup2q7")


def show_maps(cfg: Config) -> None:
    mu, nu, omega = slope_maps(cfg.p, cfg.A, cfg.B)
    print("lambda  mu  nu  omega")
    for lam in labels_for(cfg.p):
        print(
            f"{label_name(lam,cfg.p):>6} "
            f"{label_name(mu[lam],cfg.p):>3} "
            f"{label_name(nu[lam],cfg.p):>3} "
            f"{label_name(omega[lam],cfg.p):>5}"
        )
    print("equations directly involving the bad slope:")
    for lam in labels_for(cfg.p):
        if cfg.bad in (lam, mu[lam], nu[lam], omega[lam]):
            print(
                f"lambda={label_name(lam,cfg.p)}: "
                f"mu={label_name(mu[lam],cfg.p)}, "
                f"nu={label_name(nu[lam],cfg.p)}, "
                f"omega={label_name(omega[lam],cfg.p)}"
            )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="primary", choices=["primary", "backup1", "backup2q7"])
    parser.add_argument("--mode", default="full", choices=["full", "deep", "dimacs", "affine-o11-projection-sweep", "maps"])
    parser.add_argument("--solver", default="cadical", choices=["cadical", "glucose", "kissat", "maple", "minisat"])
    parser.add_argument("--out", default="solution.json", help="where to write a found solution JSON; use empty string to disable")
    parser.add_argument("--conflicts", type=int, default=0, help="optional conflict budget for solvers supporting solve_limited")
    parser.add_argument("--quiet", action="store_true", help="suppress timestamped progress logging")
    parser.add_argument("--progress-every", type=float, default=5.0,
                        help="seconds between long-running solve progress reports; use 0 to print every chunk")
    parser.add_argument("--progress-conflicts", type=int, default=50000,
                        help="conflict chunk size for solve progress when --conflicts is not set; use 0 for blocking solve")
    parser.add_argument("--no-strong-prunes", action="store_true", help="disable derived primary lambda=1/lambda=12 pruning")
    parser.add_argument("--symbreak-o11-00", type=int, choices=[0, 1], default=None,
                        help="primary only: branch on O_11(0,0)=0 or normalized nonzero value 1")
    parser.add_argument("--assume-cell", action="append", default=[], metavar="L:I:J:V",
                        help="add a unit assumption O_L(i,j)=v; use L=inf for the infinite slope")
    parser.add_argument("--branch-cell", action="append", default=[], metavar="L:I:J[=V,...]",
                        help="deep mode: split over values of a cell, or over the listed values only")
    parser.add_argument("--branch-row", action="append", default=[], metavar="L:I",
                        help="deep mode: split over all row permutations for O_L row i")
    parser.add_argument("--branch-o11-column", action="append", default=[], metavar="J",
                        help="deep mode, primary only: split over all permutations of column j of O_11")
    parser.add_argument("--primary-o11-symmetry", action="store_true",
                        help="primary deep mode: quotient the color-scalar symmetry with O_11(0,0) in {0,1}")
    parser.add_argument("--branch-mod", type=int, default=1, help="deep mode: run only branches with index congruent to --branch-index modulo this value")
    parser.add_argument("--branch-index", type=int, default=0, help="deep mode: shard index used with --branch-mod")
    parser.add_argument("--max-branches", type=int, default=0, help="deep mode: stop after this many local branches in the selected shard")
    parser.add_argument("--log", default="", help="deep mode: JSONL progress log path")
    parser.add_argument("--resume", action="store_true", help="deep mode: skip branches already marked sat/unsat in the JSONL log")
    parser.add_argument("--dry-run", action="store_true", help="deep mode: print selected branches without solving")
    parser.add_argument("--cnf-out", default="", help="dimacs mode: path for the exported CNF")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    if args.conflicts < 0:
        raise SystemExit("--conflicts must be nonnegative")
    if args.progress_conflicts < 0:
        raise SystemExit("--progress-conflicts must be nonnegative")
    if args.progress_every < 0:
        raise SystemExit("--progress-every must be nonnegative")
    if args.out == "":
        args.out = None
    cfg = config_from_name(args.config)
    if args.mode == "maps":
        show_maps(cfg)
        return 0
    if args.mode == "affine-o11-projection-sweep":
        return run_affine_o11_projection_sweep(cfg, args)
    if args.mode == "deep":
        return run_deep_sat(cfg, args)
    if args.mode == "dimacs":
        return run_dimacs_export(cfg, args)
    return run_full_sat(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
