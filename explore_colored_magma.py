#!/usr/bin/env python3
"""
Tuned SAT search for finite colored-slope magmas for Equation 677.

Identity:
    x = y * (x * ((y * x) * y))

Colored-slope construction:
    M = F_p x F_q
    (y,i) * (x,j) = (A*y + B*x, O_[y:x](i,j))  for (y,x) != (0,0)

Primary target:
    p=19, q=7, A=7, B=4, bad slope 5,
    O_5 = C_3,
    O_4(u,v)=u+2v, O_12(u,v)=6u+2v.

This tuned version keeps the same mathematical target as the original script, but changes
how the SAT instance is built and searched:

  * fixed seed cells are treated as constants, not SAT variables;
  * every generated clause is simplified immediately against fixed cells;
  * primary derived identities for lambda in {1,5,6,12} can replace their full q^5
    encodings, removing redundant clauses while preserving the same constraints under
    the row-permutation axioms;
  * branch pre-propagation can kill many deep branches before a full solve;
  * deep mode defaults to an O_11-column split for the primary instance, matching the
    theory note that O_11 is the useful branch variable.

Dependencies for solving/exporting through PySAT solvers:
    pip install python-sat[pblib,aiger]

The --mode maps and --mode stats paths do not require PySAT.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

INF_NAME = "inf"
TRUE_LIT: Optional[int] = None
FALSE_LIT = 0
InternalLit = Optional[int]  # None means satisfied literal; 0 means false literal.


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


def parse_column(text: str, cfg: Config) -> Tuple[int, int]:
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"expected COLUMN as slope:col, got {text!r}")
    a = parse_label(parts[0], cfg.p)
    j = int(parts[1])
    if not 0 <= j < cfg.q:
        raise ValueError(f"column index in {text!r} is outside 0..{cfg.q - 1}")
    return a, j


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
        raise ValueError("bullet is only configured for q=7")
    return (4 * i + 3 * j) % q


class VarPool:
    """Small custom variable pool.

    The original IDPool is convenient, but this search touches millions of literals.
    A tiny tuple-key pool avoids importing PySAT for non-solver modes and gives us direct
    control over fixed cells.
    """

    def __init__(self) -> None:
        self.top = 0
        self._ids: Dict[Tuple[int, int, int, int], int] = {}
        self._keys: Dict[int, Tuple[int, int, int, int]] = {}

    def id(self, key: Tuple[int, int, int, int]) -> int:
        old = self._ids.get(key)
        if old is not None:
            return old
        self.top += 1
        self._ids[key] = self.top
        self._keys[self.top] = key
        return self.top

    def key(self, var: int) -> Tuple[int, int, int, int]:
        return self._keys[var]


class CNFBuilder:
    def __init__(
        self,
        cfg: Config,
        strong_primary_prunes: bool = True,
        lambda6_row_prunes: bool = True,
        replace_derived_identities: bool = True,
        progress: Optional[ProgressLogger] = None,
    ) -> None:
        self.cfg = cfg
        self.p = cfg.p
        self.q = cfg.q
        self.labels = labels_for(cfg.p)
        self.mu, self.nu, self.omega = slope_maps(cfg.p, cfg.A, cfg.B)
        self.vpool = VarPool()
        self.clauses: List[List[int]] = []
        self.fixed: Dict[Tuple[int, int, int], int] = {}
        self.strong_primary_prunes = strong_primary_prunes
        self.lambda6_row_prunes = lambda6_row_prunes
        self.replace_derived_identities = replace_derived_identities
        self.progress = progress or ProgressLogger(enabled=False)
        self.trivial_clauses = 0
        self.false_literals_removed = 0
        self.duplicate_literals_removed = 0
        self.contradiction: Optional[str] = None

    def use_primary_prunes(self) -> bool:
        return self.strong_primary_prunes and self.cfg.seed_primary and self.cfg.p == 19 and self.cfg.q == 7

    def use_primary_lambda6_prunes(self) -> bool:
        return (
            self.use_primary_prunes()
            and self.mu[6] == 14
            and self.nu[6] == 5
            and self.omega[6] == 11
        )

    def covered_primary_identity_slopes(self) -> set[int]:
        if not (self.use_primary_prunes() and self.replace_derived_identities):
            return set()
        covered = {1, 5, 12}
        if self.use_primary_lambda6_prunes():
            covered.add(6)
        return covered

    def X(self, a: int, i: int, j: int, v: int) -> int:
        """Return a SAT variable for an unfixed cell value.

        Do not call this for assumptions on possibly fixed cells.  Use
        assumption_lit_for_cell instead.
        """
        if (a, i, j) in self.fixed:
            raise ValueError(f"attempted to create a variable for fixed {cell_desc(self.cfg, a, i, j, v)}")
        return self.vpool.id((a, i, j, v % self.q))

    def variable_if_unfixed(self, a: int, i: int, j: int, v: int) -> int:
        return self.vpool.id((a, i, j, v % self.q))

    def cell_lit(self, a: int, i: int, j: int, v: int, positive: bool = True) -> InternalLit:
        v %= self.q
        fixed_value = self.fixed.get((a, i, j))
        if fixed_value is not None:
            truth = fixed_value == v
            if positive:
                return TRUE_LIT if truth else FALSE_LIT
            return FALSE_LIT if truth else TRUE_LIT
        var = self.variable_if_unfixed(a, i, j, v)
        return var if positive else -var

    def assumption_lit_for_cell(self, a: int, i: int, j: int, value: int) -> Optional[int]:
        lit = self.cell_lit(a, i, j, value, positive=True)
        if lit is TRUE_LIT:
            return None
        if lit == FALSE_LIT:
            raise ValueError(f"assumption contradicts fixed seed: {cell_desc(self.cfg, a, i, j, value)}")
        return lit

    def add_clause(self, lits: Sequence[InternalLit], reason: str = "") -> None:
        if self.contradiction is not None:
            return
        seen: set[int] = set()
        out: List[int] = []
        for lit in lits:
            if lit is TRUE_LIT:
                self.trivial_clauses += 1
                return
            if lit == FALSE_LIT:
                self.false_literals_removed += 1
                continue
            assert lit is not None
            if -lit in seen:
                self.trivial_clauses += 1
                return
            if lit in seen:
                self.duplicate_literals_removed += 1
                continue
            seen.add(lit)
            out.append(lit)
        if not out:
            self.contradiction = reason or "empty clause generated"
            self.clauses.append([])
            return
        self.clauses.append(out)

    def exactly_one(self, lits: Sequence[InternalLit], reason: str = "") -> None:
        normalized: List[int] = []
        true_seen = False
        seen: set[int] = set()
        for lit in lits:
            if lit is TRUE_LIT:
                true_seen = True
            elif lit == FALSE_LIT:
                self.false_literals_removed += 1
            else:
                assert lit is not None
                if lit not in seen:
                    seen.add(lit)
                    normalized.append(lit)
        if true_seen:
            for lit in normalized:
                self.add_clause([-lit], reason=reason)
            return
        self.add_clause(normalized, reason=reason)
        for r in range(len(normalized)):
            lr = normalized[r]
            for s in range(r + 1, len(normalized)):
                self.add_clause([-lr, -normalized[s]], reason=reason)

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
        for i in range(q):
            for j in range(q):
                self.fix(self.cfg.bad, i, j, c3_row(q, i)[j])

        if self.cfg.seed_primary:
            self.progress.log("CNF seed: fixing primary O_4 and O_12 operations")
            for i in range(q):
                for j in range(q):
                    self.fix(4, i, j, i + 2 * j)
                    self.fix(12, i, j, 6 * i + 2 * j)
        self.progress.log(f"CNF seed complete: fixed_cells={len(self.fixed)}")

    def fixed_matrix_complete(self, a: int) -> bool:
        return all((a, i, j) in self.fixed for i in range(self.q) for j in range(self.q))

    def verify_covered_fixed_identity(self, lam: int) -> None:
        q = self.q
        m = self.mu[lam]
        n = self.nu[lam]
        w = self.omega[lam]
        if not all(self.fixed_matrix_complete(a) for a in (lam, m, n, w)):
            return
        for i in range(q):
            for j in range(q):
                t = self.fixed[(lam, i, j)]
                u = self.fixed[(m, t, i)]
                v = self.fixed[(n, j, u)]
                out = self.fixed[(w, i, v)]
                if out != j:
                    self.contradiction = f"fixed identity lambda={label_name(lam, self.p)} fails at i={i}, j={j}"
                    self.add_clause([], reason=self.contradiction)
                    return

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
                        continue
                    self.exactly_one(
                        [self.cell_lit(a, i, j, v, positive=True) for v in range(q)],
                        reason=f"cell exactly-one O_{label_name(a,self.p)}[{i},{j}]",
                    )

        for label_index, a in enumerate(self.labels, start=1):
            self.progress.log(
                f"CNF row permutations: O_{label_name(a, self.p)} "
                f"({label_index}/{len(self.labels)})"
            )
            for i in range(q):
                for v in range(q):
                    fixed_cols = [j for j in range(q) if self.fixed.get((a, i, j)) == v]
                    if len(fixed_cols) > 1:
                        self.contradiction = (
                            f"fixed row repeats value {v}: O_{label_name(a,self.p)} row {i}, "
                            f"cols={fixed_cols}"
                        )
                        self.add_clause([], reason=self.contradiction)
                        return
                    unfixed_lits = [
                        self.cell_lit(a, i, j, v, positive=True)
                        for j in range(q)
                        if (a, i, j) not in self.fixed
                    ]
                    if fixed_cols:
                        for lit in unfixed_lits:
                            if lit in (TRUE_LIT, FALSE_LIT):
                                self.add_clause([lit], reason="row fixed value exclusion")
                            else:
                                assert lit is not None
                                self.add_clause([-lit], reason="row fixed value exclusion")
                    else:
                        self.exactly_one(
                            unfixed_lits,
                            reason=f"row permutation O_{label_name(a,self.p)}[{i},*] contains {v}",
                        )

    def add_identity_constraints(self) -> None:
        q = self.q
        covered = self.covered_primary_identity_slopes()
        clauses_per_slope_raw = q ** 5
        for label_index, lam in enumerate(self.labels, start=1):
            if lam in covered:
                self.verify_covered_fixed_identity(lam)
                self.progress.log(
                    f"CNF identity: lambda={label_name(lam, self.p)} skipped; "
                    "covered by primary derived constraints/fixed seed"
                )
                continue
            # If all four operations are fixed, check and skip instead of emitting q^5 tautologies.
            if all(self.fixed_matrix_complete(a) for a in (lam, self.mu[lam], self.nu[lam], self.omega[lam])):
                self.verify_covered_fixed_identity(lam)
                self.progress.log(
                    f"CNF identity: lambda={label_name(lam, self.p)} fixed and checked; no clauses emitted"
                )
                continue

            m = self.mu[lam]
            n = self.nu[lam]
            w = self.omega[lam]
            before = len(self.clauses)
            triv_before = self.trivial_clauses
            false_before = self.false_literals_removed
            self.progress.log(
                f"CNF identity: lambda={label_name(lam, self.p)} "
                f"({label_index}/{len(self.labels)}), "
                f"mu={label_name(m, self.p)}, nu={label_name(n, self.p)}, "
                f"omega={label_name(w, self.p)}, raw={clauses_per_slope_raw}"
            )
            for i in range(q):
                for j in range(q):
                    for t in range(q):
                        lit1 = self.cell_lit(lam, i, j, t, positive=False)
                        if lit1 is TRUE_LIT:
                            self.trivial_clauses += q * q
                            continue
                        for u in range(q):
                            lit2 = self.cell_lit(m, t, i, u, positive=False)
                            if lit2 is TRUE_LIT:
                                self.trivial_clauses += q
                                continue
                            for v in range(q):
                                self.add_clause(
                                    [
                                        lit1,
                                        lit2,
                                        self.cell_lit(n, j, u, v, positive=False),
                                        self.cell_lit(w, i, v, j, positive=True),
                                    ],
                                    reason=f"identity lambda={label_name(lam,self.p)}",
                                )
            self.progress.log(
                f"CNF identity: lambda={label_name(lam, self.p)} complete, "
                f"clauses_added={len(self.clauses) - before}, "
                f"tautologies_skipped={self.trivial_clauses - triv_before}, "
                f"false_lits_removed={self.false_literals_removed - false_before}, "
                f"total_clauses={len(self.clauses)}"
            )

    def inverse_c3_value(self, row: int, output: int) -> int:
        if row == 0:
            return (5 * output) % self.q
        return (output - row) % self.q

    def add_equiv_cells(self, left: Tuple[int, int, int, int], right: Tuple[int, int, int, int], reason: str) -> None:
        a1, i1, j1, v1 = left
        a2, i2, j2, v2 = right
        self.add_clause([
            self.cell_lit(a1, i1, j1, v1, positive=False),
            self.cell_lit(a2, i2, j2, v2, positive=True),
        ], reason=reason)
        self.add_clause([
            self.cell_lit(a2, i2, j2, v2, positive=False),
            self.cell_lit(a1, i1, j1, v1, positive=True),
        ], reason=reason)

    def add_primary_lambda6_prunes(self) -> None:
        """Derived lambda=6 clauses for the primary seed.

        For lambda=6, mu=14, nu=5, omega=11:
            O_11(i, O_5(j, O_14(O_6(i,j), i))) = j.
        With O_5 fixed and O_11 rows permutations, choosing O_11(i,t)=j and
        O_6(i,j)=r directly forces O_14(r,i)=C_3_row_j^{-1}(t).
        """
        if not self.use_primary_lambda6_prunes():
            return

        q = self.q
        before = len(self.clauses)
        self.progress.log("CNF primary lambda=6 prunes: adding direct O_14 forcing clauses")
        forced_by_value: List[List[Tuple[int, int]]] = [[] for _ in range(q)]
        for j in range(q):
            for t in range(q):
                forced_value = self.inverse_c3_value(j, t)
                forced_by_value[forced_value].append((j, t))

        direct_before = len(self.clauses)
        for i in range(q):
            for j in range(q):
                for t in range(q):
                    forced_value = self.inverse_c3_value(j, t)
                    for r in range(q):
                        self.add_clause([
                            self.cell_lit(11, i, t, j, positive=False),
                            self.cell_lit(6, i, j, r, positive=False),
                            self.cell_lit(14, r, i, forced_value, positive=True),
                        ], reason="primary lambda=6 direct")
        direct_added = len(self.clauses) - direct_before

        repeat_before = len(self.clauses)
        if self.lambda6_row_prunes:
            self.progress.log("CNF primary lambda=6 prunes: adding O_11/O_6 row-repeat nogoods")
            for i in range(q):
                for k in range(i + 1, q):
                    for r in range(q):
                        for same_value_pairs in forced_by_value:
                            for j, t in same_value_pairs:
                                for ell, u in same_value_pairs:
                                    self.add_clause([
                                        self.cell_lit(11, i, t, j, positive=False),
                                        self.cell_lit(6, i, j, r, positive=False),
                                        self.cell_lit(11, k, u, ell, positive=False),
                                        self.cell_lit(6, k, ell, r, positive=False),
                                    ], reason="primary lambda=6 row-repeat")
        else:
            self.progress.log("CNF primary lambda=6 prunes: row-repeat nogoods disabled")
        repeat_added = len(self.clauses) - repeat_before
        self.progress.log(
            "CNF primary lambda=6 prunes complete: "
            f"direct_clauses={direct_added}, row_repeat_nogoods={repeat_added}, "
            f"clauses_added={len(self.clauses) - before}, total_clauses={len(self.clauses)}"
        )

    def add_primary_prunes(self) -> None:
        """Extra consequences valid for the primary p=19, q=7 seed.

        lambda=1:
            O_11(O_1(i,j), i) = 2(i-j).
        Hence each column of O_11 is a permutation and O_1 is determined by those columns.

        lambda=12:
            O_18(j, O_1(6i+2j, i)) = 4(j-i).

        lambda=6:
            direct O_14 forcing clauses and row-repeat nogoods for the O_11/O_6 block.
        """
        if not self.use_primary_prunes():
            self.progress.log("CNF primary prunes: skipped for this config")
            return
        before = len(self.clauses)
        self.progress.log("CNF primary prunes: adding lambda=1/lambda=12/lambda=6 consequences")
        q = self.q

        for i in range(q):
            for j in range(q):
                val = (2 * (i - j)) % q
                for r in range(q):
                    self.add_equiv_cells(
                        (1, i, j, r),
                        (11, r, i, val),
                        reason="primary lambda=1 equivalence",
                    )

        for col in range(q):
            for v in range(q):
                self.exactly_one(
                    [self.cell_lit(11, r, col, v, positive=True) for r in range(q)],
                    reason=f"primary O_11 column {col} contains {v}",
                )

        for i in range(q):
            for j in range(q):
                row = (6 * i + 2 * j) % q
                rhs = (4 * (j - i)) % q
                for u in range(q):
                    self.add_equiv_cells(
                        (1, row, i, u),
                        (18, j, u, rhs),
                        reason="primary lambda=12 equivalence",
                    )

        self.add_primary_lambda6_prunes()
        self.progress.log(
            f"CNF primary prunes complete: clauses_added={len(self.clauses) - before}, "
            f"total_clauses={len(self.clauses)}"
        )

    def build(self) -> Tuple[List[List[int]], VarPool]:
        build_start = time.time()
        self.progress.log(
            f"CNF build started: config={self.cfg.name}, p={self.p}, q={self.q}, "
            f"strong_primary_prunes={self.strong_primary_prunes}, "
            f"lambda6_row_prunes={self.lambda6_row_prunes}, "
            f"replace_derived_identities={self.replace_derived_identities}"
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
            f"vars={self.vpool.top}, clauses={len(self.clauses)}, "
            f"tautologies_skipped={self.trivial_clauses}, "
            f"false_lits_removed={self.false_literals_removed}"
        )
        if self.contradiction is not None:
            self.progress.log(f"CNF contains contradiction: {self.contradiction}")
        return self.clauses, self.vpool


def solver_class(name: str):
    try:
        from pysat.solvers import Cadical195, Glucose42, Kissat404, MapleChrono, Minisat22
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PySAT is required for solving. Install with: pip install 'python-sat[pblib,aiger]'"
        ) from exc

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


def solver_propagate(solver, assumptions: Sequence[int]) -> Optional[Tuple[bool, List[int]]]:
    if not hasattr(solver, "propagate"):
        return None
    try:
        ok, props = solver.propagate(assumptions=list(assumptions))
        return bool(ok), list(props)
    except TypeError:
        try:
            ok, props = solver.propagate(list(assumptions))
            return bool(ok), list(props)
        except Exception:
            return None
    except Exception:
        return None


def solve_with_progress(
    solver,
    assumptions: Sequence[int],
    args: argparse.Namespace,
    progress: ProgressLogger,
    label: str,
):
    assumption_list = [lit for lit in assumptions if lit]
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


def append_cell_assumption(assumptions: List[int], builder: CNFBuilder, a: int, i: int, j: int, value: int) -> None:
    lit = builder.assumption_lit_for_cell(a, i, j, value)
    if lit is not None:
        assumptions.append(lit)


def base_assumptions(cfg: Config, builder: CNFBuilder, args: argparse.Namespace) -> List[int]:
    assumptions: List[int] = []

    if args.symbreak_o11_00 is not None:
        if not cfg.seed_primary or cfg.q != 7:
            raise SystemExit("O11 symmetry break only applies to the primary q=7 seed")
        try:
            append_cell_assumption(assumptions, builder, 11, 0, 0, args.symbreak_o11_00)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    for spec in args.assume_cell or []:
        try:
            a, i, j, value = parse_assume_cell(spec, cfg)
            append_cell_assumption(assumptions, builder, a, i, j, value)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

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
                fixed = builder.fixed.get((a, i, j))
                if fixed is not None:
                    row.append(fixed)
                    continue
                vals = [v for v in range(q) if builder.variable_if_unfixed(a, i, j, v) in positive]
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
    for a, mat in O.items():
        for i, row in enumerate(mat):
            if sorted(row) != list(range(q)):
                if verbose:
                    print(f"row is not a permutation: O_{label_name(a,cfg.p)} row {i}: {row}")
                return False, None

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
    q = builder.q
    ia = inv_mod(a, q)
    ib = inv_mod(b, q)
    ass: List[int] = []
    for i in range(q):
        for j in range(q):
            append_cell_assumption(ass, builder, 11, i, j, (a * i + b * j + c) % q)
            forced_o1 = (ia * ((2 - b) * i - 2 * j - c)) % q
            append_cell_assumption(ass, builder, 1, i, j, forced_o1)
            append_cell_assumption(ass, builder, 6, i, j, j)
            k, ii = i, j
            if k == 0:
                val = (5 * ib * (-a * ii - c)) % q
            else:
                val = (ib * (k - a * ii - c) - k) % q
            append_cell_assumption(ass, builder, 14, i, j, val)
    return ass


def new_builder(cfg: Config, args: argparse.Namespace, progress: ProgressLogger) -> CNFBuilder:
    return CNFBuilder(
        cfg,
        strong_primary_prunes=not args.no_strong_prunes,
        lambda6_row_prunes=not args.no_lambda6_row_prunes,
        replace_derived_identities=not args.no_replace_derived_identities,
        progress=progress,
    )


def run_affine_o11_projection_sweep(cfg: Config, args: argparse.Namespace) -> int:
    if not cfg.seed_primary or cfg.q != 7:
        raise SystemExit("the affine O11 projection sweep is only implemented for the primary q=7 seed")
    progress = progress_logger_from_args(args)
    builder = new_builder(cfg, args, progress)
    clauses, _ = builder.build()
    S = solver_class(args.solver)
    print(f"CNF: vars={builder.vpool.top} clauses={len(clauses)} contradiction={builder.contradiction}")
    print("Sweeping 252 cases: O_11 affine, O_6(u,v)=v, O_14 forced by lambda=6")
    if builder.contradiction is not None:
        print(f"Base CNF is contradictory: {builder.contradiction}")
        return 1
    start = time.time()
    with S(bootstrap_with=clauses) as solver:
        count = 0
        for a in range(1, cfg.q):
            for b in range(1, cfg.q):
                for c in range(cfg.q):
                    count += 1
                    ass = affine_o11_projection_assumptions(builder, a, b, c)
                    progress.log(f"sweep case {count}/252 starts: a={a} b={b} c={c}")
                    if args.propagate_branches:
                        prop = solver_propagate(solver, ass)
                        if prop is not None and not prop[0]:
                            dt = time.time() - start
                            print(
                                f"case {count:3d}: a={a} b={b} c={c} -> unsat-prop   "
                                f"elapsed={dt:.2f}s {eta_text(count, 252, dt)}"
                            )
                            continue
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


def cell_choice(builder: CNFBuilder, cfg: Config, a: int, i: int, j: int, value: int) -> Optional[BranchChoice]:
    try:
        lit = builder.assumption_lit_for_cell(a, i, j, value)
    except ValueError:
        return None
    lits = [] if lit is None else [lit]
    return (
        cell_desc(cfg, a, i, j, value),
        lits,
        {"kind": "cell", "slope": label_name(a, cfg.p), "row": i, "col": j, "value": value},
    )


def row_choice(builder: CNFBuilder, cfg: Config, a: int, i: int, perm: Sequence[int]) -> Optional[BranchChoice]:
    lits: List[int] = []
    try:
        for j in range(cfg.q):
            lit = builder.assumption_lit_for_cell(a, i, j, perm[j])
            if lit is not None:
                lits.append(lit)
    except ValueError:
        return None
    return (
        row_desc(cfg, a, i, perm),
        lits,
        {"kind": "row", "slope": label_name(a, cfg.p), "row": i, "values": list(perm)},
    )


def column_choice(builder: CNFBuilder, cfg: Config, a: int, j: int, perm: Sequence[int]) -> Optional[BranchChoice]:
    lits: List[int] = []
    try:
        for i in range(cfg.q):
            lit = builder.assumption_lit_for_cell(a, i, j, perm[i])
            if lit is not None:
                lits.append(lit)
    except ValueError:
        return None
    return (
        column_desc(cfg, a, j, perm),
        lits,
        {"kind": "column", "slope": label_name(a, cfg.p), "col": j, "values": list(perm)},
    )


def branch_choice_groups(cfg: Config, builder: CNFBuilder, args: argparse.Namespace) -> List[List[BranchChoice]]:
    groups: List[List[BranchChoice]] = []

    branch_cells = list(args.branch_cell or [])
    branch_rows = list(args.branch_row or [])
    branch_columns = list(args.branch_column or [])
    branch_o11_columns = list(args.branch_o11_column or [])
    has_explicit_branch = bool(branch_cells or branch_rows or branch_columns or branch_o11_columns)

    if (
        not has_explicit_branch
        and args.symbreak_o11_00 is not None
        and args.restartable_symbreak
        and cfg.seed_primary
        and cfg.q == 7
    ):
        branch_o11_columns.append("0")
        has_explicit_branch = True

    if not has_explicit_branch and args.symbreak_o11_00 is None:
        if cfg.seed_primary and cfg.q == 7:
            if args.default_branch == "o11-column":
                branch_o11_columns.append("0")
            elif args.default_branch == "cell":
                branch_cells.append("11:0:0=0,1" if args.primary_o11_symmetry else "11:0:0")
            elif args.default_branch == "none":
                pass
            else:
                raise SystemExit(f"unknown --default-branch {args.default_branch!r}")

    for spec in branch_cells:
        try:
            (a, i, j), values = parse_branch_cell(spec, cfg)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        group = []
        for value in values:
            choice = cell_choice(builder, cfg, a, i, j, value)
            if choice is not None:
                group.append(choice)
        if not group:
            raise SystemExit(f"branch cell {spec!r} has no values compatible with fixed seed")
        groups.append(group)

    for spec in branch_rows:
        try:
            a, i = parse_row(spec, cfg)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        group = []
        for perm in itertools.permutations(range(cfg.q)):
            if cfg.seed_primary and a == 11 and i == 0 and args.symbreak_o11_00 is not None:
                if perm[0] != args.symbreak_o11_00:
                    continue
            choice = row_choice(builder, cfg, a, i, perm)
            if choice is not None:
                group.append(choice)
        if not group:
            raise SystemExit(f"branch row {spec!r} has no permutations compatible with fixed seed")
        groups.append(group)

    for spec in branch_columns:
        try:
            a, j = parse_column(spec, cfg)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        group = []
        for perm in itertools.permutations(range(cfg.q)):
            if cfg.seed_primary and a == 11 and j == 0 and args.symbreak_o11_00 is not None:
                if perm[0] != args.symbreak_o11_00:
                    continue
            if args.primary_o11_symmetry and cfg.seed_primary and a == 11 and j == 0 and perm[0] not in (0, 1):
                continue
            choice = column_choice(builder, cfg, a, j, perm)
            if choice is not None:
                group.append(choice)
        if not group:
            raise SystemExit(f"branch column {spec!r} has no permutations compatible with fixed seed")
        groups.append(group)

    for spec in branch_o11_columns:
        if not cfg.seed_primary or cfg.q != 7:
            raise SystemExit("--branch-o11-column is only justified for the primary q=7 seed")
        j = int(spec)
        if not 0 <= j < cfg.q:
            raise SystemExit(f"O11 column index {j} is outside 0..{cfg.q - 1}")
        group = []
        for perm in itertools.permutations(range(cfg.q)):
            if j == 0 and args.symbreak_o11_00 is not None and perm[0] != args.symbreak_o11_00:
                continue
            if args.primary_o11_symmetry and j == 0 and perm[0] not in (0, 1):
                continue
            choice = column_choice(builder, cfg, 11, j, perm)
            if choice is not None:
                group.append(choice)
        if not group:
            raise SystemExit(f"O11 column {j} has no permutations compatible with fixed seed")
        groups.append(group)

    return groups


def combined_branch_choices(groups: Sequence[Sequence[BranchChoice]]) -> Iterator[Tuple[str, List[int], List[Dict[str, object]]]]:
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
            if rec.get("status") in {"sat", "unsat", "unsat-prop", "bad-model", "verified-sat"} and isinstance(rec.get("branch"), str):
                completed.add(rec["branch"])
    return completed


def default_deep_log_path(cfg: Config, args: argparse.Namespace) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    name = f"{cfg.name}_{args.solver}_{stamp}.jsonl"
    return Path("run_logs") / "colored_magma_tuned" / name


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
    builder = new_builder(cfg, args, progress)
    clauses, _ = builder.build()
    base = base_assumptions(cfg, builder, args)
    groups = branch_choice_groups(cfg, builder, args)
    total = branch_count(groups)
    selected_total = selected_branch_count(total, args.branch_mod, args.branch_index)
    log_path = Path(args.log) if args.log else default_deep_log_path(cfg, args)
    completed = load_completed_branches(log_path) if args.resume else set()

    print(f"Config: {cfg}")
    print(f"base identity: {base_ok(cfg)}")
    print(
        f"CNF: vars={builder.vpool.top} clauses={len(clauses)} base_assumptions={len(base)} "
        f"tautologies_skipped={builder.trivial_clauses} false_lits_removed={builder.false_literals_removed}"
    )
    print(f"Branch groups: {[len(group) for group in groups] or [1]} total={total}")
    print(f"Shard: index={args.branch_index} mod={args.branch_mod}")
    print(f"Selected local branches: {selected_total}")
    if args.max_branches:
        print(f"Max local solves this run: {args.max_branches}")
    print(f"Log: {log_path}")
    if args.resume:
        print(f"Resume: loaded {len(completed)} completed branch record(s)")
    if args.primary_o11_symmetry and cfg.seed_primary:
        print("Using primary color-scalar symmetry: O_11(0,0)=0 or normalized to 1 for column-0 splits.")
    for desc in assumption_descriptions(cfg, args):
        print(f"Base assumption: {desc}")
    if builder.contradiction is not None:
        print(f"Base CNF is contradictory: {builder.contradiction}")
        return 1

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
    prop_unsat = 0
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
                        f"processed={solved + unknown + skipped + prop_unsat}/{selected_total}, "
                        f"elapsed={format_seconds(elapsed)} {eta_text(solved + unknown + skipped + prop_unsat, selected_total, elapsed)}"
                    )
                continue
            if args.max_branches and solved + unknown + prop_unsat >= args.max_branches:
                break

            assumptions = base + branch_assumptions
            progress.log(
                f"branch {branch_no}/{total} local={local_seen}/{selected_total} starts: "
                f"{description}; assumptions={len(assumptions)}"
            )
            start = time.time()
            if args.propagate_branches:
                prop = solver_propagate(solver, assumptions)
                if prop is not None:
                    ok, props = prop
                    if not ok:
                        elapsed = time.time() - start
                        prop_unsat += 1
                        print(
                            f"branch {branch_no}/{total}: {description} -> unsat-prop "
                            f"elapsed={elapsed:.2f}s propagated={len(props)} stats={solver_stats(solver)}"
                        )
                        append_jsonl(log_path, {
                            "branch": description,
                            "branch_no": branch_no,
                            "total_branches": total,
                            "details": details,
                            "status": "unsat-prop",
                            "elapsed_seconds": elapsed,
                            "solver": args.solver,
                            "stats": solver_stats(solver),
                        })
                        processed = solved + unknown + skipped + prop_unsat
                        run_elapsed = time.time() - run_start
                        progress.log(
                            f"deep progress: processed={processed}/{selected_total}, solved={solved}, "
                            f"prop_unsat={prop_unsat}, unknown={unknown}, skipped={skipped}, "
                            f"elapsed={format_seconds(run_elapsed)} {eta_text(processed, selected_total, run_elapsed)}"
                        )
                        continue
                    if args.propagate_only:
                        elapsed = time.time() - start
                        unknown += 1
                        print(
                            f"branch {branch_no}/{total}: {description} -> prop-ok "
                            f"elapsed={elapsed:.2f}s propagated={len(props)}"
                        )
                        continue

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
            processed = solved + unknown + skipped + prop_unsat
            run_elapsed = time.time() - run_start
            progress.log(
                f"deep progress: processed={processed}/{selected_total}, solved={solved}, "
                f"prop_unsat={prop_unsat}, unknown={unknown}, skipped={skipped}, "
                f"elapsed={format_seconds(run_elapsed)} {eta_text(processed, selected_total, run_elapsed)}"
            )
            if sat is None or sat is False:
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
        f"solved={solved} prop_unsat={prop_unsat} unknown={unknown} skipped={skipped}"
    )
    if unknown:
        return 3
    return 1


def write_dimacs(path: Path, clauses: Sequence[Sequence[int]], vars_top: int,
                 assumptions: Sequence[int], comments: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assumptions = [lit for lit in assumptions if lit]
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
    builder = new_builder(cfg, args, progress)
    clauses, _ = builder.build()
    assumptions = base_assumptions(cfg, builder, args)
    out = Path(args.cnf_out or "colored_magma_tuned.cnf")
    comments = [
        f"config={cfg}",
        f"base_identity={base_ok(cfg)}",
        f"vars={builder.vpool.top}",
        f"clauses_without_assumptions={len(clauses)}",
        f"tautologies_skipped={builder.trivial_clauses}",
        f"false_lits_removed={builder.false_literals_removed}",
        f"contradiction={builder.contradiction}",
    ]
    for desc in assumption_descriptions(cfg, args):
        comments.append(f"assumption {desc}")
    progress.log(f"DIMACS export: writing {out}")
    write_dimacs(out, clauses, builder.vpool.top, assumptions, comments)
    print(f"wrote {out} with vars={builder.vpool.top} clauses={len(clauses) + len(assumptions)}")
    return 0


def run_cubes_export(cfg: Config, args: argparse.Namespace) -> int:
    progress = progress_logger_from_args(args)
    builder = new_builder(cfg, args, progress)
    clauses, _ = builder.build()
    base = base_assumptions(cfg, builder, args)
    groups = branch_choice_groups(cfg, builder, args)
    total = branch_count(groups)
    out_dir = Path(args.cubes_out_dir or "colored_magma_cubes")
    out_dir.mkdir(parents=True, exist_ok=True)
    cnf_path = out_dir / "base.cnf"
    cubes_path = out_dir / "cubes.txt"
    meta_path = out_dir / "cubes.jsonl"
    write_dimacs(cnf_path, clauses, builder.vpool.top, [], [
        f"config={cfg}",
        f"base_identity={base_ok(cfg)}",
        f"vars={builder.vpool.top}",
        f"clauses_without_assumptions={len(clauses)}",
    ])
    selected = 0
    with cubes_path.open("w", encoding="utf-8") as cf, meta_path.open("w", encoding="utf-8") as mf:
        for branch_no, (description, branch_assumptions, details) in enumerate(combined_branch_choices(groups), start=1):
            if (branch_no - 1) % args.branch_mod != args.branch_index:
                continue
            assumptions = base + branch_assumptions
            cf.write(" ".join(map(str, assumptions)) + " 0\n")
            mf.write(json.dumps({
                "branch_no": branch_no,
                "total_branches": total,
                "description": description,
                "assumptions": assumptions,
                "details": details,
            }, sort_keys=True) + "\n")
            selected += 1
            if args.max_branches and selected >= args.max_branches:
                break
    print(f"wrote {cnf_path}")
    print(f"wrote {cubes_path} with {selected} cube(s)")
    print(f"wrote {meta_path}")
    return 0


def run_full_sat(cfg: Config, args: argparse.Namespace) -> int:
    progress = progress_logger_from_args(args)
    builder = new_builder(cfg, args, progress)
    clauses, _ = builder.build()
    assumptions = base_assumptions(cfg, builder, args)

    print(f"Config: {cfg}")
    print(f"base identity: {base_ok(cfg)}")
    print(
        f"CNF: vars={builder.vpool.top} clauses={len(clauses)} assumptions={len(assumptions)} "
        f"tautologies_skipped={builder.trivial_clauses} false_lits_removed={builder.false_literals_removed}"
    )
    for desc in assumption_descriptions(cfg, args):
        print(f"Assumption: {desc}")
    if builder.contradiction is not None:
        print(f"Base CNF is contradictory: {builder.contradiction}")
        return 1

    S = solver_class(args.solver)
    start = time.time()
    progress.log(f"creating solver {args.solver} with {len(clauses)} clauses")
    with S(bootstrap_with=clauses) as solver:
        if args.propagate_branches:
            prop = solver_propagate(solver, assumptions)
            if prop is not None and not prop[0]:
                print(f"SAT result: False by propagation   elapsed={time.time() - start:.2f}s")
                return 1
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


def run_stats(cfg: Config, args: argparse.Namespace) -> int:
    progress = progress_logger_from_args(args)
    builder = new_builder(cfg, args, progress)
    clauses, _ = builder.build()
    length_counts: Dict[int, int] = {}
    for clause in clauses:
        length_counts[len(clause)] = length_counts.get(len(clause), 0) + 1
    print(f"Config: {cfg}")
    print(f"base identity: {base_ok(cfg)}")
    print(f"vars={builder.vpool.top}")
    print(f"clauses={len(clauses)}")
    print(f"clause_lengths={dict(sorted(length_counts.items()))}")
    print(f"fixed_cells={len(builder.fixed)}")
    print(f"tautologies_skipped={builder.trivial_clauses}")
    print(f"false_lits_removed={builder.false_literals_removed}")
    print(f"duplicate_literals_removed={builder.duplicate_literals_removed}")
    print(f"contradiction={builder.contradiction}")
    covered = sorted(label_name(a, cfg.p) for a in builder.covered_primary_identity_slopes())
    print(f"covered_primary_identity_slopes={covered}")
    return 0 if builder.contradiction is None else 1


def config_from_name(name: str) -> Config:
    if name == "primary":
        return Config(name="primary", p=19, q=7, A=7, B=4, bad=5, seed_primary=True)
    if name == "backup1":
        return Config(name="backup1", p=19, q=7, A=7, B=3, bad=16, seed_primary=False)
    if name == "backup2q7":
        return Config(name="backup2q7", p=31, q=7, A=5, B=9, bad=17, seed_primary=False)
    raise SystemExit("unknown config; choose primary, backup1, or backup2q7")


def config_from_args(args: argparse.Namespace) -> Config:
    if args.config != "custom":
        return config_from_name(args.config)
    missing = [name for name in ("p", "q", "A", "B", "bad_slope") if getattr(args, name) is None]
    if missing:
        raise SystemExit(f"--config custom requires {', '.join('--' + name.replace('_', '-') for name in missing)}")
    if args.p < 2 or args.q < 2:
        raise SystemExit("custom --p and --q must be at least 2")
    if args.bad_slope < 0 or args.bad_slope > args.p:
        raise SystemExit("custom --bad-slope must be in 0..p, where p denotes infinity")
    name = f"custom_p{args.p}_q{args.q}_A{args.A}_B{args.B}_bad{args.bad_slope}"
    return Config(name=name, p=args.p, q=args.q, A=args.A, B=args.B, bad=args.bad_slope, seed_primary=False)


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
    parser.add_argument("--config", default="primary", choices=["primary", "backup1", "backup2q7", "custom"])
    parser.add_argument("--p", type=int, default=None, help="custom config base field size")
    parser.add_argument("--q", type=int, default=None, help="custom config color field size")
    parser.add_argument("--A", type=int, default=None, help="custom config left base coefficient")
    parser.add_argument("--B", type=int, default=None, help="custom config right base coefficient")
    parser.add_argument("--bad-slope", type=int, default=None, help="custom config bad slope; use p for infinity")
    parser.add_argument("--mode", default="full", choices=[
        "full", "deep", "dimacs", "cubes", "affine-o11-projection-sweep", "maps", "stats",
    ])
    parser.add_argument("--solver", default="cadical", choices=["cadical", "glucose", "kissat", "maple", "minisat"])
    parser.add_argument("--out", default="solution.json", help="where to write a found solution JSON; use empty string to disable")
    parser.add_argument("--conflicts", type=int, default=0, help="optional conflict budget for solvers supporting solve_limited")
    parser.add_argument("--quiet", action="store_true", help="suppress timestamped progress logging")
    parser.add_argument("--progress-every", type=float, default=5.0,
                        help="seconds between long-running solve progress reports; use 0 to print every chunk")
    parser.add_argument("--progress-conflicts", type=int, default=50000,
                        help="conflict chunk size for solve progress when --conflicts is not set; use 0 for blocking solve")
    parser.add_argument("--no-strong-prunes", action="store_true", help="disable derived primary pruning")
    parser.add_argument("--no-lambda6-row-prunes", action="store_true", help="disable derived lambda=6 row-repeat nogoods")
    parser.add_argument("--no-replace-derived-identities", action="store_true",
                        help="keep full q^5 identities even when primary derived constraints cover lambda=1,5,6,12")
    parser.add_argument("--symbreak-o11-00", type=int, choices=[0, 1], default=None,
                        help="primary only: assume O_11(0,0)=0 or normalized nonzero value 1")
    parser.add_argument("--restartable-symbreak", action=argparse.BooleanOptionalAction, default=True,
                        help="with --symbreak-o11-00 and no explicit branch, split O_11 column 0 into resumable cubes")
    parser.add_argument("--assume-cell", action="append", default=[], metavar="L:I:J:V",
                        help="add a unit assumption O_L(i,j)=v; use L=inf for the infinite slope")
    parser.add_argument("--branch-cell", action="append", default=[], metavar="L:I:J[=V,...]",
                        help="deep mode: split over values of a cell, or over listed values only")
    parser.add_argument("--branch-row", action="append", default=[], metavar="L:I",
                        help="deep mode: split over all row permutations for O_L row i")
    parser.add_argument("--branch-column", action="append", default=[], metavar="L:J",
                        help="deep/cubes mode: split over all column permutations for O_L column j")
    parser.add_argument("--branch-o11-column", action="append", default=[], metavar="J",
                        help="deep/cubes mode, primary only: split over all permutations of column j of O_11")
    parser.add_argument("--default-branch", default="o11-column", choices=["o11-column", "cell", "none"],
                        help="deep mode default branch when no explicit branch is given")
    parser.add_argument("--primary-o11-symmetry", action="store_true",
                        help="primary deep mode: quotient color-scalar symmetry for O_11 column 0 by perm[0] in {0,1}")
    parser.add_argument("--propagate-branches", action="store_true",
                        help="call solver.propagate on branch assumptions before full solving")
    parser.add_argument("--propagate-only", action="store_true",
                        help="deep mode: only propagation-test branches; do not run full SAT solves")
    parser.add_argument("--branch-mod", type=int, default=1, help="deep/cubes mode: run only branches with index congruent to --branch-index modulo this value")
    parser.add_argument("--branch-index", type=int, default=0, help="deep/cubes mode: shard index used with --branch-mod")
    parser.add_argument("--max-branches", type=int, default=0, help="deep/cubes mode: stop after this many local branches in the selected shard")
    parser.add_argument("--log", default="", help="deep mode: JSONL progress log path")
    parser.add_argument("--resume", action="store_true", help="deep mode: skip branches already marked complete in the JSONL log")
    parser.add_argument("--dry-run", action="store_true", help="deep mode: print selected branches without solving")
    parser.add_argument("--cnf-out", default="", help="dimacs mode: path for exported CNF")
    parser.add_argument("--cubes-out-dir", default="", help="cubes mode: directory for base.cnf and cubes.txt")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    if args.conflicts < 0:
        raise SystemExit("--conflicts must be nonnegative")
    if args.progress_conflicts < 0:
        raise SystemExit("--progress-conflicts must be nonnegative")
    if args.progress_every < 0:
        raise SystemExit("--progress-every must be nonnegative")
    if args.branch_mod < 1:
        raise SystemExit("--branch-mod must be positive")
    if args.branch_index < 0 or args.branch_index >= args.branch_mod:
        raise SystemExit("--branch-index must satisfy 0 <= index < mod")
    if args.out == "":
        args.out = None
    cfg = config_from_args(args)
    if args.mode == "maps":
        show_maps(cfg)
        return 0
    if args.mode == "stats":
        return run_stats(cfg, args)
    if args.mode == "affine-o11-projection-sweep":
        return run_affine_o11_projection_sweep(cfg, args)
    if args.mode == "deep":
        return run_deep_sat(cfg, args)
    if args.mode == "dimacs":
        return run_dimacs_export(cfg, args)
    if args.mode == "cubes":
        return run_cubes_export(cfg, args)
    return run_full_sat(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
