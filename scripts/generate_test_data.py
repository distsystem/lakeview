"""Build Lance fixtures for lakeview development and benchmarking.

Usage:
    pixi run python scripts/generate_test_data.py --target sample-data
    pixi run python scripts/generate_test_data.py --target s3://srgdata/lakeview --fixture all
    pixi run python scripts/generate_test_data.py --target s3://srgdata/lakeview --fixture fake_runs --size 50000

Fixtures:
    fake_runs    — agent_run schema (session_id, correct, error, messages, ...)
    blob_images  — Lance Blob V2 column with small PNG images

The script is idempotent per fixture (overwrites existing dataset at the
target path). S3 writes rely on AWS_* env vars in the caller's shell.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import uuid
from typing import Callable

import lance
import pyarrow as pa
from PIL import Image, ImageDraw


def _default_target() -> str | None:
    bucket = os.environ.get("S3_BUCKET")
    prefix = os.environ.get("S3_PREFIX")
    if bucket and prefix:
        return f"s3://{bucket}/{prefix}"
    return None


# -- fake_runs fixture --------------------------------------------------------


def _fake_runs_table(n: int) -> pa.Table:
    sessions = [str(uuid.uuid4()) for _ in range(n)]
    corrects = [
        (True if i % 3 == 0 else False if i % 3 == 1 else None) for i in range(n)
    ]
    errors = [None if i % 10 else f"oom at step {i}" for i in range(n)]
    messages = [
        [
            {"kind": "user", "parts": [{"content": "q", "part_kind": "text"}]},
            {
                "kind": "assistant",
                "parts": [{"content": "a" * 500, "part_kind": "text"}],
            },
        ]
        for _ in range(n)
    ]
    schema = pa.schema(
        [
            pa.field("session_id", pa.string()),
            pa.field("correct", pa.bool_(), nullable=True),
            pa.field("error", pa.string(), nullable=True),
            pa.field("output", pa.struct([pa.field("answer", pa.int64())])),
            pa.field("metadata", pa.struct([pa.field("slug", pa.string())])),
            pa.field(
                "messages",
                pa.list_(
                    pa.struct(
                        [
                            pa.field("kind", pa.string()),
                            pa.field(
                                "parts",
                                pa.list_(
                                    pa.struct(
                                        [
                                            pa.field("content", pa.string()),
                                            pa.field("part_kind", pa.string()),
                                        ]
                                    )
                                ),
                            ),
                        ]
                    )
                ),
            ),
        ]
    )
    return pa.Table.from_arrays(
        [
            pa.array(sessions, pa.string()),
            pa.array(corrects, pa.bool_()),
            pa.array(errors, pa.string()),
            pa.array([{"answer": i} for i in range(n)]),
            pa.array([{"slug": f"problem-{i}"} for i in range(n)]),
            pa.array(messages),
        ],
        schema=schema,
    )


# -- blob_images fixture ------------------------------------------------------


def _png(label: str, color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (256, 256), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([8, 8, 247, 247], outline=(255, 255, 255), width=4)
    draw.text((32, 112), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _blob_images_table(_n: int) -> pa.Table:
    rows = [
        ("red square", (220, 60, 60), "red.png"),
        ("green square", (60, 180, 100), "green.png"),
        ("blue square", (60, 120, 220), "blue.png"),
        ("yellow square", (240, 200, 50), "yellow.png"),
        ("purple square", (160, 80, 200), "purple.png"),
    ]
    schema = pa.schema(
        [
            pa.field("id", pa.uint64()),
            pa.field("filename", pa.string()),
            pa.field("caption", pa.string()),
            pa.field(
                "image",
                pa.large_binary(),
                metadata={"lance-encoding:blob": "true"},
            ),
        ]
    )
    return pa.table(
        [
            pa.array(range(len(rows)), pa.uint64()),
            pa.array([r[2] for r in rows], pa.string()),
            pa.array([r[0] for r in rows], pa.string()),
            pa.array([_png(r[0], r[1]) for r in rows], pa.large_binary()),
        ],
        schema=schema,
    )


# -- Driver -------------------------------------------------------------------


FIXTURES: dict[str, tuple[Callable[[int], pa.Table], int]] = {
    "fake_runs": (_fake_runs_table, 1000),
    "blob_images": (_blob_images_table, 5),
}


def build(fixture: str, target: str, size: int) -> None:
    build_fn, default_size = FIXTURES[fixture]
    table = build_fn(size or default_size)
    path = f"{target.rstrip('/')}/{fixture}.lance"
    lance.write_dataset(table, path, mode="overwrite")
    print(f"  wrote {fixture}: {path} ({table.num_rows} rows)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default=_default_target(),
        help=(
            "Base directory or URI (default: s3://$S3_BUCKET/$S3_PREFIX when "
            "both env vars are set; otherwise required)"
        ),
    )
    parser.add_argument(
        "--fixture",
        default="all",
        choices=["all", *FIXTURES],
        help="Which fixture to build (default: all)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=0,
        help="Row count for size-parameterized fixtures (default: per-fixture)",
    )
    args = parser.parse_args()
    if not args.target:
        parser.error(
            "--target is required (or set both S3_BUCKET and S3_PREFIX in the env)"
        )

    fixtures = list(FIXTURES) if args.fixture == "all" else [args.fixture]
    print(f"target: {args.target}")
    for name in fixtures:
        build(name, args.target, args.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
