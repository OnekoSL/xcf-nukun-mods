# Verbindliche Regel fuer Ufopaedia-Bilder

Diese Regel gilt fuer alle neu erstellten und ueberarbeiteten Ufopaedia-Bilder
dieses Projekts.

## 1. Zuerst den Palettentyp bestimmen

- Der Sprite-Typ im Ruleset entscheidet, nicht die eingebettete Palette einer
  beliebigen PNG-Datei.
- Ein Sprite-Typ mit `_CPAL` verwendet die benutzerdefinierte CPAL-Regel.
- Ein Sprite-Typ ohne `_CPAL` verwendet die vollstaendige XCF-Standardpalette.
- `UFOPEDIA_IMG_TRANSFORMATIONS` ist ein bestaetigtes Standardpaletten-Bild
  und darf nicht mit der CPAL-Regel konvertiert werden.

## 2. CPAL: 23 Indizes sind reserviert

In der aktuell geprueften XCF-Version sind exakt diese 23 Palettenindizes fuer
Text, Titel, Schaltflaechen und Cursor reserviert:

```text
0
81-88
240-249
252-255
```

Fuer das eigentliche Motiv bleiben exakt 233 Indizes frei:

```text
1-80
89-239
250-251
```

Die reservierten Indizes muessen diese RGB-Werte behalten:

```text
0   =   0,   0,   0
81  = 224, 224, 240
82  = 212, 212, 232
83  = 204, 204, 224
84  = 196, 192, 220
85  = 184, 184, 212
86  = 176, 172, 204
87  = 164, 160, 196
88  = 156, 152, 188
240 = 156, 148, 188
241 = 124, 120, 148
242 =  92,  92, 108
243 =  60,  60,  68
244 =  28,  28,  32
245 = 140, 204, 184
246 = 104, 164, 152
247 =  72, 124, 120
248 =  44,  80,  84
249 =  20,  40,  44
252 = 252, 252, 164
253 = 220, 232, 140
254 = 192, 212, 120
255 = 164, 192, 104
```

## 3. Sichere Konvertierung

- Immer vom unveraenderten hochaufloesenden `*_source.png` ausgehen, niemals
  von einem bereits palettierten oder sichtbar verfaerbten `*_ui.png`.
- Auf 320 x 200 Pixel zuschneiden und mit Lanczos verkleinern.
- Ohne Dithering auf hoechstens 233 Motivfarben quantisieren.
- Die Quantisierungsindizes anschliessend direkt auf die 233 freien
  Palettenplaetze umnummerieren.
- Niemals das Bild mit `quantize(palette=...)` gegen die fertige Gesamtpalette
  quantisieren. Dabei koennen reservierte UI-Indizes wieder ausgewaehlt werden.
- Nicht lediglich "240 Bildfarben plus 16 UI-Farben" verwenden. Auch die
  Bereiche 81-88 und 240-249 sind reserviert.
- Das Werkzeug `artwork/tools/convert_cpal.py` ist fuer CPAL-Bilder
  verbindlich.

## 4. Transparenz ist eine ausdrueckliche Ausnahme

- Index 0 darf nur dann in den Bilddaten vorkommen, wenn die betreffende Grafik
  bewusst Transparenz verwendet.
- Bei transparenten Autopsiegrafiken wird die linke Textflaeche ausdruecklich
  auf Index 0 gesetzt und die PNG mit `transparency=0` gespeichert.
- Ganzflaechige Berichte und Autopsien erhalten keine Transparenz.

## 5. Pflichtpruefung vor dem Test

Jede fertige Datei muss folgende Bedingungen erfuellen:

- PNG, 320 x 200 Pixel, indiziert (`P`), 8 Bit, PNG-Farbtyp 3;
- Palette mit 256 Eintraegen beziehungsweise 768 RGB-Werten;
- alle 23 reservierten CPAL-Farben exakt korrekt;
- kein Dithering und keine gruenen, violetten, weissen oder schwarzen
  Stoerpixel;
- Ruleset-Pfad vorhanden;
- Repository und aktiver Testmod byte-identisch.

Alle selbst erstellten CPAL-Bilder duerfen ausser einem ausdruecklich erlaubten
Transparenzindex 0 keine reservierten Indizes in den Motivpixeln verwenden.
Das gilt auch fuer aeltere Projektbilder. Korrekte RGB-Werte in den reservierten
Palettenplaetzen allein reichen nicht aus: Werden diese Indizes im Motiv
benutzt, koennen im Spiel weiterhin falsche Farben, Rauschen oder grosse
Fehlflaechen entstehen. Solche Bilder muessen erneut vom unveraenderten
`*_source.png` mit `convert_cpal.py` konvertiert werden.

Technische Kontrolle:

```powershell
python artwork/tools/audit_cpal.py --forbid-reserved-pixels image.png
```

Anschliessend OpenXcom Extended vollstaendig neu starten und das Bild im Spiel
pruefen.

Diese Werte wurden lokal gegen 196 XCF-CPAL-PNGs geprueft. Nach einem groesseren
XCF-Update muss die Reservierung erneut gegen die Originaldateien verifiziert
werden.
