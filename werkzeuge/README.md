# Werkzeuge

| Datei | Zweck | Braucht |
|---|---|---|
| `pvt_check.py` | Prüft PVT-Aufnahmen ohne zu decodieren: Bild- und Tonspur, Aussetzer (leere, kleine, Teilbilder), Raten je Sekunde, QP, Schlüsselbilder, Tonblöcke je Sekunde, Kopfangaben (Container, SPS, Abtastrate). Schreibt TXT/CSV/JSON. | Python 3.8+ |
| `ton_schleife.py` | Hörtest als Messung: eine kurze Audiodatei läuft in Dauerschleife am Eingang; jede Sekunde der Aufnahme wird mit derselben Stelle eine Schleife davor und danach verglichen. | ffmpeg, numpy |
| `mp4_reparatur.py` | Baut den MP4-Index (moov) neu, wenn er fehlt oder unvollständig ist – nötig bei Aufnahmen mit „nur Video“. Bildstrom bleibt byteidentisch. | Python 3.8+, `pvt_check.py` daneben |
| `mp4_abtastrate.py` | Gleicht die Abtastraten-Angaben im Kopf (stsd, AAC-Konfig, optional mdhd) an. | Python 3.8+ |
| `build_ai.py` | Der Baukasten als Kommandozeile: dieselben Stellen, dieselben Prüfungen, byteidentische Ergebnisse. `build <AE.BIN> <Ordner> <Breite> <Video> <Audio> [p04] [schluessel=wert …]`, `check <BIN>`. | Python 3.8+ |

Alle Werkzeuge lesen Aufnahmen nur; keines verändert oder flasht etwas am Gerät.
