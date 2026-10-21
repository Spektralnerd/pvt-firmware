#!/usr/bin/env python3
"""PVT Test AI: AE mit an die Kamera angepasster Breite (z. B. 528x576 statt 720x576),
weiter Halbbilder (576i), dazu Video-/Audioziel wie bei AG und optional der groessere
MG-Audiopuffer wie bei AH. Basis ist das unveraenderte AE (Vorfuehrstand).
Nur Zahlenwerte an geprueften Stellen, kein neuer Code.

Seit v2 (20.10., 23:00) ohne kuenstliche Grenzen: gesperrt ist nur, was technisch nicht
in die Stellen passt (ganze Zahlen; Video*5000 und Audio*1000 muessen 32 Bit bleiben).
Dazu optionale Schluesselwort-Argumente:
  hoehe=288            PAL-Hoehe (MG DecimationV): 0x2B234 Wahl, 0x2B052 Encoder-Erw., 0x2E056 RC-Erw.
  ntsc=720x480         NTSC-Bildgroesse: Breite 0x2B81E/0x0C042/0x2B924, Hoehe 0x2B82A/0x2B932/0x2E044
                       (die RC-Erweiterung prueft eine gemeinsame Breite 0x2E062 = PAL-Breite;
                       weicht NTSC ab, laeuft NTSC ohne RC-Erweiterung - wie alle 528er-Builds bisher)
  gop=50 | gop=25,50,50  GOP-Laenge je LED: 0x2C086, 0x2C090, 0x2C09A (MG Param 24; AE 50, Original 60)
  p03=2048             MG-Videopuffer (Seiten a 2 KB), 0x2A626; AB lief mit 832
  tf=3,3,3             Rauschfilter je LED (moveq-Byte 0..127), 0x2B177/0x2B17D/0x2B183
  rein=1               LED2/LED3 bekommen die LED1-RC-Werte (AE rein)
  rc7=5000             Groessentoleranz RC7 = Video x Faktor (Bit), alle drei LED-Bloecke (AE 5000 = +-5 s Video).
                       MG: SIZE_BIT_TOLERANCE - erlaubte Abweichung der Dateigroesse vom Soll; kleiner = flachere Spitzen.
  rc11=1000            Transferrate RC11 = Video x Faktor (Bit/s), alle LEDs (AE 1000); Abfluss des Leaky-Bucket.
  rc9=1 rc10=1250000 rc12=11250
                       Puffer-Regelung fuer LED1 (BUFFER_ENABLE, BUFFER_SIZE_BITS, Startverzoegerung in 90-kHz-Ticks).
                       AE: aus; AB lief mit 1/1250000/11250 (geprueft). rein=1 kopiert alles nach LED2/LED3.
  abtastrate=32000     Ton-Abtastrate, drei Stellen gemeinsam (alle im Original): 0x0C67A MG Objekt 1 Param 7
                       (AUDIO_SAMPLE_RATE), 0x1AA9E Host-Konfiguration (RAM-Struktur der Aufzeichnung),
                       0x2AA0C mp4a-Vorlage des MP4-Schreibers. UNGEPRUEFT: der 256*fs-Takt kommt laut
                       MG-Handbuch von aussen (Host oder ADC); bleibt er bei 48 kHz, ist der Ton 1,5x zu
                       langsam (pvt_check meldet das). MG-API: 24000/32000/48000.

Breite (vier 32-Bit-Konstanten 720 -> B, jeweils mit Pruefung des Befehlsworts davor):
  0x2B228  move.l #720   Breitenwahl (U/W-Bereich)       -> MG Video-In Param 5 (DecimationH)
  0x0C13C  cmpi.l #720   nativer D1-Vergleich             -> bleibt Halbbild-Pfad, PAR 16:15 nicht fest
  0x2B044  cmpi.l #720   Encoder-Erweiterung (TF, Deblocking, QP, Szene)
  0x2E062  cmpi.l #720   RC-Erweiterung (Puffer-/Groessenregelung)
  Crop (Param 1/2) bleibt 720x576: der MG skaliert waagerecht, senkrecht 1:1.
  Gilt nur fuer PAL. NTSC behaelt 720x480, verliert in diesem Build aber die RC-Erweiterung.

Video/Audio wie build_ag.py:
  Videoziel  5000 -> V kbit/s   0x08108 (nativ), 0x2C002 (erzeugt)
  RC7        25 Mbit -> V*5000  alle drei LED-Bloecke
  RC11       5 Mbit/s -> V*1000 alle drei LED-Bloecke
  Audio      384 -> A kbit/s    0x2B324
  Audio 0 = Ton aus: statt der Anforderung wird ein Byte gesetzt, 0x0C363 (moveq #1 -> #2):
             MG ENC_INPUT_SELECT/ENC_AV_SELECT (Objekt 3, Param 40 und 17) 1 = Audio+Video -> 2 = nur Video.
             Der MG kodiert dann keinen Ton; am Geraet ungeprueft (2-Minuten-Test, Rueckkehrdatei liegt bei).
Audiopuffer wie build_ah.py: MG-Tabelle p04 (0x2A62A) 48 -> N Seiten (nur wenn angegeben).

  python3 build_ai.py build <AE-CFUPDATE.BIN> <ausgabeordner> <breite> <video_kbps> <audio_kbps> [p04_seiten] [schluessel=wert ...]
  python3 build_ai.py check <CFUPDATE.BIN>
Hinweise statt Sperren: MG-Datenblatt Video 64 kbit/s..10 Mbit/s, Audio 8..384; Host-Mauer gemessen 5,25 Mbit/s
Summe; Breite/Hoehe 1..16 liest der MG als Teiler; Vielfache von 16 sind sicher; mehr als die Quelle geht nicht.
"""
import hashlib
import os
import struct
import sys

SIZE = 245760
AE_SHA256 = "d4ae6a9b99370e57d3c19652e6d0f071323a9f713d6b238462999eaa317c07a7"
MOVEL = b"\x20\x3c"
CMPIL = b"\x0c\x80"
WIDTH_SITES = ((0x2B228, MOVEL, "Breitenwahl"),
               (0x0C13C, CMPIL, "nativer D1-Vergleich"),
               (0x2B044, CMPIL, "Encoder-Erweiterung Breitenpruefung"),
               (0x2E062, CMPIL, "RC-Erweiterung Breitenpruefung"))
KBPS_OFFSETS = (0x08108, 0x2C002)
RC7 = (0x2E1C8, 0x2E320, 0x2E478)
RC11 = (0x2E162, 0x2E2BA, 0x2E412)
AUDIO = 0x2B324
AUDIO_OK = (0, 48, 64, 96, 128, 192, 256, 320, 384)   # nur noch Vorschlaege
AVSEL = 0x0C363          # Byte: moveq #1,d5 -> #2 = MG nur Video (Param 40/17)
MOVEQ = b"\x7a"
MOVEQ0 = b"\x70"
HEIGHT_SITES = ((0x2B234, MOVEL, "Hoehe PAL: Wahl -> MG DecimationV"), (0x2B052, CMPIL, "Hoehe PAL: Encoder-Erweiterung"), (0x2E056, CMPIL, "Hoehe PAL: RC-Erweiterung"))
WIDTH_N_SITES = ((0x2B81E, MOVEL, "Breite NTSC: Wahl -> MG DecimationH"), (0x0C042, CMPIL, "Breite NTSC: nativer D1-Vergleich"), (0x2B924, CMPIL, "Breite NTSC: Encoder-Erweiterung"))
HEIGHT_N_SITES = ((0x2B82A, MOVEL, "Hoehe NTSC: Wahl -> MG DecimationV"), (0x2B932, CMPIL, "Hoehe NTSC: Encoder-Erweiterung"), (0x2E044, CMPIL, "Hoehe NTSC: RC-Erweiterung"))
GOP = (0x2C086, 0x2C090, 0x2C09A)
SRATE = ((0x0C67A, MOVEL, "Abtastrate -> MG AUDIO_SAMPLE_RATE (Objekt 1, Param 7)"),
         (0x1AA9E, MOVEL, "Abtastrate: Host-Konfiguration (RAM-Struktur der Aufzeichnung)"),
         (0x2AA0C, None, "Abtastrate: MP4-Audiobeschreibung (mp4a-Vorlage)"))
SRATE_TPL = ((0x2AA04, 0x40), (0x2AA08, 0x40), (0x2AA10, 2))   # Nachbarn der mp4a-Vorlage als Lagekontrolle
P03 = 0x2A626
TF = (0x2B177, 0x2B17D, 0x2B183)
LED_BASE, LED_STEP, LED_N, LED_OFF = 0x2E11E, 0x22, 6, (0, 0x158, 0x2B0)
DEFAULT_EXTRA = dict(hoehe=576, ntsc=(720, 480), gop=(50, 50, 50), p03=2048, tf=(3, 3, 3), rein=False, abtastrate=48000,
                     rc7=5000, rc11=1000, rc9=0, rc10=1250000, rc12=11250)
LIM_VIDEO, LIM_AUDIO, LIM_SIZE, LIM_PAGES, LIM_TF = (1, 858993), (0, 4294967), (1, 65535), (1, 65535), (0, 127)
P04 = 0x2A62A
ANCHORS = [(0x2E11E, 0), (0x2E140, 1250000), (0x2E184, 11250), (0x2E1A6, 1), (0x2E2FE, 1), (0x2E456, 1),
           (0x2E298, 5000000), (0x2E3F0, 10000000), (0x2E276, 1), (0x2E3CE, 1)]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fail(msg):
    raise SystemExit("ABBRUCH: " + msg)


def u32(d, o):
    return struct.unpack(">I", d[o:o + 4])[0]


def val(d, o, size):
    return d[o] if size == 1 else u32(d, o)


def patches(width, video, audio, pages, x=None):
    """(offset, alter Wert, neuer Wert, Befehlswort davor oder None, Name, Breite in Byte)"""
    x = dict(DEFAULT_EXTRA, **(x or {}))
    p = [(o, 720, width, op, "Breite: " + name, 4) for o, op, name in WIDTH_SITES]
    p += [(o, 576, x["hoehe"], op, name, 4) for o, op, name in HEIGHT_SITES]
    p += [(o, 720, x["ntsc"][0], op, name, 4) for o, op, name in WIDTH_N_SITES]
    p += [(o, 480, x["ntsc"][1], op, name, 4) for o, op, name in HEIGHT_N_SITES]
    p += [(o, 5000, video, MOVEL, "Videoziel kbit/s", 4) for o in KBPS_OFFSETS]
    p += [(o, 25000000, video * x["rc7"], MOVEL, "RC7 Groessentoleranz (Video x %d)" % x["rc7"], 4) for o in RC7]
    p += [(o, 5000000, video * x["rc11"], MOVEL, "RC11 Transferrate (Video x %d)" % x["rc11"], 4) for o in RC11]
    p += [(LED_BASE + 0 * LED_STEP, 0, x["rc9"], MOVEL, "LED1 RC9 Puffer-Regelung", 4),
          (LED_BASE + 1 * LED_STEP, 1250000, x["rc10"], MOVEL, "LED1 RC10 Pufferbits", 4),
          (LED_BASE + 3 * LED_STEP, 11250, x["rc12"], MOVEL, "LED1 RC12 Startverzoegerung (Ticks)", 4)]
    if audio == 0:
        p += [(AVSEL, 1, 2, MOVEQ, "MG AV-Auswahl (Param 40/17): 1 = Audio+Video -> 2 = nur Video", 1)]
    else:
        p += [(AUDIO, 384, audio, MOVEL, "Audioanforderung kbit/s", 4)]
    p += [(o, 50, x["gop"][i], MOVEL, "GOP-Laenge LED%d (MG Param 24)" % (i + 1), 4) for i, o in enumerate(GOP)]
    p += [(o, 48000, x["abtastrate"], op, name, 4) for o, op, name in SRATE]
    p += [(P03, 2048, x["p03"], None, "MG-Tabelle p03 Videopuffer (Seiten a 2 KB)", 4)]
    if pages is not None:
        p += [(P04, 48, pages, None, "MG-Tabelle p04 Audiopuffer (Seiten a 2 KB)", 4)]
    p += [(o, 3, x["tf"][i], MOVEQ0, "TF-Stufe LED%d" % (i + 1), 1) for i, o in enumerate(TF)]
    return p


def rein_patches(d):
    """LED2/LED3 bekommen die sechs RC-Werte von LED1 (aus dem bereits gepatchten Abbild gelesen)."""
    p = []
    for led in (1, 2):
        for k in range(LED_N):
            src, dst = LED_BASE + k * LED_STEP, LED_BASE + LED_OFF[led] + k * LED_STEP
            p.append((dst, u32(d, dst), u32(d, src), MOVEL, "LED%d RC-Wert %d wie LED1" % (led + 1, k), 4))
    return p


def parse_extra(args):
    x = {}
    for a in args:
        if "=" not in a:
            fail("unbekanntes Argument %r (erwartet schluessel=wert)" % a)
        k, v = a.split("=", 1)
        if k == "hoehe":
            x[k] = int(v)
        elif k == "ntsc":
            w, h = v.lower().split("x"); x[k] = (int(w), int(h))
        elif k in ("gop", "tf"):
            vals = [int(t) for t in v.split(",")]
            x[k] = tuple(vals * 3 if len(vals) == 1 else vals)
            if len(x[k]) != 3:
                fail("%s: ein Wert oder drei Werte (LED1,LED2,LED3)" % k)
        elif k in ("p03", "abtastrate", "rc7", "rc11", "rc9", "rc10", "rc12"):
            x[k] = int(v)
        elif k == "rein":
            x[k] = v.lower() in ("1", "ja", "true", "yes")
        else:
            fail("unbekannter Schluessel %r" % k)
    return x


def check_anchors(d, skip=()):
    """Lagekontrolle: feste AE-Werte an bekannten Stellen (Stellen, die absichtlich geaendert wurden, werden uebersprungen)."""
    for o, v in ANCHORS:
        if o in skip:
            continue
        if d[o - 2:o] != MOVEL or u32(d, o) != v:
            fail("Lagekontrolle fehlgeschlagen bei 0x%05X" % o)
    if struct.unpack(">4I", d[0x2A60A:0x2A61A]) != (2, 0, 0, 84):
        fail("MG-Tabelle unerwartet (Kopf)")
    if P03 not in skip and u32(d, P03) != 2048:
        fail("MG-Tabelle unerwartet (p03 != 2048)")


def within(v, lim):
    return isinstance(v, int) and lim[0] <= v <= lim[1]


def build(src, outdir, width, video, audio, pages=None, x=None):
    x = dict(DEFAULT_EXTRA, **(x or {}))
    # nur technische Grenzen; alles andere sind Hinweise (siehe Kopf)
    if not within(video, LIM_VIDEO):
        fail("video_kbps: ganze Zahl 1..858993 (Video*5000 muss in 32 Bit passen)")
    if not within(audio, LIM_AUDIO):
        fail("audio_kbps: 0 (aus) oder ganze Zahl bis 4294967")
    for name, v in (("breite", width), ("hoehe", x["hoehe"]), ("ntsc-breite", x["ntsc"][0]), ("ntsc-hoehe", x["ntsc"][1])):
        if not within(v, LIM_SIZE):
            fail("%s: ganze Zahl 1..65535" % name)
    if pages is not None and not within(pages, LIM_PAGES) or not within(x["p03"], LIM_PAGES):
        fail("p03/p04: ganze Zahl 1..65535 Seiten")
    if not all(within(g, (1, 4294967295)) for g in x["gop"]):
        fail("gop: ganze Zahl ab 1 je LED")
    if not all(within(t, LIM_TF) for t in x["tf"]):
        fail("tf: ganze Zahl 0..127 je LED (moveq-Byte)")
    if not within(x["abtastrate"], (1, 4294967295)):
        fail("abtastrate: ganze Zahl in Hz")
    if not within(x["rc7"], (1, 4294967295)) or video * x["rc7"] > 4294967295:
        fail("rc7: ganze Zahl, Video*rc7 muss in 32 Bit passen")
    if not within(x["rc11"], (1, 4294967295)) or video * x["rc11"] > 4294967295:
        fail("rc11: ganze Zahl, Video*rc11 muss in 32 Bit passen")
    if x["rc9"] not in (0, 1) or not within(x["rc10"], (1, 4294967295)) or not within(x["rc12"], (0, 4294967295)):
        fail("rc9 0/1, rc10 ab 1, rc12 ab 0")
    hints = []
    if video + audio > 5250:
        hints.append("Summe %d kbit/s ueber der gemessenen Host-Mauer 5,25 Mbit/s" % (video + audio))
    if video > 10000 or video < 64:
        hints.append("Videoziel ausserhalb des MG-Datenblatts (64 kbit/s..10 Mbit/s)")
    if video < 3600:
        hints.append("unter 3600 setzt der ColdFire MG-Param 10 auf 1 statt 2 (Modus der Original-Stufen)")
    if audio and (audio < 8 or audio > 384):
        hints.append("Audio ausserhalb des MG-Datenblatts (8..384)")
    if audio >= 192:
        hints.append("Audio >= 192: Bloecke >= 450 Byte toeteten den Tonpfad binnen 20 s")
    for name, v, src_v in (("Breite", width, 720), ("Hoehe", x["hoehe"], 576), ("NTSC-Breite", x["ntsc"][0], 720), ("NTSC-Hoehe", x["ntsc"][1], 480)):
        if v != src_v:
            if v <= 16:
                hints.append("%s %d liest der MG als Teiler" % (name, v))
            elif v > src_v:
                hints.append("%s %d groesser als die Quelle %d" % (name, v, src_v))
            elif v % 16:
                hints.append("%s %d kein Vielfaches von 16" % (name, v))
            if name == "Hoehe" or name == "NTSC-Hoehe":
                hints.append("%s %d: senkrechte Skalierung am Geraet ungeprueft" % (name, v))
    if x["ntsc"][0] != width:
        hints.append("NTSC-Breite != PAL-Breite: NTSC laeuft ohne RC-Erweiterung")
    if x["p03"] + (pages or 48) > 2304:
        hints.append("p03 + p04 ueber 2304 Seiten: Speicherplan des MG ungewiss")
    if any(t > 3 for t in x["tf"]):
        hints.append("TF ueber 3 ungeprueft")
    if x["rc7"] != 5000:
        hints.append("RC7 x%d: ungeprueft; kleiner = flachere Spitzen, sehr klein = Qualitaet schwankt" % x["rc7"])
    if x["rc9"]:
        hints.append("Puffer-Regelung LED1 an: AB lief mit 1250000/5000000/11250, andere Werte ungeprueft")
    if x["abtastrate"] != 48000:
        hints.append("Abtastrate %d: ungeprueft; Takt von aussen und AAC-Konfigbyte offen (pvt_check Zeile Abtastrate)" % x["abtastrate"])
        if x["abtastrate"] not in (22050, 24000, 32000, 44100, 48000):
            hints.append("Abtastrate nicht in der MG-Liste 22050/24000/32000/44100/48000")
    data = open(src, "rb").read()
    if len(data) != SIZE or sha(data) != AE_SHA256:
        fail("Eingabe ist nicht das unveraenderte AE-CFUPDATE.BIN")
    check_anchors(data)
    for o, v in SRATE_TPL:
        if u32(data, o) != v:
            fail("mp4a-Vorlage unerwartet bei 0x%05X" % o)
    out = bytearray(data)
    allowed = set()
    plist = patches(width, video, audio, pages, x)
    for o, old, new, op, name, size in plist:
        if op is not None and data[o - len(op):o] != op:
            fail("unerwartetes Befehlswort vor 0x%05X (%s)" % (o, name))
        if val(data, o, size) != old:
            fail("alter Wert bei 0x%05X ist %d, erwartet %d (%s)" % (o, val(data, o, size), old, name))
        out[o:o + size] = bytes([new]) if size == 1 else struct.pack(">I", new)
        allowed.update(range(o, o + size))
    if x["rein"]:
        rp = rein_patches(bytes(out))
        for o, old, new, op, name, size in rp:
            if data[o - 2:o] != op:
                fail("unerwartetes Befehlswort vor 0x%05X (%s)" % (o, name))
            out[o:o + 4] = struct.pack(">I", new)
            allowed.update(range(o, o + 4))
        plist = plist + rp
    out = bytes(out)
    diff = [i for i in range(SIZE) if out[i] != data[i]]
    if any(i not in allowed for i in diff):
        fail("Unerwartete Aenderungen")
    check_anchors(out, skip=allowed)
    if os.path.exists(outdir):
        fail("Ausgabeordner existiert schon")
    os.makedirs(outdir)
    with open(os.path.join(outdir, "CFUPDATE.BIN"), "wb") as f:
        f.write(out)
    for o, old, new, _, name, _ in plist:
        if old != new:
            print("  0x%05X  %10d -> %10d  %s" % (o, old, new, name))
    for h in hints:
        print("  HINWEIS: " + h)
    print("geaenderte Bytes: %d   SHA-256 neu: %s" % (len(diff), sha(out)))
    return out


def check(path):
    d = open(path, "rb").read()
    if len(d) != SIZE:
        fail("Groesse")
    skip = {LED_BASE, LED_BASE + LED_STEP, LED_BASE + 3 * LED_STEP}
    for led in (1, 2):
        for k in range(LED_N):
            skip.add(LED_BASE + LED_OFF[led] + k * LED_STEP)
    check_anchors(d, skip=skip | {P03})
    widths = [u32(d, o) for o, _, _ in WIDTH_SITES]
    if d[AVSEL - 1:AVSEL] != MOVEQ or d[AVSEL] not in (1, 2):
        fail("AV-Auswahl bei 0x%05X unerwartet" % AVSEL)
    video, audio, pages = u32(d, KBPS_OFFSETS[0]), (0 if d[AVSEL] == 2 else u32(d, AUDIO)), u32(d, P04)
    x = dict(hoehe=u32(d, HEIGHT_SITES[0][0]), ntsc=(u32(d, WIDTH_N_SITES[0][0]), u32(d, HEIGHT_N_SITES[0][0])),
             gop=tuple(u32(d, o) for o in GOP), p03=u32(d, P03), tf=tuple(d[o] for o in TF), rein=False,
             abtastrate=u32(d, SRATE[0][0]),
             rc7=u32(d, RC7[0]) // video if video and u32(d, RC7[0]) % video == 0 else 0,
             rc11=u32(d, RC11[0]) // video if video and u32(d, RC11[0]) % video == 0 else 0,
             rc9=u32(d, LED_BASE), rc10=u32(d, LED_BASE + LED_STEP), rc12=u32(d, LED_BASE + 3 * LED_STEP))
    led = [[u32(d, LED_BASE + LED_OFF[l] + k * LED_STEP) for k in range(LED_N)] for l in range(3)]
    x["rein"] = led[1] == led[0] and led[2] == led[0]
    ok = len(set(widths)) == 1 and all(val(d, o, size) == new for o, _, new, _, _, size in
                                       patches(widths[0], video, audio, pages if pages != 48 else None, x))
    if audio == 0 and u32(d, AUDIO) != 384:
        ok = False
    print("Breite %s, Hoehe %d, NTSC %dx%d, Videoziel %d kbit/s, Audio %s, Abtastrate %d, GOP %s, p03 %d, p04 %d Seiten, TF %s, rein %s,\n"
          "  RC7 x%d, RC11 x%d, LED1 Puffer-Regelung %d (RC10 %d, RC12 %d), Werte konsistent: %s, SHA-256 %s"
          % ("/".join(map(str, widths)), x["hoehe"], x["ntsc"][0], x["ntsc"][1], video,
             "AUS (nur Video, 0x0C363 = 2)" if audio == 0 else "%d kbit/s" % audio, x["abtastrate"], "/".join(map(str, x["gop"])), x["p03"],
             pages, "/".join(map(str, x["tf"])), x["rein"], x["rc7"], x["rc11"], x["rc9"], x["rc10"], x["rc12"], ok, sha(d)))


if __name__ == "__main__":
    a = sys.argv
    if a[1:2] == ["build"] and len(a) >= 7:
        rest = a[7:]
        pages = None
        if rest and "=" not in rest[0]:
            pages = int(rest[0]); rest = rest[1:]
        build(a[2], a[3], int(a[4]), int(a[5]), int(a[6]), pages, parse_extra(rest))
    elif a[1:2] == ["check"] and len(a) == 3:
        check(a[2])
    else:
        raise SystemExit(__doc__)
