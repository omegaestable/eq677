from __future__ import annotations

import argparse
import ast
import json
import random
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from e677_api import (
    MANIFEST_URL,
    TOKEN_ENV,
    configure_utf8_stdio,
    fetch_text,
    load_manifest,
    post_display_reorder,
    post_magma_comment,
    post_size_comment,
    submit_table,
    table_url,
)


Table = list[list[int]]


def parse_table(text: str) -> Table:
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty table")
    if stripped.startswith("["):
        parsed = json.loads(stripped)
        if not isinstance(parsed, list):
            raise ValueError("JSON table must be an array of arrays")
        table = [[int(value) for value in row] for row in parsed]
    else:
        rows = []
        for line in stripped.splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append([int(part) for part in line.replace(",", " ").split()])
        table = rows
    validate_table_shape(table)
    return table


def validate_table_shape(table: Table) -> None:
    order = len(table)
    if order == 0:
        raise ValueError("table must have positive size")
    for row in table:
        if len(row) != order:
            raise ValueError("table must be square")
        for value in row:
            if value < 0 or value >= order:
                raise ValueError("table value out of range")


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
    expected = set(range(len(table)))
    return all(set(row) == expected for row in table)


def right_cancellative(table: Table) -> bool:
    order = len(table)
    for column in range(order):
        values = [table[row][column] for row in range(order)]
        if len(set(values)) != order:
            return False
    return True


def idempotent(table: Table) -> bool:
    return all(table[x][x] == x for x in range(len(table)))


def e677_holds(table: Table) -> bool:
    return all(e677_at(table, x, y) for x in range(len(table)) for y in range(len(table)))


def e255_failures(table: Table) -> list[int]:
    return [x for x in range(len(table)) if not e255_at(table, x)]


def orbit_under_left(table: Table, x: int) -> list[int]:
    current = x
    orbit: list[int] = []
    for _ in range(len(table) + 1):
        orbit.append(current)
        current = table[x][current]
        if current == x:
            return orbit
    return orbit


def right_fibers(table: Table, x: int) -> dict[int, list[int]]:
    fibers: dict[int, list[int]] = defaultdict(list)
    for y in range(len(table)):
        fibers[table[y][x]].append(y)
    return dict(fibers)


def collision_profile(table: Table) -> Counter[int]:
    profile: Counter[int] = Counter()
    for x in range(len(table)):
        for fiber in right_fibers(table, x).values():
            if len(fiber) > 1:
                profile[len(fiber)] += 1
    return profile


def linear_table(order: int, alpha: int, beta: int, const: int = 0) -> Table:
    return [
        [((alpha * left) + (beta * right) + const) % order for right in range(order)]
        for left in range(order)
    ]


def cache_path(cache_dir: Path, record: dict[str, Any]) -> Path:
    size = int(record["size"])
    canonical_hash = str(record["canonical_hash"])
    return cache_dir / str(size) / f"{canonical_hash}.txt"


def load_table(record: dict[str, Any], cache_dir: Path | None) -> Table:
    if cache_dir is not None:
        path = cache_path(cache_dir, record)
        if path.exists():
            return parse_table(path.read_text(encoding="utf-8"))
        text = fetch_text(table_url(record))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return parse_table(text)
    return parse_table(fetch_text(table_url(record)))


def selected_records(args: argparse.Namespace, magmas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = magmas
    if args.size is not None:
        sizes = set(args.size)
        records = [record for record in records if int(record.get("size", -1)) in sizes]
    if args.min_size is not None:
        records = [record for record in records if int(record.get("size", -1)) >= args.min_size]
    if args.max_size is not None:
        records = [record for record in records if int(record.get("size", -1)) <= args.max_size]
    if args.hash_prefix:
        prefixes = tuple(prefix.lower() for prefix in args.hash_prefix)
        records = [
            record
            for record in records
            if str(record.get("canonical_hash", "")).lower().startswith(prefixes)
        ]
    records = sorted(records, key=lambda record: (int(record["size"]), str(record["canonical_hash"])))
    if args.sample:
        rng = random.Random(args.seed)
        records = rng.sample(records, min(args.sample, len(records)))
        records = sorted(records, key=lambda record: (int(record["size"]), str(record["canonical_hash"])))
    if args.limit is not None:
        records = records[: args.limit]
    return records


def manifest_stats(manifest: dict[str, Any]) -> dict[str, Any]:
    magmas = manifest["magmas"]
    return {
        "magmas": magmas,
        "by_size": Counter(int(record["size"]) for record in magmas),
        "satisfies_255": Counter(bool(record.get("satisfies_255")) for record in magmas),
        "right_cancellative": Counter(bool(record.get("right_cancellative")) for record in magmas),
        "idempotent": Counter(bool(record.get("idempotent")) for record in magmas),
        "commented_sizes": {
            int(item["size"]): item["comment"] for item in manifest.get("size_commentary", [])
        },
    }


def summarize_manifest(manifest: dict[str, Any]) -> None:
    stats = manifest_stats(manifest)
    by_size: Counter[int] = stats["by_size"]
    commented_sizes: dict[int, str] = stats["commented_sizes"]
    sizes = sorted(by_size)

    print(f"manifest count: {manifest.get('count', len(stats['magmas']))}")
    print(f"loaded magmas: {len(stats['magmas'])}")
    if sizes:
        print(f"size range: {sizes[0]}..{sizes[-1]}")
        missing = [size for size in range(sizes[0], sizes[-1] + 1) if size not in by_size]
        print(f"sizes present: {len(sizes)}")
        print(f"sizes missing in range: {missing[:40]}{' ...' if len(missing) > 40 else ''}")
    print(f"satisfies_255 counts: {dict(stats['satisfies_255'])}")
    print(f"right_cancellative counts: {dict(stats['right_cancellative'])}")
    print(f"idempotent counts: {dict(stats['idempotent'])}")
    print("top sizes by record count:")
    for size, count in by_size.most_common(15):
        note = " commented" if size in commented_sizes else ""
        print(f"  size {size}: {count}{note}")
    if commented_sizes:
        print("size commentary entries:")
        for size in sorted(commented_sizes)[:30]:
            first_line = commented_sizes[size].strip().splitlines()[0]
            print(f"  size {size}: {first_line[:120]}")


def analyze_record(record: dict[str, Any], table: Table) -> dict[str, Any]:
    order = len(table)
    period_counts = Counter(len(orbit_under_left(table, x)) for x in range(order))
    right_collision_counts = collision_profile(table)
    failures = e255_failures(table)
    label = str(record.get("canonical_hash", record.get("label", "local")))[:16]
    return {
        "hash": label,
        "size": order,
        "e677": e677_holds(table),
        "e255_failures": failures,
        "left_rows_permutations": left_rows_are_permutations(table),
        "right_cancellative": right_cancellative(table),
        "idempotent": idempotent(table),
        "period_counts": dict(sorted(period_counts.items())),
        "right_collision_fiber_sizes": dict(sorted(right_collision_counts.items())),
    }


def print_record_summary(summary: dict[str, Any]) -> None:
    print(
        f"{summary['hash']} size={summary['size']} e677={summary['e677']} "
        f"e255_failures={summary['e255_failures']} left_rows={summary['left_rows_permutations']} "
        f"right_cancel={summary['right_cancellative']} idempotent={summary['idempotent']} "
        f"periods={summary['period_counts']} collisions={summary['right_collision_fiber_sizes']}"
    )


def product_shape(value: str) -> tuple[int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("must have the form base,fiber such as 11,61")
    try:
        base_size, fiber_size = (int(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("base and fiber sizes must be integers") from exc
    if base_size <= 0 or fiber_size <= 0:
        raise argparse.ArgumentTypeError("base and fiber sizes must be positive")
    return base_size, fiber_size


def display_order(record: dict[str, Any], order: int) -> list[int] | None:
    raw = record.get("display_reorder")
    if raw is None:
        return None
    if isinstance(raw, str):
        parsed = list(ast.literal_eval(raw))
    elif isinstance(raw, list):
        parsed = [int(value) for value in raw]
    else:
        raise ValueError("display_reorder must be a string or list")
    if sorted(parsed) != list(range(order)):
        raise ValueError("display_reorder must be a permutation of table labels")
    return parsed


def display_product_profile(
    record: dict[str, Any],
    table: Table,
    shape: tuple[int, int],
) -> dict[str, Any]:
    base_size, fiber_size = shape
    order = len(table)
    if base_size * fiber_size != order:
        raise ValueError("display product shape must multiply to the table order")
    reorder = display_order(record, order)
    if reorder is None:
        raise ValueError("record has no display_reorder for product profiling")
    position = {label: index for index, label in enumerate(reorder)}

    def coord(label: int) -> tuple[int, int]:
        return divmod(position[label], fiber_size)

    base_table: list[list[int]] = []
    base_dependency_failures = 0
    coefficient_counts: Counter[tuple[int, int]] = Counter()
    coefficients_by_diff: dict[int, Counter[tuple[int, int]]] = defaultdict(Counter)
    affine_failures = 0

    for base_left in range(base_size):
        base_row: list[int] = []
        for base_right in range(base_size):
            base_values: set[int] = set()
            for left_fiber in range(fiber_size):
                for right_fiber in range(fiber_size):
                    output = table[reorder[base_left * fiber_size + left_fiber]][
                        reorder[base_right * fiber_size + right_fiber]
                    ]
                    base_values.add(coord(output)[0])
            if len(base_values) != 1:
                base_dependency_failures += 1
                base_row.append(-1)
                continue
            output_base = next(iter(base_values))
            base_row.append(output_base)

            y00 = coord(table[reorder[base_left * fiber_size]][reorder[base_right * fiber_size]])[1]
            y10 = coord(table[reorder[base_left * fiber_size + 1]][reorder[base_right * fiber_size]])[1]
            y01 = coord(table[reorder[base_left * fiber_size]][reorder[base_right * fiber_size + 1]])[1]
            coeff_left = (y10 - y00) % fiber_size
            coeff_right = (y01 - y00) % fiber_size
            for left_fiber in range(fiber_size):
                for right_fiber in range(fiber_size):
                    output = table[reorder[base_left * fiber_size + left_fiber]][
                        reorder[base_right * fiber_size + right_fiber]
                    ]
                    if coord(output)[1] != (coeff_left * left_fiber + coeff_right * right_fiber + y00) % fiber_size:
                        affine_failures += 1
                        break
            coefficient_counts[(coeff_left, coeff_right)] += 1
            if base_size > 1:
                coefficients_by_diff[(base_left - base_right) % base_size][(coeff_left, coeff_right)] += 1
        base_table.append(base_row)

    return {
        "display_product_shape": shape,
        "display_base_dependency_failures": base_dependency_failures,
        "display_fiber_affine_failures": affine_failures,
        "display_fiber_coefficients": dict(sorted(coefficient_counts.items())),
        "display_coefficients_by_base_diff": {
            diff: dict(sorted(counter.items())) for diff, counter in sorted(coefficients_by_diff.items())
        },
        "display_base_table": base_table,
    }


def analyze_tables(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    magmas = manifest["magmas"]
    records = selected_records(args, magmas)
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    if not records:
        print("no records selected")
        return 1
    print(f"selected records: {len(records)}")

    aggregate_periods: Counter[int] = Counter()
    aggregate_collisions: Counter[int] = Counter()
    bad_hashes: list[str] = []
    for record in records:
        table = load_table(record, cache_dir)
        summary = analyze_record(record, table)
        product_summary = None
        if args.display_product is not None:
            product_summary = display_product_profile(record, table, args.display_product)
        aggregate_periods.update(summary["period_counts"])
        aggregate_collisions.update(summary["right_collision_fiber_sizes"])
        if summary["e255_failures"]:
            bad_hashes.append(str(record["canonical_hash"]))
        print_record_summary(summary)
        if product_summary is not None:
            collapsed = sum(
                count
                for (left_coeff, _right_coeff), count in product_summary["display_fiber_coefficients"].items()
                if left_coeff == 0
            )
            print(
                f"  display_product={product_summary['display_product_shape']} "
                f"base_dep_failures={product_summary['display_base_dependency_failures']} "
                f"fiber_affine_failures={product_summary['display_fiber_affine_failures']} "
                f"left_collapsed_base_pairs={collapsed} "
                f"coefficients={product_summary['display_fiber_coefficients']}"
            )
            print(f"  coefficients_by_base_diff={product_summary['display_coefficients_by_base_diff']}")
            if args.show_base_table:
                print("  display base table:")
                for row in product_summary["display_base_table"]:
                    print("   " + " ".join(f"{value:2d}" for value in row))
    print("aggregate L_x orbit periods:")
    for period, count in sorted(aggregate_periods.items()):
        print(f"  {period}: {count}")
    print("aggregate right-collision fiber sizes:")
    for fiber_size, count in sorted(aggregate_collisions.items()):
        print(f"  {fiber_size}: {count}")
    if bad_hashes:
        print("E255 failures found:")
        for canonical_hash in bad_hashes:
            print(f"  {canonical_hash}")
        return 2
    return 0


def manifest_command(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    summarize_manifest(manifest)
    if args.save:
        Path(args.save).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        print(f"saved manifest: {args.save}")
    return 0


def analyze_command(args: argparse.Namespace) -> int:
    return analyze_tables(args)


def analyze_file_command(args: argparse.Namespace) -> int:
    table_path = Path(args.table)
    table = parse_table(table_path.read_text(encoding="utf-8"))
    summary = analyze_record({"label": table_path.name}, table)
    print_record_summary(summary)
    if summary["e255_failures"]:
        return 2
    if not summary["e677"]:
        return 1
    return 0


def print_json_response(response: Any) -> None:
    print(json.dumps(response, indent=2, sort_keys=True))


def submit_command(args: argparse.Namespace) -> int:
    table_text = Path(args.table).read_text(encoding="utf-8")
    print_json_response(submit_table(table_text, content_type=args.content_type))
    return 0


def magma_comment_command(args: argparse.Namespace) -> int:
    print_json_response(post_magma_comment(args.hash, args.content))
    return 0


def size_comment_command(args: argparse.Namespace) -> int:
    print_json_response(post_size_comment(args.size, args.content))
    return 0


def display_reorder_command(args: argparse.Namespace) -> int:
    display_reorder = None if args.identity else args.display_reorder
    print_json_response(post_display_reorder(args.hash, display_reorder))
    return 0


def selftest_command(_args: argparse.Namespace) -> int:
    parsed = parse_table("[[0,1],[1,0]]")
    assert parsed == [[0, 1], [1, 0]]

    f5 = linear_table(5, 2, -1)
    assert left_rows_are_permutations(f5)
    assert right_cancellative(f5)
    assert e677_holds(f5)
    assert e255_failures(f5) == []
    assert left_div(f5, 2, f5[2][3]) == 3

    fake_manifest = {
        "count": 2,
        "magmas": [
            {
                "canonical_hash": "abc123",
                "size": 5,
                "satisfies_255": True,
                "right_cancellative": True,
                "idempotent": True,
            },
            {
                "canonical_hash": "def456",
                "size": 25,
                "satisfies_255": True,
                "right_cancellative": False,
                "idempotent": True,
            },
        ],
        "size_commentary": [{"size": 2, "comment": "No magma of size 2 satisfies Equation 677."}],
    }
    stats = manifest_stats(fake_manifest)
    assert stats["by_size"][5] == 1
    assert stats["right_cancellative"][False] == 1
    assert stats["commented_sizes"][2].startswith("No magma")

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
        json.dump(fake_manifest, handle)
        manifest_path = Path(handle.name)
    try:
        assert load_manifest(str(manifest_path))["count"] == 2
    finally:
        manifest_path.unlink(missing_ok=True)

    assert table_url("abc123").endswith("/magma/abc123/table.txt")
    assert table_url({"canonical_hash": "def456"}).endswith("/magma/def456/table.txt")
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


def add_selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--size", action="append", type=positive_int, help="select one size; can be repeated")
    parser.add_argument("--min-size", type=positive_int, help="minimum selected size")
    parser.add_argument("--max-size", type=positive_int, help="maximum selected size")
    parser.add_argument("--hash-prefix", action="append", help="select hashes with this prefix; can be repeated")
    parser.add_argument("--limit", type=nonnegative_int, help="maximum selected records after sorting/filtering")
    parser.add_argument("--sample", type=nonnegative_int, help="random sample size before limit")
    parser.add_argument("--seed", type=int, default=677, help="random seed for --sample")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze the public Equation 677 database")
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest", help="summarize the database manifest")
    manifest.add_argument("--manifest", default=MANIFEST_URL, help="manifest URL or local JSON path")
    manifest.add_argument("--save", help="save the manifest JSON to this path")
    manifest.set_defaults(func=manifest_command)

    analyze = subparsers.add_parser("analyze", help="download selected tables and compute invariants")
    analyze.add_argument("--manifest", default=MANIFEST_URL, help="manifest URL or local JSON path")
    analyze.add_argument("--cache-dir", help="optional directory for cached canonical tables")
    analyze.add_argument(
        "--display-product",
        type=product_shape,
        help="profile a display_reorder product layout, for example 11,61 for size 671",
    )
    analyze.add_argument("--show-base-table", action="store_true", help="print the induced display-product base table")
    add_selection_args(analyze)
    analyze.set_defaults(func=analyze_command)

    analyze_file = subparsers.add_parser("analyze-file", help="compute invariants for a local Cayley table")
    analyze_file.add_argument("table", help="path to a local plain-text or JSON Cayley table")
    analyze_file.set_defaults(func=analyze_file_command)

    submit = subparsers.add_parser("submit", help=f"submit a table; requires ${TOKEN_ENV}")
    submit.add_argument("table", help="path to a local plain-text or JSON Cayley table")
    submit.add_argument("--content-type", choices=["text/plain", "application/json"], default="text/plain")
    submit.set_defaults(func=submit_command)

    comment = subparsers.add_parser("comment", help=f"replace a magma comment; requires ${TOKEN_ENV}")
    comment.add_argument("hash", help="canonical hash or unique prefix")
    comment.add_argument("content", help="replacement comment content")
    comment.set_defaults(func=magma_comment_command)

    size_comment = subparsers.add_parser("size-comment", help=f"replace size commentary; requires ${TOKEN_ENV}")
    size_comment.add_argument("size", type=positive_int)
    size_comment.add_argument("content", help="replacement size commentary")
    size_comment.set_defaults(func=size_comment_command)

    reorder = subparsers.add_parser("display-reorder", help=f"set display reorder; requires ${TOKEN_ENV}")
    reorder.add_argument("hash", help="canonical hash or unique prefix")
    reorder_group = reorder.add_mutually_exclusive_group(required=True)
    reorder_group.add_argument("--display-reorder", help="comma-separated permutation")
    reorder_group.add_argument("--identity", action="store_true", help="clear stored reorder")
    reorder.set_defaults(func=display_reorder_command)

    selftest = subparsers.add_parser("selftest", help="run offline parser and invariant checks")
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
