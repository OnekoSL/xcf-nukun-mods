# Arbeitsanweisung: Ufopaedia-Ersatzbilder für XCF

Diese Arbeitsanweisung beschreibt den verbindlichen Ablauf für neue oder
Überarbeitete Ufopaedia-Bilder im Mod `XCF_Ufopaedia_Art`. Ziel sind
OpenXcom-kompatible PNG-Dateien ohne Farbrauschen, falsche UI-Farben oder
Überlagerungen mit dem Artikeltext.

## 1. XCF-Eintrag eindeutig zuordnen

Vor der Bildbearbeitung müssen Artikel, Sprite-ID und Originaldatei eindeutig
ermittelt werden.

1. Den sichtbaren Titel in den XCF-Sprachdateien suchen und die `STR_...`-ID
   notieren.
2. Diese ID in `Ruleset/ufopaedia_XCOMFILES.rul` suchen.
3. Aus dem Artikel folgende Werte notieren:
   - `image_id`
   - `text_width`
   - gegebenenfalls `align_bottom`
4. Die `image_id` in `Ruleset/extraSprites_XCOMFILES.rul` suchen.
5. Dort Originalpfad, `width`, `height` und den exakten Sprite-Typ übernehmen.

Der Sprite-Typ muss einschließlich Groß-/Kleinschreibung und Zusätzen wie
`_CPAL` oder `.SPK` exakt beibehalten werden. Ein Typ mit `.SPK` darf über
`extraSprites` trotzdem auf eine PNG-Datei des Mods zeigen.

## 2. Komposition für den Artikel planen

Ufopaedia-Grafiken sind 320 × 200 Pixel groß. Das generierte Quellbild sollte
bereits ein Seitenverhältnis von 16:10 besitzen.

- Keine Titel, Schaltflächen, Cursor, Beschriftungen oder sonstige UI in das
  Bild generieren.
- Die Artikeldefinition bestimmt die freie Textzone. `text_width` ist die
  Mindestbreite; zusätzlich einen kleinen Sicherheitsabstand vorsehen.
- Bei Autopsien mit `text_width: 150` bleiben aktuell die Pixelspalten
  `x = 0..157` vollständig frei.
- Bei `align_bottom: true` muss besonders die untere Textzone ruhig und
  kontrastarm bleiben.
- Für Artikel mit `text_width: 310` liegt der Text fast über der gesamten
  Grafik. Solche Bilder müssen insgesamt dunkel, kontrastarm und in der Mitte
  wenig detailreich sein.
- Wichtige Gesichter, Objekte und Silhouetten nicht in die Textzone legen.

## 3. Quellbild verkleinern

Das hochauflösende Quellbild proportional auf 320 × 200 bringen. Empfohlen ist
Pillow mit Lanczos-Skalierung:

```python
from PIL import Image, ImageOps

source = Image.open("source.png").convert("RGB")
fitted = ImageOps.fit(
    source,
    (320, 200),
    method=Image.Resampling.LANCZOS,
    centering=(0.5, 0.5),
)
```

Vor dem Skalieren genug Sicherheitsrand im Motiv lassen. Ein nachträglicher
Beschnitt darf keine Köpfe, Gliedmaßen oder wichtigen Geräte abschneiden.

## 4. Palettentyp bestimmen

OpenXcom lädt diese Ufopaedia-Grafiken als indizierte 8-Bit-PNGs. Es gibt zwei
unterschiedliche Konvertierungswege.

### 4.1 Standardpalette

Für Bilder, deren Original die allgemeine XCF-Ufopaedia-Palette verwendet,
wird die vollständige Palette der funktionierenden XCF-Originaldatei
übernommen. Es wird **nicht gedithert**.

Beispiel mit Pillow:

```python
from PIL import Image

original = Image.open(original_path).convert("P")
source = Image.open(source_path).convert("RGB")
palette_source = Image.new("P", (1, 1))
palette_source.putpalette(original.getpalette())
indexed = source.quantize(palette=palette_source, dither=Image.Dither.NONE)
indexed.save(target_path, transparency=original.info.get("transparency"))
```

Dithering erzeugt mit der XCF-Palette oft großflächige Muster sowie einzelne
grüne, violette oder andersfarbige Störpixel. Deshalb niemals
`Image.Dither.FLOYDSTEINBERG` für diese Ersatzbilder verwenden.

### 4.2 Benutzerdefinierte Palette

Bei Bildern mit eigener Palette darf der Bildanteil neu belegt werden. Ob
OpenXcom diese Palette tatsächlich zur Laufzeit verwendet, wird durch den
Sprite-Typ bestimmt. Der Namenszusatz `_CPAL` ist daher verbindlich: Fehlt er,
muss das Ersatzbild mit der normalen Ufopaedia-Palette quantisiert werden,
selbst wenn die eingebettete Palette der Original-PNG davon abweicht.

`FRIENDS_ON_THE_COUNCIL_02` ist der bestätigte Gegencheck: Seine Original-PNG
enthält eine abweichende Palette, der Sprite-Typ besitzt jedoch kein `_CPAL`.
Eine adaptive Palette erzeugt ingame starke Farb- und Rasterfehler; die
Standardpalette wird korrekt dargestellt.

Bestätigte Standardpaletten-Beispiele: `PORSCHE.SPK`, `MUDRANGER.SPK` und
`FRIENDS_ON_THE_COUNCIL_02`. Bestätigte Custom-Paletten-Beispiele:
`POSTAL_DIARY_CPAL`, `CIVILIAN_CAR_CPAL.SPK` und `VAN_CPAL.SPK`.

Weitere bestätigte Tutorial-Beispiele: `UFOPEDIA_IMG_DOSSIERS` und
`CRAFT_EQUIPMENT_TYPES` verwenden die Standardpalette;
`UFOPEDIA_IMG_NEED_TO_KNOW_BASIS_CPAL` und `PILOTS_CPAL` verwenden
eine benutzerdefinierte Palette.

Bestimmte Indizes sind jedoch für Ufopaedia-Text und Bedienelemente reserviert.

Für die aktuell geprüfte XCF-Version bleiben diese 23 Indizes unverändert:

```text
0
81-88
240-249
252-255
```

Die übrigen 233 Indizes erhalten eine adaptive Palette aus dem neuen Bild.
Auch hier wird nicht gedithert.

```python
from PIL import Image

fixed = {0, *range(81, 89), *range(240, 250), *range(252, 256)}
free = [index for index in range(256) if index not in fixed]

original = Image.open("xcf-original-cpal.png").convert("P")
original_flat = original.getpalette()
full_palette = [
    tuple(original_flat[index * 3:index * 3 + 3])
    for index in range(256)
]

adaptive = fitted.quantize(
    colors=len(free),
    method=Image.Quantize.MEDIANCUT,
    dither=Image.Dither.NONE,
)
adaptive_flat = adaptive.getpalette()
used = sorted(set(adaptive.getdata()))
adaptive_colors = [
    tuple(adaptive_flat[index * 3:index * 3 + 3])
    for index in used
]

for slot, color in zip(free, adaptive_colors):
    full_palette[slot] = color

palette_holder = Image.new("P", (1, 1))
palette_holder.putpalette([
    channel
    for color in full_palette
    for channel in color
])

indexed = fitted.quantize(
    palette=palette_holder,
    dither=Image.Dither.NONE,
)
indexed.save("replacement.png", format="PNG", optimize=True)
```

Die reservierten Indizes wurden durch Vergleich von 195 lokalen XCF-CPAL-PNGs
ermittelt. Nach größeren XCF-Updates sollte diese Annahme erneut geprüft werden.

## 5. Transparente Autopsiebilder

Bei den aktuellen Autopsieartikeln ist Palettenindex 0 transparent. Nach dem
Skalieren muss die komplette linke Textfläche auf Schwarz gesetzt werden, damit
sie bei der Quantisierung sicher Index 0 erhält.

```python
for y in range(200):
    for x in range(158):
        fitted.putpixel((x, y), (0, 0, 0))

indexed = fitted.quantize(
    palette=palette_image,
    dither=Image.Dither.NONE,
)
indexed.save(
    "replacement.png",
    format="PNG",
    transparency=0,
    optimize=True,
)
```

Normale ganzflächige Berichtsillustrationen erhalten keine Transparenz, sofern
das jeweilige XCF-Original ebenfalls keine besitzt.

## 6. Ruleset ergänzen

Jedes Ersatzbild wird über die originale Sprite-ID überschrieben:

```yaml
extraSprites:
  - type: ORIGINAL_SPRITE_ID
    singleImage: true
    width: 320
    height: 200
    files:
      0: Resources/Ufopaedia/Example.png
```

Der Dateipfad ist relativ zum Modordner. Nach Änderungen Ruleset und Bilder in
den aktiven Testmod kopieren.

## 7. Technische Prüfung

Windows kann ein indiziertes PNG beim Laden intern als 32-Bit-Bild darstellen.
`System.Drawing.PixelFormat` ist deshalb kein zuverlässiger Nachweis für das
Dateiformat. Entscheidend ist der PNG-IHDR-Header.

```python
from pathlib import Path
from PIL import Image
import struct

path = Path("replacement.png")
data = path.read_bytes()
width, height, bit_depth, color_type = struct.unpack(
    ">IIBB",
    data[16:26],
)

image = Image.open(path)
assert (width, height) == (320, 200)
assert bit_depth == 8
assert color_type == 3       # indizierte Palette
assert image.mode == "P"
assert len(image.getpalette()) == 768
```

Zusätzlich prüfen:

- Transparenz entspricht dem Original.
- Bei Standardbildern stimmt die gesamte Palette mit dem Original überein.
- Bei `_CPAL` stimmen die 23 reservierten UI-Indizes mit dem Original überein.
- Autopsien verwenden in der gesamten linken Textfläche Index 0.
- Alle Ruleset-Pfade verweisen auf vorhandene Dateien.
- Checkout und aktiver Mod enthalten byte-identische Kopien.
- `git diff --check` meldet keine Fehler.

## 8. Ingame-Prüfung

OpenXcom nach jeder Bildänderung vollständig neu starten, da bereits geladene
Ressourcen zwischengespeichert sein können.

Im Spiel kontrollieren:

- keine Abstürze beim öffnen des Artikels;
- keine grünen, violetten oder schachbrettartigen Farbstörungen;
- korrekte Farben von Titel, Text und Schaltflächen;
- gute Lesbarkeit in der tatsächlich verwendeten Sprache;
- keine Überdeckung wichtiger Bilddetails durch Titel oder Fließtext;
- vollständiger Bildausschnitt ohne abgeschnittene Motive.

Erst nach erfolgreichem Ingame-Test committen und pushen.
