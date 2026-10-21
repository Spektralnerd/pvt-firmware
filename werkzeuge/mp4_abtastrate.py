#!/usr/bin/env python3
"""mp4_abtastrate.py - gleicht die drei Abtastraten-Angaben im Kopf einer PVT-MP4 an (stsd/mp4a,
mdhd-Zeitbasis, AAC-Konfiguration im esds), ohne den Ton neu zu kodieren. Gedacht fuer Versuche
mit geaenderter Abtastrate, falls der ColdFire z. B. die AAC-Konfiguration bei 48 kHz laesst.

    python3 mp4_abtastrate.py AUFNAHME.MP4 32000            -> AUFNAHME_32000.MP4
    python3 mp4_abtastrate.py AUFNAHME.MP4 32000 --mdhd     -> auch die mdhd-Zeitbasis umrechnen

Ohne --mdhd bleiben mdhd-Zeitbasis und stts unangetastet (richtig, wenn der ColdFire sie schon
auf die neue Rate geschrieben hat). Mit --mdhd wird die Zeitbasis der Tonspur auf den neuen
Wert gesetzt (richtig, wenn die Tonspur mit 48000 ausgewiesen ist, die Daten aber zur neuen
Rate gehoeren). Vorher pvt_check.py lesen: Zeile "Abtastrate".
"""
import os
import struct
import sys

ASC_RATES = (96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350)


def boxes(d, start, end, out, depth=0):
    p = start
    while p + 8 <= end:
        size, typ = struct.unpack(">I4s", d[p:p + 8]); hdr = 8
        if size == 1:
            size = struct.unpack(">Q", d[p + 8:p + 16])[0]; hdr = 16
        elif size == 0:
            size = end - p
        if size < hdr:
            break
        out.append((typ, p, size, hdr))
        if typ in (b"moov", b"trak", b"mdia", b"minf", b"stbl"):
            boxes(d, p + hdr, p + size, out, depth + 1)
        elif typ == b"stsd":
            boxes(d, p + hdr + 8, p + size, out, depth + 1)
        elif typ == b"mp4a":
            boxes(d, p + hdr + 28, p + size, out, depth + 1)
        p += size
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    path, rate = sys.argv[1], int(sys.argv[2])
    fix_mdhd = "--mdhd" in sys.argv
    if rate not in ASC_RATES:
        sys.exit("Rate %d hat keinen AAC-Index (erlaubt: %s)" % (rate, ", ".join(map(str, ASC_RATES))))
    d = bytearray(open(path, "rb").read())
    bl = boxes(d, 0, len(d), [])
    changed = []
    # Tonspur finden: trak mit mp4a
    traks = [(p, s) for t, p, s, h in bl if t == b"trak"]
    for tp, ts in traks:
        inner = [b for b in bl if tp <= b[1] < tp + ts]
        mp4a = [b for b in inner if b[0] == b"mp4a"]
        if not mp4a:
            continue
        _, mp, ms, mh = mp4a[0]
        old = struct.unpack(">I", d[mp + 8 + 24:mp + 8 + 28])[0] >> 16
        d[mp + 8 + 24:mp + 8 + 28] = struct.pack(">I", rate << 16); changed.append("mp4a %d -> %d" % (old, rate))
        for t, p, s, h in inner:
            if t == b"esds":
                e = d[p + 8:p + s]
                j = e.find(b"\x05")
                if j >= 0 and j + 3 < len(e):
                    a0, a1 = e[j + 2], e[j + 3]
                    idx = ASC_RATES.index(rate)
                    na0 = (a0 & 0xF8) | (idx >> 1)
                    na1 = (a1 & 0x7F) | ((idx & 1) << 7)
                    d[p + 8 + j + 2] = na0; d[p + 8 + j + 3] = na1
                    oidx = ((a0 & 7) << 1) | (a1 >> 7)
                    changed.append("AAC-Konfig Index %d (%s) -> %d (%d)" % (oidx, ASC_RATES[oidx] if oidx < len(ASC_RATES) else "?", idx, rate))
            if t == b"mdhd" and fix_mdhd:
                v = d[p + 8]
                o = p + 8 + (20 if v == 1 else 12)
                old = struct.unpack(">I", d[o:o + 4])[0]
                d[o:o + 4] = struct.pack(">I", rate); changed.append("mdhd Zeitbasis %d -> %d" % (old, rate))
    if not changed:
        sys.exit("Keine Tonspur (mp4a) gefunden.")
    out = os.path.splitext(path)[0] + "_%d.MP4" % rate
    open(out, "wb").write(d)
    print("\n".join("  " + c for c in changed))
    print("geschrieben:", out)


if __name__ == "__main__":
    main()
