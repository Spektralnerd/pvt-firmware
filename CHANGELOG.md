# Änderungen

## Baukasten
- **1.5** (21.10.2026): Ratenregelung des MG einstellbar – Größentoleranz RC7 (Faktor × Video), Transferrate RC11, Puffer-Regelung RC9/RC10/RC12 für LED1 (Leaky Bucket, wie bei AB).
- **1.4.2** (21.10.): „nur Video“ geprüft (VID00012): Aufnahme makellos, Index unvollständig → `mp4_reparatur.py`.
- **1.4.1** (20.10.): Abtastrate geprüft (VID00011): Audiotakt kommt von außen, kein Hebel; Build als bekannt markiert.
- **1.4** (20.10.): Abtastrate als Experiment (drei Stellen gemeinsam).
- **1.3** (20.10.): freie Werte – nur noch technische Sperren; neu Höhe, NTSC-Bildgröße, GOP je LED, Videopuffer p03, TF als Zahl; Summenbalken skaliert mit.
- **1.2** (20.10.): Ton aus (nur Video) über ein Byte (MG ENC_AV_SELECT = VIDEO_ONLY); Preset dafür.
- **1.1** (20.10.): Ton 48/64 kbit/s, Presets „Mit Ton“ 4500/96 und 4500/64, bekannte Builds V5000_A96 und V4500_A96 mit Prüfstand.
- **1.0** (20.10.): erste Fassung – Original → AE per Differenz, Video/Audio/Breite/p04/rein/TF, ZIP mit Rückkehrdateien.

## Werkzeuge
- `pvt_check.py` 1.6: Müll-Einträge in der Audio-Größentabelle erkennen; 1.5: Zeile „Abtastrate“ (stsd/mdhd/AAC-Konfig) und 1,5×-Signatur; 1.4: Tonblöcke je Sekunde (erstes Loch, tot ab); 1.3: Container- und SPS-Größe, Pixel-Seitenverhältnis.
- `ton_schleife.py` (20.10.): Hörtest als Messung gegen eine Schleifen-Audioquelle; Schleifenlänge aus der Aufnahme.
- `mp4_reparatur.py` (21.10.): Index einer Nur-Video-Aufnahme aus dem Bildstrom neu bauen, Gegenprobe gegen den vorhandenen Teil-Index.
- `mp4_abtastrate.py` (20.10.): Abtastraten-Angaben im MP4-Kopf angleichen.
- `build_ai.py` v2 (20./21.10.): freie Werte, Schlüsselwort-Argumente (hoehe, ntsc, gop, p03, tf, rein, abtastrate, rc7, rc11, rc9, rc10, rc12), `check` liest alles zurück.
