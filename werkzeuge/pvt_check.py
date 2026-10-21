#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pvt_check.py - Pruefwerkzeug fuer MP4-Aufnahmen des Pinnacle Video Transfer (MG1264)

Nur Python-Standardbibliothek (ab 3.8). Kein FFmpeg, keine Internetverbindung.
Das Werkzeug LIEST die MP4-Dateien nur; es veraendert und flasht nichts.

Aufruf:
    python pvt_check.py AUFNAHME.MP4 [weitere.MP4 ...]
    python pvt_check.py *.MP4 --out ergebnisse     (zusaetzlich TXT, CSV, JSON je Datei)
    python pvt_check.py AUFNAHME.MP4 --alle        (alle auffaelligen Bilder auflisten)

Was geprueft wird (alles direkt aus den MP4-Tabellen und den H.264-Slice-Koepfen):
  * Laenge von Bild- und Tonspur (stts) und Kopfangaben (mdhd), Differenzen
  * tatsaechliche Datenraten, Rate je Sekunde, hoechste 0,2-s- und 1-s-Fenster
  * Schluesselbilder (stss) und ihre Abstaende
  * QP je Bild (26 + pic_init_qp_minus26 + slice_qp_delta)
  * "leere" Bilder: alle Makrobloecke uebersprungen (exakte Wiederholung, nur CAVLC)
  * sehr kleine Bilder (< 1000 Byte) und Teilbilder (< 40 % der Nachbarbilder, nur nahe
    an Aussetzern); ruhige oder schwarze Szenen werden dabei nicht mitgezaehlt
  * Beginn der Stoerung: Zeitpunkt UND Videodatenmenge bis dahin
  * Audio/Video-Verzahnung in Dateireihenfolge: Videopausen, waehrend Ton weiterlaeuft

Unter Windows: MP4-Dateien einfach auf pvt_check_ziehen.bat ziehen.
Die kleinen TXT/CSV/JSON-Dateien reichen fuer eine spaetere Auswertung; die grossen
Videos muessen dafuer nicht weitergegeben werden.

Grenzen: Es wird nichts decodiert. "Leer" ist eindeutig (alle MB uebersprungen),
"sehr klein" und "Teilbild" sind Hinweise, keine Pixelbeweise. Die Dateireihenfolge
zeigt, wann Daten beim Schreiben ankamen, nicht die Echtzeit am Geraet.
"""

import argparse
from array import array
import csv
import hashlib
import json
import os
import statistics
import struct
import sys

VERSION = "1.6"

# ---------------------------------------------------------------------------
# MP4 / ISO-BMFF
# ---------------------------------------------------------------------------

CONTAINERS = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"dinf"}


class Mp4Error(Exception):
    pass


def iter_boxes(f, start, end):
    """Liefert (typ, box_start, payload_start, box_ende) fuer alle Boxen im Bereich."""
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        head = f.read(8)
        if len(head) < 8:
            break
        size, typ = struct.unpack(">I4s", head)
        hsize = 8
        if size == 1:
            size = struct.unpack(">Q", f.read(8))[0]
            hsize = 16
        elif size == 0:
            size = end - pos
        if size < hsize:
            raise Mp4Error("Kaputte Boxgroesse bei Offset %d" % pos)
        yield typ, pos, pos + hsize, min(pos + size, end)
        pos += size


def read_payload(f, pstart, bend):
    f.seek(pstart)
    return f.read(bend - pstart)


ASC_RATES = (96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350)


def parse_track(f, pstart, bend):
    t = {"handler": None, "timescale": None, "mdhd_duration": None, "stts": [],
         "ctts": [], "stss": None, "stsc": [], "stsz": [], "chunk_offsets": [],
         "codec": None, "width": None, "height": None, "avcC": None,
         "samplerate": None, "channels": None, "elst": None, "track_id": None,
         "tkhd_width": None, "tkhd_height": None, "asc_rate": None, "asc_index": None, "asc_channels": None}

    def walk(s, e):
        for typ, bs, ps, be in iter_boxes(f, s, e):
            if typ in CONTAINERS:
                walk(ps, be)
            elif typ == b"tkhd":
                d = read_payload(f, ps, be)
                v = d[0]
                t["track_id"] = struct.unpack(">I", d[12:16] if v == 0 else d[20:24])[0]
                # v1.3: Anzeigegroesse des Tracks (16.16-Festkomma, letzte 8 Byte der tkhd)
                if len(d) >= 8:
                    tw, th = struct.unpack(">II", d[-8:])
                    t["tkhd_width"], t["tkhd_height"] = tw / 65536.0, th / 65536.0
            elif typ == b"mdhd":
                d = read_payload(f, ps, be)
                if d[0] == 1:
                    t["timescale"], t["mdhd_duration"] = struct.unpack(">IQ", d[20:32])
                else:
                    t["timescale"], t["mdhd_duration"] = struct.unpack(">II", d[12:20])
            elif typ == b"hdlr":
                d = read_payload(f, ps, be)
                t["handler"] = d[8:12].decode("latin-1")
            elif typ == b"elst":
                d = read_payload(f, ps, be)
                v = d[0]
                n = struct.unpack(">I", d[4:8])[0]
                ent = []
                p = 8
                for _ in range(n):
                    if v == 1:
                        dur, mt = struct.unpack(">Qq", d[p:p + 16]); p += 16
                    else:
                        dur, mt = struct.unpack(">Ii", d[p:p + 8]); p += 8
                    rate = struct.unpack(">i", d[p:p + 4])[0]; p += 4
                    ent.append((dur, mt, rate))
                t["elst"] = ent
            elif typ == b"stsd":
                d = read_payload(f, ps, be)
                n = struct.unpack(">I", d[4:8])[0]
                if n >= 1:
                    esize, etype = struct.unpack(">I4s", d[8:16])
                    t["codec"] = etype.decode("latin-1")
                    entry = d[16:8 + esize]
                    if etype in (b"avc1", b"avc3"):
                        t["width"], t["height"] = struct.unpack(">HH", entry[24:28])
                        p = 78
                        while p + 8 <= len(entry):
                            cs, ct = struct.unpack(">I4s", entry[p:p + 8])
                            if cs < 8:
                                break
                            if ct == b"avcC":
                                t["avcC"] = entry[p + 8:p + cs]
                            p += cs
                    elif etype == b"mp4a":
                        t["channels"] = struct.unpack(">H", entry[16:18])[0]
                        t["samplerate"] = struct.unpack(">I", entry[24:28])[0] >> 16
                        # v1.5: AAC-Konfiguration (AudioSpecificConfig) aus dem esds: Abtastraten-Index 0..12
                        i = entry.find(b"esds", 28)
                        if i > 0:
                            e = entry[i + 8:]
                            j = e.find(b"\x05")      # DecoderSpecificInfo-Tag
                            if j >= 0 and j + 3 < len(e):
                                asc = e[j + 2:j + 4]
                                idx = ((asc[0] & 7) << 1) | (asc[1] >> 7)
                                t["asc_index"] = idx
                                t["asc_channels"] = (asc[1] >> 3) & 15
                                t["asc_rate"] = ASC_RATES[idx] if idx < len(ASC_RATES) else None
            elif typ == b"stts":
                d = read_payload(f, ps, be)
                n = struct.unpack(">I", d[4:8])[0]
                t["stts"] = list(struct.iter_unpack(">II", d[8:8 + 8 * n]))
            elif typ == b"ctts":
                d = read_payload(f, ps, be)
                n = struct.unpack(">I", d[4:8])[0]
                t["ctts"] = list(struct.iter_unpack(">Ii", d[8:8 + 8 * n]))
            elif typ == b"stss":
                d = read_payload(f, ps, be)
                n = struct.unpack(">I", d[4:8])[0]
                t["stss"] = [x[0] for x in struct.iter_unpack(">I", d[8:8 + 4 * n])]
            elif typ == b"stsc":
                d = read_payload(f, ps, be)
                n = struct.unpack(">I", d[4:8])[0]
                t["stsc"] = list(struct.iter_unpack(">III", d[8:8 + 12 * n]))
            elif typ == b"stsz":
                d = read_payload(f, ps, be)
                ssize, n = struct.unpack(">II", d[4:12])
                if ssize:
                    t["stsz"] = [ssize] * n
                else:
                    t["stsz"] = [x[0] for x in struct.iter_unpack(">I", d[12:12 + 4 * n])]
            elif typ == b"stz2":
                d = read_payload(f, ps, be)
                fs = d[7]
                n = struct.unpack(">I", d[8:12])[0]
                raw = d[12:]
                if fs == 8:
                    t["stsz"] = list(raw[:n])
                elif fs == 16:
                    t["stsz"] = [x[0] for x in struct.iter_unpack(">H", raw[:2 * n])]
                else:
                    t["stsz"] = [(raw[i // 2] >> (4 if i % 2 == 0 else 0)) & 15 for i in range(n)]
            elif typ == b"stco":
                d = read_payload(f, ps, be)
                n = struct.unpack(">I", d[4:8])[0]
                t["chunk_offsets"] = [x[0] for x in struct.iter_unpack(">I", d[8:8 + 4 * n])]
            elif typ == b"co64":
                d = read_payload(f, ps, be)
                n = struct.unpack(">I", d[4:8])[0]
                t["chunk_offsets"] = [x[0] for x in struct.iter_unpack(">Q", d[8:8 + 8 * n])]

    walk(pstart, bend)
    return t


class Samples:
    """Sampletabelle einer Spur, speichersparend in Arrays (offset, groesse, dts, dauer, cts)."""
    __slots__ = ("off", "size", "dts", "dur", "cts")

    def __init__(self):
        self.off = array("q")
        self.size = array("q")
        self.dts = array("q")
        self.dur = array("q")
        self.cts = array("q")

    def __len__(self):
        return len(self.off)

    def __getitem__(self, i):
        return (self.off[i], self.size[i], self.dts[i], self.dur[i], self.cts[i])

    def __iter__(self):
        return zip(self.off, self.size, self.dts, self.dur, self.cts)


def build_samples(t):
    """Liefert Samples (offset, groesse, dts, dauer, cts_offset) in Spur-Zeiteinheiten."""
    sizes = t["stsz"]
    n = len(sizes)
    s = Samples()
    stsc = t["stsc"]
    si = 0
    k = 0
    for ci, coff in enumerate(t["chunk_offsets"], 1):
        while k + 1 < len(stsc) and stsc[k + 1][0] <= ci:
            k += 1
        if not stsc or stsc[k][0] > ci:
            raise Mp4Error("stsc unvollstaendig")
        o = coff
        for _ in range(stsc[k][1]):
            if si >= n:
                break
            s.off.append(o)
            s.size.append(sizes[si])
            o += sizes[si]
            si += 1
    if len(s.off) != n:
        raise Mp4Error("Sample-Tabellen passen nicht zusammen (%d Offsets, %d Groessen)" % (len(s.off), n))
    cur = 0
    for cnt, delta in t["stts"]:
        for _ in range(cnt):
            if len(s.dts) >= n:
                break
            s.dts.append(cur)
            s.dur.append(delta)
            cur += delta
    if len(s.dts) < n:
        raise Mp4Error("stts kuerzer als Sampleanzahl")
    cts = [0] * n
    if t["ctts"]:
        i = 0
        for cnt, off in t["ctts"]:
            for _ in range(cnt):
                if i < n:
                    cts[i] = off
                i += 1
    s.cts = array("q", cts)
    t["stsz"] = None  # Speicher freigeben
    return s


def apply_edit_shift(samples, t, info):
    """Einfache Editlisten-Verschiebung wie bei FFmpeg (leere Edits + media_time)."""
    if not t["elst"] or not samples:
        return samples
    mts = info["mvhd"][0] if info["mvhd"] else t["timescale"]
    shift = 0
    for dur, mt, rate in t["elst"]:
        if mt == -1:
            shift += dur * t["timescale"] // mts
        else:
            shift -= mt
            break
    samples.dts = array("q", (d + shift for d in samples.dts))
    return samples


def read_mp4(path):
    info = {"path": path, "size": os.path.getsize(path), "brand": None,
            "moov_pos": None, "mdat_pos": None, "mvhd": None, "tracks": []}
    with open(path, "rb") as f:
        moov = None
        for typ, bs, ps, be in iter_boxes(f, 0, info["size"]):
            if typ == b"ftyp":
                info["brand"] = read_payload(f, ps, min(be, ps + 4)).decode("latin-1")
            elif typ == b"moov":
                moov = (ps, be)
                info["moov_pos"] = bs
            elif typ == b"mdat" and info["mdat_pos"] is None:
                info["mdat_pos"] = bs
        if moov is None:
            raise Mp4Error("Keine moov-Box gefunden: Datei unvollstaendig (Aufnahme nicht "
                           "ordnungsgemaess beendet?)")
        for typ, bs, ps, be in iter_boxes(f, moov[0], moov[1]):
            if typ == b"mvhd":
                d = read_payload(f, ps, be)
                if d[0] == 1:
                    ts, dur = struct.unpack(">IQ", d[20:32])
                else:
                    ts, dur = struct.unpack(">II", d[12:20])
                info["mvhd"] = (ts, dur)
            elif typ == b"trak":
                info["tracks"].append(parse_track(f, ps, be))
    return info


# ---------------------------------------------------------------------------
# H.264: Bitleser, SPS/PPS, Slice-Kopf
# ---------------------------------------------------------------------------

class BitReader:
    def __init__(self, data):
        self.d = data
        self.p = 0  # Bitposition

    def u(self, n):
        v = 0
        for _ in range(n):
            byte = self.d[self.p >> 3]
            v = (v << 1) | ((byte >> (7 - (self.p & 7))) & 1)
            self.p += 1
        return v

    def ue(self):
        z = 0
        while self.u(1) == 0:
            z += 1
            if z > 31:
                raise ValueError("ue(v) zu lang")
        return (1 << z) - 1 + (self.u(z) if z else 0)

    def se(self):
        k = self.ue()
        return (k + 1) // 2 if k & 1 else -(k // 2)


def rbsp(nal):
    """Entfernt Emulation-Prevention-Bytes (00 00 03)."""
    out = bytearray()
    zeros = 0
    for b in nal:
        if zeros >= 2 and b == 3:
            zeros = 0
            continue
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
    return bytes(out)


HIGH_PROFILES = {100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135}
# H.264 Tabelle E-1 (aspect_ratio_idc -> Pixel-Seitenverhaeltnis)
SAR_TABLE = {1: (1, 1), 2: (12, 11), 3: (10, 11), 4: (16, 11), 5: (40, 33), 6: (24, 11), 7: (20, 11),
             8: (32, 11), 9: (80, 33), 10: (18, 11), 11: (15, 11), 12: (64, 33), 13: (160, 99),
             14: (4, 3), 15: (3, 2), 16: (2, 1)}


def parse_sps(nal):
    r = BitReader(rbsp(nal[1:]))
    s = {"profile_idc": r.u(8)}
    r.u(8)
    s["level_idc"] = r.u(8)
    s["sps_id"] = r.ue()
    s["chroma_format_idc"] = 1
    s["separate_colour_plane"] = 0
    if s["profile_idc"] in HIGH_PROFILES:
        s["chroma_format_idc"] = r.ue()
        if s["chroma_format_idc"] == 3:
            s["separate_colour_plane"] = r.u(1)
        r.ue(); r.ue(); r.u(1)
        if r.u(1):
            for i in range(8 if s["chroma_format_idc"] != 3 else 12):
                if r.u(1):
                    size = 16 if i < 6 else 64
                    last = nxt = 8
                    for _ in range(size):
                        if nxt != 0:
                            nxt = (last + r.se() + 256) % 256
                        last = nxt if nxt != 0 else last
    s["log2_max_frame_num"] = r.ue() + 4
    s["poc_type"] = r.ue()
    if s["poc_type"] == 0:
        s["log2_max_poc_lsb"] = r.ue() + 4
    elif s["poc_type"] == 1:
        s["delta_pic_order_always_zero"] = r.u(1)
        r.se(); r.se()
        for _ in range(r.ue()):
            r.se()
    s["max_num_ref_frames"] = r.ue()
    r.u(1)
    s["width_mbs"] = r.ue() + 1
    s["height_map_units"] = r.ue() + 1
    s["frame_mbs_only"] = r.u(1)
    s["mbaff"] = r.u(1) if not s["frame_mbs_only"] else 0
    s["chroma_array_type"] = 0 if s["separate_colour_plane"] else s["chroma_format_idc"]
    # v1.2: kodierte Groesse (mit Cropping) und Pixel-Seitenverhaeltnis aus der VUI
    try:
        r.u(1)  # direct_8x8_inference_flag
        crop = (r.ue(), r.ue(), r.ue(), r.ue()) if r.u(1) else (0, 0, 0, 0)
        cx = 2 if s["chroma_array_type"] in (1, 2) else 1
        cy = (2 if s["chroma_array_type"] == 1 else 1) * (2 - s["frame_mbs_only"])
        s["breite"] = s["width_mbs"] * 16 - cx * (crop[0] + crop[1])
        s["hoehe"] = (2 - s["frame_mbs_only"]) * s["height_map_units"] * 16 - cy * (crop[2] + crop[3])
        s["sar"] = None
        if r.u(1) and r.u(1):  # vui_parameters_present_flag, aspect_ratio_info_present_flag
            idc = r.u(8)
            s["sar"] = (r.u(16), r.u(16)) if idc == 255 else SAR_TABLE.get(idc)
    except Exception:
        pass
    return s


def parse_pps(nal):
    r = BitReader(rbsp(nal[1:]))
    p = {"pps_id": r.ue(), "sps_id": r.ue()}
    p["cabac"] = r.u(1)
    p["bottom_field_poc_present"] = r.u(1)
    p["num_slice_groups"] = r.ue() + 1
    if p["num_slice_groups"] > 1:
        raise ValueError("Slice-Gruppen werden nicht unterstuetzt")
    p["num_ref_idx_l0_default"] = r.ue() + 1
    p["num_ref_idx_l1_default"] = r.ue() + 1
    p["weighted_pred"] = r.u(1)
    p["weighted_bipred_idc"] = r.u(2)
    p["pic_init_qp"] = 26 + r.se()
    r.se()
    r.se()
    p["deblocking_control_present"] = r.u(1)
    r.u(1)
    p["redundant_pic_cnt_present"] = r.u(1)
    return p


def parse_slice(nal, sps_map, pps_map):
    """Parst den Slice-Kopf und (bei CAVLC-P-Slices) den ersten mb_skip_run."""
    nal_ref_idc = (nal[0] >> 5) & 3
    nal_type = nal[0] & 31
    r = BitReader(rbsp(nal[1:80]))
    h = {"nal_type": nal_type}
    h["first_mb"] = r.ue()
    st = r.ue()
    h["slice_type"] = st % 5  # 0=P 1=B 2=I 3=SP 4=SI
    pps = pps_map[r.ue()]
    sps = sps_map[pps["sps_id"]]
    if sps["separate_colour_plane"]:
        r.u(2)
    h["frame_num"] = r.u(sps["log2_max_frame_num"])
    field = bottom = 0
    if not sps["frame_mbs_only"]:
        field = r.u(1)
        if field:
            bottom = r.u(1)
    h["field"], h["bottom"] = field, bottom
    if nal_type == 5:
        r.ue()
    if sps["poc_type"] == 0:
        r.u(sps["log2_max_poc_lsb"])
        if pps["bottom_field_poc_present"] and not field:
            r.se()
    if sps["poc_type"] == 1 and not sps.get("delta_pic_order_always_zero", 0):
        r.se()
        if pps["bottom_field_poc_present"] and not field:
            r.se()
    if pps["redundant_pic_cnt_present"]:
        r.ue()
    t = h["slice_type"]
    if t == 1:
        r.u(1)
    n0, n1 = pps["num_ref_idx_l0_default"], pps["num_ref_idx_l1_default"]
    if t in (0, 1, 3):
        if r.u(1):
            n0 = r.ue() + 1
            if t == 1:
                n1 = r.ue() + 1
    # ref_pic_list_modification
    for lst in ((0, 1) if t == 1 else ((0,) if t in (0, 3) else ())):
        if r.u(1):
            while True:
                idc = r.ue()
                if idc in (0, 1, 2):
                    r.ue()
                elif idc == 3:
                    break
                else:
                    raise ValueError("ungueltige ref_pic_list_modification")
    # pred_weight_table
    if (pps["weighted_pred"] and t in (0, 3)) or (pps["weighted_bipred_idc"] == 1 and t == 1):
        r.ue()
        cat = sps["chroma_array_type"]
        if cat:
            r.ue()
        for n in ((n0, n1) if t == 1 else (n0,)):
            for _ in range(n):
                if r.u(1):
                    r.se(); r.se()
                if cat and r.u(1):
                    r.se(); r.se(); r.se(); r.se()
    # dec_ref_pic_marking
    if nal_ref_idc:
        if nal_type == 5:
            r.u(1); r.u(1)
        elif r.u(1):
            while True:
                mmco = r.ue()
                if mmco == 0:
                    break
                if mmco in (1, 3):
                    r.ue()
                if mmco == 2:
                    r.ue()
                if mmco in (3, 6):
                    r.ue()
                if mmco == 4:
                    r.ue()
    if pps["cabac"] and t not in (2, 4):
        r.ue()
    h["qp"] = pps["pic_init_qp"] + r.se()
    if t in (3, 4):
        if t == 3:
            r.u(1)
        r.se()
    if pps["deblocking_control_present"]:
        idc = r.ue()
        h["deblock_idc"] = idc
        if idc != 1:
            h["alpha"] = r.se()
            h["beta"] = r.se()
    height = (2 - sps["frame_mbs_only"]) * sps["height_map_units"] // (1 + field)
    h["mbs_in_pic"] = sps["width_mbs"] * height
    h["skip_run"] = None
    if not pps["cabac"] and t in (0, 1, 3):
        try:
            h["skip_run"] = r.ue()
        except (IndexError, ValueError):
            h["skip_run"] = None
    mb_factor = 2 if (sps["mbaff"] and not field) else 1
    h["mbs_in_slice_max"] = h["mbs_in_pic"] - h["first_mb"] * mb_factor
    return h


def parse_avcc(avcc):
    length_size = (avcc[4] & 3) + 1
    sps_map, pps_map = {}, {}
    p = 5
    nsps = avcc[p] & 31
    p += 1
    sps_info = None
    for _ in range(nsps):
        ln = struct.unpack(">H", avcc[p:p + 2])[0]
        nal = avcc[p + 2:p + 2 + ln]
        s = parse_sps(nal)
        sps_map[s["sps_id"]] = s
        sps_info = s
        p += 2 + ln
    npps = avcc[p]
    p += 1
    for _ in range(npps):
        ln = struct.unpack(">H", avcc[p:p + 2])[0]
        nal = avcc[p + 2:p + 2 + ln]
        q = parse_pps(nal)
        pps_map[q["pps_id"]] = q
        p += 2 + ln
    return length_size, sps_map, pps_map, sps_info


def scan_video_headers(path, samples, avcc):
    """Liest je Videobild die Slice-Koepfe. Liefert Liste von Dicts (oder None)."""
    length_size, sps_map, pps_map, sps_info = parse_avcc(avcc)
    out = []
    errors = 0
    total = len(samples)
    step = max(1, total // 20)
    with open(path, "rb") as f:
        for k, (off, size, _, _, _) in enumerate(samples):
            if total > 20000 and k % step == 0:
                sys.stderr.write("\r  lese Slice-Koepfe: %3d %%" % (100 * k // total))
                sys.stderr.flush()
            f.seek(off)
            head = f.read(min(size, 256))
            slices = []
            err = None
            try:
                p = 0
                while p + length_size <= size:
                    if p + length_size > len(head):
                        f.seek(off + p)
                        head2 = f.read(length_size + 96)
                        base = p
                    else:
                        head2 = head
                        base = 0
                    q = p - base
                    n = int.from_bytes(head2[q:q + length_size], "big")
                    if n <= 0 or p + length_size + n > size:
                        raise ValueError("NAL-Laenge ungueltig")
                    start = p + length_size
                    if start + min(n, 96) <= len(head):
                        nal = head[start:start + min(n, 96)]
                    else:
                        f.seek(off + start)
                        nal = f.read(min(n, 96))
                    typ = nal[0] & 31
                    if typ == 7:
                        if n > 96:
                            f.seek(off + start); nal = f.read(n)
                        s = parse_sps(nal); sps_map[s["sps_id"]] = s
                    elif typ == 8:
                        if n > 96:
                            f.seek(off + start); nal = f.read(n)
                        q2 = parse_pps(nal); pps_map[q2["pps_id"]] = q2
                    elif typ in (1, 5):
                        h = parse_slice(nal, sps_map, pps_map)
                        # kompakt: (slice_type, field, bottom, qp, skip_run, mbs_in_slice_max)
                        slices.append((h["slice_type"], h["field"], h["bottom"], h["qp"],
                                       h["skip_run"], h["mbs_in_slice_max"]))
                    p = start + n
            except Exception as e:  # defekte/unerwartete Daten nicht verschweigen
                err = str(e)
                errors += 1
            out.append((tuple(slices), err))
    if total > 20000:
        sys.stderr.write("\r  lese Slice-Koepfe: 100 %\n")
    return out, errors, sps_info


# ---------------------------------------------------------------------------
# Auswertung
# ---------------------------------------------------------------------------

class Frame:
    """Ein Videobild; speichersparend, aber wie ein Dict ansprechbar."""
    __slots__ = ("nr", "zeit_s", "bytes", "dateiposition", "videobytes_davor", "typen", "halbbilder",
                 "qp", "qp_alle", "skip_run", "voll_uebersprungen", "schluesselbild", "klasse",
                 "audio_davor", "versatz_s")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def __getitem__(self, k):
        return getattr(self, k)

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def get(self, k, default=None):
        v = getattr(self, k, None)
        return default if v is None else v

def fmt(x, nd=3):
    """Deutsche Zahlendarstellung."""
    if x is None:
        return "-"
    s = ("{:,.%df}" % nd).format(x)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def mb(x):
    return fmt(x / 1e6, 3) + " MB"


def analyse(path, want_sha=False, parse_h264=True):
    res = {"datei": os.path.basename(path), "pfad": os.path.abspath(path),
           "werkzeug": "pvt_check " + VERSION, "warnungen": []}
    info = read_mp4(path)
    res["dateigroesse"] = info["size"]
    res["marke"] = info["brand"]
    res["moov_am_ende"] = bool(info["mdat_pos"] is not None and info["moov_pos"] > info["mdat_pos"])
    if want_sha:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        res["sha256"] = h.hexdigest()
    vt = next((t for t in info["tracks"] if t["handler"] == "vide"), None)
    at = next((t for t in info["tracks"] if t["handler"] == "soun"), None)
    if vt is None:
        raise Mp4Error("Keine Videospur gefunden")
    vs = apply_edit_shift(build_samples(vt), vt, info)
    vts = vt["timescale"]
    a_s = apply_edit_shift(build_samples(at), at, info) if at else []
    ats = at["timescale"] if at else 1
    for tr, name in ((vt, "Video"), (at, "Ton")):
        if tr and tr["elst"] and any(mt != 0 for _, mt, _ in tr["elst"]):
            res["warnungen"].append("%s-Spur hat eine verschiebende Editliste %s (Zeiten wie FFmpeg "
                                    "angepasst)." % (name, tr["elst"]))

    # --- Zeitachsen ---
    vdur = (vs[-1][2] + vs[-1][3]) / vts if vs else 0.0
    adur = (a_s[-1][2] + a_s[-1][3]) / ats if a_s else None
    res["video"] = {"bilder": len(vs), "dauer_s": vdur,
                    "mdhd_s": vt["mdhd_duration"] / vts if vt["mdhd_duration"] is not None else None,
                    "zeitbasis": vts, "codec": vt["codec"], "breite": vt["width"], "hoehe": vt["height"],
                    "tkhd_breite": vt["tkhd_width"], "tkhd_hoehe": vt["tkhd_height"],
                    "editliste": vt["elst"]}
    durs = sorted(set(vs.dur))
    res["video"]["bilddauern_ticks"] = durs[:10]
    if at:
        res["audio"] = {"bloecke": len(a_s), "dauer_s": adur,
                        "mdhd_s": at["mdhd_duration"] / ats if at["mdhd_duration"] is not None else None,
                        "samplerate": at["samplerate"], "kanaele": at["channels"], "codec": at["codec"],
                        "mdhd_timescale": ats, "asc_rate": at["asc_rate"], "asc_index": at["asc_index"], "asc_kanaele": at["asc_channels"]}
    vbytes = sum(vs.size)
    # v1.6: unsinnige Eintraege in der Audio-Groessentabelle (VID00011: 8 Werte bis 1,7 GB) erkennen und ausschliessen
    a_sizes = list(a_s.size) if a_s else []
    a_bad = [x for x in a_sizes if x > 65536]
    if a_bad:
        res["warnungen"].append("Audio-Groessentabelle (stsz): %d unsinnige Eintraege (groesster %d Byte) - der MP4-Schreiber hat Muell geschrieben; Player stolpern hier."
                                % (len(a_bad), max(a_bad)))
        if "audio" in res:
            res["audio"]["stsz_muell"] = len(a_bad)
    abytes = sum(x for x in a_sizes if x <= 65536)
    res["video"]["datenrate_mbit"] = vbytes * 8 / vdur / 1e6 if vdur else None
    if at and adur:
        res["audio"]["datenrate_kbit"] = abytes * 8 / adur / 1e3
    if adur is not None:
        res["differenz_audio_minus_video_s"] = adur - vdur
        if adur - vdur > 0.2:
            res["warnungen"].append(
                "Videozeitachse %s s kuerzer als Ton: Bilder fehlen ohne Platzhalter (vgl. Z/LED2)."
                % fmt(adur - vdur))
        elif vdur - adur > 0.2:
            res["warnungen"].append("Ton %s s kuerzer als Video." % fmt(vdur - adur))
    if res["video"]["mdhd_s"] is not None and abs(res["video"]["mdhd_s"] - vdur) > 0.2:
        res["warnungen"].append("Video-mdhd (%s s) passt nicht zur Sampletabelle stts (%s s)."
                                % (fmt(res["video"]["mdhd_s"]), fmt(vdur)))

    # --- Schluesselbilder ---
    if vt["stss"] is not None:
        kf = [(i - 1) for i in vt["stss"] if 0 < i <= len(vs)]
    else:
        kf = list(range(len(vs)))
    kft = [vs[i][2] / vts for i in kf]
    gaps = [round(b - a, 3) for a, b in zip(kft, kft[1:])]
    res["schluesselbilder"] = {"anzahl": len(kf), "abstaende_s": sorted(set(gaps))[:8],
                               "groesster_abstand_s": max(gaps) if gaps else None}

    # --- Datenraten ---
    per_sec = {}
    for off, size, dts, dur, _ in vs:
        k = int(dts / vts)
        per_sec[k] = per_sec.get(k, 0) + size
    res["video"]["mbit_je_sekunde"] = [round(per_sec.get(k, 0) * 8 / 1e6, 3)
                                       for k in range(0, int(vdur) + 1)]

    def max_window(win):
        best = 0.0
        j = 0
        acc = 0
        times = [s[2] / vts for s in vs]
        for i in range(len(vs)):
            acc += vs[i][1]
            while times[i] - times[j] >= win - 1e-9:
                acc -= vs[j][1]
                j += 1
            best = max(best, acc * 8 / win / 1e6)
        return best
    res["video"]["max_0_2s_mbit"] = max_window(0.2)
    res["video"]["max_1s_mbit"] = max_window(1.0)

    # --- H.264-Koepfe ---
    frames = []
    hdr_errors = 0
    sps_info = None
    if parse_h264 and vt["avcC"]:
        hdrs, hdr_errors, sps_info = scan_video_headers(path, vs, vt["avcC"])
    else:
        hdrs = [None] * len(vs)
    if sps_info:
        res["video"]["profil"] = {66: "Baseline", 77: "Main", 100: "High"}.get(sps_info["profile_idc"],
                                                                              str(sps_info["profile_idc"]))
        res["video"]["level"] = sps_info["level_idc"] / 10
        if "breite" in sps_info:
            res["video"]["sps_breite"] = sps_info["breite"]
            res["video"]["sps_hoehe"] = sps_info["hoehe"]
            res["video"]["sar"] = "%d:%d" % sps_info["sar"] if sps_info.get("sar") else None
    if hdr_errors:
        res["warnungen"].append("%d Bilder mit nicht lesbaren Slice-Koepfen." % hdr_errors)

    # --- Einzelbilder klassifizieren ---
    keyset = set(kf)
    n = len(vs)
    sizes = vs.size
    is_i = []
    cum = 0
    for i, (off, size, dts, dur, cto) in enumerate(vs):
        t = dts / vts
        sl = hdrs[i][0] if hdrs and hdrs[i] else ()
        qps = [s[3] for s in sl]
        types = "".join("PBIPI"[s[0]] for s in sl)
        fields = "".join(("u" if s[2] else "o") if s[1] else "F" for s in sl)
        full_skip = bool(sl) and all(s[0] in (0, 3) and s[4] is not None and s[4] >= s[5] for s in sl)
        is_i.append(("I" in types) or (not types and i in keyset))
        frames.append(Frame(nr=i, zeit_s=round(t, 4), bytes=size, dateiposition=off,
                            videobytes_davor=cum, typen=sys.intern(types), halbbilder=sys.intern(fields),
                            qp=qps[0] if qps else None, qp_alle=tuple(qps),
                            skip_run=tuple(s[4] for s in sl), voll_uebersprungen=full_skip,
                            schluesselbild=i in keyset, klasse=""))
        cum += size

    hdrs = None

    def context(i, exclude_small):
        vals = [sizes[j] for j in range(max(0, i - 5), min(n, i + 6))
                if j != i and not is_i[j] and not (exclude_small and sizes[j] < 1000)]
        return statistics.median(vals) if vals else 0

    # 1. leere und sehr kleine Bilder - nur in bewegtem Umfeld. Ruhige oder schwarze
    #    Szenen erzeugen legitim kleine Bilder und werden deshalb nicht gezaehlt.
    for i, fr in enumerate(frames):
        if i == 0 or is_i[i]:
            continue
        small = fr["voll_uebersprungen"] or sizes[i] < 1000
        if small and context(i, False) > 4000:
            fr["klasse"] = "leer" if fr["voll_uebersprungen"] else "klein"
    # 2. Teilbilder nur in der Naehe (1 s) solcher Aussetzer (Hinweis, kein Beweis)
    marks = [fr["zeit_s"] for fr in frames if fr["klasse"]]
    if marks:
        for i, fr in enumerate(frames):
            if fr["klasse"] or i == 0 or is_i[i]:
                continue
            if not any(abs(fr["zeit_s"] - m) <= 1.0 for m in marks):
                continue
            med = context(i, True)
            if med > 4000 and sizes[i] < 0.4 * med:
                fr["klasse"] = "teil"

    anomalies = [fr for fr in frames if fr["klasse"] and fr["zeit_s"] > 0]
    res["auffaellig"] = {
        "leer": sum(1 for fr in anomalies if fr["klasse"] == "leer"),
        "klein": sum(1 for fr in anomalies if fr["klasse"] == "klein"),
        "teil": sum(1 for fr in anomalies if fr["klasse"] == "teil"),
    }
    if anomalies:
        a0, a1 = anomalies[0], anomalies[-1]
        res["auffaellig"].update({
            "erstes_zeit_s": a0["zeit_s"], "erstes_nr": a0["nr"],
            "erstes_videobytes_davor": a0["videobytes_davor"],
            "erstes_dateiposition": a0["dateiposition"],
            "letztes_zeit_s": a1["zeit_s"]})
    qpv = [fr["qp"] for fr in frames if fr["qp"] is not None]
    if qpv:
        dist = {}
        for q in qpv:
            dist[q] = dist.get(q, 0) + 1
        res["qp"] = {"min": min(qpv), "max": max(qpv), "mittel": sum(qpv) / len(qpv),
                     "verteilung": dict(sorted(dist.items()))}
    fieldpics = sum(1 for fr in frames if fr["halbbilder"] in ("ou", "uo"))
    res["video"]["halbbildcodierte_bilder"] = fieldpics

    # --- Audio/Video-Verzahnung in Dateireihenfolge ---
    if a_s:
        v_order = sorted(range(len(vs)), key=vs.off.__getitem__) \
            if any(vs.off[i] > vs.off[i + 1] for i in range(len(vs) - 1)) else range(len(vs))
        a_order = sorted(range(len(a_s)), key=a_s.off.__getitem__) \
            if any(a_s.off[i] > a_s.off[i + 1] for i in range(len(a_s) - 1)) else range(len(a_s))

        def merged():
            ai = iter(a_order)
            nxt = next(ai, None)
            for vi in v_order:
                vo = vs.off[vi]
                while nxt is not None and a_s.off[nxt] < vo:
                    yield "A", nxt
                    nxt = next(ai, None)
                yield "V", vi
        last_a = None
        a_run = 0
        for typ, i in merged():
            if typ == "A":
                last_a = i
                a_run += 1
            else:
                fr = frames[i]
                fr["audio_davor"] = a_run
                if last_a is None:
                    fr["versatz_s"] = None
                else:
                    fr["versatz_s"] = round(a_s.dts[last_a] / ats - vs.dts[i] / vts, 4)
                a_run = 0
        lags = [fr["versatz_s"] for fr in frames if fr.get("versatz_s") is not None]
        # Grundversatz aus den ersten 1,5 s (dort trat in keiner Aufnahme eine Stoerung auf);
        # Rueckfall: Median des unteren Drittels
        early = [fr["versatz_s"] for fr in frames if fr.get("versatz_s") is not None and fr["zeit_s"] < 1.5]
        if len(early) >= 10:
            base = statistics.median(early)
        else:
            low = sorted(lags)[:max(1, len(lags) * 3 // 10)]
            base = statistics.median(low) if lags else 0.0
        res["verzahnung"] = {"grundversatz_s": base}
        episodes = []
        cur = None
        for fr in frames:
            lg = fr.get("versatz_s")
            if lg is None:
                continue
            if lg > base + 0.1:
                if cur is None:
                    cur = {"beginn_s": fr["zeit_s"], "videobytes_davor": fr["videobytes_davor"],
                           "dateiposition": fr["dateiposition"], "max_versatz_s": lg,
                           "audio_bloecke_davor": fr.get("audio_davor", 0), "ende_s": fr["zeit_s"]}
                else:
                    cur["max_versatz_s"] = max(cur["max_versatz_s"], lg)
                    cur["ende_s"] = fr["zeit_s"]
            elif cur is not None:
                episodes.append(cur)
                cur = None
        if cur is not None:
            episodes.append(cur)
        res["verzahnung"]["videopausen"] = episodes
        # Verlauf des Versatzes (fuer fehlende Videozeit)
        marks = {}
        for fr in frames:
            k = int(fr["zeit_s"] // 10) * 10
            if k not in marks and fr.get("versatz_s") is not None:
                marks[k] = fr["versatz_s"]
        res["verzahnung"]["versatz_je_10s"] = marks
        # v1.4: Tonbloecke je Sekunde Aufnahmezeit (Zeit = Videobild davor in Dateireihenfolge).
        # Soll: Abtastrate/1024 je Sekunde (48 kHz: 46,9). Loecher zeigen, wann der Tonpfad stockt.
        per_sec = {}
        t_cur = 0.0
        for typ, i in merged():
            if typ == "V":
                t_cur = frames[i]["zeit_s"]
            else:
                k = int(t_cur)
                per_sec[k] = per_sec.get(k, 0) + 1
        soll = ats / 1024.0 if ats else 0
        total_s = int(frames[-1]["zeit_s"]) if frames else 0  # letzte, angefangene Sekunde nicht werten
        counts = [per_sec.get(k, 0) for k in range(total_s)]
        full = [c >= soll * 0.9 for c in counts]
        first_hole = next((k for k, f in enumerate(full) if not f), None)
        dead_from = None
        for k in range(total_s):
            if all(c < soll * 0.2 for c in counts[k:]) and total_s - k >= 3:
                dead_from = k
                break
        res["verzahnung"]["ton_je_sekunde"] = counts
        res["verzahnung"]["ton_soll_je_sekunde"] = round(soll, 1)
        res["verzahnung"]["ton_erstes_loch_s"] = first_hole
        res["verzahnung"]["ton_tot_ab_s"] = dead_from
    res["_frames"] = frames
    return res


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def report(res, show_all=False):
    L = []
    v = res["video"]
    L.append("=" * 78)
    L.append(res["datei"])
    L.append("=" * 78)
    L.append("Datei:      %s Byte, Marke '%s', moov %s" % (
        fmt(res["dateigroesse"], 0), res["marke"], "am Ende" if res["moov_am_ende"] else "vorne"))
    if res.get("sha256"):
        L.append("SHA-256:    %s" % res["sha256"])
    prof = v.get("profil", "?")
    fp = "Halbbilder (field_pic) in %s von %s Bildern" % (fmt(v["halbbildcodierte_bilder"], 0),
                                                           fmt(v["bilder"], 0))
    L.append("Video:      %s %s, %sx%s, %s Bilder, %s s, %s Mbit/s" % (
        v["codec"], prof, v["breite"], v["hoehe"], fmt(v["bilder"], 0), fmt(v["dauer_s"]),
        fmt(v["datenrate_mbit"])))
    L.append("            %s" % fp)
    if v.get("tkhd_breite") is not None:
        L.append("Container:  avc1 %sx%s, tkhd %gx%g (Anzeigegroesse)" % (v["breite"], v["hoehe"], v["tkhd_breite"], v["tkhd_hoehe"]))
    if v.get("sps_breite"):
        sar = v.get("sar")
        if sar:
            sw, sh = map(int, sar.split(":"))
            anz = v["sps_breite"] * sw / sh
            L.append("SPS:        %sx%s, Pixel %s -> Anzeige %.0fx%s (%.3f:1, 4:3 = 1.333)" % (
                v["sps_breite"], v["sps_hoehe"], sar, anz, v["sps_hoehe"], anz / v["sps_hoehe"]))
        else:
            L.append("SPS:        %sx%s, kein Pixel-Seitenverhaeltnis in der VUI" % (v["sps_breite"], v["sps_hoehe"]))
    if "audio" in res:
        a = res["audio"]
        L.append("Audio:      %s %s Hz, %s Bloecke, %s s, %s kbit/s%s" % (
            a["codec"], a["samplerate"], fmt(a["bloecke"], 0), fmt(a["dauer_s"]),
            fmt(a.get("datenrate_kbit"), 1), (" (ohne %d Muell-Eintraege)" % a["stsz_muell"]) if a.get("stsz_muell") else ""))
        # v1.5: drei Abtastraten im Kopf (stsd/mp4a, mdhd-Zeitbasis, AAC-Konfig) muessen uebereinstimmen
        rates = {"stsd": a["samplerate"], "mdhd": a.get("mdhd_timescale"), "AAC-Konfig": a.get("asc_rate")}
        vals = [r for r in rates.values() if r]
        same = len(set(vals)) <= 1
        L.append("Abtastrate: stsd %s, mdhd %s, AAC-Konfig %s (Index %s, %s Kanaele)  [%s]" % (
            rates["stsd"], rates["mdhd"], rates["AAC-Konfig"], a.get("asc_index"), a.get("asc_kanaele"),
            "OK" if same else "UNEINHEITLICH - Player nehmen die AAC-Konfig; Tonhoehe/Tempo pruefen, mp4_abtastrate.py kann angleichen"))
        d = res["differenz_audio_minus_video_s"]
        ok = "OK" if abs(d) <= 0.2 else "AUFFAELLIG"
        L.append("Zeitachsen: Ton minus Video = %s s  [%s]" % (fmt(d), ok))
        if res["video"]["dauer_s"] and a["dauer_s"] and abs(a["dauer_s"] / res["video"]["dauer_s"] - 1.5) < 0.05:
            L.append("            Ton ist 1,5x so lang wie das Video: Signatur eines 48-kHz-Takts bei 32-kHz-Einstellung (Takt kommt von aussen).")
    L.append("            mdhd Video %s s / stts %s s" % (fmt(v["mdhd_s"]), fmt(v["dauer_s"])))
    k = res["schluesselbilder"]
    L.append("Schluesselbilder: %s, Abstaende %s s" % (
        k["anzahl"], ", ".join(fmt(x, 2) for x in k["abstaende_s"]) or "-"))
    ps = v["mbit_je_sekunde"]
    L.append("Videorate je Sekunde (erste 12 s): %s" % " ".join(fmt(x, 2) for x in ps[:12]))
    L.append("Hoechstes Fenster: 0,2 s = %s Mbit/s, 1 s = %s Mbit/s (Medienzeit, nicht USB)" % (
        fmt(v["max_0_2s_mbit"], 2), fmt(v["max_1s_mbit"], 2)))
    if "qp" in res:
        q = res["qp"]
        L.append("QP (Slice): %s..%s, Mittel %s" % (q["min"], q["max"], fmt(q["mittel"], 2)))
    a = res["auffaellig"]
    L.append("")
    L.append("Wiederholungen / Aussetzer:")
    L.append("  leer (alle Makrobloecke uebersprungen): %d" % a["leer"])
    L.append("  sehr klein (< 1000 Byte):              %d" % a["klein"])
    L.append("  Teilbild (< 40 %% des Medians):          %d" % a["teil"])
    L.append("  ('leer' = exakte Wiederholung; 'sehr klein'/'Teilbild' = Verdacht, nur in bewegtem Umfeld)")
    if "erstes_zeit_s" in a:
        L.append("  erstes auffaelliges Bild: %s s (Bild %d), nach %s Videodaten (Dateiposition %s)" % (
            fmt(a["erstes_zeit_s"], 2), a["erstes_nr"], mb(a["erstes_videobytes_davor"]),
            mb(a["erstes_dateiposition"])))
        L.append("  letztes auffaelliges Bild: %s s" % fmt(a["letztes_zeit_s"], 2))
        lst = [fr for fr in res["_frames"] if fr["klasse"] and fr["zeit_s"] > 0]
        L.append("  %s:" % ("alle" if show_all else "die ersten 12"))
        L.append("      Zeit    Bytes  QP  Klasse  Videodaten davor  Skip-Run (je Slice)")
        for fr in (lst if show_all else lst[:12]):
            L.append("   %7s %8s  %2s  %-6s  %15s  %s" % (
                fmt(fr["zeit_s"], 2), fmt(fr["bytes"], 0), fr["qp"] if fr["qp"] is not None else "-",
                fr["klasse"], mb(fr["videobytes_davor"]),
                "/".join("-" if x is None else str(x) for x in fr["skip_run"])))
    else:
        L.append("  keine")
    if "verzahnung" in res:
        z = res["verzahnung"]
        L.append("")
        L.append("Audio/Video in Dateireihenfolge: Grundversatz %s s" % fmt(z["grundversatz_s"], 3))
        ep = z["videopausen"]
        if not ep:
            L.append("  keine Videopausen ueber 0,1 s")
        last_t = res["_frames"][-1]["zeit_s"] if res["_frames"] else 0
        for e in ep[:8]:
            if e["ende_s"] >= last_t - 0.5 and res.get("differenz_audio_minus_video_s", 0) > 0.2:
                L.append("  wachsender Video-Rueckstand ab %s s bis Dateiende (max. %s s): Videozeit fehlt"
                         % (fmt(e["beginn_s"], 2), fmt(e["max_versatz_s"], 2)))
                continue
            L.append("  Videopause ab %s s (%s MB Videodaten): Video bis %s s hinter Ton, "
                     "%d Tonbloecke am Stueck, Aufholen bis %s s" % (
                         fmt(e["beginn_s"], 2), fmt(e["videobytes_davor"] / 1e6, 3),
                         fmt(e["max_versatz_s"] - res["verzahnung"]["grundversatz_s"], 2),
                         e["audio_bloecke_davor"], fmt(e["ende_s"], 2)))
        if len(ep) > 8:
            L.append("  ... %d weitere" % (len(ep) - 8))
        if abs(res.get("differenz_audio_minus_video_s", 0)) > 0.2:
            L.append("  Versatz je 10 s: " + ", ".join(
                "%d s: %s" % (kk, fmt(vv, 2)) for kk, vv in sorted(z["versatz_je_10s"].items())))
        if "ton_je_sekunde" in z:
            c = z["ton_je_sekunde"]
            soll = z["ton_soll_je_sekunde"]
            holes = sum(1 for x in c if x < soll * 0.9)
            if z["ton_erstes_loch_s"] is None:
                L.append("Ton je Sekunde: vollstaendig (%s Bloecke/s in allen %d Sekunden)" % (fmt(soll, 1), len(c)))
            else:
                L.append("Ton je Sekunde (Soll %s Bloecke/s): erstes Loch bei %d s, %d von %d Sekunden unvollstaendig%s" % (
                    fmt(soll, 1), z["ton_erstes_loch_s"], holes, len(c),
                    (", Tonpfad tot ab %d s" % z["ton_tot_ab_s"]) if z["ton_tot_ab_s"] is not None else ""))
                L.append("  " + " ".join("%d:%d" % (k, x) for k, x in enumerate(c[:60])) + (" ..." if len(c) > 60 else ""))
    if res["warnungen"]:
        L.append("")
        for w in res["warnungen"]:
            L.append("WARNUNG: " + w)
    return "\n".join(L)


def summary_table(results):
    L = ["", "=" * 78, "Uebersicht", "=" * 78,
         "%-24s %7s %7s %5s %5s %5s %8s %7s %9s" % (
             "Datei", "Video s", "Ton-Vid", "Mbit", "leer", "klein", "Beginn s", "bei MB", "Pause MB")]
    for r in results:
        if "fehler" in r:
            L.append("%-28s FEHLER: %s" % (r["datei"][:28], r["fehler"]))
            continue
        a = r["auffaellig"]
        ep = r.get("verzahnung", {}).get("videopausen", [])
        L.append("%-24s %7s %7s %5s %5d %5d %8s %7s %9s" % (
            r["datei"][:24], fmt(r["video"]["dauer_s"], 2),
            fmt(r.get("differenz_audio_minus_video_s"), 2),
            fmt(r["video"]["datenrate_mbit"], 2), a["leer"], a["klein"],
            fmt(a.get("erstes_zeit_s"), 2) if "erstes_zeit_s" in a else "-",
            fmt(a["erstes_videobytes_davor"] / 1e6, 3) if "erstes_zeit_s" in a else "-",
            fmt(ep[0]["videobytes_davor"] / 1e6, 3) if ep else "-"))
    return "\n".join(L)


def write_exports(res, outdir):
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(res["datei"])[0]
    cpath = os.path.join(outdir, stem + "_pvtcheck.csv")
    def de(x):  # Dezimalkomma fuer deutsches Excel
        return "" if x is None else str(x).replace(".", ",")
    with open(cpath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["nr", "zeit_s", "bytes", "dateiposition", "videobytes_davor", "schluesselbild",
                    "slicetypen", "halbbilder", "qp", "qp_alle", "skip_run", "klasse",
                    "audio_davor", "versatz_s"])
        for fr in res["_frames"]:
            w.writerow([fr["nr"], de(fr["zeit_s"]), fr["bytes"], fr["dateiposition"], fr["videobytes_davor"],
                        int(fr["schluesselbild"]), fr["typen"], fr["halbbilder"],
                        "" if fr["qp"] is None else fr["qp"], "/".join(map(str, fr["qp_alle"])),
                        "/".join("" if x is None else str(x) for x in fr["skip_run"]), fr["klasse"],
                        fr.get("audio_davor", ""), de(fr.get("versatz_s"))])
    jpath = os.path.join(outdir, stem + "_pvtcheck.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in res.items() if not k.startswith("_")}, f, ensure_ascii=False, indent=1)
    return cpath, jpath


def main(argv=None):
    ap = argparse.ArgumentParser(description="Prueft PVT-/MG1264-MP4-Aufnahmen (nur lesend).")
    ap.add_argument("--version", action="version", version="pvt_check " + VERSION)
    ap.add_argument("dateien", nargs="+", help="MP4-Dateien")
    ap.add_argument("--out", help="Ordner fuer CSV (je Bild) und JSON (Zusammenfassung)")
    ap.add_argument("--alle", action="store_true", help="alle auffaelligen Bilder auflisten")
    ap.add_argument("--sha256", action="store_true", help="SHA-256 der Datei berechnen")
    ap.add_argument("--ohne-h264", action="store_true", help="keine Slice-Koepfe lesen (schneller)")
    args = ap.parse_args(argv)
    results = []
    for p in args.dateien:
        try:
            r = analyse(p, want_sha=args.sha256, parse_h264=not args.ohne_h264)
            text = report(r, show_all=args.alle)
            print(text)
            if args.out:
                c, j = write_exports(r, args.out)
                tpath = os.path.join(args.out, os.path.splitext(r["datei"])[0] + "_pvtcheck.txt")
                with open(tpath, "w", encoding="utf-8") as f:
                    f.write(report(r, show_all=True) + "\n")
                print("\nGeschrieben: %s\n             %s\n             %s" % (tpath, c, j))
            results.append(r)
        except (Mp4Error, OSError, ValueError) as e:
            print("=" * 78 + "\n%s\nFEHLER: %s" % (os.path.basename(p), e))
            results.append({"datei": os.path.basename(p), "fehler": str(e)})
    if len(results) > 1:
        table = summary_table(results)
        print(table)
        if args.out:
            with open(os.path.join(args.out, "uebersicht.txt"), "w", encoding="utf-8") as f:
                f.write(table + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
