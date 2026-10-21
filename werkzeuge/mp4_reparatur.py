#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mp4_reparatur.py - baut den Index (moov) einer PVT-Aufnahme neu, deren Index fehlt oder
abgeschnitten ist (z. B. "nur Video"-Aufnahmen: der ColdFire bricht beim Schreiben des Index
ab, die Datei laesst sich nicht abspielen). Der Bildstrom im mdat bleibt unveraendert.

    python3 mp4_reparatur.py VID0001x.MP4            -> VID0001x_repariert.MP4

Vorgehen: NAL-Einheiten im mdat (4-Byte-Laengen) lesen, mit dem Slice-Kopf zu Bildern
(Zugriffseinheiten) buendeln - bei Halbbildern: oberes + unteres Halbbild = ein Bild -,
daraus stts/stsz/stss/stsc/stco bauen. SPS/PPS kommen aus dem noch vorhandenen stsd/avcC,
sonst aus dem Strom. Ein vorhandener Teil-Index wird als Gegenprobe benutzt (die ersten
Samplegroessen muessen zur eigenen Buendelung passen). Nur Video; eine Tonspur mit 0 Bloecken
wird nicht angelegt. Liegt pvt_check.py daneben, werden dessen H.264-Parser verwendet.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import pvt_check
    from pvt_check import parse_sps, parse_pps, parse_slice
except ImportError:
    sys.exit("pvt_check.py muss im selben Ordner liegen (H.264-Parser).")
if getattr(pvt_check, "VERSION", "0") < "1.4":
    print("HINWEIS: pvt_check.py %s gefunden; die aktuelle Fassung (1.6) liegt im Test-Paket unter werkzeug/." % getattr(pvt_check, "VERSION", "?"))


def sps_size(sps):
    """Bildgroesse aus dem SPS, auch mit aelteren pvt_check-Fassungen ohne 'breite'/'hoehe'."""
    w = sps.get("breite") or sps["width_mbs"] * 16
    h = sps.get("hoehe") or (2 - sps["frame_mbs_only"]) * sps["height_map_units"] * 16
    return w, h

TICKS_PER_FRAME = {90000: 3600}


def u32(b, o):
    return struct.unpack(">I", b[o:o + 4])[0]


def box(typ, payload):
    return struct.pack(">I4s", 8 + len(payload), typ) + payload


def top_boxes(d):
    out, p = [], 0
    while p + 8 <= len(d):
        size, typ = struct.unpack(">I4s", d[p:p + 8])
        hdr = 8
        if size == 1:
            size = struct.unpack(">Q", d[p + 8:p + 16])[0]
            hdr = 16
        elif size == 0:
            size = len(d) - p
        out.append((typ, p, size, hdr, p + size > len(d)))
        if size < hdr:
            break
        p += size
    return out


def find_boxes(d, start, end, want, out):
    """Sucht (auch in abgeschnittenen Containern) nach Boxen; liefert (typ, offset, groesse, vollstaendig)."""
    p = start
    while p + 8 <= end:
        size, typ = struct.unpack(">I4s", d[p:p + 8])
        if size < 8:
            break
        complete = p + size <= end
        if typ in want:
            out.append((typ, p, size, complete))
        if typ in (b"moov", b"trak", b"mdia", b"minf", b"stbl"):
            find_boxes(d, p + 8, min(p + size, end), want, out)
        p += size
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    d = open(path, "rb").read()
    tb = top_boxes(d)
    print("Boxen:", ", ".join("%s@%#x(%d%s)" % (t.decode("latin1"), p, s, " abgeschnitten" if tr else "") for t, p, s, h, tr in tb))
    ftyp = next((d[p:p + s] for t, p, s, h, tr in tb if t == b"ftyp"), None)
    mdat = next(((p, s, h) for t, p, s, h, tr in tb if t == b"mdat"), None)
    if mdat is None:
        sys.exit("Kein mdat gefunden.")
    mdat_off, mdat_size, mdat_hdr = mdat
    data_start, data_end = mdat_off + mdat_hdr, min(mdat_off + mdat_size, len(d))
    moov = next(((p, s) for t, p, s, h, tr in tb if t == b"moov"), None)
    found = []
    if moov:
        find_boxes(d, moov[0] + 8, min(moov[0] + moov[1], len(d)), {b"mvhd", b"tkhd", b"mdhd", b"hdlr", b"vmhd", b"dinf", b"stsd", b"stts", b"stsz", b"avcC"}, found)
    have = {}
    for typ, p, s, complete in found:
        if typ == b"hdlr" and d[p + 16:p + 20] != b"vide":
            continue
        if typ not in have:
            have[typ] = (p, s, complete)
    for k, (p, s, c) in have.items():
        print("  Index-Teil %s: %d Byte%s" % (k.decode("latin1"), s, "" if c else " (abgeschnitten)"))

    # SPS/PPS: aus avcC, sonst aus dem Strom
    sps_map, pps_map, avcc = {}, {}, None
    if b"stsd" in have and have[b"stsd"][2]:
        p, s, _ = have[b"stsd"]
        stsd = d[p:p + s]
        i = stsd.find(b"avcC")
        if i > 0:
            alen = u32(stsd, i - 4)
            avcc = stsd[i + 4:i - 4 + alen]
            q = 6
            for _ in range(avcc[5] & 31):
                ln = struct.unpack(">H", avcc[q:q + 2])[0]
                s_ = parse_sps(avcc[q + 2:q + 2 + ln])
                sps_map[s_["sps_id"]] = s_
                q += 2 + ln
            npps = avcc[q]
            q += 1
            for _ in range(npps):
                ln = struct.unpack(">H", avcc[q:q + 2])[0]
                p_ = parse_pps(avcc[q + 2:q + 2 + ln])
                pps_map[p_["pps_id"]] = p_
                q += 2 + ln
    # Strom lesen
    nals = []
    p = data_start
    while p + 4 <= data_end:
        ln = u32(d, p)
        if ln == 0 or p + 4 + ln > data_end:
            print("  Strom endet bei %#x (Rest %d Byte wird verworfen)" % (p, data_end - p))
            break
        nals.append((p, 4 + ln, d[p + 4] & 31))
        p += 4 + ln
    stream_end = p
    inline_sps = [n for n in nals if n[2] == 7]
    inline_pps = [n for n in nals if n[2] == 8]
    for off, ln, t in inline_sps:
        s_ = parse_sps(d[off + 4:off + ln])
        sps_map.setdefault(s_["sps_id"], s_)
    for off, ln, t in inline_pps:
        p_ = parse_pps(d[off + 4:off + ln])
        pps_map.setdefault(p_["pps_id"], p_)
    if not sps_map or not pps_map:
        sys.exit("Keine SPS/PPS gefunden (weder im Index noch im Strom) - ohne sie kein Bild.")
    sps = next(iter(sps_map.values()))
    sps_w, sps_h = sps_size(sps)
    print("  NAL-Einheiten: %d, SPS %dx%d, Halbbilder: %s, SPS im Strom: %d, PPS im Strom: %d"
          % (len(nals), sps_w, sps_h, "ja" if not sps["frame_mbs_only"] else "nein", len(inline_sps), len(inline_pps)))

    # Buendeln zu Bildern: ein Bild beginnt mit Nicht-VCL-NALs (SPS/PPS/SEI/AUD) oder mit einem Slice,
    # dessen first_mb = 0 ist und der nicht das untere Halbbild zum vorigen oberen ist.
    samples, cur, cur_has_vcl, cur_field_top = [], [], False, False
    idr = []
    for off, ln, t in nals:
        if t in (1, 5):
            h = parse_slice(d[off + 4:off + ln], sps_map, pps_map)
            new_pic = h["first_mb"] == 0 and not (h["field"] and h["bottom"] and cur_field_top)
            if new_pic and cur_has_vcl:
                samples.append(cur)
                cur, cur_has_vcl, cur_field_top = [], False, False
            cur.append((off, ln))
            cur_has_vcl = True
            if h["field"] and not h["bottom"]:
                cur_field_top = True
            if h["field"] and h["bottom"]:
                cur_field_top = False
            if t == 5 and (not idr or idr[-1] != len(samples) + 1):
                idr.append(len(samples) + 1)
        else:
            if cur_has_vcl:
                samples.append(cur)
                cur, cur_has_vcl, cur_field_top = [], False, False
            cur.append((off, ln))
    if cur:
        samples.append(cur)
    sizes = [sum(ln for _, ln in s) for s in samples]
    offsets = [s[0][0] for s in samples]
    # Zusammenhang pruefen
    for i in range(1, len(samples)):
        if offsets[i] != offsets[i - 1] + sizes[i - 1]:
            sys.exit("Bilder liegen nicht lueckenlos hintereinander bei Bild %d" % i)
    print("  Bilder: %d, Schluesselbilder: %d, Groesse min/median/max %d/%d/%d Byte"
          % (len(sizes), len(idr), min(sizes), sorted(sizes)[len(sizes) // 2], max(sizes)))

    # Gegenprobe mit dem vorhandenen Index: der ColdFire schreibt bei "nur Video" nur die letzten
    # Eintraege seines Tabellenpuffers (VID00012: 118 von 1509), die Boxgroessen nennen aber die volle Zahl.
    # Die vorhandenen Eintraege muessen zum Anfang ODER zum Ende der eigenen Buendelung passen.
    if b"stsz" in have:
        p, s, complete = have[b"stsz"]
        cnt = u32(d, p + 16)
        known = []
        q = p + 20
        while q + 4 <= min(p + s, len(d)):
            v = u32(d, q)
            if q + 8 <= len(d) and d[q + 4:q + 8] in (b"stsc", b"stco", b"stss", b"stsh", b"ctts", b"sdtp"):
                break  # naechste Box beginnt schon: Tabelle kuerzer als angegeben
            known.append(v)
            q += 4
        n_known = len(known)
        head_ok = n_known <= len(sizes) and known == sizes[:n_known]
        tail_ok = n_known <= len(sizes) and known == sizes[len(sizes) - n_known:]
        print("  Gegenprobe stsz: Index nennt %d Bilder und enthaelt %d Groessen (%s); gefunden %d Bilder; passt zum %s"
              % (cnt, n_known, "vollstaendig" if n_known == cnt else "unvollstaendig", len(sizes),
                 "Anfang" if head_ok else ("Ende" if tail_ok else "NICHTS")))
        if n_known and not (head_ok or tail_ok):
            sys.exit("Buendelung passt nicht zum vorhandenen Index - Abbruch (nichts geschrieben).")
        if cnt != len(sizes):
            print("  HINWEIS: Bildzahl im Index (%d) und gefunden (%d) weichen ab; es gilt der Strom." % (cnt, len(sizes)))
    if b"stts" in have and have[b"stts"][2]:
        p, s, _ = have[b"stts"]
        delta = u32(d, p + 20)
    else:
        delta = 3600
    timescale = 90000
    if b"mdhd" in have and have[b"mdhd"][2]:
        p, s, _ = have[b"mdhd"]
        v = d[p + 8]
        timescale = u32(d, p + (28 if v == 1 else 20))
    n = len(sizes)
    dur = n * delta

    # Index bauen
    def fullbox(typ, payload, version=0, flags=0):
        return box(typ, struct.pack(">I", (version << 24) | flags) + payload)

    if b"mvhd" in have and have[b"mvhd"][2]:
        p, s, _ = have[b"mvhd"]
        mvhd = bytearray(d[p:p + s])
        mts = u32(mvhd, 20)
        mvhd[24:28] = struct.pack(">I", dur * mts // timescale)
        mvhd = bytes(mvhd)
    else:
        mvhd = fullbox(b"mvhd", struct.pack(">IIII", 0, 0, 1000, dur * 1000 // timescale) + struct.pack(">IH", 0x00010000, 0x0100) + b"\0" * 10
                       + struct.pack(">9I", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) + b"\0" * 24 + struct.pack(">I", 2))
    if b"tkhd" in have and have[b"tkhd"][2]:
        p, s, _ = have[b"tkhd"]
        tkhd = bytearray(d[p:p + s])
        mts = u32(mvhd, 20)
        tkhd[28:32] = struct.pack(">I", dur * mts // timescale)
        tkhd = bytes(tkhd)
    else:
        tkhd = fullbox(b"tkhd", struct.pack(">IIIII", 0, 0, 1, 0, dur * 1000 // timescale) + b"\0" * 8 + struct.pack(">HHHH", 0, 0, 0, 0)
                       + struct.pack(">9I", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) + struct.pack(">II", sps_w << 16, sps_h << 16), flags=7)
    if b"mdhd" in have and have[b"mdhd"][2]:
        p, s, _ = have[b"mdhd"]
        mdhd = bytearray(d[p:p + s])
        mdhd[24:28] = struct.pack(">I", dur)
        mdhd = bytes(mdhd)
    else:
        mdhd = fullbox(b"mdhd", struct.pack(">IIII", 0, 0, timescale, dur) + struct.pack(">HH", 0x15c7, 0))
    if b"hdlr" in have and have[b"hdlr"][2]:
        p, s, _ = have[b"hdlr"]
        hdlr = d[p:p + s]
    else:
        hdlr = fullbox(b"hdlr", b"\0" * 4 + b"vide" + b"\0" * 12 + b"AVC Video Handler\0")
    vmhd = fullbox(b"vmhd", b"\0" * 8, flags=1)
    dinf = box(b"dinf", fullbox(b"dref", struct.pack(">I", 1) + fullbox(b"url ", b"", flags=1)))
    if b"stsd" in have and have[b"stsd"][2]:
        p, s, _ = have[b"stsd"]
        stsd = d[p:p + s]
    else:
        # avc1 + avcC aus dem Strom bauen
        sps_nal = d[inline_sps[0][0] + 4:inline_sps[0][0] + inline_sps[0][1]]
        pps_nal = d[inline_pps[0][0] + 4:inline_pps[0][0] + inline_pps[0][1]]
        avcc_new = bytes([1, sps_nal[1], sps_nal[2], sps_nal[3], 0xff, 0xe1]) + struct.pack(">H", len(sps_nal)) + sps_nal + b"\x01" + struct.pack(">H", len(pps_nal)) + pps_nal
        avc1 = box(b"avc1", b"\0" * 6 + struct.pack(">H", 1) + b"\0" * 16 + struct.pack(">HH", sps_w, sps_h)
                   + struct.pack(">IIIH", 0x480000, 0x480000, 0, 1) + b"\0" * 32 + struct.pack(">Hh", 24, -1) + box(b"avcC", avcc_new))
        stsd = fullbox(b"stsd", struct.pack(">I", 1) + avc1)
    stts = fullbox(b"stts", struct.pack(">III", 1, n, delta))
    stss = fullbox(b"stss", struct.pack(">I", len(idr)) + b"".join(struct.pack(">I", i) for i in idr))
    stsc = fullbox(b"stsc", struct.pack(">IIII", 1, 1, n, 1))
    stsz = fullbox(b"stsz", struct.pack(">II", 0, n) + b"".join(struct.pack(">I", s) for s in sizes))
    # Ausgabe: ftyp + mdat (nur der verwertete Strom) + moov; stco zeigt auf den mdat-Inhalt
    ftyp = ftyp or box(b"ftyp", b"isom" + struct.pack(">I", 0) + b"isomavc1")
    stream = d[data_start:stream_end]
    new_mdat_hdr = 8 if len(stream) + 8 < 0xFFFFFFFF else 16
    chunk_off = len(ftyp) + new_mdat_hdr
    stco = fullbox(b"stco", struct.pack(">II", 1, chunk_off))
    stbl = box(b"stbl", stsd + stts + stss + stsc + stsz + stco)
    minf = box(b"minf", vmhd + dinf + stbl)
    mdia = box(b"mdia", mdhd + hdlr + minf)
    trak = box(b"trak", tkhd + mdia)
    moov_new = box(b"moov", mvhd + trak)
    if new_mdat_hdr == 8:
        mdat_box = struct.pack(">I4s", 8 + len(stream), b"mdat")
    else:
        mdat_box = struct.pack(">I4sQ", 1, b"mdat", 16 + len(stream))
    out = os.path.splitext(path)[0] + "_repariert" + os.path.splitext(path)[1]
    with open(out, "wb") as f:
        f.write(ftyp)
        f.write(mdat_box)
        f.write(stream)
        f.write(moov_new)
    print("geschrieben: %s (%d Bilder, %.2f s, Index %d Byte)" % (out, n, dur / timescale, len(moov_new)))


if __name__ == "__main__":
    main()
