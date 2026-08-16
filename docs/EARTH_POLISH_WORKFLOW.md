# XCF Earth Polish workflow

`XCF_Earth_Polish` changes only the 42 indexed terrain frames in
`TEXTURE.DAT`. It deliberately contains no `globe:` rule and no custom
palette. X-Com Files therefore remains responsible for polygon-to-terrain
mapping, oceans, borders, cities, markers, lighting, seasons, missions, and
Battlescape terrain selection.

## Pinned input

The source is NASA Earth Observatory's *Blue Marble Next Generation:
Topography and Bathymetry*, January, 5400 x 2700 JPEG. Its URL, dimensions,
and SHA-256 are pinned in
`artwork/source/geoscape/earth-polish/manifest.json`. The downloaded JPEG is
stored below `artwork/cache/`, which is ignored by Git. Derived 512 x 512
biome sources are committed.

The 14 source tiles blend representative regions for northern forest,
plains, temperate mixed terrain, southern forest, savanna, mountains, marshy
forest, sand desert, rock desert, polar mountains, rain forest, tundra, ice
fields, and cold desert. Their sampling coordinates and color grading are
data in the manifest, not hidden tool defaults. Unmistakable ocean-blue pixels
in those land samples are neutralized before blending; polar and ice samples keep
a cold tint. This preprocessing never touches the actual Geoscape ocean.

## Rebuild

Python 3 and Pillow are required. From the repository root:

```powershell
python artwork/tools/build_earth_polish.py --refresh-sources --download
python artwork/tools/audit_earth_polish.py
```

`--download` is only needed when the ignored cache is empty. The build tool
verifies the NASA file's hash before deriving sources. It reads the installed
XCF atlas as the palette authority; override its location with `--baseline`
when the OpenXcom user directory is elsewhere.

The build makes three hybrid variants per biome. Large NASA structures are
removed with a periodic high-pass filter, while the matching XCF frame supplies
a repetition-resistant spatial microtexture. NASA still controls the biome's
mean color and contributes high-frequency detail:

- row 0: near view, 70% XCF detail and 30% NASA detail, used by zoom levels 4 and 5;
- row 1: medium view, 75% XCF and 25% NASA, used by levels 2 and 3;
- row 2: far view, 65% XCF and 35% NASA, used by levels 0 and 1.

The palette luminance spans are 0.70, 0.63, and 0.61 after metric-based
fine-tuning. Only indices already used by the matching biome in XCF's original
three frames are candidates. A deterministically rotated and offset 8 x 8
Bayer pattern is restrained in rows 0 and 1 and disabled in row 2. Opposite
borders are identical after quantization. This preserves `PAL_GEOSCAPE`
day/night shading and compatibility with palette overlays such as Dark
Geoscape; night screenshots are expected to remain dark.

## Audit and runtime checklist

The automated audit checks source size and seams, PNG mode `P`, the 448 x 96
atlas geometry, all 42 frames, a full 256-entry palette, absence of
transparency, palette-index safety, biome distinction, forbidden ruleset
keys, macro variation, neighbor detail, contrast relative to XCF, and a
byte-identical deterministic rebuild. To compare an installed
test copy too, pass:

```powershell
python artwork/tools/audit_earth_polish.py `
  --active-mod "$HOME/OneDrive/Dokumente/OpenXcom/mods/XCF_Earth_Polish"
```

Before a release, test OXCE 8.5 with X-Com Files 4.0 and inspect the log for
new warnings or errors. Compare the same globe position and time across all
six zoom levels at day, dusk, and night; cover representative forest, desert,
mountain, tundra, and ice regions. Repeat with seasons and
`globeSurfaceCache` both enabled and disabled, load `nukunuku01.sav`, begin a
new campaign, and verify unchanged bases, routes, missions, and Battlescape
terrains. Finally activate Dark Geoscape: recoloring is expected, load errors
are not.
