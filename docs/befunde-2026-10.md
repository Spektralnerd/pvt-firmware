# PVT / MG1264 — Übergabe-Nachtrag (Oktober 2026)

**Dieser Nachtrag ergänzt das bestehende Übergabepaket `PVT_HANDOVER`.**
Er fasst zusammen, was seit dem Stand „Test AB, keine AB-Hardwareergebnisse“
hinzugekommen ist. Alles hier beruht auf vom Nutzer gelieferten Aufnahmen und
auf erneuter Analyse der bereits im Paket enthaltenen Firmwaredateien. Keine
neue Firmware wurde erzeugt, kein Gerät wurde ferngesteuert.

Statusbegriffe wie im Originalpaket: **Nutzerbeobachtung**, **historischer
Messbefund**, **Code-/Modellbefund**, **Hypothese**.

---

## 0. In fünf Minuten einsteigen

**Kurzfassung 10.10.2026, 16:30: Beide Fehler sind gelöst und am Gerät bestätigt
(Abschnitte 13–16). Vorführstand = Firmware AE auf LED1
(`PVT_AE_LED1_VORFUEHRSTAND.zip`), 2 h 30 min Langzeitlauf mit 4-GiB-Wechsel ohne
Befund. Die Abschnitte 1–9 beschreiben den Weg dorthin.**

1. Dieses Dokument lesen.
2. `pvt_check.py` ist das zentrale neue Werkzeug (Abschnitt 5). Nur Python-
   Standardbibliothek, kein FFmpeg, liest PVT-MP4s direkt.
3. Wichtigste neue Erkenntnis: Das Anlaufstottern beginnt **immer nach einer
   festen Videodatenmenge von ca. 1,49 MB**, firmware- und QP-unabhängig
   (Abschnitt 1). Ursache sitzt im Datenweg/Puffer, nicht im Ratenregler.
4. AB ist jetzt hardwaregetestet (Abschnitt 2). LED1 ist die beste der drei
   Stufen, LED3 die schlechteste, LED2 nutzlos.
5. Zwei offene Fehlerbilder haben vermutlich dieselbe Ursache: rotes Blinken
   nach LED-Wechsel und fehlender 4-GB-Dateiwechsel (Abschnitt 3).
6. Nächster entscheidender Test braucht KEINE neue Firmware: dieselbe Aufnahme
   mit der Originalfirmware 01.00.46.03 (Abschnitt 6).
7. **Neu (10.10.2026):** Elgato Turbo.264 1.4 ausgewertet, MG-Speicherbudget per
   Emulation berechnet. Der Video-Ausgabepuffer passt auf der MG-Seite bis
   2351 Seiten; 2048 Seiten (4 MiB) sind der empfohlene Testwert (Abschnitt 10b).
8. **Test AC am Gerät getestet** (Abschnitt 13): Anlaufstottern weg → Puffer
   bestätigt; aber laufender Videozeitverlust ab ~20 s → nicht aufnahmetauglich.
   Test AD (1536 Seiten) gebaut, noch ungetestet.
9. **Stand 12.10.2026:** Generalprobe 5 h 03 min bestanden (Abschnitt 21),
   Hardware identifiziert, 5,25-Mbit/s-Mauer ist Architektur (Abschnitt 22),
   unbestückter 2×13-Port vermutlich ColdFire-BDM — Pinliste und Messplan in
   Abschnitt 23, Messung durch den Nutzer steht aus.
10. **12.10., 23:46: Die Veranstaltung ist auf unbestimmte Zeit verschoben**
   (Location abgesagt). Kein Termin mehr; der Nutzer erwägt, das Projekt
   stattdessen auf YouTube zu zeigen. Damit ändert sich die Reihenfolge:
   erst das Tonproblem sauber lösen (24a/24b, Entscheidungsbaum), dann
   Gerät-2-Dump (23b), dann die saubere Neubau-Kette aus dem Original für
   eine Veröffentlichung (Patcher ohne Herstellerbinaries). Abschnitt 9
   („Plan bis zur Vorführung“) ist damit überholt.

---

## 1. Hauptbefund: feste Datenmarke ca. 1,49 MB

**Messbefund über zehn Aufnahmen aus fünf Firmwareständen.** Das untersuchte
Anlaufstottern (kleine/leere Zwischenbilder) beginnt nicht nach einer festen
Zeit, sondern nach einer festen Menge geschriebener Videodaten:

| Clip | Besonderheit | Beginn Zeit | Videodaten bis dahin |
|---|---|---:|---:|
| X/LED1 | QPmin 28, ohne Puffer-RC | 2,56 s | 1,523 MB |
| Y/LED2 | Puffer 2,5 Mbit | 2,64 s | 1,545 MB |
| Z/LED3 | Delay 16875 | 2,80 s | 1,534 MB |
| AA/LED2 | QPmin 26 | 3,60 s | 1,479 MB |
| AA/LED3 | QPmin 27 | 3,64 s | 1,477 MB |
| Y/LED3 (Referenz) | | 3,72 s | 1,484 MB |
| Z/LED2 | Delay 5625 | 3,76 s | 1,486 MB |
| AB/LED1 | neuester Build | 3,36 s | 1,486 MB |
| AB/LED2 | Größen-RC aus | 3,48 s | 1,482 MB |
| AB/LED3 | enge Toleranz | 3,20 s | 1,510 MB |
| AB lang (VID00004) | 1h53m | 3,36 s | 1,488 MB |

Startzeit schwankt um Faktor 1,5, die Datenmenge nur ±2 %. Das ist der
robusteste Befund des ganzen Projekts.

**Der QP ist nicht der Auslöser.** X/LED1 lief durchgehend bei QP 28 mit fast
gleich großen Bildern und stockte trotzdem genau an dieser Marke. In Y/Z/AA ist
das erste auffällige Bild noch mit QP 29 codiert; der QP-Abfall ist Folge, nicht
Ursache.

**Codebefund (eingegrenzte Hypothese).** Die ColdFire-Firmware enthält bei
Dateioffset 0x2A61A (= Laufzeit 0x2E61A) einen eigenen 84-Wort-Block, den der
MG beim Start als „custom product configuration“ übernimmt. Pinnacle setzt darin
den Video-Ausgabepuffer (Pool „mux vid“) auf **832 Seiten × 2048 = 1.703.936
Byte** (Mobilygen-Standard wäre 2048 Seiten = 4 MiB) und die Eingangsbildpuffer
auf **6** statt 8. Der Encoder verweigert ein neues Bild, wenn im Ausgabepuffer
weniger als ein Schutzabstand („guardband“) frei ist; aus den Clips lässt sich
dieser auf ca. 324 KB eingrenzen. 1.703.936 − 324.000 ≈ 1,38 MB; sechs
Eingangsbilder später erscheint bei ca. 1,48 MB das erste übersprungene Bild.
Das passt zur Marke.

**Korrektur gegenüber Zwischenstand:** Die „Videopause im Dateiinterleave bei
ca. 1,38 MB“ ist KEIN gesicherter Auslöser. In der langen Aufnahme (VID00004)
und einigen Clips liegt diese Pause NACH dem Stotterbeginn. Belastbar ist nur
die feste Datenmarke selbst.

Relevante MG-Adressen (versionsgebunden, Stand 00.01.07.28, Laufzeitadressen):
- RC-Konfigurations-Diagnose (beschriftet alle Felder): MG 0x2A480
- Ausgabepuffer-Objekt, Feld +0x54 = Puffergröße in Byte
- Guardband-Berechnung: MG 0xA1098 (ein Faktor aus Encoderfeld +0x744)

---

## 2. AB ist jetzt hardwaregetestet

**Nutzeraufnahmen VID00001–03 = AB/LED1, LED2, LED3** (Reihenfolge aus dem
Datenratenverlauf abgeleitet, passt eindeutig).

| | LED1 | LED2 | LED3 |
|---|---|---|---|
| Stottern ab | 3,36 s / 1,486 MB | 3,48 s / 1,482 MB | 3,20 s / 1,510 MB |
| leere + fast leere Bilder | 22 | 17 | 61 |
| letzte Störung | 5,56 s | 5,32 s | 10,88 s |
| verlorene Videozeit | – | – | 0,49 s (~12 Bilder) |
| Datenrate | 3,5→5,0 Mbit/s | durchgehend ~3,4, QP29 | ~4,9 Mbit/s |

- **LED3 ist die schlechteste Stufe.** Längstes Stottern, verliert Videozeit
  (im Kleinen wie Z/LED2 damals). Nicht verwenden.
- **LED2 bringt nichts.** Ohne Größen-RC bleibt der Encoder bei QP 29 und nutzt
  das 5-Mbit-Budget nie aus. Stottert trotzdem.
- **LED1 ist die beste der drei.** Das ist die Vorführkonfiguration.

**Folgerung:** Die AB-Hypothese (Größen-RC beeinflusst das Startverhalten) ist
damit widerlegt. LED2 hat keinen Größenregler und stockt an derselben Marke.
Der Regler bestimmt nur, wie schlimm es wird, nicht den Auslöser.

---

## 3. Zwei offene Fehlerbilder, vermutlich eine Ursache

### 3a. Lange Aufnahme VID00004 (AB/LED1, Überwachungskamera, nachts)

**Bester Langzeitlauf des Projekts.** 1 h 53 min, durchgehend 5,00 Mbit/s (kein
Einbruch unter 3 Mbit/s nach dem Anlauf), 3391 Schlüsselbilder im Abstand von
genau 2,00 s, Bild/Ton am Ende 0,05 s auseinander, nach 7,04 s kein einziges
auffälliges Bild mehr. Datei sauber abgeschlossen (Index geschrieben).

**Das Ende ist kein Absturz, sondern die FAT32-Grenze.** Dateigröße
4.258.087.391 Byte = 3,966 GiB, ca. 37 MB unter 4 GiB. Das Gerät hat die Datei
korrekt geschlossen. **ABER: es wurde keine Fortsetzungsdatei (VID00005)
angelegt.** Der 4-GB-Dateiwechsel ist fehlgeschlagen. Beim Abbruch haben die
LEDs rot geblinkt. Speicher war 100 GB frei, also kein Platzproblem.

### 3b. Rotes Blinken nach LED-Wechsel + kurze Abbrüche beim Start

**Nutzerbeobachtung:** Nach einem LED-Wechsel direkt nach einer Aufnahme blinkt
es erst rot, dann wird der Speicher neu initialisiert, danach geht es wieder.
Mehrere Startversuche brachen nach kurzer/längerer Zeit ab, teils ohne Datei.

**Codebefund + Hypothese.** Rotes Blinken ist Pinnacles allgemeines Signal
„Aufnahme wegen Fehler gestoppt“ (Original-Readme: eigentlich für Signalverlust;
Signalverlust scheidet hier aus, da bis zuletzt 5 Mbit/s Bild kam). In den
Testfirmwares ab W laufen zusätzlich **fehlgeschlagene MG-Konfigurationsbefehle
in genau diesen Fehlerausgang (CF 0x10852)**; das Original hat dort nur die
Normprüfung (einziger Original-Absprung bei CF 0x1040E, Fehlercode 0x08000007 =
Norm weder PAL noch NTSC).

Gemeinsame Hypothese für 3a und 3b: In jedem Moment, in dem die Firmware den
Encoder neu einrichtet (Aufnahmestart, LED-Wechsel, Dateiwechsel), kann ein
einzelner MG-Befehl einmal fehlschlagen (z. B. weil der Chip den Abschluss der
vorigen Datei noch nicht fertig hat). Die Testfirmware bricht dann ab, wo das
Original weitergemacht hätte. Erklärt alle drei Beobachtungen und auch, warum
früher 4-GB-Wechsel funktioniert haben.

---

## 4. Korrekturen an früheren Annahmen (auch aus dem W-Builder)

- **RC8 = 1 ist Originalverhalten, kein Patch-Überbleibsel.** Die Original-
  ColdFire-Firmware setzt im RC-Setup (ab CF 0x10924) selbst RC6 = 1,
  RC7 = Bitrate × 5000 und RC8 = 1 und aktiviert danach. Was RC8 bewirkt, bleibt
  unbekannt (wird in der MG-Diagnose bei 0x2A480 nicht ausgegeben).
- **Die W-Builder-Felder `afr_qp_max` / `afr_qp_min` sind fehlzugeordnet.** Das
  Original schreibt an diesen Plätzen RC29 = 1000 und RC30 = Bitrate × 5000
  (= 25.000.000 bei 5 Mbit/s), keine QP-Werte. **Diese zwei Felder nicht
  benutzen.** In keiner bisherigen Konfiguration wurden sie gesetzt (geprüft).
- Die Konstanten 0x120000–0x170000 im MG-Code sind Registernummern, keine
  Puffergrößen (falsche Zwischenspur, verworfen).

---

## 5. Neues Werkzeug: pvt_check.py (v1.1)

Liest PVT-MP4s direkt aus den MP4-Tabellen und den H.264-Slice-Köpfen. Nur
Python-Standardbibliothek, kein FFmpeg, keine Netzverbindung. Verändert die
Dateien nicht.

Aufruf: `python pvt_check.py *.MP4 --out ergebnisse`
Windows: MP4s auf `pvt_check_ziehen.bat` ziehen.

Meldet je Datei: Bild-/Tonlänge und mdhd-Abgleich, Datenrate je Sekunde und
Spitzenfenster, Schlüsselbilder, QP, „leere“ Bilder (alle Makroblöcke
übersprungen = exakte Wiederholung, eindeutig), „kleine“/„Teil“-Bilder (Verdacht,
nur in bewegtem Umfeld), **Beginn der Störung mit Zeit UND Videodatenmenge**,
und wachsenden Video-Rückstand (fehlende Videozeit wie bei Z/LED2).

Verifiziert gegen FFmpeg: MP4-Tabellen und Slice-QP bitgenau an Testdateien und
an bitweise nachgebauten echten PVT-Köpfen (Y/LED3, 4848 Slices, 0 Fehler).
Die Klasse „leer“ wurde gegen decodierte Pixel bestätigt.

---

## 6. Nächster entscheidender Test — OHNE neue Firmware

**Dieselbe lange Aufnahme mit der Originalfirmware 01.00.46.03**
(`05_ORIGINAL/STOCK_01_00_46_03/CFUPDATE.BIN`, Installation nach Pinnacle-
Readme). Gleiche Kamera, gleicher Speicher, über 1 h 53 min hinaus laufen
lassen. Danach mit `pvt_check.py` auswerten.

- **Entsteht eine Fortsetzungsdatei:** Dann liegt der Abbruch an der
  Fehlerbehandlung der Patches. Reparatur dann klein und klar: Fehlerbehandlung
  wieder wie im Original (kein Abbruch bei einzelnem fehlgeschlagenem Befehl),
  Parameter unverändert.
- **Bricht auch das Original bei 4 GiB ab:** Dann liegt es am Speicher/
  Dateisystem, nicht an unseren Änderungen.
- Nebenbei klärt der Lauf, ob das ~1,5-MB-Anlaufstottern auch im Original
  auftritt (bisher nie verglichen).

---

## 7. Danach: ein einziger Firmwareversuch (optional, falls Zeit)

**Stand 10.10.2026: gebaut, siehe Abschnitt 12 (`PVT_TEST_AC_PUFFER.zip`).**

Die MG-Speicheraufteilung ist eine **Datentabelle** im ColdFire-Code (0x2A61A),
kein Programmcode. Den Video-Ausgabepuffer zu vergrößern ist die Änderung eines
einzigen Wertes an bekannter Adresse, einbaubar mit der vorhandenen Patch-
Funktion des Builders. **MG-Seite inzwischen geprüft (Abschnitt 10b):** passt
bis 2351 Seiten, Testwert 2048 an CF-Datei 0x2A626.
Test wie bei AB: kurze Kaltstart-Clips, dann `pvt_check.py`.

**Nicht hier abschließbar:** der genaue ColdFire-Schreibpfad (wo BLOCK_DONE
relativ zum USB-Schreiben sitzt) und ob der 832-Seiten-Wert gefahrlos erhöhbar
ist. Grund: Das Lesen des ColdFire-Disassemblats hat in der KI-Umgebung
wiederholt eine Sicherheitsabschaltung ausgelöst. Der Weg dafür ist Ghidra oder
`m68k-linux-gnu-objdump` lokal (Laufzeit = Dateioffset + 0x4000, Sprache
68000/ColdFire big-endian). Wichtige Einstiegsadressen stehen in Abschnitt 8.

---

## 8. ColdFire-Adresskarte (Original 01.00.46.03, Laufzeitadressen)

| Adresse | Bedeutung |
|---|---|
| CF 0xF940 | sendCommand (MG-Befehl absetzen, voll gehandshaked) |
| CF 0xFE4C | RC-Parameter-Setter (Objekt 3, Opcode 0x13) |
| CF 0xFD3C | Encoder-Setter (Objekt 3, Opcode 0x0E), aktiviert selbst nach Erfolg |
| CF 0xFD94 | Encoder-Aktivierung (Opcode 0x0F) |
| CF 0x10924 | RC-Setup: setzt RC6=1, RC7=Bitrate×5000, RC8=1 |
| CF 0x10984 | BITSTREAM_BLOCK_DONE senden (Objekt 3, Opcode 5) |
| CF 0x10AC8–0x10D90 | Ereignisschleifen, rufen 0x10984 auf |
| CF 0x10852 | Fehlerausgang; Testfirmwares springen zusätzlich hierher |
| CF 0x1040E | einziger Original-Fehlerabsprung (Normprüfung) |
| CF 0x2E61A | Pinnacles 84-Wort-MG-Produktkonfiguration |
| CF 0x32000 | Beginn der RC-Codeerweiterung der Patchprojekte |

MG-Adressen siehe Abschnitt 1 und das Original-`START_RE.md`.

---

## 9. Plan bis zur Vorführung (Ende Oktober)

- **Stand 10.10., 13:30: AE/LED1 ist der Kandidat (Abschnitt 15), kein Vorlauf
  mehr nötig; Rückfall bleibt AB/LED1 + 10 s Vorlauf** (laufendes Bild vor
  dem Inhalt, damit die ~1,5-MB-Marke in den Vorlauf fällt). Dazu die Geschichte
  (entpackte MG-Firmware, Parameterzuordnung, feste Datenmarke, Pinnacles
  832-Seiten-Puffer) und `pvt_check.py` als Live-Demo.
- **Erledigt 10.10.:** Puffer (AC/AD), Regelung (AE), Langzeitlauf mit 4-GiB-Wechsel
  (Abschnitt 16). Der Originalfirmware-Vergleichstest (Abschnitt 6) ist damit
  nicht mehr nötig.
- **Danach, falls Zeit:** Test AC, kurze beaufsichtigte Clips (Abschnitt 12).
- **Letzte Woche:** nur Absicherung, keine neuen Experimente, Rückkehrdatei
  parat.

Nicht versprochen: dass das Stottern bis dahin weg ist. Falls nicht, bleibt die
Vorlauf-Umgehung, die für die Vorführung reicht.

---

## 10. Zweites Gerät: Elgato Turbo.264 (Crusher-Referenz)

Laut Nutzer 1:1 die Mobilygen-„Crusher“-Referenz, gleicher MG1264. Die beigelegte
Software-CD hat Disc Rot. Der Crusher hat **keinen ColdFire und keinen
Videoeingang**; der Mac dekodiert Dateien und schickt rohe YUV-Bilder über USB
(Cypress FX2). Die MG-Firmware liegt daher in der Mac-Software, nicht auf dem
Stick. Nutzen fürs Projekt: eine zweite MG-Firmwareversion zum Vergleich mit
00.01.07.28. Encoder/Regler nachstellbar, Eingangspfad (656, Halbbilder,
Kamerarauschen) nicht.

Zugang zur Firmware: CD mit ddrescue/IsoBuster retten (nur die eine Firmwaredatei
im Installer muss lesbar werden), oder Download über Wayback Machine der alten
Elgato-Legacy-Seiten / Macintosh Garden / Macintosh Repository (gesucht:
„Turbo.264“ ohne HD). Ein DMG lässt sich mit 7-Zip öffnen; die Firmwaredatei kann
mit dem vorhandenen `unpack_u8_lzo.py` gegen die PVT-Version gehalten werden.
**Nebengleis — hinter die Veranstaltung schieben.**

### 10a. Stand der Software-Suche (10.10.2026)

- **CD des ersten Sticks:** Laufwerk meldet „keine Disc“, läuft kurz an und
  hört auf → Inhaltsverzeichnis am Innenrand unlesbar, praktisch verloren.
  Nutzer hat zwei weitere Sticks bestellt (einer OVP, einer eingeschweißt mit
  Apple-Store-Aufkleber).
- **Macintosh Repository**, Eintrag „Elgato Turbo264“
  (macintoshrepository.org/32622-elgato-turbo264): fünf Dateien, ohne
  Beschriftung, ohne Versionsangabe. Größe / Art / SHA-1 laut Seite:
  - 12,8 MB ZIP (2020-09-13) — `cb733f6f3cc841c0327475be6e1007e52592f65d`
  - 15,06 MB DMG (2024-12-03) — `0038b1fdf6f63f2bb7245c565d20273595df7334`
  - 12,1 MB DMG (2024-12-03) — `aff7ba50e8da376a257f8e0e81bb2bc14d693cc6`
  - 8,9 MB DMG (2024-12-03) — `137893520b24911ac96c2ed62b2da1b63340b458`
  - 9,04 MB DMG (2024-12-03) — `88bf06849a56e9f2e648cd24cad383bb6f8e22b5`
- **Mac Informer:** „Elgato Turbo.264 Update“ 1.4, Datei
  `turbo_14_311_update.dmg`, 13,8 MB (Größe passt zu keiner der fünf oben).
- **Versionsfolge laut Presse:** 1.1, 1.3 (Mai 2008), 1.4 (Dez. 2009:
  Deinterlacing, AC-3, Kapitelmarken, Untertitel). Getrennte Linie:
  Turbo.264 HD (2009, eigene Hardware) und die „HD Software Edition“ (Juli 2010,
  nur Intel, ohne Stick) — für den MG1264 nicht die erste Wahl.
- **Alte Elgato-Updateseite** (für die Wayback Machine):
  `http://www.elgato.com/elgato/na/mainmenu/support/Update-Start/Update-Turbo.en.html`
  — von hier aus nicht prüfbar (Archivseite gesperrt).
- **Aus dieser Umgebung nicht herunterladbar** (Proxy sperrt die Seiten). Weg:
  Nutzer lädt herunter, prüft SHA-1 (`certutil -hashfile <Datei> SHA1`), lädt
  hoch. Hier dann: Versionen bestimmen, MG-Firmware finden, gegen 00.01.07.28
  halten, Elgatos MG-Konfiguration (Puffergrößen) als Anhaltspunkt für die
  832-Seiten-Frage lesen. Vorsicht: Der Crusher wird vom Mac gedrosselt
  gefüttert (Dateiumwandlung, nicht Echtzeit) — seine Puffergröße zeigt, was
  im Speicher Platz hat, beweist aber nicht, was der PVT braucht.
- **Neue CDs sichern:** sofort nach dem Auspacken als komplettes Sektorabbild
  (.iso bzw. .bin/.cue, z. B. ImgBurn „Read“ oder IsoBuster), SHA-1 notieren,
  doppelt ablegen, Hülle/Label/Handbuch scannen. Windows-Explorer zeigt
  Mac-CDs (HFS) leer oder unlesbar an — das ist kein Defekt.

### 10b. Turbo.264 1.4 ausgewertet (10.10.2026)

**Datei:** `turbo_14_311_update.dmg`, 14.452.278 Byte,
SHA-1 `6e68318b84dba3087334da70dfcc123f09ff46da` (vom Nutzer, Quelle Mac Informer).
UDIF/zlib, HFS+-Volume „Turbo.264“, zuletzt geändert 11.12.2009. Enthält die
**vollständige Anwendung** „Turbo.264 1.4 (311)“, © 2007–2009, keine bloße
Aktualisierung (Readme: alte App ersetzen, neue hineinziehen). Unterstützt
beide Sticks: `Crusher.framework` (Turbo.264, MG1264) und `CrusherHD.framework`
(Turbo.264 HD, MG3500). QuickTime-Komponente „Elgato Turbo“ 1.0.3 (843).
Die Nutzer-Downloads von Macintosh Repository sind laut Nutzer Juni/Aug. 2009,
also älter. Fürs Archiv: 1.4 ist der jüngste bekannte Stand.

**Inhalt Crusher.framework/Resources (MG1264-Teil):**
- `qmmapp.seve1-eb-8mb.bin` (419.772 B) und `qmmapp.seve1-eb-16mb.bin`
  (421.748 B): MG1264-Firmware im **selben MBY0-Format wie beim PVT**. Das
  vorhandene `unpack_u8_lzo.py` entpackt beide unverändert, alle Adler-32-
  Prüfsummen stimmen (je 8 LZO-Blöcke).
- Sieben Produktkonfigurationen à 352 Byte (`vgaconfig.bin`,
  `vgaconfig_16mb.bin`, `qvgaconfig.bin`, `qvgaconfig_8mb.bin`,
  `qvgaconfig_16mb.bin`, `newqvgaconfig2.bin`, `arbiconfig_16mb.bin`):
  **dasselbe Format wie Pinnacles Tabelle** (Kopf ver=2, type=0, offset=0,
  size=84, dann 84 Parameter), nur little-endian gespeichert.
- Klartext-Encoderskripte im Mobilygen-„webserver backend“-Format
  (`vga.txt`, `qvga.txt`, `*_qbox.txt`, `rate_*.txt`), `FX2Firmware.hex`.

**Versionsvergleich (aus den SVN-`$Id$`-Zeilen der Firmware):** Elgatos
MG1264-Firmware ist **älter** als die des PVT. Höchste Quellrevision Elgato
r6695 (13.07.2006), PVT 00.01.07.28 r10201 (12.06.2007). Muxer (`mux.cpp`
r5240 vs. r10201, `mux_qbox.cpp` r6612 vs. r10201) und Demuxer sind beim PVT
neuer, der AAC-Decoder fehlt bei Elgato. **`buffctrl.cpp` ist in beiden
identisch (r5966).** Elgato bringt also keine neuere Firmware mit Fehlerbehebungen;
der Nutzen liegt in den Konfigurationen.

**Parameterbedeutung jetzt aus dem MG-Code belegt** (PVT-Firmware, MEInit ab
MG 0x57558, Pool-Belegung 0x572C8, Parameterzugriff 0x57074):
- p00: 1 = gemeinsamer Pool für Encoder und Decoder (Summe), 0 = getrennte,
  sich überlappende Pools (Pinnacle: 0)
- p01: erste Pufferseite (0 = automatisch hinter der Firmware), p02: Anzahl
  verfügbarer Seiten. Seitengröße 2048 Byte. Die MG prüft jede Belegung gegen
  p02 und meldet sonst „MEInit Error: fail to alloc“.
- p03: „mux vid“ (Video-Ausgabepuffer) in Seiten, p04: „mux aud“,
  p08: Eingangsbilder, p12/p13: „demux video/aud“ (nur Decoder-Seite).

| | PVT (CF 0x2A61A) | Elgato VGA | Elgato QVGA | Mobilygen-Standard (MG-Tabelle 0) |
|---|---|---|---|---|
| p00 Pool-Modus | 0 getrennt | 1 gemeinsam | 1 | 1 |
| p01 Startseite | 1024 (2 MiB) | 0 (auto) | 0 | 2048 |
| p02 Seiten | 5120 (Ende 12 MiB) | 6144 | 6144 | 14336 |
| p03 Video-Ausgabe | **832 (1,6 MiB)** | **2048 (4 MiB)** | 512 (`qvga`), 2048 (`qvga_16mb`) | 2048 |
| p04 Audio-Ausgabe | 48 | 1 (kein Ton) | 1 | 256 |
| p08 Eingangsbilder | 6 | 6 | 6 | 8 |

**Speicherbudget per Emulation (Code-/Modellbefund).** Eigener kleiner
MG-Emulator (`mgemu.py`) führt MEInit der PVT-Firmware mit Pinnacles Tabelle
aus und protokolliert jede Belegung. Encoder-Seite mit Originalwerten:
6 Eingangsbilder × 324 Seiten (768×576 4:2:0) = 1944, 2 Encoderbilder = 648,
Statistik/Befehle/Audio-Eingang ≈ 129, mux vid 832, mux aud 48 →
**3601 von 5120 Seiten, Ende bei 9,03 MiB.** Frei: 1519 Seiten (≈ 3 MiB).
- p03 = 2048 → 4817 Seiten, Ende 11,41 MiB, passt (303 Seiten Reserve).
- p03 = 2351 → genau 5120 Seiten (Obergrenze).
- p03 = 2352 → Emulation meldet „fail to alloc [mux aud]“ — die MG-eigene
  Prüfung greift, kein stilles Überschreiben.
Gegenproben: Pinnacles eigene eingebaute MG-Tabelle (gemeinsamer Pool,
p01=1024, p02=7168) endet bei 15,88 MiB, schon der Originalstand braucht über
9 MiB → **der PVT hat 16 MiB (128 Mbit) SDRAM.** Elgatos VGA-Tabelle
emuliert (Startseite automatisch aus dem Bootkopf) bis 15,82 MiB;
`qvgaconfig_8mb.bin` ist mit p01+p02 = 4096 Seiten exakt auf 8 MiB zugeschnitten.
Einschränkungen: vier Objekt-Hilfsroutinen wurden übersprungen, ein Befehl
(0x8C00-Familie) vorläufig gedeutet; die Poolgrößen hängen nachweislich nicht
davon ab (Ergebnis bei beiden Deutungen identisch).

**Folgerung für den Firmwareversuch:** Einziger zu ändernder Wert:
CF-Datei **0x2A626** (Laufzeit 0x2E626), big-endian `00000340` (832) →
`00000800` (2048). p01/p02 und p12 (demux video, ebenfalls 832) NICHT ändern.
Erwartung: Die Stotter-Marke wandert von ca. 1,49 MB auf ca. 4,0 MB
(≈ +4 s bei 5 Mbit/s). Da die Störphase bisher nach 5,3–5,6 s (LED1/LED2)
endet, könnte sie ganz verschwinden. **Offen und nur am Gerät prüfbar:** ob
der ColdFire mehr ausstehende Blöcke verträgt (Warteschlangengröße auf
CF-Seite unbekannt). Rückkehrdatei bereithalten.

---

## 11. Was weiterhin ausdrücklich fehlt

Fortsetzungsdatei nach 4 GiB; Originalfirmware-Langzeitlauf zum Vergleich;
ColdFire-Schreibpfad-Analyse; Beweis, dass der Puffer die Stotterursache ist
(nur eingegrenzt, nicht bewiesen). Erledigt: zweite MG-Firmware vom Crusher
(Abschnitt 10b, älter als die des PVT) und MG-seitige Obergrenze für den
Videopuffer (2351 Seiten, empfohlen 2048). Keine neue
Firmware wurde in dieser Phase erzeugt.

---

## 12. Test AC: AB + Videopuffer 2048 Seiten (gebaut 10.10.2026, 0 Hardwaretests)

**Hardware bestätigt (Nutzerfoto der Platine):** Mobilygen **MG1264B**
(Datumscode 0744, Stepping FA0) mit Samsung **K4S281632I-UC60** daneben:
128 Mbit SDRAM, 8M × 16, 3,3 V, 6 ns (166 MHz), Datumscode 801 (Anfang 2008).
Das sind **16 MiB**, das Maximum für den MG1264, und deckt sich mit der
Emulation (Originalstand belegt > 9 MiB, Pinnacles eingebaute MG-Tabelle endet
bei 15,88 MiB).

**Paket `PVT_TEST_AC_PUFFER.zip`:**
- `01_INSTALL/CFUPDATE.BIN` = Test AB mit p03 „mux vid“ 832 → 2048 Seiten.
  Geänderte Bytes: CF-Datei 0x2A628 `03→08`, 0x2A629 `40→00`, sonst nichts.
  SHA-256 `070d43a45529fae1cbe07648051a9c87ff7ba57c7acf7b8c207590f088a34957`.
- `02_RETURN_AB`, `03_RETURN_ORIGINAL` (01.00.46.03) als Rückkehrdateien.
- `04_OPTIONAL_ORIGINAL_PLUS_PUFFER` = Original + derselbe eine Wert
  (SHA-256 `fd867d81…0b92`), nur für den Vergleich nach dem Original-Langzeittest.
- `werkzeug/build_ac.py` baut beide Varianten reproduzierbar aus AB oder
  Original (Basis-Hash wird geprüft), `check` prüft eine Datei.
  Dazu der MG-Emulator (`mgemu.py`, `run_meinit.py`, `pvt_mem.py`, `qdis.py`).

**Geprüft ohne Gerät:** (1) Die ColdFire-Firmware kopiert die Tabelle als
Ganzes (88 Worte ab 0x2E60A) an den MG; der Wert 832 kommt in der CF-Firmware
sonst nirgends vor, auch nicht als 832 × 2048. (2) CFUPDATE.BIN trägt keine
Prüfsumme (AB änderte 3291 Bytes ohne Kopf-/Endänderung und lief). (3) MG-
Emulation mit genau der AC-Tabelle: Encoder-Pool 4817/5120 Seiten, Decoder-Pool
unverändert 3504, kein Fehler. (4) Schutzabstand („guardband“, Encoderfeld
+0x4DC) wird im MG-Code als Objektfeld +0x30 × Encoderfeld +0x744 berechnet;
die Puffergröße (+0x54) geht nicht ein → Erwartung Marke ≈ 4,19 MB − 0,32 MB
≈ **ca. 4,0 MB** statt 1,49 MB, oder Störung verschwindet ganz (bisheriges
Störende bei 5,3–5,6 s).

**Nicht geprüft:** ColdFire-Verhalten bei mehr ausstehenden Bitstromblöcken.
Mögliche Ausgänge am Gerät: (a) keine Störung mehr / Marke bei ~4 MB → Puffer
ist die Ursache; (b) Marke bleibt bei 1,49 MB → Puffer ist nicht die Ursache,
Hypothese verworfen; (c) Aufnahme startet gar nicht (sofort rotes Blinken) →
MG lehnt Tabelle ab oder CF-Blockverwaltung überfordert; zurück zu AB.
Testablauf und Abbruchkriterien: `README_INSTALL_DE.txt` im Paket.

---

## 13. Ergebnis Test AC (Nutzeraufnahmen 10.10.2026, drei Clips, je ca. 2 min)

| | AC/LED1 Test 1 | AC/LED1 Test 2 | AC/LED3 |
|---|---|---|---|
| leere Bilder (Stottern) | **0** | **0** | **0** |
| Beginn der Störung | keine (3 Verdachtsbilder ab 42 s) | keine | keine |
| Ton minus Video | **12,7 s** | **10,0 s** | 0,86 s |
| Verlust beginnt | 20,2 s (10,0 MB Video) | 22,9 s (11,7 MB) | 24,1 s (14,4 MB) |
| Datenrate | 3,7–4,0 bis 17 s, dann ~5,0 (wechselnd 5,3/4,6) | wie Test 1 ab ~21 s | ab 6 s stetig 5,0 |
| QP | 16–26, Mittel 20,6 | 17–26, 21,0 | 17–24, 20,5 |

**Bestätigt (Messbefund am Gerät):** Die feste 1,49-MB-Marke ist mit 2048
Seiten Videopuffer in allen drei Clips verschwunden. Der zu kleine Puffer war
die Ursache des Anlaufstotterns.

**Neu (Messbefund):** AC verliert laufend Videozeit ohne Platzhalter (wie
Z/LED2), beginnend sobald die Datenrate ca. 5 Mbit/s erreicht, bei LED1 rund
10 % der Zeit, bei LED3 (enge Größentoleranz) nur 0,7 %. Mit AB lief dieselbe
Rate 1 h 53 min ohne Verlust (VID00004). **AC ist nicht aufnahmetauglich;
Vorführstand bleibt AB/LED1 + Vorlauf.** Mechanismus offen; Beobachtung: der
Verlust hängt an der Rate und am LED-Profil, nicht an der Pufferfüllung
(Beginn erst bei 10–14 MB Videodaten, weit hinter dem 4-MiB-Puffer).

**Nächster Schritt gebaut:** Test AD (`PVT_TEST_AD_PUFFER_1536.zip`) =
AB + 1536 Seiten (3 MiB), SHA-256 `e17853854d1d…8fce9`, Bytes 0x2A628 `03→06`,
0x2A629 `40→00`. Emulation: 4305/5120 Seiten. Entscheidet, ob ein mittlerer
Wert das Stottern ohne den Verlust beseitigt. Auswertung: Zeilen „leer“ (soll
0) und „Ton minus Video“ (soll < 0,2 s) in `pvt_check.py`.

**Nebenbefund (12:05):** Drei Clips mit `04_OPTIONAL_ORIGINAL_PLUS_PUFFER`
(Original 01.00.46.03 + 2048 Seiten) versehentlich statt AD aufgenommen:
LED1 = 320×240 Baseline 0,77 Mbit/s, LED3 = 720×576 Baseline 1,49 Mbit/s,
Vollbilder, Schlüsselbild alle 2,4 s, QP 22–28. Kein Stottern, kein Verlust,
Ton/Bild deckungsgleich (bei ≤ 1,5 Mbit/s erwartbar). Erster Beleg, dass auch
die Originalfirmware die geänderte Tabelle annimmt und normal aufnimmt. Zugleich
die ersten vermessenen Originalprofile (Vergleichswert für die Vorführung).
AD (AB + 1536) damit noch ungetestet.

---

## 14. Ergebnis Test AD (1536 Seiten) und Neudeutung des Verlusts (10.10., 12:40)

| | AD/LED1 Test 1 | AD/LED1 Test 2 | AD/LED3 |
|---|---|---|---|
| leere Bilder | 0 | **2** (+9 klein) bei 5,8–7,0 s nach **2,94 MB** | 0 (10 klein/13 teil bei 9–11 s) |
| Ton minus Video | **7,6 s** | **8,2 s** | 0,9 s |
| Verlust beginnt | 22,4 s | 22,9 s | 10,6 s |
| Datenrate / QP | 4,80 / 16–26 | 4,81 / 17–24 | 4,95 / 17–24 |

**Puffer zum zweiten Mal bestätigt:** Die Stottermarke skaliert mit p03:
832 Seiten → 1,49 MB, 1536 Seiten → 2,94 MB (Rechnung 3,15 MB − 0,32 MB
Schutzabstand ≈ 2,8 MB + Eingangsbilder), 2048 Seiten → keine Marke mehr.
1536 ist knapp (Stall endet ohnehin bei ~5,5 s); **2048 bleibt der Wert.**

**Verlust neu gedeutet (Messbefund + Hypothese):** Der laufende Videozeit-
verlust ist mit 1536 und 2048 gleich → hängt nicht an der Puffergröße. Er
hängt am Inhalt und am RC-Profil:
- je Sekunde korreliert der Verlust mit der Datenmenge dieser Sekunde
  (r = 0,6–0,8), in Sekunden mit Schlüsselbild doppelt so hoch;
- LED1 (lockere Größentoleranz, Sekunden bis 5,6 Mbit) verliert 6–13 %,
  LED3 (enge Toleranz, stetig 5,0) 0,7 %;
- **AB/LED3 hatte ihn schon** (0,49 s in 2 min, 0,2-s-Spitze 6,9 Mbit/s),
  AB/LED1 nachts nicht: Rauschen liefert gleichmäßige Bilder ohne Spitzen
  (0,2-s-Spitze 5,9–6,4 Mbit/s). Der Langzeitlauf war deshalb verlustfrei.
Verdacht: die in den Testfirmwares aktivierte **Puffer-Regelung** (RC9–12:
Modell 1,25 Mbit bei 5 Mbit/s = 0,25 s, Anfang 11250 Ticks) verwirft Bilder,
wenn Spitzen das Modell überfahren. Passt zu Z/LED2 (Delay 5625 → Verlust).
Die Originalfirmware setzt RC9–12 nicht; Elgato gibt dem Chip 1–5 s Modell.

**Test AE gebaut** (`PVT_TEST_AE_RC_VARIANTEN.zip`, SHA-256 `d4ae6a9b…07a7`,
18 geänderte Bytes gegenüber AB, nur Zahlenwerte in den AB-RC-Setzern bei
CF 0x2E11E–0x2E478 plus p03 = 2048):
LED1 = Puffer-Regelung aus (wie Original) · LED2 = Modell 5 Mbit/0,5 s, Größen-RC an ·
LED3 = Modell 10 Mbit/1,0 s, Toleranz 25 Mbit. Deutung siehe README im Paket.
Lage der RC-Konstanten in AB (je LED ein Block, Abstand 0x158; Werte als
`move.l #imm` vor dem Index): LED1 RC9 0x2E11E, RC10 0x2E140, RC11 0x2E162,
RC12 0x2E184, RC6 0x2E1A6, RC7 0x2E1C8; LED2 +0x158; LED3 +0x2B0.

---

## 15. Ergebnis Test AE (10.10., 13:33): alle drei Varianten sauber

| | AE/LED1 (Puffer-RC aus) | AE/LED2 (Modell 5 Mbit/0,5 s) | AE/LED3 (Modell 10 Mbit/1 s) |
|---|---|---|---|
| Dauer | 147 s | 138 s | 127 s |
| leere / kleine Bilder | 0 / 0 | 0 / 0 | 0 / 0 |
| Ton minus Video | −0,02 s | −0,03 s | −0,04 s |
| mdhd = stts | ja | ja | ja |
| Datenrate | **5,00** (4,3–5,5, σ 0,16), ab Sekunde 1 | 4,90 | 4,97 |
| QP | 21–24, Mittel 21,3 | 17–24 | 17–24 |
| 0,2-s-Spitze | 7,19 Mbit/s | 6,90 | 7,26 |

Gegenprüfung unabhängig von `pvt_check.py`: ffprobe zählt 3680/3454/3169
Bilder bei 25/s = exakt den stts-Dauern; ffmpeg `freezedetect` findet in den
ersten 30 s von LED1 keine wiederholten Bilder (decodierte Pixel).

**Beide Fehler sind damit am Gerät gelöst und ursächlich zugeordnet:**
1. Anlaufstottern ← zu kleiner MG-Videopuffer (Pinnacle 832 Seiten).
   Fix: p03 = 2048 Seiten (CF-Datei 0x2A626).
2. Laufender Videozeitverlust bei Spitzen ← die in den Testfirmwares (ab T/U)
   aktivierte Puffer-Regelung mit 0,25-s-Modell. Fix: aus (wie Original), oder
   Modell ≥ 5 Mbit; beides verlustfrei.

**Kandidat für Vorführung und Langzeitlauf: AE/LED1** (Original-Regelung +
Größen-RC 25 Mbit + 2048 Seiten; 5,00 Mbit/s ab der ersten Sekunde, engste
QP-Spanne). LED2/LED3 sind gleichwertige Alternativen mit Modellpuffer.
Vorlauf-Umgehung nicht mehr nötig.

**Offen (nur noch eine Frage):** der 4-GiB-Dateiwechsel (Abschnitt 3a). Nächster
Schritt: Langzeitlauf mit AE/LED1 über 2,5 h (Wechsel bei ~1 h 53 min bei
5 Mbit/s), Tagesmotiv. Entsteht VID-Fortsetzungsdatei ohne rotes Blinken, ist
die Firmware vorführreif. Falls nicht: Fehlerbehandlung der AB-Patches auf
Originalverhalten zurücksetzen (Abschnitt 3b, 6) → Test AF.

---

## 16. Langzeitlauf AE/LED1 bestanden (10.10., 16:20) — Vorführstand steht

| | VID00001.MP4 | VID00002.MP4 (Fortsetzung) |
|---|---|---|
| Größe | 4.258.121.264 Byte (3,966 GiB) | 1.406.049.973 Byte |
| Dauer | 1 h 52 min 54 s | 37 min 17 s |
| Datenrate | 5,00 Mbit/s (4,3–5,6, σ 0,20; 0 s unter 4,0) | 5,00 (σ 0,21) |
| QP | 19–24, 67 % bei 21 | 19–24 |
| leere / kleine Bilder | 0 / 0 | 0 / 0 |
| Ton minus Video | −0,035 s, konstant −0,02 über die ganze Datei | −0,027 s |
| Index (moov) | 3,9 MB, sauber | 1,3 MB, sauber |

**Der 4-GiB-Dateiwechsel funktioniert**, die Fortsetzungsdatei beginnt ohne
Stottern (5,0 Mbit/s ab Sekunde 1). Damit ist auch die letzte offene Frage aus
Abschnitt 3a geschlossen. Gesamt 2 h 30 min 11 s ohne einen einzigen Befund.

**Warum der Wechsel mit AB (VID00004) scheiterte — Hypothese, nicht bewiesen:**
Beim Schließen der 4-GB-Datei schreibt der ColdFire 3,9 MB Index und legt die
neue Datei an; in dieser Zeit liefert der MG weiter 5 Mbit/s. Der alte Puffer
(832 Seiten) hält nur 2,7 s, der neue (2048) 6,7 s. Läuft der Puffer über,
schlägt ein MG-Befehl fehl, und die Fehlerbehandlung der Testfirmwares bricht
ab (rotes Blinken). Passt zu allen Beobachtungen; direkt prüfbar wäre es nur
mit AB und einer Stoppuhr am Dateiwechsel. Für den Vorführstand unerheblich.

**Vorführstand = `PVT_AE_LED1_VORFUEHRSTAND.zip`**: AE (SHA-256 `d4ae6a9b…07a7`)
auf LED1, Rückkehrdateien AB und Original, `pvt_check.py` + .bat, Prüfberichte
der Kurzclips und des Langzeitlaufs, `build_ae.py` für den Neubau aus AB.
Eingefroren; bis zur Veranstaltung keine Firmwareänderung mehr.

**Noch zu tun vor der Veranstaltung (ohne Firmware):** einmal mit echter
Tonquelle aufnehmen (alle Tests bisher mit Stille), Synchronität anhören.

**Nach der Veranstaltung (optional):** LED2/LED3 mit anderen Bitraten belegen
(3,5 / 7–8 Mbit/s, jeweils eigener Test); sauberer Neubau direkt aus dem
Original mit nur den drei belegten Änderungen (Puffer 2048, 5 Mbit/s-Profil,
Regelung) für eine Veröffentlichung; Elgato-Software archivieren (Abschnitt 10).

---

## 17. Nach dem Vorführstand: Test AF (8/7 Mbit/s) gebaut, ungetestet (10.10., 16:45)

**Bitrate im Firmwarestand:** global, nicht je LED. Sie steht als `move.l #kbps`
an zwei Stellen: nativer Qualitätspfad CF-Datei **0x08108** (Original dort
1500 = Pinnacles „Best“ 1,5 Mbit/s; seit T/U 5000) und erzeugter Qualitätscode
**0x2C002** (Laufzeit 0x30002), beide schreiben die RAM-Variable 0x2000025A
(kbit/s). Native Profilwahl: ≤ 1500 Low, ≤ 3500 Medium, darüber High.
RC7 (Größentoleranz) und RC30 folgen nativ der Formel kbit/s × 5000; AB/AE
überschreiben RC7 mit einer Konstante je LED (0x2E1C8/0x2E320/0x2E478).

**`PVT_TEST_AF_HOEHERE_RATE.zip`:** AF8 (8000 kbit/s, SHA-256 `5064bb21…537c`)
und AF7 (7000, `630780bd…4833`), je 27 Bytes gegenüber AE: Videoziel an beiden
Stellen, RC7 = kbps × 5000, RC9 aus auf LED2/LED3, RC11 = kbps × 1000. Alle
drei LEDs identisch (= AE/LED1-Regelung). Rückkehr: AE. Testplan im README.
Unbekannt: USB-Dauerlast bei 1 MB/s, native Klammerung oberhalb 5000.

**Befund zum 2-s-Pumpen (Nutzerbeobachtung, Messung Langzeitlauf):** Das
Schlüsselbild ist „IP“ (oberes Halbbild intra, unteres P). QP der I-Bilder
20,93, der P-Bilder 20,96 → kein QP-Sprung; der sichtbare Wechsel ist Intra-
Neucodierung des Rauschens, das die P-Bilder (Skip) sonst einfrieren. Hebel:
mehr Datenrate (kleinerer Wechsel), längerer GOP (seltener). Nicht abschaltbar.

---

## 18. Ergebnis AF8 (16:46): Durchsatzgrenze des Schreibpfads gemessen

AF8 (Ziel 8000 kbit/s) wurde durchgereicht: Encoder 8,17 Mbit/s, QP 14–24,
Sekunden bis 9,9 Mbit/s. **Nach 4,16 s / 4,21 MB (= der 4-MiB-Puffer) Dauerstau:**
156 leere + 831 kleine Bilder, 50,7 s von 140,6 s Videozeit verloren (36 %).
Die Datei wuchs dabei mit der maximal möglichen Rate: **92,3 MB in 140,6 s =
0,656 MB/s = 5,25 Mbit/s.** Das ist die Obergrenze des ColdFire/USB-Schreibpfads
auf der Test-SSD. Der AE-Langzeitlauf lag bei 5,03 Mbit/s, also **96 % davon.**
Folgerung: 5 Mbit/s bleibt; 7 Mbit/s nicht getestet (liegt ebenfalls über der
Grenze); 5,5 Mbit/s nicht ratsam. Warum 5,0 trotzdem stabil läuft: die
Größen-RC-Toleranz (25 Mbit = 3,1 MB) ist kleiner als der 4-MiB-Puffer, der
Encoder kann dem Mittel nie weiter vorauslaufen, als der Puffer fasst.
Nebenbefund: der Stau setzte exakt beim Puffervolumen ein — dritte Bestätigung
der Puffergröße.

Optionen für mehr Durchsatz, alle außerhalb des Projektziels: ColdFire-USB-
Schreibpfad (Blockgröße/Transfers) ändern = Codeanalyse und -änderung; billiger
Vorversuch ohne Firmware: SSD mit 64-KB-Clustern formatieren und AF8 2 min
laufen lassen (ändert nur die FAT-Last). Für die Veranstaltung: dieselbe SSD
wie im Langzeitlauf verwenden, da die Grenze vom Medium abhängen kann.

**Nachtrag 18:28, Clustergrößen-Versuch:** zweite Platte mit MBR/FAT32 und
64-KB-Clustern (`pvt_platte.py`), AF8, 2 min: Schreibrate 0,658 MB/s =
5,26 Mbit/s (vorher 5,25). Stau erst nach 9,5 s / 9,5 MB statt 4,2 s (Schreib-
cache der Platte), Dauerrate identisch. **Die Grenze liegt im USB-Pfad des
ColdFire, nicht in der FAT-Verwaltung. 64-KB-Cluster werden vom PVT akzeptiert.**
Für die Veranstaltung bleibt die SSD aus dem Langzeitlauf.

---

## 19. „AE rein“: AE/LED1 auf allen drei Stufen (18:45, ungetestet auf LED2/LED3)

`PVT_AE_REIN_LED1_ALLE.zip`, SHA-256 `6e39e44e…7d99`. Aus AB mit 9 Bytes:
p03 = 2048, RC9 = 0 auf allen LEDs, LED2 RC6 = 1, LED3 RC7 = 25 Mbit. Der
LED1-Block ist byteidentisch mit AE (Langzeitlauf), LED2/LED3 sind wertgleich
dazu → MODE-Stellung egal. Vor Übernahme als Vorführstand je 2 min auf LED2
und LED3 prüfen. `build_aer.py` baut und prüft (drei wertgleiche Blöcke).

---

## 20. Nachtfahrt auf der neuen Platte (20:21): die Platte, nicht das Rauschen

Drei Aufnahmen (14 min Tag→Dämmerung, 7 min, 8 min Nacht, Stadt, Beifahrer),
AE-Stand, 5,00 Mbit/s, QP 25–27, **auf der neuen 64-KB-Platte**. Befund:
- Alle drei sauber bis **116 / 119 / 130 MB** geschriebener Daten (186–208 s),
  auch die reinen Nachtclips — danach Stau-Gruppen von 10–16 s Dauer alle
  40–50 s (leere + kleine Bilder), bis zum Ende. Mittlere Produktion vor und
  nach dem Einsetzen identisch 5,00 Mbit/s.
- Effektive Schreibrate über die Echtzeit (mdhd): 4,91 / 4,94 / 4,81 Mbit/s —
  **unter der Produktion.** mdhd − stts = 20 / 7,5 / 22 s: so lange stand die
  ganze Aufzeichnung (Bild und Ton gemeinsam, Synchronität bleibt).
- Deutung: Die neue Platte hat ~120 MB schnellen Schreibcache (deshalb im
  2-min-Test 5,26 Mbit/s), danach fällt sie auf < 5 Mbit/s mit periodischen
  Pausen (Flash-Aufräumen). Die Langzeit-SSD lief 2,5 h ohne das.
- Rauschen: nicht die Ursache (Produktion bleibt 5,00; die ersten 3 Minuten
  der Nachtclips sind sauber), nur höherer QP (26 statt 21).
**Konsequenz:** neue Platte nicht fürs PVT; bei Platten vor Einsatz einen
≥ 10-min-Lauf prüfen (Stau nach ~2–3 min = Cache-Platte). Vorführung mit der
Langzeit-SSD.
Neue Platte laut Nutzer: Intenso M.2-SATA-SSD in USB-Gehäuse mit Realtek
RTL9210B-Bridge. Intenso-M.2-SATA sind DRAM-lose Billig-SSDs (SLC-Cache klein,
Mapping-Tabelle nur im Controller-SRAM); die vielen kleinen Schreibzugriffe des
ColdFire bringen so eine FTL nach kurzer Zeit in periodische Aufräumpausen —
passt zu „~120 MB sauber, dann Pausen alle 45 s“. Für das PVT also SSDs mit
DRAM-Cache oder die bewährte Langzeit-SSD; jede Platte ≥ 10 min testen.

**Bekannt gute Aufnahmeplatte (Langzeitlauf 2,5 h):** Kingston **SH103S3/240G**
(HyperX 3K, SandForce SF-2281, MLC-NAND, Datecode 1335 = Ende August 2013) in
einem AliExpress-Gehäuse mit Initio **INIC-1618N**-Bridge. Das ist eine SSD ohne
SLC-Cache-Klippe: MLC wird direkt beschrieben, der Durchsatz bleibt konstant.
Faustregel präzisiert: nicht „DRAM-Cache“ ist entscheidend (die SandForce hat
keinen), sondern **kein Einbruch nach dem Schreibcache** — MLC-SSDs der
2012–2015-Generation oder gute TLC mit DRAM; QLC/DRAM-los meiden; ≥ 10 min testen.

---

## 21. Generalprobe auf einer kleinen Veranstaltung (11.10.2026): 5 h 03 min, zwei 4-GiB-Wechsel

| Datei | Dauer | Mbit/s (σ) | leer / klein / teil | Ton − Video | mdhd = stts |
|---|---|---|---|---|---|
| VID00001 (manuell) | 5 min 44 s | 5,00 (0,52) | 3 / 1 / 6 bei 322,2–323,1 s | −0,003 s | ja |
| VID00002 (manuell) | 32 min 45 s | 5,00 (0,50) | 0 / 0 / 0 | −0,048 s | ja |
| VID00003 | 1 h 52 min 54 s (4 GiB) | 5,00 (0,53) | 0 / 6 / 13 bei 68,6–69,4 s | −0,056 s | ja |
| VID00004 (Fortsetzung) | 1 h 52 min 54 s (4 GiB) | 5,00 (0,47) | 0 / 0 / 0 | −0,032 s | ja |
| VID00005 (Fortsetzung) | 39 min 24 s | 5,00 (0,49) | 0 / 0 / 0 | −0,040 s | ja |

VID00003→04→05 ist **eine durchgehende Aufnahme von 4 h 25 min mit zwei 4-GiB-
Dateiwechseln**, beide sauber, beide Fortsetzungen ohne Anlaufstottern. Inhalt
deutlich bewegter als bisher (QP 13–42, 0,2-s-Spitzen bis 18 Mbit/s), das
System hat alle Spitzen aufgefangen.
- VID00001, 322,2–323,1 s: unregelmäßiger Wechsel normaler (27–72 KB), winziger
  (2–7 KB) und drei leerer Bilder, QP fällt kurz 28→22. Kein Puffermuster (das
  wären zusammenhängende Platzhalter), sondern Signal-/Quellenseite (Kabel,
  Umschalten, Sync-Verlust) — 1 s in 5 h.
- VID00003, 68,6–69,4 s: kleine Bilder mit QP 26→15 = statischer/dunkler Inhalt,
  kein Fehler.
Damit sind **AE-Stand und Kingston-SSD (sofern verwendet) über 7,5 h Aufnahme
mit drei 4-GiB-Wechseln belegt.** Tonspur weiterhin ~24 kbit/s (Stille) —
der Tontest mit echter Quelle steht noch aus.

**Platte der Generalprobe (Nutzerangabe 19:48):** die „neue“ Platte, nach dem
Plan vom Vorabend die **SanDisk Ultra 3D 512 GB (SDSSDH3-512)**, mit
`pvt_platte.py` frisch als MBR/FAT32 angelegt. Damit zweite bekannt gute
Platte: 5 h 03 min, zwei 4-GiB-Wechsel, 0 leere Bilder. Audiokabel war nicht
dabei → Tontest weiterhin offen.

**Stromverbrauch (Nutzerangabe 19:56):** PVT + SSD liefen die kompletten
5 h 03 min an einer 5000-mAh-Powerbank (USB-C → 5,5×2,5-mm-Adapter mit
CC-Widerständen), Ende bei 2 % Rest. Rechnung: ~18,5 Wh nominal, ~16 Wh nutzbar
→ **ca. 3,2 W = 0,64 A bei 5 V** für PVT + SSD. Faustregel: 10 000 mAh ≈ 10 h,
20 000 mAh ≈ 20 h. Kamera + Rückfahrmonitor liefen mit 12 V PD an einer
10 000-mAh-Bank (danach halb voll). Videosignal passiv auf PVT und Monitor
gesplittet, keine sichtbare Bildänderung (AGC am Eingang gleicht den Pegel-
verlust zweier 75-Ω-Abschlüsse aus).

---

## 22. Hardware identifiziert (Platinenfoto 12.10.2026) — die 5,25-Mbit/s-Mauer ist Architektur

Platine **„Stimpy V1.0“, 8520-00189-01** (Lesung korrigiert 12.10., 17:50 —
der Bootloader heißt „STIMPY-BL“, vorher fälschlich „Stingray“). Host-CPU **Freescale
ColdFire MCF52223CAF80** (V2-Kern, 80 MHz, 256 KB Flash, 32 KB SRAM, LQFP-100,
Datumscode 0743). Datenblatt Rev. 3 (3/2011), S. 5: USB OTG mit
**„Full-speed / low-speed host controller“** → USB 1.1, 12 Mbit/s, kein
High-Speed. Blockschaltbild S. 4: **kein externer Bus** (nur GPIO, QSPI, UART,
I²C) → die 16-Bit-Hostschnittstelle des MG1264 wird per GPIO von der CPU bedient
(Registerzugriffe bei 0x4000… in der Firmware = IPSBAR-Peripherie). Gemessene
0,656 MB/s = 44 % der rohen USB-Bitrate — für einen Software-FS-Host das obere
Ende. **Kein Drop-in-Ersatz:** MCF5225x pinverwandt, aber ebenfalls nur FS-USB;
HS-USB-ColdFires (MCF5329/5373) andere Gehäuse/PHY. Der SDRAM gehört dem MG.
Der Typ-B-Anschluss hängt am selben einzigen OTG-Controller (Gerätemodus, FS).
Weitere Bausteine: Spansion S25FL008A bei **U8** = SPI-Flash mit der MG-Firmware
(daher „U8DUMP“), PCA9535-I/O-Expander (U7, LEDs/Tasten), 74LVC14A/LVC08A,
Video-ADC ADV7xxx (unten), zwei 4,7-µH-Buck-Wandler. SDRAM dieses Geräts:
K4S281632I-**UC75** (Woche 43/2007); das Gerät vom ersten Foto hatte -UC60
(2008) → mindestens zwei Fertigungslose beim Nutzer.
Mehr Durchsatz nur mit neuem Host-Teil (eigener MCU + SD-Karte an der MG-
Hostschnittstelle; MG bootet selbst, muxt selbst) — eigenes Projekt.

---

## 23. Unbestückter 2×13-Port neben dem ColdFire: vermutlich BDM-Debugport (12.10.2026, Vermutung, Messung steht aus)

Der Nutzer misst den unbestückten Port durch. **Ein Videodatenstrom ist dort
nicht abgreifbar** (Weg: MG1264 → 16-Bit-Hostschnittstelle an GPIO → ColdFire-
RAM → USB; keine Zwischenstation auf einem Steckverbinder). Wahrscheinlicher
und wertvoller: 2×13 = 26 Pins = Freescale-Standard-BDM-Stecker für ColdFire.

**MCF52223, LQFP-100, Pinnummern (Datenblatt Rev. 3, Fig. 2 / Tab. 4).**
Pin 1 an der Punktmarke, Zählung gegen den Uhrzeigersinn: links 1–25 (oben nach
unten), unten 26–50, rechts 51–75 (unten nach oben), oben 76–100 (rechts nach
links). Debugsignale sitzen gebündelt an der Ecke 75/76 (oben rechts):

| Signal (BDM-Modus / JTAG-Modus) | MCU-Pin | BDM-Stecker-Pin |
|---|---|---|
| BKPT / TMS | 76 | 2 |
| DSCLK / TRST | 85 | 4 |
| PSTCLK (CLKOUT) / TCLK | 64 | 24 (und 6) |
| RSTI | 96 | 7 |
| DSI / TDI | 79 | 8 |
| DSO / TDO | 80 | 10 |
| PST3, PST2, PST1, PST0 | 70, 69, 66, 65 | 12, 13, 14, 15 |
| DDATA3, DDATA2, DDATA1, DDATA0 | 84, 83, 78, 77 | 16, 17, 18, 19 |
| ALLPST | 86 | — |
| GND | 3,15,24,25,35,42,56,67,75,82,92 | 3, 5, 11, 20, 23 |
| 3,3 V (VDD) | 1,2,14,22,23,34,41,57,68,81,93 | 9 (VDD_CPU), 25 (VDD_IO) |
| JTAG_EN (intern Pull-down: low = BDM) | 26 | — |
| TEA (bei V2 unbenutzt) | — | 26 |
| unbenutzt | — | 1, 21, 22 |

Weitere Pins für andere Hypothesen: **EzPort** (SPI-Zugriff auf den internen
Flash im Reset): RCON/EZPCS 21, EZPCK 18, EZPD 16, EZPQ 17 (+ RSTI 96).
**UARTs:** UART0 RX 7 / TX 8 (RTS 9, CTS 6), UART1 RX 100 / TX 99,
UART2 RX 28 / TX 29. USB: DM 61, DP 60. TEST-Pin 5 (an GND).

**Messplan (stromlos, Durchgangspiepser, feine Nadel an den Pinfüßen):**
1. Masse-Pads finden (Durchgang zu USB-Schirm / Minus der Buchse). Muster
   3/5/11/20/23 legt die Orientierung fest (Pad 1 = eckiges Pad).
2. Pad 2 ↔ MCU 76 und Pad 4 ↔ MCU 85 → BDM bestätigt. Dann 8 ↔ 79, 10 ↔ 80,
   7 ↔ 96, 24 ↔ 64.
3. Kein Durchgang zu irgendeinem ColdFire-Pin → Port gehört dem MG1264
   (dessen Debug/JTAG).
4. Der bestückte Header ist ein **2×5-Serviceanschluss, auf der Unterseite
   beschriftet, kombiniert SPI + UART** (Korrektur 17:50 nach Screenshots der
   ChatGPT-Phase): SPI-Seite GND, MISO, MOSI, SCK, CS#, RST#, 3V3 für den U8-
   Flash (In-Circuit-Programmierung der MG-Firmware), dazu die **ColdFire-
   UART: Pad „RxD“ → RX eines 3,3-V-USB-Seriell-Adapters (CH340), GND → GND,
   119048 Baud 8N1, keine Flusssteuerung.** Beim Start kommt ein Banner mit
   den Zeilen `CF:` (ColdFire-Version), `MG:` (MG1264-Firmware), `CD:`. Die
   Testfirmwares der frühen Phase meldeten dort z. B. „FIELD PRE-INPUT:
   ACCEPTED“. **Das ist der abgreifbare Datenstrom:** die Konsole des
   ColdFire. Noch nie gemacht: diese Konsole während einer Aufnahme mit AE
   mitschreiben (meldet die Firmware MG-Befehlsfehler? → offener Punkt
   „Fehlerbehandlung der Testreihe“). Ob RST# die MG- oder die Gesamt-Reset-
   Leitung ist: Durchgang zu MCU-Pin 96 (RSTI) messen.

**Nutzer-Werkzeug `PVT_ESP32C3_SPI_Flash_Reader.zip` (05.08.2026, geprüft
12.10.):** ESP32-C3 SuperMini als reiner Lese-Dumper für U8 (S25FL008A, 1 MiB).
Sketch `pvt_flash_reader_esp32c3.ino`: GPIO4 SCK, GPIO5 MISO, GPIO6 MOSI,
GPIO7 CS (= Arduino-Standardpins des C3), SPI-Modus 0, 250 kHz, Befehle nur
0xAB/0x9F/0x05/0x03 (kein WREN/Program/Erase), 1-KiB-Blöcke, CRC32 am Ende;
`receive_dump.py` (pyserial, 921600 Bd) empfängt, prüft CRC, Doppeldump mit
SHA-256-Vergleich. RST# des Ziels über ~1 kΩ auf Masse, 3V3 NICHT verbinden.
Urteil: sauber und sicher; damit ist vermutlich U8DUMP entstanden.
**Derselbe Aufbau taugt als EzPort-Leser für den ColdFire** (EzPort ist
befehlskompatibel zu SPI-NOR): CS → MCU 21 (EZPCS/RCON), SCK → 18 (EZPCK),
MOSI → 16 (EZPD), MISO → 17 (EZPQ), zusätzlich RSTI 96 steuerbar (Open-Drain-
GPIO). Einstieg: EZPCS low halten, RSTI kurz low, RSTI loslassen → Chip bleibt
im EzPort-Modus (CPU angehalten) bis zum nächsten Reset mit RCON high. Dann
0x05 RDSR (Bit 7 FS = Flash Security, Bit 6 CRL, Bit 1 WEN, Bit 0 WIP) — bei
FS=1 abbrechen — und 0x03 READ mit 24-Bit-Adresse, 0x40000 Byte (Datenblatt
Tab. 27: READ max. fsys/8, alle anderen fsys/2). Im Sketch zu
ändern: FLASH_BYTES 0x40000, 0xAB/0x9F raus, Reset-GPIO + Einstiegssequenz
rein; niemals 0x06/0x02/0xD8/0xC7/0x01/0xBA senden. Sofortige Dump-Kontrolle:
Bytes 0x4000–0x3FFFF müssen der gerade geflashten CFUPDATE.BIN gleichen.
Offen: ob QSPI-Pins 16–21 auf der Platine anderweitig benutzt sind (dann MG
per Serviceheader-RST# in Reset halten, Serienwiderstände 220–470 Ω).

**U8DUMP1/2.BIN (Nutzer, 12.10. erneut hochgeladen):** beide identisch, SHA-256
`132f69cf…312c17` = genau die Referenz in `PVT_HANDOVER/04_REVERSE_ENGINEERING/
MG_ENTPACKT/input_hashes.json` und `05_ORIGINAL/PINNACLE/`. Aufbau: 4 Byte
Länge big-endian bei 0x0 (0x000776F8 = 489 208), `MBY0`-Abbild ab 0x10000,
belegt bis 0x876F7, Rest 0xFF; die 8 LZO-Blöcke prüfen mit Adler-32 sauber →
der ESP32-C3-Leser hat damals bitgenau gelesen. **Neu bemerkt:** im
unkomprimierten Ladeteil (U8 0x1D275 ff.) die Strings „QMM bootstrap console“
(build Jul 30 2007), „Debug mode requested, wait for GDB connection“, und ein
GDB-Remote-Stub (vCont, qfThreadInfo, Threadzustände „Wait Mutex/Cond/AInt“,
Tag „cwein@10728“, Jun 27 2005) → **der MG1264 hat eine serielle Konsole mit
GDB-Stub.** Die Hauptfirmware loggt mit Verbose-Stufen („INFO: %d (current
verbose level = %d)“). Wo die MG-UART auf der Platine liegt, ist unbekannt —
Kandidat: der 2×13-Port, falls er sich NICHT als ColdFire-BDM erweist.

**Gebaut (12.10., 15:55, 0 Hardwaretests): `PVT_ESP32C3_EZPORT_READER.zip`** —
Sketch `pvt_ezport_reader_esp32c3.ino` (GPIO4 SCK→18, GPIO5 MISO←17, GPIO6
MOSI→16, GPIO7 CS→21, GPIO10 Open-Drain→RSTI 96, optional GPIO3→MG-RST#;
Befehle ENTER/STATUS/READ/DUMP/DUMP FORCE/BOOT; sendet nur 0x05 und 0x03;
Leitungen bis ENTER hochohmig; bricht bei FS=1 ab) und `cf_dump.py` (pyserial,
ENTER→DUMP→CRC32, schreibt Bootloader 0x0000–0x3FFF separat, erkennt den
Anwendungsstand am SHA-256 aller bekannten CFUPDATE.BIN-Stände, `--cfupdate`
Byte-Vergleich, `--vergleich` Doppeldump, `--boot`, `--analysiere` offline).
Mit g++-Stubs syntaxgeprüft, Serienprotokoll mit Emulation durchgespielt.
WRCR 0x01 ist nicht nötig: **Nutzer bestätigt 16:14, dass der Dump vom Sommer
2026 mit ESP32-C3 am EzPort entstand** → READ ohne WRCR, Flash offen, Pins
16/17/18/21/96 waren erreichbar. Der Leser ist damit nur noch Nachprüfung. README_DE.txt im Zip hat
Messvoraussetzungen a–e, Verdrahtung, Ablauf, Fehlerbilder.

**Was BDM bringt (falls bestätigt):**
- Vollständiger Flash-Dump 256 KB: CFUPDATE.BIN deckt nur 0x4000–0x3FFFF
  (240 KB); **die 16 KB Bootloader 0x0000–0x3FFF (Update-Logik, Flash-
  Konfigurationsfeld 0x400–0x417 mit Security-Bits) sind in keiner Datei.**
  Dump = Sicherung, mit der jedes verbrickte Gerät wiederherstellbar ist.
- Live: RAM lesen (z. B. 0x2000025A kbit/s-Ziel), Haltepunkte, Flashen ohne
  Stick.
- Hardware: USBDM (Open Source, pgo) **nur in einer Variante mit CFV2-
  Unterstützung (JMxx-Bauform, nicht die billige JS16-Bauform, die kann nur
  HCS08/HCS12/CFV1)** oder P&E USB ColdFire Multilink. EzPort-Alternative:
  beliebiger SPI-Master (Raspberry Pi/ESP32) an 21/18/16/17 + Reset.
- **Security: geklärt, NICHT gesichert** (siehe 23a: CFMSEC-Wort im Dump = 0x0000;
  nur 0x4AC8 würde sichern). Trotzdem gilt: nie „unsecure/mass erase“.

### 23a. Der ColdFire-Dump existiert schon (Nutzer-Upload 12.10., 16:03)

`pinnacle_mcf52223_2.bin`, 262 144 Byte, SHA-256 `3486ce21…bdfdf3c`, vom
Nutzer im Sommer 2026 (ChatGPT-Phase), **laut Nutzer mit ESP32-C3 am EzPort**
gezogen. Befund:
- Vektortabelle plausibel (SP 0x20002600, PC 0x428), 127 belegte Vektoren in
  den Bootloader; Anwendung ab 0x4000 mit eigener Tabelle = CFUPDATE-Anfang.
- **Flash-Konfigurationsfeld 0x400–0x417 = 0x00 → SEC 0x0000 → unsecured.**
  Korrektur zu vorher: beim ColdFire-CFM sichert nur SEC = 0x4AC8, alle
  anderen Werte = offen (gelöscht 0xFFFF ist offen). cf_dump.py/Sketch/README
  entsprechend berichtigt (Zip neu, SHA 4e09849b…).
- **Bootloader 0x0000–0x3FFF („STIMPY-BL“)**, 16 021 Byte belegt, Texte bei
  0x3F6A ff.: „PT_U“, „00.00.00.00“, „cfupdate.bin“, „STIMPY-BL“, „CODE REV.“,
  „UPDATING“; USB-Massenspeicher-Signaturen „USBC“/„USBS“ bei 0x1A6C/0x1BCE →
  Bootloader = USB-Host + Dateisuche + Flash-Programmierung. Ändert sich bei
  Stick-Updates nicht. **Damit ist das Ziel des EzPort-Lesers (Bootloader-
  Sicherung) bereits erreicht**; der Leser bleibt für Nachprüfung/Vergleich.
- Anwendungsteil = **früher Custom-Build**, nicht Original: Bitratenleiter
  2500–4000 kbit/s (Datei 0x2A452: 0FA0 0DAC 0CB2 0BB8 09C4 statt 05DC 03E8
  0300 0200 0100), Hook bei Laufzeit 0x10700 → 56-Byte-Cave 0x2F040, 32 Byte
  bei 0x0D65E. 106 Byte Abstand zum Original, 513 zu
  `PVT_CFUPDATE_TRUE_576I_FIELD` (SHA 7658bbc0…, Nutzer-Upload 16:07; das ist
  der nächstjüngere Build derselben Linie: zusätzlich GOP-Hook 0x1057A, 392-
  Byte-Cave, 110-Byte-Textcave 0x2F700, Basis laut PATCHINFO
  `CFUPDATE_CUSTOM_576I_ADAPTIVE_LADDER_2500-4000.BIN` SHA 1943cfa9…, nicht
  vorhanden). SHA des Dump-Anwendungsteils 0b3a998e… ist in cf_dump.py als
  bekannter Stand eingetragen.
- **Geliefert: `PVT_MCF52223_VOLLBILD.zip`** — Dump, Bootloader allein,
  Bootloader+Original (SHA 16ffd835…) und Bootloader+AE (SHA 3220f25b…) als
  256-KB-Vollbilder für Wiederherstellung per EzPort-Schreiben/BDM (beides
  nicht gebaut). Annahme: Updater legt CFUPDATE.BIN byteweise ab 0x4000 ab —
  per EzPort-Dump des Vorführgeräts mit `--cfupdate` zu bestätigen.
- **ColdFire-UART bestätigt** (README von TRUE_576I_FIELD): Debugausgaben mit
  **119048 Baud 8N1** (= 80 MHz/(32·21)); Pin nicht dokumentiert, Kandidaten
  UTXD0 Pin 8, UTXD1 Pin 99, UTXD2 Pin 29 — beim Einschalten mit Oszi/Logic
  Analyzer suchen; Bootloader-Texte „CODE REV.“/„UPDATING“ sprechen für
  Ausgaben schon beim Start. Der Nutzer hat **zwei Geräte** („Gerät 2
  unverändert lassen“).

### 23b. Zwei Geräte, Stand aus der ChatGPT-Phase (Screenshots 12.10., 17:50)

| | Gerät 1 (Test-/Vorführgerät) | Gerät 2 (unverändert) |
|---|---|---|
| Platine | Stimpy V1.0, 8520-00189-01 | dieselbe Revision |
| SDRAM | K4S281632I-**UC75** | K4S281632I-**UC60** |
| ColdFire-Firmware (UART-Banner) | 01.00.46.03, Build 14.03.2008 | **00.01.00.46, Build 21.01.2008** |
| MG1264-Firmware | 00.01.07.28 | 00.01.07.28 |

Gerät 2 trägt also den **Werksstand 00.01.00.46**, von dem es keine Datei
gibt (Pinnacles Update-ZIP enthält nur 01.00.46.03). Ein EzPort-Dump von
Gerät 2 (rein lesend, ändert nichts) würde Werks-Anwendung + Bootloader
archivieren und zeigt, ob der Bootloader zwischen Januar und März 2008 gleich
blieb. Empfehlung nach der Vorführung: `cf_dump.py` an Gerät 2, dann
`--vergleich` gegen den Gerät-1-Dump; den Anwendungsteil als
`CFUPDATE_WERK_00.01.00.46.BIN` ablegen. Die MG-Firmware ist auf beiden gleich,
U8DUMP gilt für beide.

### 23c. Namen, Herkunft, Muster (Stringanalyse 12.10., 20:20 — nur Klartexte, keine Disassemblierung)

**ColdFire-Firmware (Original 01.00.46.03, Datei-Offsets):**
- 0x2AFD4 `AVID Development GmbH Braunschweig, Germany`, 0x2AFC0
  `www.pinnaclesys.com`, 0x2AFAE `MPEG-4 Videofile`, 0x2B000 `Pinnacle Video
  Transfer`, 0x2B018 `Captured Video` → MP4-Metadaten; die Host-Firmware kommt
  aus Braunschweig (ex-miro → Pinnacle Systems GmbH → Avid). „Stimpy“ ist ein
  Braunschweiger Codename.
- UART-Banner (0x2973A ff.): `00.00.00.00`, `CF: `, `MG: `, `\r\n\nSTIMPY\r\n\n`,
  `CD: `, `Mar 14 2008`, `, `, `11:29:05` → **`CD:` = Compile Date** (Datum +
  Uhrzeit des Builds), kein drittes Bauteil. `PT_0 `…`PT_4 `, `PT_STARTED`,
  `PT_SUSPEND`, `PT_RESUME`, `PT_RESET`, `PT_RESET_ABORTED`, `PT_U ` → Zustands-
  meldungen mit Präfix PT (Pinnacle Transfer); `PT_U` auch im Bootloader.
- Update-Dateien (0x29835, 0x2A533, 0x2A56B): `cfupdate.bin`→`cf_done_.bin`,
  `mgupdate.bin`→`mg_done_.bin` (daneben `MBY0` = Magic des MG-Abbilds → **die
  Stock-Firmware kann U8 vom Stick aus neu beschreiben**), `ppupdate.bin`→
  `pp_done_.bin` (PP unbekannt; Hypothese: Parameter-/Produktprofil, evtl. für
  den leeren ersten 64-KB-Sektor von U8). Alle Namen 12 Zeichen, 8.3 → nach
  Erfolg wird der Verzeichniseintrag in gleicher Länge umbenannt.
  `======= reset ========` als UART-Trenner.
- Zielgeräte: `Apple`, `iPod`, `Sony`, `PSP`, `iTunesDB`, `SPACER.pod`,
  `:iPod_Control:Music:F99:`, `iPod_C~1/Music/F99`, `JFIF` → Aufnahme direkt
  auf iPod (Ablage in F99 + iTunesDB-Eintrag, JPEG-Vorschaubild) und PSP.
- Container: `qbox` (der MG liefert QBox, der ColdFire baut daraus MP4),
  Tabellen `vtts/vtsz/vtsc/vtco` (= stts/stsz/stsc/stco des Videotracks),
  `.mux` Zwischendatei, `vid*.mp4`, `custom.txt` mit Schlüsseln
  `vhres/vrate/arate/start/title`, `\VIDEO\best.txt`.
- Versionen: Werk `00.01.00.46` (21.01.2008) → Update `01.00.46.03`
  (14.03.2008, 11:29:05); die „46“ bleibt, die Felder rutschen — Schema
  unklar.

**MG1264-Firmware (Mobilygen, SVN-`$Id$`-Zeilen):** Q-Präfix durchgehend:
`QMM` (RTOS/Bootstrap mit Threads, Mutex, Syscalls, Root-FS, GDB-Stub),
`QBox` (Container), `qac*` (AAC-Decoder: filterbank, huff, is, ms, pns,
requant, tns), `qma*` (MPEG-Audio enc/dec, psych), `qmp4*` (MP4 avc1 mux/
demux, boxcntx), `qsp*` (DSP-Bibliothek: DRC, Filter, MDCT, nonlinear, rand).
Elgatos Dateiname `qmmapp.seve1-eb-8mb.bin` = QMM-Applikation für Ziel
„seve1-eb“ (unbekannt, vermutlich Board/EVB) mit 8 MB. Entwickler-Handles:
`imontgomerie` (buffctrl.cpp r5966 **04.05.2006 — die Pufferregelung, die uns
beschäftigt hat, danach nie mehr angefasst**; demux r10023), `kevint` (mux,
mux_qbox, demux_qbox r10201 12.06.2007 = letzter Stand im PVT; mux_es r4391
11/2005), `tonyv` (gesamte Audio-/DSP-Schicht, Massen-Commit r9600
10.04.2007), `nmittal` (qacdectns), `cwein` (qmp4avc1mx r9968; Bootstrap-Tag
`cwein@10728`, Build 30.07.2007), `jenchung` (qmp4boxcntx r7930). Zeitachse:
r4391 (11/2005) → r10728 (07/2007) ≈ 10 Commits/Arbeitstag → mittelgroßes
Team. Elgato-Firmware r6695 (07/2006) ist ein Jahr älter als die des PVT; die
MG-Firmware des PVT (`00.01.07.28`, evtl. Build 28.07.2007) wurde von Pinnacle
nie aktualisiert — beide Geräte identisch.

---

## 24. Offene Gefahr vor der Vorführung: echter Ton kann AE über die Mauer schieben — Test AG gebaut (12.10., 21:00, 0 Hardwaretests)

**Rechnung.** Mauer 5,25 Mbit/s. Alle AE-Nachweise liefen mit 5,00 Video +
~24 kbit/s Stille = ~5,05 Mbit/s (96 %). AE **fordert aber 384 kbit/s Audio an**
(W-Builder: `0x2F322` Laufzeit = Datei `0x2B324`, `move.l #384`, MG-Objekt 3,
Opcode 41, Parameter 1 = kbit/s × 1000; W-Builder erlaubt 96/128/192/256/320/384;
„audio_output_384_confirmed: False“ in allen Builder-Modellen). Liefert der
AAC-Encoder bei echtem Ton 384 kbit/s → Summe 5,38 → über der Mauer → Verlust
wie bei AF8. Die 24 kbit/s bei Stille sagen nichts über echten Ton.
Nebenbefund: Muxer-Audiopuffer p04 = 48 Seiten = 96 KB → 2 s bei 384 kbit/s,
4 s bei 192, 6 s bei 128 (Videopuffer 6,7 s) — bei Aussetzern läuft der
Tonpuffer zuerst voll. Beim 4-GiB-Wechsel wird der moov (3,9 MB) ~6 s lang am
Limit geschrieben; 6 s × 5,05 Mbit/s = 3,8 MB passen gerade in die 4 MiB —
jede weitere Last nimmt diese Reserve. **Nie „Video allein auf 5,25“:** null
Reserve, Rückstände werden nie abgebaut.

**Entscheidung (Nutzerfrage „Audio weg oder drosseln?“): drosseln, Summe auf
dem bewiesenen Niveau halten, Ton aus dem Video nehmen.** 4 % weniger Video
sind unsichtbar; 192 kbit/s AAC-LC ist für Composite/S-Video-Quellen mehr
als genug.

**Gebaut: `PVT_TEST_AG_AUDIO.zip`** (`werkzeug/build_ag.py`, aus AE, nur
Zahlenwerte): 01 = **AG_4800_192** (Video 4800, Audio 192, Summe 4,99; SHA
`54d9afb8…4d4bd8`, 24 Bytes), 02 = AG_4900_128 (Summe 5,03; SHA `ecfc7a29…faf93`),
03 = AE zurück. Patches: 0x08108/0x2C002 Video, RC7 ×3 = Video×5000, RC11 ×3
= Video×1000, 0x2B324 Audio. LED2/LED3 wie AE.

**Testplan:** (1) erst mit AE und echtem Ton (Musik vom Handy an den
Audioeingang) 2–3 min aufnehmen, `pvt_check.py` → Zeile „Audio: … kbit/s“ und
Gesamtrate = Dateigröße/Länge; ~384 → AG Pflicht, 100–200 → AG empfohlen,
< 100 → AE bleibt. (2) AG_4800_192 gleiche Aufnahme: Video ~4,8, Audio ~192,
leer 0, Ton synchron. (3) Freigabe erst nach 30 min mit Ton, besser nach einem
4-GiB-Wechsel (> 1 h 55 min). Hashes in `cf_dump.py` eingetragen.

### 24a. Ergebnis mit echtem Ton (23:29): **AE bricht mit Ton nach Sekunden** — Vorführung mit Ton derzeit NICHT möglich

`VID00006.MP4`, AE/LED1, 2 min, Musik mit hohem Pegel auf beiden Kanälen
(Bericht in `PVT_TEST_AG_AUDIO/befund_ae_mit_ton/`):
- Ton: 879 AAC-Blöcke = 18,75 s Tonzeit bei 251,8 s Aufnahme (normal ~47
  Blöcke/s). Sekunden 0–3 normal, Sekunde 4 nur 8 Blöcke, 8–10 Einbrüche,
  **ab Sekunde 14 nur noch 0–3 Blöcke/s**, am Ende ein Schub. Audio-stsz im
  moov ist Schrott (Summe 740 MB bei 141 MB Datei) → die „315.768 kbit/s“ von
  pvt_check sind ein Artefakt der kaputten Tabelle. Aus Dateigröße minus
  Videobytes bleiben ~0,3–0,4 MB für Ton+moov → die echte AAC-Rate ist aus
  dieser Datei nicht bestimmbar.
- Video: ab 16,08 s (10 MB Videodaten) massiver Verlust: 159 leer, 1744 sehr
  klein, 183 Teilbild (37 % von 5.637), Zeitachse 225,5 s statt mdhd 251,8 s.
  Videorate je Medien-Sekunde weiter 5,0 Mbit/s.
- Dieselbe Firmware mit Stille: 2 h 30 min und 5 h 03 min fehlerfrei. **Der
  Ton (Blockgröße ~1 KB statt ~64 B, Bedarf 5,38 statt 5,05 Mbit/s, Tonpuffer
  p04 = 48 Seiten = 96 KB = 2 s bei 384 kbit/s) kippt den Datenweg innerhalb
  von Sekunden; das Video folgt.** Welcher Anteil Datenrate, Blockgröße oder
  Puffer ist, trennen die Builds in 24b.
- Fallback steht: **AE ohne Audiokabel** ist bewiesen (Veranstaltung 5 h).

### 24b. `PVT_TEST_AG_AUDIO.zip` neu geschnürt (23:45): Entscheidungsbaum

01 **AG_4900_128** (Summe 5,03 = bewiesenes Niveau, Blöcke ~340 B, Tonpuffer
6 s; SHA `ecfc7a29…faf93`) — ERSTER TEST, gleiche Quelle, gleicher Pegel, plus
einmal normal ausgesteuert. 02 **AG_4800_192** (4,99; `54d9afb8…4d4bd8`) —
zweiter Test, besserer Ton. 03 bei Bedarf **AG_4500_128** (4,63;
`92ad9a5c…c1da3`) — prüft, ob die Mauer mit Ton tiefer liegt (Handshake je
Block am GPIO-Hostbus). 04 bei Bedarf **AH_4900_128_P04_256** (wie 01 + MG-
Tabelle p04 48 → 256 Seiten = 512 KB, Mobilygen-Standard; MEInit-Emulation
5025/5120 Seiten ok, 192 Seiten → 4961; `da2342eb…cffc1e`, `build_ah.py`,
Datei 0x2A62A). 05 AE zurück. Sauber = leer 0, Ton minus Video < 0,2 s,
Audiodauer = Videodauer, AAC-Rate plausibel, Ton in VLC sauber. Freigabe mit
Ton erst nach 30 min + 4-GiB-Wechsel. Scheitern alle: Audio 96 probieren oder
ohne Ton vorführen. Hashes in `cf_dump.py` eingetragen (AG 4900/128, 4800/192).

---

## 25. Test AI: Breite an die Kamera angepasst, 528×576i (20.10.2026, 0 Hardwaretests)

**Nutzervorgabe:** Weniger Video-Mbit (für Ton) nur, wenn die Auflösung an die
Kamera angepasst wird. Kamera: AVC 571, 1/3"-Sony-CCD, 512×582 PAL, 400 TVL.

**Herleitung der Breite:** 512 Sensorpunkte auf der aktiven Zeile (52 µs = 702
Abtastwerte) → im 720er-Fenster 512 × 720/702 = 525 → **528** (16er-Raster).
528 trägt bis 4,95 MHz, SAR 16:15 × 720/528 = **16:11** (Standard-idc 4) → 4:3.
Senkrecht 576 mit Halbbildern unverändert. Messung an AE-Clips VID00001–03:
Energie > 5 MHz 0,09 %, ab ~5,5 MHz flacher Rauschboden (−20 dB); Rundweg
720→528→720 (Lanczos) 46–47 dB PSNR. Bits/Bildpunkt: AE 0,48; 528 @ 4,5 = 0,59;
528 @ 4,8 = 0,63.

**MG-Befund (Handbuch S. 187, 212–216 + MG-Code):** Video-In-Parameter = Wortindex
der MG-Struktur 0xED8A4 (Konfigurationsausgabe bei MG 0x2A180): 0 Norm, 1/2 Crop,
3/4 Crop-Start, **5 DecimationH**, 6 DecimationV, 7/8 Zoom, 9 ProgressiveSrc,
10 TF, 25/26 PixelAR, 27 FixedPixelAR, 28 Ticks in, 29 Int2ProgScale, 30 Ticks out.
SET_VIDEO_IN_PARAM schreibt 0xED8A4 + 4·Index (MG 0x297BC), Aktivierung kopiert
47 Worte in den VIN-Treiber (MG 0x52B4C). Skaliererroutine MG 0x4A9E8 (Codebefund,
Registerzuordnung wegen unbekannter Halbwort-Befehle teils unsicher): Schritt
(Eingang<<16)/Ausgang allgemein; Filtertabellen nur für 1:1 (0xD344E),
720→640 (0xD33D6), 2:1 (0xD3476), 4:1 (0xD349E), Sonderfälle →280; alles andere
mit Interpolationstabelle 0xD33AE ohne Tiefpass + UART-Meldung „unsupported
horizontal decimation“ (MG 0x4ACD2). Beliebige Koeffizienten (MG 0x66C7C) nur bei
Treiberflag +0x104 ≠ 0, das bei der Initialisierung 0 ist.

**CF (nur Zahlen, Blackbox-Mutationstest mit dem CF-Modell der Übergabe, kein
Disassemblat):** Die Tabelle bei 0x2A43E (720/640/352/320, 480…, 1500…) dient
nicht der LED-Wahl (vermutlich custom.txt `vhres`). Originalprofile laut Modell:
LED1 320×240 @ 768, LED2 640×480 @ 1200, LED3 720×576 @ 1500. Wirksame Stellen
in AE (alle 32-Bit-Konstante 720): **0x2B228** `move.l` Breitenwahl → Param 5;
**0x0C13C** `cmpi.l` nativer D1-Vergleich (sonst progressiv, PAR 1:1 fest);
**0x2B044** `cmpi.l` Encoder-Erweiterung; **0x2E062** `cmpi.l` RC-Erweiterung.
Alle vier auf 528: PAL LED1–3 im Modell identisch zur 720er-Referenz bis auf
DecimationH 720→528. NTSC bleibt 720×480, verliert die RC-Erweiterung.

**Gebaut: `PVT_TEST_AI_528.zip`** (`werkzeug/build_ai.py`, aus AE, Hashes):
01 AI_528_4500_192 `091fb10a…eab0e0`, 02 AI_528_4800_192 `fd5e2f35…5bfca4e`,
03 AI_528_4500_192 + p04 256 `271938db…f61df21`, 04 AE zurück.
`pvt_check.py` v1.2 zeigt jetzt die SPS-Größe und das Pixel-Seitenverhältnis.
**Offen am Gerät:** volles 4:3-Bild oder Rand/Beschnitt (Aspektlogik des MG
mit Flag +0x100 = 1), was der CF in tkhd/avc1 schreibt, Ton bei 4,69/4,99 Mbit/s.
Ausweichbreite mit eigener MG-Filtertabelle: 640.

**Nachtrag 20.10., 12:30 — RD-Messung (x264 mit MG-Werkzeugen: Main, CAVLC, keine
B-Bilder, 2 Referenzen, GOP 50, interlaced; zwei 40-s-Stücke aus AE-Clips, Laub im
Wind; `analyse/RD_ERGEBNIS.txt`):** Erste Messung an der unveränderten Quelle gab
0–3 % Ersparnis, war aber zugunsten von 720 verzerrt (Quelle ist MG-H.264, das
720-Raster liegt auf dem alten Raster). Kontrolle mit um 2 px/2 Zeilen verschobener
Quelle (`ctl.sh`): im Kameraband (≤ 4,95 MHz, beide Seiten durch denselben Tiefpass)
entspricht 528 @ X etwa 720 @ 1,03–1,07·X; gleiche Qualität wie AE (720 @ 5,0)
braucht bei 528 ≈ 4,65–4,85 Mbit/s. **Ersparnis durch die Breite 3–7 %
(≈ 150–350 kbit/s), nicht 27 %.** Vollband bleibt 528 schlechter (fehlender
Rauschboden > 5 MHz zählt als Fehler; AF8 bei 8 Mbit/s zeigt denselben Boden,
−19 dB → Quelle, nicht Kompression). Bit-Anteile AE: I-Bilder 4 % (GOP 50),
P ≈ ½ I → Bits gehen in Bewegung/Rauschen; längere GOP spart nur 1–2 %.
Folgerung: 02 (528 @ 4,8 + 192 Ton) ≈ AE-Niveau; AG_4800_192 (720) liegt ≈ 0,2 dB
darunter — beides mit dem Auge nicht zu unterscheiden; AI lohnt sich nur, wenn der
Skalierer-/Aspektpfad am Gerät sauber ist.

## 26. Erste AI-Aufnahmen mit echtem Ton (20.10., 19:00–19:30): Breite bestätigt, Ton-Pfad vermessen

**VID00007 = AI_528_4500_192 (Baukasten), 112 s, echter Ton, Kamera.** Bild: SPS 528×576,
SAR 16:11 → 4:3, avc1 und tkhd 528×576, Halbbilder in allen Bildern, Video 4,66 Mbit/s,
QP 13–29. **Die Breite ist damit am Gerät bestätigt** (Skalierer + Container).
Ton: nur 684 von ~5.280 AAC-Blöcken (Median 516 B) in der Datei, ohne Zeitlücken
aneinandergehängt → „der Ton springt“. Tonblöcke je Sekunde Aufnahmezeit: 0–3 s voll
(46–47), **4 s: 3**, 5: 24, 6–7 voll, 8: 29, 9: 10, 10: 23, 11–12 voll, 13–16 lückig,
**ab 19 s tot** (1 Block alle paar Sekunden). Video bis 65 s sauber, dann Verlust (Folge
des toten Tonpfads, wie VID00006). Löcher beginnen kurz nach Schlüsselbildern (4, 8, 10,
14, 16, 18 s), nicht nach allen; Videolast an den Stellen unauffällig. VID00006 (384 kbit/s)
hatte das erste Loch ebenfalls bei 4 s → Zeitpunkt des ersten Lochs hängt nicht von der
Tonrate ab, nur das Sterben kommt schneller (384: 14 s, 192: 19 s). Summe 4,69 Mbit/s =
89 % der Mauer → **nicht die Gesamtdatenrate**.

**VID00008 = AE_V5000_A96_B528_REIN (Baukasten, Nutzerwahl), 105 s, echter Ton.** Bild
wieder korrekt. **Ton 96 kbit/s (Blöcke 220–488 B, Median 252) hält:** 4.781 von ~4.900
Blöcken, 0–19 s lückenlos, danach unregelmäßig (27–91/s), nie tot, insgesamt 2,5 s fehlend.
**Dafür Video:** ab 19 s 40 % leere Bilder in Phasen (19–61 s, 73–95 s), dazwischen sauber
(62–72, 96–104 s). Last 4,97 + 0,095 = 5,07 Mbit/s, knapp über dem bewährten 5,02 (AE mit
Stille). Phasenmuster erinnert an Platten-Stalls (Nachtfahrt 10.10.) → **Platte erfragen**.
`pvt_check.py` v1.4: Zeilen „Container“ (avc1/tkhd), „SPS“, „Ton je Sekunde“ (erstes Loch,
tot ab) — Paket `PVT_TEST_AI_528.zip` aktualisiert.

**Stand der Ton-Frage:** Blöcke ≤ ~300 B (96 kbit/s) kommen durch, ≥ 450 B (192/384) töten
den Tonpfad binnen 20 s, unabhängig von der Gesamtlast (bei 4,5 Mbit/s Video genauso wie bei
5,0). Hypothese: Host-/MG-Tonpuffer in Blöcken oder Bytes, der bei großen Blöcken innerhalb
der Bedienlücken des Hosts überläuft; Mechanismus ohne CF-Code nicht benennbar. Nächste
Tests: 4500+96 (bewährte SSD, 30 min), dann 4500+128 (Blöcke ~340 B, Grenze eingrenzen),
Original-Firmware LED3 mit Ton (Pinnacle-Fehler oder Lastfrage).

**VID00010 = AE_V4500_A96_B528_REIN (21:16), 117 s, echter Ton, SanDisk-SSD.** Bild korrekt
(528×576, 16:11). Video 4,50 Mbit/s (kein Überschwingen, QP 23–27). **Ton 5.457 Blöcke =
99,1 %**, lückenlos bis 80 s. Eine Störung 81–96 s: Ton 34–46 Blöcke/s, Video 86–95 s
19 leer + 42 klein + 13 Teilbild, danach wieder vollständig sauber bis 117 s. Nichts in der
Datei erklärt den Beginn (Audio-Bytes konstant 12 KB/s, Videorate 4,4–4,6, Dateirate
0,56–0,59 MB/s). Verglichen mit VID00008 (5000+96: 40 % Verlust in Phasen) und VID00007
(4500+192: Tonpfad tot) ist das der erste brauchbare Stand mit Ton; ob die Störung
wiederkehrt, zeigt der 30-min-Lauf. Baukasten 1.1: Ton 48/64 ergänzt (MG: 8–384 kbit/s,
Pinnacle-Tabelle bis 64), Presets „Mit Ton“ 4500/96 und 4500/64, Hinweise aus den
Messungen, bekannte Builds um V5000_A96 (`9952bab7…`) und V4500_A96 (`13508fa0…`) ergänzt.

## 27. Ton aus (nur Video) und Mono – 20.10.2026, 22:30

**Frage:** Ton am PVT ganz abschalten (nichts schreiben) oder einen Kanal einsparen?

**Mono:** Der MG kennt `AI_CHANNELS` (1 Stereo, 2 vertauscht, 3 Mono links, 4 Mono rechts),
der ColdFire sendet den Parameter aber nie (CF-Modell: Audio-Opcode 41 nur (2,0),(0,0),(7,0),
(1,384000); Objekt 1: 7=48000, 8=16, 9=1, 19=1). Ohne Code ist Mono also nicht erreichbar.
Nötig ist es auch nicht: die AAC-Blockgröße hängt an der kbit/s-Zahl, nicht an der Kanalzahl;
bei Monoquelle kodiert Joint-Stereo ohnehin fast wie Mono. Aufnahmen sind echtes Stereo
(L/R-Korrelation 0,67 in VID00010). Weg zum selben Ziel: 64 oder 48 kbit/s wählen.

**Ton aus:** `ENC_INPUT_SELECT`/`ENC_AV_SELECT` (MG Objekt 3, Param 40 und 17; 1 = AV,
2 = VIDEO_ONLY, 3 = AUDIO_ONLY). Mutationstest über alle 729 „#1“-Konstanten der AE-Datei im
CF-Modell: genau eine Stelle setzt beide Parameter, **Datei-Offset 0x0C363** (Wort `7A01` =
`moveq #1` bei 0x0C362, im Original identisch). 1 → 2 ändert in der gesamten emulierten
Befehlskette nur (3,1026,40) und (3,1026,17) von 1 auf 2 – PAL/NTSC, LED1–3, sonst nichts.
Der MG muxt ohne Tonspur (String „No audio yet, Mux w/o audio“), der ColdFire bekommt keine
Tonblöcke mehr. **Ungeprüft:** ob der CF-MP4-Schreiber ohne Tonblöcke die Datei sauber
schließt (Erwartung: leere mp4a-Spur oder keine; VLC spielt beides). Kein Risiko fürs Gerät,
2-Minuten-Test genügt; `pvt_check` muss 0 Tonblöcke zeigen.
Gewinn: der ganze Tonpfad des Hosts entfällt, auch mit eingestecktem Kabel. Bei Stille war er
schon fast kostenlos (AE 5,02 Mbit/s 5 h); bei echtem Ton kostete 96 kbit/s die Reserve
zwischen 4500 (hält) und 5000 (kippt). Ohne Ton sollte 5000 (oder 4800 + 528) wieder laufen.

**Werkzeuge:** Baukasten 1.2 (Artefakt Version 3, `PVT_Firmware_Baukasten.zip`): Audio
„aus: nur Video“, Preset „Nur Video: AE ohne Ton“, Label `_NURVIDEO`, Anforderung 0x2B324
bleibt 384, README-Hinweis; `identify` erkennt das Byte, Normalisierung zurück auf AE geprüft
(node test_core.js, smoke.py). `build_ai.py`: Audio 0 = aus, 1-Byte-Patch mit `moveq`-Prüfung,
`check` meldet „Audio AUS (nur Video, 0x0C363 = 2)“; Breite 720 jetzt erlaubt.
Hashes: AE_NURVIDEO (720/5000) `5944faf96cd86771040aaff4557e9f5e0d2d756771a324074df100e57e377ccf`
(Baukasten und build_ai.py identisch); 528/4500/aus (ohne rein) `ad624c99…7d3b`;
528/4500/aus/rein (Baukasten) `96f00ffd…`.

## 28. Baukasten 1.3 / build_ai.py v2: freie Werte – 20.10.2026, 23:00

Auf Wunsch des Nutzers („alles so offen zum Experimentieren wie möglich“) sperren beide
Werkzeuge nur noch, was technisch nicht in die Stellen passt: ganze Zahlen, Video×5000 und
Audio×1000 in 32 Bit (Video ≤ 858 993 kbit/s), Größen 1–65535, Puffer 1–65535 Seiten,
GOP ≥ 1, TF 0–127 (moveq-Byte). Datenblatt- und Messgrenzen (MG 64 kbit/s–10 Mbit/s,
Audio 8–384, Host-Mauer 5,25, Param-10-Wechsel unter 3600, Vielfache von 16, Teiler-Deutung
1–16, Speicherplan p03+p04 ≤ 2304) sind nur noch Hinweise.

**Neue Stellen (Mutationstest im CF-Modell, je Stelle genau ein MG-Parameter, Kette sonst
unverändert):**
- Höhe PAL: `0x2B234` (move.l, Wahl → DecimationV), `0x2B052` (cmpi.l, Encoder-Erw.),
  `0x2E056` (cmpi.l, RC-Erw.). Crop-Höhe `0x0C49E` bleibt 576.
- NTSC Breite: `0x2B81E` (Wahl), `0x0C042` (D1-Vergleich → Pixelformat 8:9), `0x2B924`
  (Encoder-Erw.); NTSC Höhe: `0x2B82A`, `0x2B932`, `0x2E044`. Crop NTSC `0x0C7C2`/`0x0C7D8`.
- Die RC-Erweiterung prüft **eine** Breite für beide Normen (`0x2E062`): bisherige 528er-
  Builds (NTSC 720) verlieren NTSC die RC-Erweiterung; mit NTSC-Breite = PAL-Breite ist die
  NTSC-Kette wieder vollständig (93 Befehle).
- GOP je LED: `0x2C086`, `0x2C090`, `0x2C09A` (move.l #50 → Objekt 3 Param 24).
- Videopuffer p03 `0x2A626` jetzt einstellbar (AB: 832).
- Gefunden, aber **nicht** eingebaut: Abtastrate 48000 an `0x0C67A` (→ Objekt 1 Param 7),
  dazu zwei weitere 48000-Konstanten `0x1AA9E` (nativ, vermutlich MP4-Schreiber oder ADC-
  Takt) und `0x2AA0C` (AE-Tabelle) mit unbekannter Rolle – ohne Code-Lesen nicht sauber.

**Bedienung:** Zahlenfelder mit Vorschlagslisten statt Auswahllisten; Experten-Teil mit
NTSC-Größe, p03, GOP×3, TF×3; Summenbalken skaliert mit, Mauer-Marke bleibt. Labels:
`_B544x288`, `_N544x240`, `_G25` bzw. `_G25-50-50`, `_VP1536`, `_TF325`/`_TF0-3-127`.
build_ai.py: Schlüsselwörter `hoehe= ntsc=WxH gop= p03= tf= rein=1`, Breite 720 erlaubt,
`check` liest alles zurück. Beide Werkzeuge liefern für gleiche Werte byteidentische
Dateien (geprüft: 4500/96/528/rein = `13508fa0…`, Beispiel frei = `ed3a5ce7…`).
Tests: node test_core.js (freie Werte angenommen, technische Sperren greifen), smoke.py
(Bau 6000/544×288/GOP 25 über die Mauer, Sperre bei Video 0, Handybreite ohne Überlauf).

## 29. Abtastrate als Experiment (Baukasten 1.4, build_ai.py, pvt_check 1.5) – 20.10.2026, 23:30

Externe Analyse der Hersteller-Disassemblierung (vom Nutzer geliefert, 23:00) bestätigt die
beiden nativen 48000-Konstanten und ihre Rollen: `0x0C67A` ist das Immediate eines `move.l`,
das den Wert mit Kennung 7 an die MG-Konfigurationsroutine gibt (= Objekt 1 Param 7, laut
MG-Handbuch Q_SYS_CFG_AUDIO_SAMPLE_RATE, erlaubt 24000/32000/48000); `0x1AA9E` initialisiert
eine RAM-Konfigurationsstruktur, deren Wert später in die Aufzeichnungsstruktur kopiert wird.
Die dritte Stelle `0x2AA0C` liegt – anders als zuerst vermutet – nicht in AE, sondern in der
MP4-Atomvorlage des Originals (`'mp4a' 0x20F 0 0x40 0x40 48000 2`, daneben `mdhd`, `esds`,
„AAC Audio Handler“). Die Aufnahmen tragen 48000 dreifach: stsd/mp4a (16.16), mdhd-Zeitbasis,
AAC-Konfig im esds (`11 90` = AAC-LC, Index 3, Stereo). Der Konfigbyte steht nirgends als
Literal im Image → wird zur Laufzeit gebildet, Quelle unbekannt.

MG-Handbuch Kap. 7: der 256×fs-Takt (AUD_CLK) muss von außen kommen, der MG ist Audio-Slave;
LRCK/BCK kann er als Master erzeugen. Bleibt der externe Takt bei 48 kHz, liefert eine
32-kHz-Einstellung Ton, der 1,5× zu langsam läuft (Tonspur 1,5× Videolänge).

**Eingebaut (ungeprüft, Hinweise statt Sperren):** Feld „Abtastrate“ im Experten-Teil,
Label `_SR32000`; build_ai.py `abtastrate=`; alle drei Stellen gemeinsam, Vorlage mit
Nachbar-Lagekontrolle (0x40, 0x40, 2). pvt_check 1.5: Zeile „Abtastrate: stsd/mdhd/AAC-Konfig“
mit Index und Kanälen, Warnung bei Uneinheitlichkeit, Erkennung der 1,5×-Signatur.
`mp4_abtastrate.py`: gleicht mp4a, AAC-Konfig-Index und optional mdhd einer Aufnahme an.
Hashes: AE + 32000 = `aed8cd2a…6790` (Baukasten = build_ai.py).

## 30. VID00011 = AE_V4500_A96_B528_SR32000_REIN (`7ee1f171…`), 23:25 – Abtastrate ist kein Hebel

133 s Video, Schleifenton. **Kopf richtig:** stsd/mdhd/AAC-Konfig alle 32000 (Index 5) – der
ColdFire leitet den AAC-Konfigbyte aus dem Wert ab, die drei Stellen reichen für den Container.
**Takt falsch:** Korrelation der ersten 3,8 s mit der Schleifenquelle 0,47 unter der Annahme
„48-kHz-Takt, als 32 kHz ausgewiesen“ gegen 0,14 für „echte 32 kHz“ → der 256×fs-Takt kommt von
außen (ADC/Oszillator) und bleibt bei 48 kHz. Folgen: Ton 1,5× zu langsam; Tonpfad ab 4 s tot
(1–3 Blöcke/s Rest, kurzer Schub 58–59 s), 773 Blöcke statt 4.165, 8 Müll-Einträge in der
Audio-stsz (bis 1,77 GB) → Player stolpern; **Video von der ersten Sekunde an zu 50 % kaputt**
(898 leer, 610 klein, 134 Teilbild gleichmäßig über alle 10-s-Fenster, 635 h264-Fehler, mdhd
156,8 s gegen stts 133,4 s = 23 s Bilder fehlen). Deutung: MG-Audioeingang läuft bei 1,5-facher
Eingangsrate über und stört die ganze MG-Pipeline – anders als die Host-Stalls (Phasen) in
VID00008. Blöcke ~370 B bei 31/s töteten den Host-Tonpfad wie 512 B bei 47/s; 256 B bei 47/s
halten → Blockgröße, nicht Bytes/s (Vorbehalt: MG-Überlauf gleichzeitig). Direkte Größenprobe:
48 kHz mit 112 (~300 B) und 128 kbit/s (~340 B).
Werkzeuge: Baukasten 1.4.1 (Hinweis + bekannter Build), pvt_check 1.6 (stsz-Müll erkennen,
Bitrate ohne Müll), README-Abschnitt. Abtastrate bleibt wählbar (Nutzerwunsch), gilt als erledigt.

## 31. VID00012 = nur Video (528, Ton aus), 23:33 – Aufnahme makellos, Index unvollständig

**Datei spielt nicht:** moov am Ende mit korrekt deklarierten Größen (moov 12.854 B, stsz
6.056 B = 1.509 Einträge, stco 6.052 B), tatsächlich aber nur 1.766 B geschrieben: stsz und
stco enthalten je nur die **letzten** ~120 Einträge (Offsets ab 36,3 MB), stss vollständig (31).
Deutung: der Schreiber hält die Sampletabellen in einem kleinen Puffer und schreibt ihn
normalerweise im Takt der Tonblöcke weg; ohne Ton bleibt nur der Pufferinhalt am Ende.
**Reparatur:** `werkzeug/mp4_reparatur.py` – NAL-Einheiten im mdat (4-Byte-Längen) per
Slice-Kopf (pvt_check-Parser) zu Bildern gebündelt (Halbbildpaar = 1 Bild, 3.080 NALs →
1.509 Bilder, 62 PPS inline, keine SPS inline), neuer Index mit stsd aus dem Original; die
eigene Bündelung wird gegen die vorhandenen Index-Einträge geprüft (passt zum Ende). Ergebnis
decodiert fehlerfrei (ffmpeg 0 Fehler), pvt_check: 1.509 Bilder, 60,36 s, mdhd = stts.
**Befund der Aufnahme:** 5,25 Mbit/s Video, 0 leer/klein/Teilbild, kein Bild fehlt, QP 21–27,
GOP 2 s. Erster Lauf ohne Aussetzer bei dieser Rate – ohne Tonpfad fällt die 5,25-Mauer
(60 s, zu kurz für eine Freigabe). Nächste Versuche: nur Video 30 min bei 5000; Ton 8 kbit/s
(21-B-Blöcke) als Ersatz für „aus“, falls der Index dann vollständig wird.
Baukasten 1.4.2: Hinweis bei Ton 0 und im README des Pakets.

## 32. Nur Video 6000/8000 springen; Ratenregelung als Hebel (Baukasten 1.5) – 21.10., 07:30

Nutzerbericht: nur Video mit 6000 und 8000 kbit/s – beide fangen nach kurzer Zeit gleichmäßig
an zu springen; länger aufgenommen wäre das Bild vermutlich stehen geblieben. Deutung: USB-
Durchsatz des Hosts, nicht die Platte (keine Phasen). **Host-Mauer ohne Ton: 5,25 (sauber, 60 s)
bis 6,0 Mbit/s.** Betriebspunkt ohne Ton 5000, maximal 5250; mit Ton bleibt 4500 + 96.

Hebel gegen die Spitzen (VID00012: 6,65 Mbit/s im 1-s-Fenster bei 5,25 Mittel): AE/LED1 läuft
nur mit der Größenregelung (MG-Handbuch 10.11: SIZE_ENABLE/SIZE_BIT_TOLERANCE, ±25 MBit =
±5 s), die Puffer-Regelung (BUFFER_ENABLE/BUFFER_SIZE_BITS/Transferrate/Startverzögerung =
Leaky Bucket, RC9/10/11/12) ist bei LED1 aus – AB hatte sie an (1,25 MBit, 5 Mbit/s, 125 ms,
geprüft). Baukasten 1.5 / build_ai.py: Felder RC7-Faktor (×Video, AE 5000), RC11-Faktor
(AE 1000), RC9 an/aus, RC10, RC12 für LED1 (rein kopiert nach LED2/3); readSettings leitet die
Faktoren aus dem LED1-Block ab (AB wird als `_B1-1250000-11250_VP832` erkannt). Emulation:
RC7 → Param 7 in allen LEDs, RC9/10/11/12 → Params 9–12 LED1. Labels `_T1000`, `_TR1100`,
`_B1-2500000-22500`. Hashes: 528/5000/aus/rc7=1000 `3a89c9f4…`; 528/5000/aus/Bucket
2,5 MBit/22500/×1100/rein `b950a847…` (beide Werkzeuge identisch). Am Gerät ungeprüft.
