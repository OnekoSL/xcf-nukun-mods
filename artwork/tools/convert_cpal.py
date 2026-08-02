#!/usr/bin/env python3
"""Convert one Ufopaedia source image to XCF's safe sparse CPAL layout."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image, ImageOps


SIZE = (320, 200)
FIXED_COLORS = {
    0: (0, 0, 0),
    81: (224, 224, 240),
    82: (212, 212, 232),
    83: (204, 204, 224),
    84: (196, 192, 220),
    85: (184, 184, 212),
    86: (176, 172, 204),
    87: (164, 160, 196),
    88: (156, 152, 188),
    240: (156, 148, 188),
    241: (124, 120, 148),
    242: (92, 92, 108),
    243: (60, 60, 68),
    244: (28, 28, 32),
    245: (140, 204, 184),
    246: (104, 164, 152),
    247: (72, 124, 120),
    248: (44, 80, 84),
    249: (20, 40, 44),
    252: (252, 252, 164),
    253: (220, 232, 140),
    254: (192, 212, 120),
    255: (164, 192, 104),
}
FIXED = frozenset(FIXED_COLORS)
FREE = tuple(index for index in range(256) if index not in FIXED)


def fit_source(path: Path) -> Image.Image:
    with Image.open(path) as source:
        return ImageOps.fit(
            source.convert("RGB"),
            SIZE,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )


def convert(
    source_path: Path,
    output_path: Path,
    preview_path: Path | None,
    transparent_left: int,
) -> None:
    fitted = fit_source(source_path)
    if preview_path:
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        fitted.save(preview_path, format="PNG", optimize=True)

    adaptive = fitted.quantize(
        colors=len(FREE),
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    adaptive_palette = adaptive.getpalette()

    full_palette = [(0, 0, 0)] * 256
    for index, color in FIXED_COLORS.items():
        full_palette[index] = color
    for adaptive_index, target_index in enumerate(FREE):
        offset = adaptive_index * 3
        full_palette[target_index] = tuple(adaptive_palette[offset : offset + 3])

    remap = bytes(FREE[index] for index in range(len(FREE)))
    indexed = Image.frombytes(
        "P",
        SIZE,
        bytes(remap[index] for index in adaptive.getdata()),
    )
    indexed.putpalette(
        [channel for color in full_palette for channel in color],
        rawmode="RGB",
    )

    if transparent_left:
        if not 0 <= transparent_left <= SIZE[0]:
            raise ValueError("--transparent-left must be between 0 and 320")
        pixels = bytearray(indexed.tobytes())
        for y in range(SIZE[1]):
            start = y * SIZE[0]
            pixels[start : start + transparent_left] = b"\x00" * transparent_left
        indexed = Image.frombytes("P", SIZE, bytes(pixels))
        indexed.putpalette(
            [channel for color in full_palette for channel in color],
            rawmode="RGB",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_args = {"format": "PNG", "optimize": True}
    if transparent_left:
        save_args["transparency"] = 0
    indexed.save(output_path, **save_args)
    validate(output_path, allow_transparency=bool(transparent_left))


def validate(path: Path, allow_transparency: bool) -> None:
    data = path.read_bytes()
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    with Image.open(path) as image:
        if (width, height) != SIZE or image.size != SIZE:
            raise ValueError(f"wrong dimensions: {image.size}")
        if bit_depth != 8 or color_type != 3 or image.mode != "P":
            raise ValueError("output is not an indexed 8-bit PNG")
        palette = image.getpalette()
        if len(palette) != 768:
            raise ValueError("output does not contain a 256-color palette")
        for index, expected in FIXED_COLORS.items():
            actual = tuple(palette[index * 3 : index * 3 + 3])
            if actual != expected:
                raise ValueError(f"reserved index {index}: {actual} != {expected}")
        used_reserved = set(image.getdata()) & FIXED
        allowed = {0} if allow_transparency else set()
        unexpected = used_reserved - allowed
        if unexpected:
            raise ValueError(f"reserved indices used by motif: {sorted(unexpected)}")
        if allow_transparency and image.info.get("transparency") != 0:
            raise ValueError("index 0 transparency is missing")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument(
        "--transparent-left",
        type=int,
        default=0,
        metavar="PIXELS",
        help="set this many left columns to transparent palette index 0",
    )
    args = parser.parse_args()
    convert(args.source, args.output, args.preview, args.transparent_left)


if __name__ == "__main__":
    main()
