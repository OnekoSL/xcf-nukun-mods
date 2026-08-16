#!/usr/bin/env python3
"""Audit XCF Earth Polish sources, atlas, rules, and reproducibility."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOD = REPO_ROOT / "mods/XCF_Earth_Polish"
DEFAULT_MANIFEST = REPO_ROOT / "artwork/source/geoscape/earth-polish/manifest.json"
DEFAULT_BASELINE = Path.home() / "OneDrive/Dokumente/OpenXcom/mods/XComFiles/Resources/Geoscape/XCF_GLOBE_TEXTURE.png"
DEFAULT_ACTIVE = Path.home() / "OneDrive/Dokumente/OpenXcom/mods/XCF_Earth_Polish"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_builder():
    path = Path(__file__).with_name("build_earth_polish.py")
    spec = importlib.util.spec_from_file_location("build_earth_polish", path)
    require(spec is not None and spec.loader is not None, "Cannot load build tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_periodic(image: Image.Image, label: str) -> None:
    left = image.crop((0, 0, 1, image.height))
    right = image.crop((image.width - 1, 0, image.width, image.height))
    top = image.crop((0, 0, image.width, 1))
    bottom = image.crop((0, image.height - 1, image.width, image.height))
    require(ImageChops.difference(left, right).getbbox() is None, f"{label}: left/right seam")
    require(ImageChops.difference(top, bottom).getbbox() is None, f"{label}: top/bottom seam")


def texture_metrics(image: Image.Image) -> tuple[float, float, float]:
    gray = image.convert("L")
    macro = ImageStat.Stat(gray.filter(ImageFilter.GaussianBlur(3))).stddev[0]
    horizontal = ImageChops.difference(
        gray.crop((1, 0, gray.width, gray.height)),
        gray.crop((0, 0, gray.width - 1, gray.height)),
    )
    vertical = ImageChops.difference(
        gray.crop((0, 1, gray.width, gray.height)),
        gray.crop((0, 0, gray.width, gray.height - 1)),
    )
    neighbor = (ImageStat.Stat(horizontal).mean[0] + ImageStat.Stat(vertical).mean[0]) / 2.0
    contrast = ImageStat.Stat(gray).stddev[0]
    return macro, neighbor, contrast


def compare_trees(expected: Path, actual: Path) -> None:
    expected_files = sorted(path.relative_to(expected) for path in expected.rglob("*") if path.is_file())
    actual_files = sorted(path.relative_to(actual) for path in actual.rglob("*") if path.is_file())
    require(expected_files == actual_files, "Repository and active mod file lists differ")
    for relative in expected_files:
        require(
            digest(expected / relative) == digest(actual / relative),
            f"Repository and active mod differ: {relative}",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, default=DEFAULT_MOD)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--active-mod", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    builder = load_builder()
    source_dir = args.manifest.parent
    atlas_path = args.mod / "Resources/Geoscape/XCF_EARTH_POLISH_TEXTURE.png"
    rules_path = args.mod / "Ruleset/extraSprites.rul"
    metadata_path = args.mod / "metadata.yml"

    require(manifest.get("schema") == 2, "Manifest schema must be 2")
    require(
        [profile.get("name") for profile in manifest.get("zoomProfiles", [])]
        == ["near", "medium", "far"],
        "Manifest must define near, medium, and far zoom profiles",
    )
    require(len(manifest["biomes"]) == 14, "Manifest must contain 14 biomes")
    for biome in manifest["biomes"]:
        path = source_dir / f"{biome['id']:02d}_{biome['slug']}_source.png"
        require(path.is_file(), f"Missing biome source: {path}")
        with Image.open(path) as source:
            require(source.mode == "RGB", f"{path.name}: expected RGB mode")
            require(source.size == (512, 512), f"{path.name}: expected 512x512")
            assert_periodic(source, path.name)

    require(rules_path.is_file(), "Missing ruleset")
    require(metadata_path.is_file(), "Missing metadata")
    rules = rules_path.read_text(encoding="utf-8")
    metadata = metadata_path.read_text(encoding="utf-8")
    require("Resources/Geoscape/XCF_EARTH_POLISH_TEXTURE.png" in rules, "Ruleset atlas path missing")
    require('requiredExtendedVersion: "8.5"' in metadata, "Wrong OXCE requirement")
    require('version: "0.2.0"' in metadata, "Wrong Earth Polish version")
    require("master: x-com-files" in metadata, "Wrong master")
    lower_rules = rules.lower()
    for forbidden in ("globe:", "custompalettes:", "world.dat", "globemarkers"):
        require(forbidden not in lower_rules, f"Forbidden ruleset key: {forbidden}")

    with Image.open(args.baseline) as opened:
        require(opened.mode == "P" and opened.size == (448, 96), "Invalid baseline atlas")
        baseline = opened.copy()
    allowed = set(baseline.getdata())
    with Image.open(atlas_path) as opened:
        require(opened.mode == "P", "Atlas must use PNG mode P")
        require(opened.size == (448, 96), "Atlas must be 448x96")
        require("transparency" not in opened.info, "Atlas must not contain transparency")
        palette = opened.getpalette() or []
        require(len(palette) == 768, "Atlas must contain 256 palette entries")
        atlas = opened.copy()
    require(448 // 32 * (96 // 32) == 42, "Atlas geometry must contain 42 frames")
    require(set(atlas.getdata()) <= allowed, "Atlas uses indices outside the XCF-safe set")

    row_tiles: list[list[Image.Image]] = []
    baseline_row_tiles: list[list[Image.Image]] = []
    for row in range(3):
        row_data = []
        baseline_data = []
        hashes: set[str] = set()
        for biome in range(14):
            tile = atlas.crop((biome * 32, row * 32, biome * 32 + 32, row * 32 + 32))
            assert_periodic(tile, f"atlas row {row}, biome {biome}")
            candidates = set(builder.candidate_indices(baseline, biome))
            require(set(tile.getdata()) <= candidates, f"Biome {biome} uses unsafe indices")
            tile_hash = hashlib.sha256(tile.tobytes()).hexdigest()
            require(tile_hash not in hashes, f"Duplicate biome tile in row {row}")
            hashes.add(tile_hash)
            row_data.append(tile.convert("RGB"))
            baseline_data.append(
                baseline.crop((biome * 32, row * 32, biome * 32 + 32, row * 32 + 32)).convert("RGB")
            )
        row_tiles.append(row_data)
        baseline_row_tiles.append(baseline_data)

    # Texture difference, not merely mean hue: every biome pair must differ visibly.
    for row, tiles in enumerate(row_tiles):
        minimum_rms = 255.0
        for left in range(14):
            for right in range(left + 1, 14):
                rms = sum(ImageStat.Stat(ImageChops.difference(tiles[left], tiles[right])).rms) / 3.0
                minimum_rms = min(minimum_rms, rms)
        require(minimum_rms >= 3.0, f"Biome distinction too low in row {row}: RMS {minimum_rms:.2f}")

    for row, (tiles, baseline_tiles) in enumerate(zip(row_tiles, baseline_row_tiles)):
        output_metrics = [texture_metrics(tile) for tile in tiles]
        baseline_metrics = [texture_metrics(tile) for tile in baseline_tiles]
        output_macro = sum(metric[0] for metric in output_metrics) / 14.0
        baseline_macro = sum(metric[0] for metric in baseline_metrics) / 14.0
        require(
            output_macro <= baseline_macro * 1.6,
            f"Row {row}: macro variation {output_macro:.2f} exceeds 1.6x XCF ({baseline_macro:.2f})",
        )
        for biome, (output_metric, baseline_metric) in enumerate(zip(output_metrics, baseline_metrics)):
            macro_limit = max(5.0, baseline_metric[0] * 2.0)
            require(
                output_metric[0] <= macro_limit,
                f"Row {row}, biome {biome}: macro variation {output_metric[0]:.2f} exceeds {macro_limit:.2f}",
            )
        output_neighbor = sum(metric[1] for metric in output_metrics) / 14.0
        baseline_neighbor = sum(metric[1] for metric in baseline_metrics) / 14.0
        neighbor_ratio = output_neighbor / baseline_neighbor
        require(
            0.70 <= neighbor_ratio <= 1.50,
            f"Row {row}: neighbor variation ratio outside 0.70..1.50: {neighbor_ratio:.3f}",
        )
        output_contrast = sum(metric[2] for metric in output_metrics) / 14.0
        baseline_contrast = sum(metric[2] for metric in baseline_metrics) / 14.0
        contrast_ratio = output_contrast / baseline_contrast
        require(
            0.50 <= contrast_ratio <= 1.35,
            f"Row {row}: contrast ratio outside 0.50..1.35: {contrast_ratio:.3f}",
        )
        print(
            f"PASS: row {row} macro={output_macro:.2f}, "
            f"neighbor={neighbor_ratio:.3f}x XCF, contrast={contrast_ratio:.3f}x XCF"
        )

    with tempfile.TemporaryDirectory(prefix="xcf-earth-polish-") as temp_dir:
        rebuilt = Path(temp_dir) / atlas_path.name
        builder.build_atlas(manifest, args.baseline, source_dir, rebuilt)
        require(digest(rebuilt) == digest(atlas_path), "Atlas build is not byte-deterministic")

    if args.active_mod is not None:
        require(args.active_mod.is_dir(), f"Active mod not found: {args.active_mod}")
        compare_trees(args.mod, args.active_mod)

    print("PASS: 14 seamless sources, 42 indexed frames, safe palette, deterministic build")
    if args.active_mod is not None:
        print("PASS: repository and active mod are byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
