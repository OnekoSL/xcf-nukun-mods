#!/usr/bin/env python3
"""Build the deterministic XCF Earth Polish texture atlas.

The raw NASA image is cached but never committed. Derived 512 px biome source
tiles and the palette-indexed game atlas are deterministic build products.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageStat


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "artwork/source/geoscape/earth-polish/manifest.json"
DEFAULT_CACHE = REPO_ROOT / "artwork/cache/earth-polish"
DEFAULT_BASELINE = Path.home() / "OneDrive/Dokumente/OpenXcom/mods/XComFiles/Resources/Geoscape/XCF_GLOBE_TEXTURE.png"
DEFAULT_ATLAS = REPO_ROOT / "mods/XCF_Earth_Polish/Resources/Geoscape/XCF_EARTH_POLISH_TEXTURE.png"
BAYER_8 = (
    (0, 32, 8, 40, 2, 34, 10, 42),
    (48, 16, 56, 24, 50, 18, 58, 26),
    (12, 44, 4, 36, 14, 46, 6, 38),
    (60, 28, 52, 20, 62, 30, 54, 22),
    (3, 35, 11, 43, 1, 33, 9, 41),
    (51, 19, 59, 27, 49, 17, 57, 25),
    (15, 47, 7, 39, 13, 45, 5, 37),
    (63, 31, 55, 23, 61, 29, 53, 21),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 2:
        raise ValueError("Earth Polish manifest schema must be 2")
    biome_ids = [entry["id"] for entry in manifest["biomes"]]
    if biome_ids != list(range(14)):
        raise ValueError("Manifest biome IDs must be exactly 0 through 13")
    profiles = manifest.get("zoomProfiles", [])
    if [profile.get("name") for profile in profiles] != ["near", "medium", "far"]:
        raise ValueError("Manifest zoom profiles must be near, medium, and far")
    if [profile.get("row") for profile in profiles] != [0, 1, 2]:
        raise ValueError("Manifest zoom profile rows must be 0, 1, and 2")
    for profile in profiles:
        if abs(profile["xcfDetailWeight"] + profile["nasaDetailWeight"] - 1.0) > 1e-9:
            raise ValueError(f"Zoom profile weights must sum to 1: {profile['name']}")
        for key in ("xcfDetailWeight", "nasaDetailWeight", "lumaSpan"):
            if not 0.0 <= profile[key] <= 1.0:
                raise ValueError(f"Zoom profile {key} outside 0..1: {profile['name']}")
        if profile["highPassRadius"] <= 0.0 or profile["ditherStrength"] < 0.0:
            raise ValueError(f"Invalid zoom filter setting: {profile['name']}")
    return manifest


def ensure_nasa_source(manifest: dict, cache_dir: Path, download: bool) -> Path:
    source = manifest["source"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / source["cacheFile"]
    if not path.exists():
        if not download:
            raise FileNotFoundError(
                f"NASA source not found at {path}; rerun with --download"
            )
        print(f"Downloading {source['downloadUrl']}")
        urllib.request.urlretrieve(source["downloadUrl"], path)
    actual_hash = sha256(path)
    if actual_hash != source["sha256"]:
        raise ValueError(f"NASA source SHA-256 mismatch: {actual_hash}")
    with Image.open(path) as image:
        if image.size != (source["width"], source["height"]):
            raise ValueError(f"NASA source has unexpected dimensions {image.size}")
    return path


def wrapped_crop(world: Image.Image, lon: float, lat: float, span: float) -> Image.Image:
    width, height = world.size
    size = max(8, round(span * width / 360.0))
    center_x = (lon + 180.0) / 360.0 * width
    center_y = (90.0 - lat) / 180.0 * height
    left = round(center_x - size / 2)
    top = round(center_y - size / 2)
    tripled = Image.new("RGB", (width * 3, height))
    tripled.paste(world, (0, 0))
    tripled.paste(world, (width, 0))
    tripled.paste(world, (width * 2, 0))
    left += width
    top = max(0, min(height - size, top))
    return tripled.crop((left, top, left + size, top + size))


def make_seamless(image: Image.Image, band: int) -> Image.Image:
    result = image.copy().convert("RGB")
    pixels = result.load()
    width, height = result.size
    band = min(band, width // 3, height // 3)
    for offset in range(band):
        strength = ((band - offset) / band) ** 2
        left_x = offset
        right_x = width - 1 - offset
        for y in range(height):
            left = pixels[left_x, y]
            right = pixels[right_x, y]
            average = tuple((left[c] + right[c]) // 2 for c in range(3))
            pixels[left_x, y] = tuple(
                round(left[c] * (1.0 - strength) + average[c] * strength)
                for c in range(3)
            )
            pixels[right_x, y] = tuple(
                round(right[c] * (1.0 - strength) + average[c] * strength)
                for c in range(3)
            )
    for offset in range(band):
        strength = ((band - offset) / band) ** 2
        top_y = offset
        bottom_y = height - 1 - offset
        for x in range(width):
            top = pixels[x, top_y]
            bottom = pixels[x, bottom_y]
            average = tuple((top[c] + bottom[c]) // 2 for c in range(3))
            pixels[x, top_y] = tuple(
                round(top[c] * (1.0 - strength) + average[c] * strength)
                for c in range(3)
            )
            pixels[x, bottom_y] = tuple(
                round(bottom[c] * (1.0 - strength) + average[c] * strength)
                for c in range(3)
            )
    # Force exact periodic borders after the soft transition.
    for y in range(height):
        pixels[width - 1, y] = pixels[0, y]
    for x in range(width):
        pixels[x, height - 1] = pixels[x, 0]
    return result


def suppress_ocean(image: Image.Image, biome_id: int) -> Image.Image:
    """Remove unmistakable ocean blue from samples used as land textures."""
    result = image.copy().convert("RGB")
    pixels = result.load()
    polar = biome_id in (9, 12)
    for y in range(result.height):
        for x in range(result.width):
            red, green, blue = pixels[x, y]
            if blue > 25 and blue - red > 8 and blue > red * 1.15 and blue > green * 1.06:
                value = 0.2126 * red + 0.7152 * green + 0.0722 * blue
                if polar:
                    pixels[x, y] = (
                        min(255, round(value * 0.94)),
                        min(255, round(value * 1.00)),
                        min(255, round(value * 1.08)),
                    )
                else:
                    pixels[x, y] = (
                        min(255, round(value * 0.82)),
                        min(255, round(value * 0.92)),
                        min(255, round(value * 0.66)),
                    )
    return result


def grade_biome(image: Image.Image, biome: dict) -> Image.Image:
    multipliers = biome["color"]
    lut = []
    for channel in range(3):
        lut.extend(min(255, round(value * multipliers[channel])) for value in range(256))
    result = image.point(lut)
    result = ImageEnhance.Color(result).enhance(1.10)
    result = ImageEnhance.Contrast(result).enhance(biome["contrast"])
    result = ImageEnhance.Brightness(result).enhance(biome["brightness"])
    return result


def create_biome_sources(manifest: dict, nasa_path: Path, output_dir: Path) -> None:
    size = manifest["sourceSize"]
    seed = manifest["generatorSeed"]
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(nasa_path) as opened:
        world = opened.convert("RGB")
    for biome in manifest["biomes"]:
        rng = random.Random(seed + biome["id"] * 104729)
        combined = None
        for index, (lon, lat, span) in enumerate(biome["samples"]):
            sample = wrapped_crop(world, lon, lat, span).resize(
                (size, size), Image.Resampling.LANCZOS
            )
            # Fixed quarter-turns diversify repeated geographic structures.
            sample = sample.rotate(90 * rng.randrange(4))
            sample = suppress_ocean(sample, biome["id"])
            combined = sample if combined is None else Image.blend(
                combined, sample, 1.0 / (index + 1)
            )
        assert combined is not None
        combined = grade_biome(combined, biome)
        combined = make_seamless(combined, 72)
        path = output_dir / f"{biome['id']:02d}_{biome['slug']}_source.png"
        combined.save(path, format="PNG", optimize=False, compress_level=9)
        print(f"Wrote {path.relative_to(REPO_ROOT)}")


def palette_data(baseline: Image.Image) -> tuple[list[int], list[tuple[int, int, int]]]:
    raw = list(baseline.getpalette() or [])
    raw.extend([0] * (768 - len(raw)))
    raw = raw[:768]
    colors = [tuple(raw[index:index + 3]) for index in range(0, 768, 3)]
    return raw, colors


def candidate_indices(baseline: Image.Image, biome_id: int) -> list[int]:
    indices: set[int] = set()
    for row in range(3):
        tile = baseline.crop((biome_id * 32, row * 32, biome_id * 32 + 32, row * 32 + 32))
        indices.update(tile.getdata())
    return sorted(indices)


def periodic_blur(image: Image.Image, radius: float) -> Image.Image:
    width, height = image.size
    tiled = Image.new(image.mode, (width * 3, height * 3))
    for tile_y in range(3):
        for tile_x in range(3):
            tiled.paste(image, (tile_x * width, tile_y * height))
    blurred = tiled.filter(ImageFilter.GaussianBlur(radius=radius))
    return blurred.crop((width, height, width * 2, height * 2))


def normalized_detail(image: Image.Image, radius: float) -> list[float]:
    gray = image.convert("L")
    low = periodic_blur(gray, radius)
    values = [float(value) - float(base) for value, base in zip(gray.getdata(), low.getdata())]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    deviation = max(variance ** 0.5, 1.0)
    return [(value - mean) / deviation for value in values]


def make_zoom_tile(
    source: Image.Image,
    baseline_tile: Image.Image,
    profile: dict,
    biome_id: int,
    seed: int,
) -> Image.Image:
    rng = random.Random(seed + biome_id * 4099 + profile["row"] * 131)
    shifted = ImageChops.offset(source, rng.randrange(source.width), rng.randrange(source.height))
    satellite = shifted.resize((32, 32), Image.Resampling.LANCZOS)
    satellite_low = periodic_blur(satellite, profile["highPassRadius"])
    nasa_detail = normalized_detail(satellite, profile["highPassRadius"])
    xcf_detail = normalized_detail(baseline_tile.convert("RGB"), 1.5)
    mean_color = ImageStat.Stat(satellite).mean
    mean_luma = 0.2126 * mean_color[0] + 0.7152 * mean_color[1] + 0.0722 * mean_color[2]

    satellite_pixels = list(satellite.getdata())
    satellite_low_pixels = list(satellite_low.getdata())
    output = Image.new("RGB", (32, 32))
    output_pixels = output.load()
    for index, (satellite_rgb, low_rgb) in enumerate(zip(satellite_pixels, satellite_low_pixels)):
        hybrid = (
            profile["xcfDetailWeight"] * xcf_detail[index]
            + profile["nasaDetailWeight"] * nasa_detail[index]
        )
        hybrid = max(-2.5, min(2.5, hybrid))
        target_luma = mean_luma + 28.0 * hybrid
        x = index % 32
        y = index // 32
        output_pixels[x, y] = tuple(
            max(
                0,
                min(
                    255,
                    round(
                        mean_color[channel]
                        + (target_luma - mean_luma)
                        + 0.25 * (satellite_rgb[channel] - low_rgb[channel])
                    ),
                ),
            )
            for channel in range(3)
        )
    return make_seamless(output, 2)


def bayer_adjustment(
    x: int,
    y: int,
    strength: float,
    biome_id: int,
    row: int,
    seed: int,
) -> float:
    if strength == 0.0:
        return 0.0
    rng = random.Random(seed + biome_id * 65537 + row * 8191)
    offset_x = rng.randrange(8)
    offset_y = rng.randrange(8)
    rotation = rng.randrange(4)
    bx = (x + offset_x) % 8
    by = (y + offset_y) % 8
    for _ in range(rotation):
        bx, by = 7 - by, bx
    return (BAYER_8[by][bx] - 31.5) * (strength / 8.0)


def quantize_tile(
    tile: Image.Image,
    candidates: list[int],
    colors: list[tuple[int, int, int]],
    profile: dict,
    biome_id: int,
    seed: int,
) -> Image.Image:
    output = Image.new("P", tile.size)
    source_pixels = tile.load()
    output_pixels = output.load()

    def luminance(rgb: tuple[int, int, int]) -> float:
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

    source_luma = sorted(luminance(pixel) for pixel in tile.getdata())
    source_low = source_luma[len(source_luma) // 10]
    source_high = source_luma[len(source_luma) * 9 // 10]
    if source_high <= source_low:
        source_high = source_low + 1.0
    candidate_luma = {index: luminance(colors[index]) for index in candidates}
    palette_low = min(candidate_luma.values())
    palette_high = max(candidate_luma.values())
    luma_span = profile["lumaSpan"]

    cache: dict[tuple[tuple[int, int, int], int], int] = {}
    for y in range(tile.height):
        for x in range(tile.width):
            rgb = source_pixels[x, y]
            adjustment = bayer_adjustment(
                x,
                y,
                profile["ditherStrength"],
                biome_id,
                profile["row"],
                seed,
            )
            target = tuple(max(0, min(255, round(value + adjustment))) for value in rgb)
            normalized = max(
                0.0,
                min(1.0, (luminance(target) - source_low) / (source_high - source_low)),
            )
            normalized = 0.5 + (normalized - 0.5) * luma_span
            mapped_luma = palette_low + normalized * (palette_high - palette_low)
            cache_key = (target, round(mapped_luma))
            if cache_key not in cache:
                cache[cache_key] = min(
                    candidates,
                    key=lambda index: (
                        3 * (colors[index][0] - target[0]) ** 2
                        + 4 * (colors[index][1] - target[1]) ** 2
                        + 2 * (colors[index][2] - target[2]) ** 2
                        + 35 * (candidate_luma[index] - mapped_luma) ** 2
                    ),
                )
            output_pixels[x, y] = cache[cache_key]
    # Preserve exact periodic borders after palette mapping and dithering.
    for y in range(tile.height):
        output_pixels[tile.width - 1, y] = output_pixels[0, y]
    for x in range(tile.width):
        output_pixels[x, tile.height - 1] = output_pixels[x, 0]
    return output

def build_atlas(manifest: dict, baseline_path: Path, source_dir: Path, atlas_path: Path) -> None:
    with Image.open(baseline_path) as opened:
        if opened.mode != "P" or opened.size != (448, 96):
            raise ValueError("Baseline XCF atlas must be a 448x96 indexed PNG")
        baseline = opened.copy()
    palette, colors = palette_data(baseline)
    atlas = Image.new("P", (448, 96))
    atlas.putpalette(palette)
    seed = manifest["generatorSeed"]
    for profile in manifest["zoomProfiles"]:
        row = profile["row"]
        for biome in manifest["biomes"]:
            source_path = source_dir / f"{biome['id']:02d}_{biome['slug']}_source.png"
            with Image.open(source_path) as opened:
                source = opened.convert("RGB")
            if source.size != (512, 512):
                raise ValueError(f"Unexpected source size for {source_path}: {source.size}")
            baseline_tile = baseline.crop(
                (biome["id"] * 32, row * 32, biome["id"] * 32 + 32, row * 32 + 32)
            )
            rgb_tile = make_zoom_tile(source, baseline_tile, profile, biome["id"], seed)
            indices = candidate_indices(baseline, biome["id"])
            tile = quantize_tile(rgb_tile, indices, colors, profile, biome["id"], seed)
            atlas.paste(tile, (biome["id"] * 32, row * 32))
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(atlas_path, format="PNG", optimize=False, compress_level=9)
    print(f"Wrote {atlas_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--atlas", type=Path, default=DEFAULT_ATLAS)
    parser.add_argument("--refresh-sources", action="store_true")
    parser.add_argument("--download", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    source_dir = args.manifest.parent
    if args.refresh_sources:
        nasa_path = ensure_nasa_source(manifest, args.cache, args.download)
        create_biome_sources(manifest, nasa_path, source_dir)
    build_atlas(manifest, args.baseline, source_dir, args.atlas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
