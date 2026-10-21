# PVT Firmware – Pinnacle Video Transfer auf voller Auflösung

Werkzeuge, Firmware-Baukasten und Messergebnisse für den **Pinnacle Video Transfer** (PVT, 2008):
ein eigenständiger Recorder, der analoges Video (Composite/S-Video, PAL/NTSC) mit dem
Mobilygen-Codec **MG1264** als H.264/AAC-MP4 auf USB-Speicher schreibt, gesteuert von einem
ColdFire **MCF52223**. Ab Werk nimmt er mit 320×240 bei 768 kbit/s, 640×480 bei 1200 kbit/s
oder 720×576 bei 1500 kbit/s auf. Mit der hier entstandenen Firmware **AE** läuft er in voller
Auflösung 720×576i bei 5 Mbit/s – geprüft über 5 Stunden am Stück.

*English: tools, a browser-based firmware builder and measurements for the Pinnacle Video
Transfer (MG1264 H.264 encoder, ColdFire MCF52223 host). The stock device records at most
720×576 at 1.5 Mbit/s; the modified firmware "AE" records full D1 at 5 Mbit/s. The repository
contains no Pinnacle or Mobilygen code or documents – the builder works on the original update
file you supply. German documentation; the tools print German messages.*

## Was hier liegt

| Ordner | Inhalt |
|---|---|
| `baukasten/` | **Firmware-Baukasten**: eine HTML-Datei, läuft offline im Browser. Original-Update laden, Werte wählen, fertiges Update-Paket mit Rückkehrdateien speichern. |
| `werkzeuge/` | `pvt_check.py` (Aufnahmen prüfen), `ton_schleife.py` (Hörtest als Messung), `mp4_reparatur.py` (Index neu bauen), `mp4_abtastrate.py`, `build_ai.py` (Baukasten als Kommandozeile) |
| `docs/` | Befunde und Messungen (Oktober 2026), Testpläne, Prüfberichte der Aufnahmen |

## Schnellstart

1. **Original-Update besorgen:** Pinnacle-Update 01.00.46.03 vom 14.03.2008, Datei `PVT1.00.46.03.zip`
   mit `CFUPDATE.BIN` (245.760 Byte, SHA-256 `032fd7d2241aff1eb87403b72554dd1c7babe97a31c54b7418f9ea1657213fdc`).
   Es liegt nicht in diesem Repository.
2. **Baukasten öffnen:** `baukasten/dist/PVT_Firmware_Baukasten.html` per Doppelklick (Firefox oder Chromium).
   Das ZIP hineinziehen. Der Baukasten prüft den Hash, macht aus dem Original per eingebauter
   Byte-Differenz den Stand AE und zeigt die Einstellungen.
3. **Werte wählen:** Presets für die geprüften Stände, sonst alles frei – Videoziel, Ton, Bildgröße,
   GOP, Puffer, Ratenregelung. Hinweise zu Datenblatt- und Messgrenzen erscheinen, gesperrt wird
   nur, was technisch nicht in die Stellen passt.
4. **Bauen und speichern:** Das ZIP enthält `01_INSTALL_…/CFUPDATE.BIN`, die Rückkehrdateien
   (AE und Original), `README_DE.txt` mit allen geänderten Werten und `SHA256SUMS.txt`.
5. **Einspielen:** nur die eine `CFUPDATE.BIN` ins Hauptverzeichnis eines leeren FAT32-Sticks.
   PVT aus, Netzteil und Geräte trennen, Stick rein, Netzteil dran – das Gerät startet selbst.
   USB-LED rot und MODE-LEDs blau blinkend = Update läuft, nichts trennen. Alle LEDs blinken
   blau, dann Standby. MODE kurz drücken; Stick erst ziehen, wenn die USB-LED blau leuchtet.
6. **Prüfen:** 1–2 Minuten aufnehmen, dann `python3 werkzeuge/pvt_check.py VID0000x.MP4`.

## Stand der Dinge (Oktober 2026)

- **AE** (720×576i, 5000 kbit/s, Ton 384 kbit/s angefordert): 2 h 30 min und 5 h 03 min ohne
  Tonquelle fehlerfrei. Das ist der Vorführstand und die Basis aller Varianten.
- **Mauer des Hosts:** Der ColdFire schreibt über USB Full Speed. Ohne Ton laufen 5,25 Mbit/s
  sauber (60 s), 6 Mbit/s und mehr verwerfen gleichmäßig Bilder. Mit Stille lag die Summe aus
  Video und Ton bei 5,02 Mbit/s über 5 Stunden; 5,25 ist die gemessene Grenze.
- **Ton:** Der Tonpfad des Hosts stirbt bei AAC-Blöcken über etwa 300 Byte (192 und 384 kbit/s
  bei 48 kHz) binnen 20 Sekunden, unabhängig von der Videorate; 96 kbit/s (256-Byte-Blöcke) hält.
  Geprüfter Stand mit Ton: **528×576i, 4500 kbit/s, Ton 96 kbit/s** (99 % der Tonblöcke, eine
  Störung in 2 Minuten; der 30-Minuten-Lauf steht noch aus).
- **Breite 528:** an die Auflösung einer 1/3"-CCD-Kamera (512 Punkte) angepasst, spart gemessen
  3–7 % Bits bei gleicher Qualität im Band der Kamera; Seitenverhältnis im MP4 korrekt (16:11 → 4:3).
- **Nur Video:** Ein Byte schaltet den MG auf reines Video. Die Aufnahme ist makellos, aber der
  ColdFire schreibt den MP4-Index unvollständig – `mp4_reparatur.py` baut ihn neu.
- **Abtastrate:** Der Audiotakt kommt von außen und bleibt bei 48 kHz; 32 kHz einzustellen
  überlastet den MG. Kein Hebel.
- Details, Zahlen und Adressen: `docs/befunde-2026-10.md`.

## Werkzeuge

Alle Werkzeuge sind Python 3 (ab 3.8). `pvt_check.py`, `mp4_reparatur.py` und `mp4_abtastrate.py`
brauchen nur die Standardbibliothek; `ton_schleife.py` braucht `ffmpeg` im PATH und `numpy`.

```
python3 werkzeuge/pvt_check.py AUFNAHME.MP4 --out ergebnisse   # Bild- und Tonspur, Aussetzer, Raten, Kopfangaben
python3 werkzeuge/ton_schleife.py AUFNAHME.MP4                 # Ton gegen eine Schleifen-Audioquelle prüfen
python3 werkzeuge/mp4_reparatur.py AUFNAHME.MP4                # Index einer Nur-Video-Aufnahme neu bauen
python3 werkzeuge/build_ai.py build CFUPDATE_AE.BIN ausgabe 528 4500 96 rein=1   # wie der Baukasten, nur ohne Browser
```

## Wie der Baukasten arbeitet

Das Original wird über eine eingebaute Byte-Differenz (29 Bereiche, 3.293 Byte) zum Stand AE und
per SHA-256 geprüft. Jede Einstellung ist ein Zahlenwert an bekannten Stellen des Abbilds; vor
jedem Wert wird das erwartete Befehlswort geprüft (`move.l #`, `cmpi.l #` oder `moveq`). Es wird
kein Code hinzugefügt, nichts anderes berührt, und ein abschließender Byte-Vergleich stellt
sicher, dass sich nur die gewünschten Stellen geändert haben. Welche Stelle welchen Parameter
des MG setzt, wurde mit einem Modell der ColdFire-Befehlskette per Mutationstest bestätigt.
Die Stellen stehen in `baukasten/src/core.js` und im Baukasten unter „Was der Baukasten genau
ändert“.

Bauen aus den Quellen: `python3 baukasten/build.py`. Tests: `node baukasten/tests/test_core.js`
(mit `PVT_ORIGINAL=…/CFUPDATE.BIN` werden alle bekannten Builds nachgebaut und gegen ihre
Hashes geprüft) und `baukasten/tests/smoke.py` (Playwright, Download im Browser).

## Warnung

Experimentelle Firmware ohne Herstellerfreigabe. Jede neue Kombination hat null Hardwaretests,
bis sie jemand geprüft hat. Ein fehlgeschlagenes Update kann das Gerät unbrauchbar machen; die
Rückkehrdateien helfen nur, solange der Updatepfad des Geräts funktioniert. Backups und Dumps
behalten. Freigabe für lange Aufnahmen erst nach 30 Minuten mit Ton und einem Lauf über den
4-GiB-Dateiwechsel.

## Rechtliches

Dieses Repository enthält keine Firmware von Pinnacle und keine Dokumente von Mobilygen. Der
Baukasten arbeitet ausschließlich auf der Update-Datei, die der Nutzer selbst mitbringt; die
eingebaute Differenz besteht aus eigenem Code und den wenigen Bytes, die er ersetzt. Pinnacle,
Mobilygen und MG1264 sind Marken ihrer Inhaber. Lizenz der Werkzeuge und des Baukastens: MIT.

Analyse und Werkzeuge entstanden in Zusammenarbeit mit Claude (Anthropic).
