#!/usr/bin/env python3
"""Audit indexed Ufopaedia CPAL PNGs for XCF's reserved palette entries."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image

from convert_cpal import FIXED, FIXED_COLORS, SIZE


def audit(path: Path, forbid_reserved_pixels: bool) -> list[str]:
    problems: list[str] = []
    data = path.read_bytes()
    if len(data) < 26 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return ["not a PNG"]
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    with Image.open(path) as image:
        if (width, height) != SIZE or image.size != SIZE:
            problems.append(f"dimensions {image.size}, expected {SIZE}")
        if bit_depth != 8 or color_type != 3 or image.mode != "P":
            problems.append(
                f"format mode={image.mode}, bit_depth={bit_depth}, color_type={color_type}"
            )
            return problems
        palette = image.getpalette()
        if len(palette) != 768:
            problems.append(f"palette length {len(palette)}, expected 768")
            return problems
        mismatches = []
        for index, expected in FIXED_COLORS.items():
            actual = tuple(palette[index * 3 : index * 3 + 3])
            if actual != expected:
                mismatches.append(index)
        if mismatches:
            problems.append(f"wrong reserved colors at {mismatches}")
        if forbid_reserved_pixels:
            used = set(image.getdata()) & FIXED
            allowed = {0} if image.info.get("transparency") == 0 else set()
            unexpected = sorted(used - allowed)
            if unexpected:
                problems.append(f"reserved indices used by motif: {unexpected}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--forbid-reserved-pixels",
        action="store_true",
        help="also reject reserved indices in image data (index 0 is allowed for transparency)",
    )
    args = parser.parse_args()
    failed = False
    files: list[Path] = []
    for path in args.paths:
        files.extend(sorted(path.rglob("*.png")) if path.is_dir() else [path])
    for path in files:
        problems = audit(path, args.forbid_reserved_pixels)
        if problems:
            failed = True
            print(f"FAIL {path}: {'; '.join(problems)}")
        else:
            print(f"OK   {path}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
