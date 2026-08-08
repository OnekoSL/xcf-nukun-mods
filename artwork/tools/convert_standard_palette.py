#!/usr/bin/env python3
"""Convert a Ufopaedia source image with an exact XCF donor palette."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image, ImageOps


SIZE = (320, 200)


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
    donor_path: Path,
    output_path: Path,
    preview_path: Path | None,
) -> None:
    fitted = fit_source(source_path)
    if preview_path:
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        fitted.save(preview_path, format="PNG", optimize=True)

    with Image.open(donor_path) as donor:
        if donor.mode != "P" or donor.size != SIZE:
            raise ValueError("donor must be a 320x200 indexed PNG")
        donor_palette = donor.getpalette()
        if donor_palette is None or len(donor_palette) != 768:
            raise ValueError("donor does not contain a 256-color palette")
        palette_image = donor.copy()

    indexed = fitted.quantize(
        palette=palette_image,
        dither=Image.Dither.NONE,
    )
    indexed.putpalette(donor_palette, rawmode="RGB")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    indexed.save(output_path, format="PNG", optimize=True)
    validate(output_path, donor_path)


def validate(path: Path, donor_path: Path) -> None:
    data = path.read_bytes()
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    with Image.open(path) as image, Image.open(donor_path) as donor:
        if (width, height) != SIZE or image.size != SIZE:
            raise ValueError(f"wrong dimensions: {image.size}")
        if bit_depth != 8 or color_type != 3 or image.mode != "P":
            raise ValueError("output is not an indexed 8-bit PNG")
        if image.getpalette() != donor.getpalette():
            raise ValueError("output palette differs from donor palette")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("donor", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    convert(args.source, args.donor, args.output, args.preview)


if __name__ == "__main__":
    main()
