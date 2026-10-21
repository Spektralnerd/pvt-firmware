#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ton_schleife.py - Hoertest als Messung: stimmt der aufgenommene Ton mit sich selbst eine
Schleife spaeter ueberein? Gedacht fuer Aufnahmen, bei denen eine kurze Audiodatei in
Dauerschleife am Eingang haengt (z. B. die 12,168-s-Datei vom Tablet).

Jede Sekunde der Aufnahme wird mit derselben Stelle eine Schleife frueher UND spaeter
verglichen (Kreuzkorrelation, 100-5000 Hz, Suche +-150 ms gegen Schleifenluecken).
Stimmt eine Sekunde mit keinem der beiden Nachbarn ueberein, ist dort der Ton falsch -
auch wenn alle AAC-Bloecke da sind und sauber decodieren.

Braucht ffmpeg (im PATH) und numpy:   sudo pacman -S ffmpeg python-numpy

    python3 ton_schleife.py AUFNAHME.MP4 [weitere.MP4 ...]
    python3 ton_schleife.py AUFNAHME.MP4 --periode 12.168     Schleifenlaenge vorgeben
    python3 ton_schleife.py AUFNAHME.MP4 --quelle schleife.mp3 Laenge aus der Quelldatei

Ohne Vorgabe wird die Schleifenlaenge aus der Aufnahme selbst bestimmt (Autokorrelation
der ersten 60 s, Suche 3-60 s). Ein Wert nahe der Dateilaenge der Quelle heisst: das
Abspielgeraet loopt luecken- und stoerungsfrei.
"""
import argparse
import os
import subprocess
import sys

try:
    import numpy as np
except ImportError:
    sys.exit("numpy fehlt:  sudo pacman -S python-numpy")

SR = 16000
OK, UNSICHER = 0.85, 0.60


def decode(path):
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    try:
        raw = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    except FileNotFoundError:
        sys.exit("ffmpeg fehlt:  sudo pacman -S ffmpeg")
    except subprocess.CalledProcessError as e:
        sys.exit("ffmpeg konnte %s nicht decodieren: %s" % (path, e.stderr.decode(errors="replace").strip()))
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def bandpass(x, lo=100.0, hi=5000.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def find_period(x, lo_s=3.0, hi_s=60.0, use_s=60.0):
    seg = x[:int(use_s * SR)]
    env = np.abs(seg) - np.mean(np.abs(seg))
    E = np.fft.rfft(env, 2 * len(env))
    ac = np.fft.irfft(E * np.conj(E))[:len(env)]
    lo, hi = int(lo_s * SR), min(int(hi_s * SR), len(ac) - 1)
    if hi <= lo:
        return None, 0.0
    k = lo + int(np.argmax(ac[lo:hi]))
    return k / SR, float(ac[k] / (ac[0] + 1e-12))


def similarity(x, start, offset, win, maxlag):
    """beste normierte Korrelation des Fensters [start, start+win) mit dem Fenster bei start+offset (+-maxlag)"""
    a = x[start:start + win]
    a = a - a.mean()
    na = np.linalg.norm(a) + 1e-9
    s0 = start + offset - maxlag
    if s0 < 0 or s0 + win + 2 * maxlag > len(x):
        return None
    seg = x[s0:s0 + win + 2 * maxlag]
    c = np.correlate(seg, a, mode="valid")
    e = np.sqrt(np.convolve(seg ** 2, np.ones(win), "valid")) + 1e-9
    return float(np.max(c / (e * na)))


def analyse(path, period=None):
    x = bandpass(decode(path))
    dur = len(x) / SR
    if period is None:
        period, strength = find_period(x)
        src = "aus der Aufnahme bestimmt (Autokorrelation %.2f)" % strength
        if strength < 0.2:
            return {"datei": path, "fehler": "kein Schleifenton erkannt (Autokorrelation %.2f). Lief die Schleifendatei? "
                    "Sonst Laenge mit --periode oder --quelle vorgeben." % strength}
    else:
        src = "vorgegeben"
    if not period or period * 2 > dur:
        return {"datei": path, "fehler": "Schleifenlaenge nicht bestimmbar (Aufnahme zu kurz oder kein Schleifenton)"}
    P = int(round(period * SR))
    win, maxlag = SR, int(0.15 * SR)
    secs = []
    for s in range(int(dur)):
        st = s * SR
        if st + win > len(x):
            break
        prev = similarity(x, st, -P, win, maxlag)
        nxt = similarity(x, st, P, win, maxlag)
        vals = [v for v in (prev, nxt) if v is not None]
        best = max(vals) if vals else None
        secs.append((s, prev, nxt, best))
    # Randsekunden mit nur einem Nachbarn: ist dieser Nachbar selbst beschaedigt, ist nichts pruefbar
    judged = {s: b for s, _, _, b in secs}
    Ps = int(round(period))
    for i, (s, prev, nxt, best) in enumerate(secs):
        if prev is None and nxt is not None:
            nb = judged.get(s + Ps)
            if nb is not None and nb < UNSICHER and nxt < UNSICHER:
                secs[i] = (s, prev, nxt, None)
        elif nxt is None and prev is not None:
            nb = judged.get(s - Ps)
            if nb is not None and nb < UNSICHER and prev < UNSICHER:
                secs[i] = (s, prev, nxt, None)
    rms = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    # Abschnitte mit falschem Ton (beste Nachbar-Aehnlichkeit unter UNSICHER) und unsichere
    def runs(pred):
        out, cur = [], None
        for s, _, _, b in secs:
            if b is not None and pred(b):
                cur = [s, s] if cur is None else [cur[0], s]
            elif cur is not None:
                out.append(tuple(cur)); cur = None
        if cur is not None:
            out.append(tuple(cur))
        return out
    bad = runs(lambda b: b < UNSICHER)
    unsure = runs(lambda b: UNSICHER <= b < OK)
    good_until = next((s for s, _, _, b in secs if b is not None and b < OK), None)
    return {"datei": path, "dauer_s": dur, "periode_s": period, "periode_quelle": src, "pegel_dbfs": rms,
            "sekunden": secs, "falsch": bad, "unsicher": unsure, "ok_bis_s": good_until}


def report(r):
    L = ["=" * 78, os.path.basename(r["datei"]), "=" * 78]
    if "fehler" in r:
        L.append("FEHLER: " + r["fehler"])
        return "\n".join(L)
    L.append("Ton %.1f s, Pegel %.1f dBFS, Schleife %.3f s (%s)" % (r["dauer_s"], r["pegel_dbfs"], r["periode_s"], r["periode_quelle"]))
    secs = r["sekunden"]
    n = sum(1 for s in secs if s[3] is not None)
    nbad = sum(1 for s in secs if s[3] is not None and s[3] < UNSICHER)
    nuns = sum(1 for s in secs if s[3] is not None and UNSICHER <= s[3] < OK)
    if r["ok_bis_s"] is None:
        L.append("Ergebnis:  TON STIMMT in allen %d Sekunden (Aehnlichkeit >= %.2f)" % (n, OK))
    else:
        L.append("Ergebnis:  Ton stimmt bis %d s; %d Sekunden falsch, %d unsicher (von %d)" % (r["ok_bis_s"], nbad, nuns, n))
        if r["falsch"]:
            L.append("  falsch:   " + ", ".join("%d-%d s" % (a, b + 1) for a, b in r["falsch"]))
        if r["unsicher"]:
            L.append("  unsicher: " + ", ".join("%d-%d s" % (a, b + 1) for a, b in r["unsicher"]))
    L.append("Aehnlichkeit je Sekunde (1,00 = wie die Nachbarschleife; '<' unsicher, '<<' falsch):")
    cells = []
    for s, prev, nxt, best in secs:
        if best is None:
            cells.append("%d:?" % s)
        else:
            cells.append("%d:%.2f%s" % (s, best, "" if best >= OK else ("<" if best >= UNSICHER else "<<")))
    for i in range(0, len(cells), 10):
        L.append("  " + " ".join(cells[i:i + 10]))
    L.append("Hinweis: eine Sekunde gilt als richtig, wenn sie zur Schleife davor ODER danach passt; '?' = nicht")
    L.append("         pruefbar (Rand, einziger Nachbar selbst kaputt). AAC-Rauschen drueckt gesunde Werte auf ~0,95.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Schleifen-Hoertest fuer PVT-Aufnahmen")
    ap.add_argument("dateien", nargs="+")
    ap.add_argument("--periode", type=float, help="Schleifenlaenge in s (sonst aus der Aufnahme bestimmt)")
    ap.add_argument("--quelle", help="Quelldatei der Schleife; ihre Laenge wird als Schleifenlaenge genommen")
    ap.add_argument("--out", help="Ordner fuer TXT-Berichte")
    a = ap.parse_args()
    period = a.periode
    if a.quelle and period is None:
        period = len(decode(a.quelle)) / SR
        print("Schleifenlaenge aus %s: %.3f s" % (a.quelle, period))
    for f in a.dateien:
        r = analyse(f, period)
        txt = report(r)
        print(txt)
        print()
        if a.out:
            os.makedirs(a.out, exist_ok=True)
            with open(os.path.join(a.out, os.path.splitext(os.path.basename(f))[0] + "_tonschleife.txt"), "w", encoding="utf-8") as fh:
                fh.write(txt + "\n")


if __name__ == "__main__":
    main()
