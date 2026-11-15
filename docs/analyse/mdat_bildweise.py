"""Bildweise durch das mdat: Bild = [PPS 0x68, L=4] + genau zwei Slices (0x65/0x41, erstes Bit 1).
Ton = Luecken; ein Bildanfang gilt nur, wenn das ganze Bild parst und danach Ton (0x20/0x21),
ein weiteres Bild oder das mdat-Ende folgt."""
import sys, struct, json, statistics
from collections import Counter
fn = sys.argv[1]; END = int(sys.argv[2]); out = sys.argv[3]
d = open(fn, 'rb').read()
def nal(q):
    if q + 6 > END: return None
    L = struct.unpack('>I', d[q:q+4])[0]; h = d[q+4]
    if h == 0x68 and L == 4 and (d[q+5] & 0xC0) == 0xC0: return L, 8
    if h in (0x65, 0x41) and 4 <= L <= 1_500_000 and q + 4 + L <= END and (d[q+5] & 0x80): return L, h & 31
    return None
def frame_at(q):
    p = q; types = []; ns = 0
    r = nal(p)
    if not r: return None
    if r[1] == 8:
        types.append(8); p += 8; r = nal(p)
        if not r or r[1] == 8: return None
    while ns < 2:
        if not r or r[1] == 8: return None
        types.append(r[1]); ns += 1; p += 4 + r[0]
        if ns < 2: r = nal(p)
    return p - q, types
def frame_start_ok(q):
    f = frame_at(q)
    if not f: return None
    e = q + f[0]
    if e >= END - 6 or d[e] in (0x20, 0x21) or frame_at(e): return f
    return None
frames = []; gaps = []
p = 40
while p < END:
    f = frame_start_ok(p)
    if f:
        frames.append((p, f[0], f[1])); p += f[0]; continue
    q = p + 1
    while q < END and not frame_start_ok(q): q += 1
    gaps.append((p, q - p, len(frames)))
    p = q
sizes = [s for _, s, _ in frames]
gs = [g for _, g, _ in gaps]
print("Bilder: %d (leer <= 32 B: %d) | Videobytes %d | Tonbytes %d in %d Luecken" % (len(frames), sum(1 for s in sizes if s <= 32), sum(sizes), sum(gs), len(gaps)))
print("Luecken min %d / Median %d / max %d | haeufig: %s" % (min(gs), statistics.median(gs), max(gs), Counter(gs).most_common(6)))
json.dump({"frames": frames, "gaps": gaps, "end": END}, open(out, "w"))
