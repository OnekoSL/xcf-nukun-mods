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

Die neuen Tutorial-Sprites `UFOPEDIA_IMG_TRANSFORMATIONS`,
`UFOPEDIA_IMG_RETREAT`, `UFOPEDIA_IMG_OVERSTUN` und `UFOPEDIA_IMG_CAMO`
verwenden ebenfalls die Standardpalette.

Weitere gepruefte Tutorial-Sprites: `UFOPEDIA_IMG_OUTDATED_WEAPONS_CPAL`,
`UFOPEDIA_IMG_MISSIONS_AND_RESEARCH_CPAL` und `UFOPEDIA_IMG_SANITY_CPAL`
verwenden eine benutzerdefinierte Palette. `UFOPEDIA_IMG_TEAMWORK` verwendet
die Standardpalette.

Bei den Mechanikartikeln verwenden `UFOPEDIA_IMG_DAMAGE_CPAL` und
`UFOPEDIA_IMG_FIRE_SPRAYING_CPAL` eine benutzerdefinierte Palette.
`UFOPEDIA_IMG_DAMAGE_ROLLS` und `UFOPEDIA_IMG_ACCURACY` verwenden die
Standardpalette.


Auch `UFOPEDIA_IMG_NIGHTVISION`, `HEAT_VISION`,
`UFOPEDIA_IMG_CROWD_CONTROL` und `UFOPEDIA_IMG_HUNTER_HUNTED` verwenden die
Standardpalette.

Bei der naechsten Tutorial-Gruppe verwenden `UFOPEDIA_IMG_SURRENDER`,
`UFOPEDIA_IMG_STR_SNIPER_SPOTTER_COOPERATION` und
`UFOPEDIA_IMG_CONCEALABLE_ITEMS` die Standardpalette.
`UFOPEDIA_IMG_ENEMY_REINFORCEMENTS_CPAL` verwendet eine benutzerdefinierte
Palette mit den reservierten Indizes.

Auch `CQC_CPAL.SPK`, `UFOPEDIA_IMG_FIRE_DAMAGE_CPAL` und
`UFOPEDIA_IMG_SMOKE_DAMAGE_CPAL` verwenden benutzerdefinierte Paletten mit
den reservierten Indizes.

Bei den Waffenvorstellungen verwenden `UFOPEDIA_IMG_UNARMED_COMBAT`,
`UFOPEDIA_IMG_PISTOLS`, `UFOPEDIA_IMG_SMGS` und `UFOPEDIA_IMG_RIFLES` die
Standardpalette. `UFOPEDIA_IMG_MELEE_WEAPONS_CPAL` verwendet eine
benutzerdefinierte Palette mit den reservierten Indizes.

Die restlichen Waffenvorstellungen `UFOPEDIA_IMG_SNIPER_RIFLES`,
`UFOPEDIA_IMG_SHOTGUNS`, `UFOPEDIA_IMG_CANNONS`,
`UFOPEDIA_IMG_MACHINE_GUNS`, `UFOPEDIA_IMG_LAUNCHERS` und
`UFOPEDIA_IMG_INCENDIARIES` verwenden ebenfalls die Standardpalette.



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

Die Quantisierungsindizes müssen anschließend direkt auf die 233 freien
Palettenplätze umnummeriert werden. Mit `quantize(palette=...)` darf das Motiv
nicht erneut gegen die Gesamtpalette quantisiert werden, weil Pillow dabei
reservierte UI-Indizes auswählen kann.

Für CPAL-Bilder ist deshalb das geprüfte Projektwerkzeug verbindlich:

```powershell
python artwork/tools/convert_cpal.py source.png replacement.png
```

Die vollständige Kurzregel und alle festen RGB-Werte stehen in `regel.md`.

Die reservierten Indizes wurden durch Vergleich von 196 lokalen XCF-CPAL-PNGs
ermittelt. Nach größeren XCF-Updates sollte diese Annahme erneut geprüft werden.

## 5. Transparente Autopsiebilder

Bei Autopsieartikeln kann Palettenindex 0 transparent sein. Diese Ausnahme
wird nur verwendet, wenn das konkrete Ersatzbild bewusst eine transparente
Textfläche benötigt. Dann wird die komplette linke Textfläche direkt auf Index
0 gesetzt und die PNG mit `transparency=0` gespeichert.

```powershell
python artwork/tools/convert_cpal.py source.png replacement.png --transparent-left 158
```

Ganzflächige Autopsie- und Berichtsillustrationen erhalten keine Transparenz.
Die Transparenz darf niemals allein aufgrund des Dateinamens angenommen werden.

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
- Transparente Autopsien verwenden in der linken Textflaeche Index 0;
  ganzflaechige Autopsien nicht.
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
