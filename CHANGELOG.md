# Änderungen

## Baukasten
- **1.6.2** (15.11.2026, 15:45): 528 · 4800 · Ton 192 · p04 256 am Gerät sauber (131 s, voller Pegel, Summe 4,99 Mbit/s). Die Schätzung „mit Ton nur 4,2–4,45 Mbit/s“ aus 1.6 war falsch und ist entfernt; die Warnung gilt nur noch für p04 unter 256. Vorlagen: geprüfter Stand 4800 + 192, Reserve 3800 + 192.
- **1.6.1** (15.11.2026, 15:00): Ergebnisse vom Gerät eingetragen – 528 · 3800 · Ton 192 · p04 256 geprüft (zwei Läufe à 2 min, voller Pegel), Vorlage „Nächster Test“ 528 · 4800 · Ton 192 · p04 256; die 8000er-Messläufe sind gestrichen (PVT stoppt nach 28 s, Index unbrauchbar).
- **1.6** (15.11.2026): Hinweise nach der Neuauswertung berichtigt (Befunde §33) – Tonpufferzeit aus p04 und Tonrate statt „Blockgröße“, Durchsatz mit echtem Ton 4,2–4,45 Mbit/s, Puffer-Regelung nicht mit dem kleinen 1,25-MBit-Modell; Vorlagen „Test 1“ (528 · 3800 · Ton 192 · p04 256) und zwei Messläufe (8000 + Ton). Kern unverändert, alle Hashes bleiben.
- **1.5** (21.10.2026): Ratenregelung des MG einstellbar – Größentoleranz RC7 (Faktor × Video), Transferrate RC11, Puffer-Regelung RC9/RC10/RC12 für LED1 (Leaky Bucket, wie bei AB).
- **1.4.2** (21.10.): „nur Video“ geprüft (VID00012): Aufnahme makellos, Index unvollständig → `mp4_reparatur.py`.
- **1.4.1** (20.10.): Abtastrate geprüft (VID00011): Audiotakt kommt von außen, kein Hebel; Build als bekannt markiert.
- **1.4** (20.10.): Abtastrate als Experiment (drei Stellen gemeinsam).
- **1.3** (20.10.): freie Werte – nur noch technische Sperren; neu Höhe, NTSC-Bildgröße, GOP je LED, Videopuffer p03, TF als Zahl; Summenbalken skaliert mit.
- **1.2** (20.10.): Ton aus (nur Video) über ein Byte (MG ENC_AV_SELECT = VIDEO_ONLY); Preset dafür.
- **1.1** (20.10.): Ton 48/64 kbit/s, Presets „Mit Ton“ 4500/96 und 4500/64, bekannte Builds V5000_A96 und V4500_A96 mit Prüfstand.
- **1.0** (20.10.): erste Fassung – Original → AE per Differenz, Video/Audio/Breite/p04/rein/TF, ZIP mit Rückkehrdateien.

## Werkzeuge
- `docs/analyse/mdat_bildweise.py` (15.11.): Aufnahme ohne brauchbaren Index bildweise aus dem mdat auswerten.
- `pvt_check.py` 1.7: meldet unvollständige oder unstimmige Indizes mit Klartext statt Abbruch.
- `pvt_check.py` 1.7 (15.11.): Zeile „Datenrate im Mittelteil“ (Steigung Dateiposition gegen Tonzeit) – bei Überlast der Durchsatz des Hosts.
- `build_ai.py` (15.11.): Hinweise wie Baukasten 1.6 (Tonpufferzeit, Durchsatz mit Ton, Puffer-Regelung).
- `pvt_check.py` 1.6: Müll-Einträge in der Audio-Größentabelle erkennen; 1.5: Zeile „Abtastrate“ (stsd/mdhd/AAC-Konfig) und 1,5×-Signatur; 1.4: Tonblöcke je Sekunde (erstes Loch, tot ab); 1.3: Container- und SPS-Größe, Pixel-Seitenverhältnis.
- `ton_schleife.py` (20.10.): Hörtest als Messung gegen eine Schleifen-Audioquelle; Schleifenlänge aus der Aufnahme.
- `mp4_reparatur.py` (21.10.): Index einer Nur-Video-Aufnahme aus dem Bildstrom neu bauen, Gegenprobe gegen den vorhandenen Teil-Index.
- `mp4_abtastrate.py` (20.10.): Abtastraten-Angaben im MP4-Kopf angleichen.
- `build_ai.py` v2 (20./21.10.): freie Werte, Schlüsselwort-Argumente (hoehe, ntsc, gop, p03, tf, rein, abtastrate, rc7, rc11, rc9, rc10, rc12), `check` liest alles zurück.
