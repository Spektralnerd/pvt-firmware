/* PVT Firmware-Baukasten – Kern (reine Funktionen, keine DOM-Zugriffe).
   Alles läuft im Browser. Basis ist immer das geprüfte AE-Abbild; das Original
   01.00.46.03 wird über die eingebaute Differenz zu AE gemacht. Geändert werden
   ausschließlich Zahlenwerte an bekannten Stellen mit Prüfung des Befehlsworts davor
   (wie build_ag.py / build_ah.py / build_ai.py des Projekts). */
const CORE = (() => {
  'use strict';
  const SIZE = 245760;
  const KNOWN = [
    ['032fd7d2241aff1eb87403b72554dd1c7babe97a31c54b7418f9ea1657213fdc', 'Original 01.00.46.03 (Pinnacle, 14.03.2008)', 'Werksstand'],
    ['d4ae6a9b99370e57d3c19652e6d0f071323a9f713d6b238462999eaa317c07a7', 'AE (Vorführstand)', 'am Gerät geprüft: 2 h 30 min und 5 h 03 min ohne Ton'],
    ['6e39e44e80b7a0ace55d7f7f3dbbbf0c15b66a2f5223b03c6b944a4f8a287d99', 'AE rein (LED2/LED3 wie LED1)', 'LED1 wie AE geprüft, LED2/LED3 ungeprüft'],
    ['34633fcbf56e7db68e64cd967b21890081655c4a460eb69a8e03f34113a72dfd', 'AB (Vorgänger von AE)', 'am Gerät geprüft'],
    ['ecfc7a297c95dbdc75f0faeb8fed1e1b771f0c1690a970610c8600ce5e1faf93', 'AG_4900_128', 'ungeprüft'],
    ['54d9afb8ff3d95cee1d003b54f71eca5bc97280b07966d209e7ee185954d4bd8', 'AG_4800_192', 'ungeprüft'],
    ['92ad9a5c56585ff7113e79d1378b415fdee589957c63694a189cc29d845c1da3', 'AG_4500_128', 'ungeprüft'],
    ['da2342eb4791231e589c4accb262ca8fcfb9ab459aa8529e5719374b3ecffc1e', 'AH_4900_128_P04_256', 'ungeprüft'],
    ['091fb10a5c69745a09797b815a00031e81a304b25719e29b6ab6126042eab0e0', 'AI_528_4500_192', 'ungeprüft'],
    ['fd5e2f3584542146d229ce3d899ff2a50e9b9b8834250e0300771c6535bfca4e', 'AI_528_4800_192', 'ungeprüft'],
    ['271938dbd8987439869488e3d3dae20a51ce93b376628e78776019809f61df21', 'AI_528_4500_192_P04_256', 'ungeprüft'],
    ['9952bab7e17a43a9b5fd756497f1c89fecd1bb12a40b323df33323483602e1fe', 'AE_V5000_A96_B528_REIN', 'geprüft 20.10.: Bild ok, Ton hält, Video 40 % Verlust in Phasen (zu hohe Rate)'],
    ['13508fa0b54fdd72fcb88738b69f0ed294b3599dc462655fe0d65fe0405a8960', 'AE_V4500_A96_B528_REIN', 'geprüft 20.10.: 117 s, Ton 99 %, Video sauber bis auf 10 s Störung bei 86 s'],
    ['7ee1f171721867e2df5f4c8136d94faba823073bc10a489b9ab283fe5aa559d9', 'AE_V4500_A96_B528_SR32000_REIN', 'geprüft 20.10. (VID00011): Takt bleibt 48 kHz → Ton 1,5× zu langsam, MG läuft über, Video 50 % kaputt, Ton tot ab 4 s. Abtastrate ist kein Hebel.']
  ];
  const H_ORIG = KNOWN[0][0], H_AE = KNOWN[1][0];
  /*DELTA*/

  // ---- Bytes, Hex, SHA-256, CRC-32 --------------------------------------------
  const hex = (u8) => Array.from(u8, b => b.toString(16).padStart(2, '0')).join('');
  const unhex = (s) => { const u = new Uint8Array(s.length / 2); for (let i = 0; i < u.length; i++) u[i] = parseInt(s.substr(i * 2, 2), 16); return u; };
  const u32 = (b, o) => ((b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]) >>> 0;
  const u16 = (b, o) => (b[o] << 8) | b[o + 1];
  const put32 = (b, o, v) => { b[o] = (v >>> 24) & 255; b[o + 1] = (v >>> 16) & 255; b[o + 2] = (v >>> 8) & 255; b[o + 3] = v & 255; };
  const sha256 = (data) => {
    const K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
    let H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    const len = data.length, padLen = ((len + 9 + 63) >> 6) << 6;
    const m = new Uint8Array(padLen); m.set(data); m[len] = 0x80;
    const bits = len * 8; m[padLen - 4] = (bits >>> 24) & 255; m[padLen - 3] = (bits >>> 16) & 255; m[padLen - 2] = (bits >>> 8) & 255; m[padLen - 1] = bits & 255;
    m[padLen - 8] = Math.floor(bits / 0x100000000) & 255;
    const w = new Int32Array(64), rotr = (x, n) => (x >>> n) | (x << (32 - n));
    for (let off = 0; off < padLen; off += 64) {
      for (let i = 0; i < 16; i++) w[i] = (m[off + i * 4] << 24) | (m[off + i * 4 + 1] << 16) | (m[off + i * 4 + 2] << 8) | m[off + i * 4 + 3];
      for (let i = 16; i < 64; i++) { const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3), s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10); w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0; }
      let [a, b, c, d, e, f, g, h] = H;
      for (let i = 0; i < 64; i++) {
        const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25), ch = (e & f) ^ (~e & g), t1 = (h + S1 + ch + K[i] + w[i]) | 0;
        const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22), maj = (a & b) ^ (a & c) ^ (b & c), t2 = (S0 + maj) | 0;
        h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
      }
      H = [a, b, c, d, e, f, g, h].map((v, i) => (H[i] + v) | 0);
    }
    return H.map(v => (v >>> 0).toString(16).padStart(8, '0')).join('');
  };
  const CRC_T = (() => { const t = new Int32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c; } return t; })();
  const crc32 = (u8) => { let c = -1; for (let i = 0; i < u8.length; i++) c = CRC_T[(c ^ u8[i]) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };

  // ---- Bekannte Stellen im AE-Abbild (Datei-Offsets) --------------------------
  // Alle Stellen sind Zahlenkonstanten mit festem Befehlswort davor. Rollen per Mutationstest im
  // CF-Modell der Übergabe bestätigt (jede Stelle ändert genau den genannten MG-Parameter).
  const MOVEL = 0x203c, CMPIL = 0x0c80, MOVEQ = 0x70;
  const KBPS = [0x08108, 0x2c002];                 // move.l #5000  Videoziel kbit/s
  const RC7 = [0x2e1c8, 0x2e320, 0x2e478];         // move.l #25000000  Größentoleranz = Video×5000
  const RC11 = [0x2e162, 0x2e2ba, 0x2e412];        // move.l #5000000   Modelltransfer = Video×1000
  const AUDIO = 0x2b324;                           // move.l #384  Audioanforderung kbit/s
  const WIDTH = [[0x2b228, MOVEL, 'Breite PAL: Wahl → MG DecimationH'], [0x0c13c, CMPIL, 'Breite PAL: nativer D1-Vergleich (Pixelformat 16:15)'],
    [0x2b044, CMPIL, 'Breite PAL: Encoder-Erweiterung'], [0x2e062, CMPIL, 'Breite: RC-Erweiterung (PAL und NTSC gemeinsam)']];          // 720
  const HEIGHT = [[0x2b234, MOVEL, 'Höhe PAL: Wahl → MG DecimationV'], [0x2b052, CMPIL, 'Höhe PAL: Encoder-Erweiterung'], [0x2e056, CMPIL, 'Höhe PAL: RC-Erweiterung']]; // 576
  const WIDTH_N = [[0x2b81e, MOVEL, 'Breite NTSC: Wahl → MG DecimationH'], [0x0c042, CMPIL, 'Breite NTSC: nativer D1-Vergleich (Pixelformat 8:9)'], [0x2b924, CMPIL, 'Breite NTSC: Encoder-Erweiterung']]; // 720
  const HEIGHT_N = [[0x2b82a, MOVEL, 'Höhe NTSC: Wahl → MG DecimationV'], [0x2b932, CMPIL, 'Höhe NTSC: Encoder-Erweiterung'], [0x2e044, CMPIL, 'Höhe NTSC: RC-Erweiterung']]; // 480
  const GOP = [0x2c086, 0x2c090, 0x2c09a];         // move.l #50 je LED → MG GOP-Länge (Objekt 3, Param 24)
  // Abtastrate 48000 an drei Stellen (alle schon im Original): MG-Systemparameter, Host-Konfiguration (RAM-Struktur,
  // laut externer Analyse in den Aufzeichnungsablauf kopiert), MP4-Audiobeschreibung (mp4a-Vorlage: 0x40, 0x40, 48000, 2 Kanäle).
  const SRATE = [[0x0c67a, MOVEL, 'Abtastrate → MG Q_SYS_CFG_AUDIO_SAMPLE_RATE (Objekt 1, Param 7)'],
    [0x1aa9e, MOVEL, 'Abtastrate: Host-Konfiguration (RAM-Struktur, Aufzeichnung/MP4-Zeitbasis)'],
    [0x2aa0c, null, 'Abtastrate: MP4-Audiobeschreibung (mp4a-Vorlage)']];
  const SRATE_TPL = [[0x2aa04, 0x40], [0x2aa08, 0x40], [0x2aa10, 2]]; // Nachbarn der Vorlage als Lagekontrolle
  const MGHEAD = 0x2a60a, P03 = 0x2a626, P04 = 0x2a62a; // MG-Tabelle: Kopf (2,0,0,84), Videopuffer 2048, Audiopuffer 48 Seiten
  const TF = [0x2b177, 0x2b17d, 0x2b183];          // moveq #3 je LED (Byte)
  const LED = { base: 0x2e11e, step: 0x22, n: 6, off: [0, 0x158, 0x2b0] }; // RC9, RC10, RC11, RC12, RC6, RC7 je LED, move.l
  const LED_AE = [[0, 1250000, 5000000, 11250, 1, 25000000], [1, 5000000, 5000000, 45000, 1, 25000000], [1, 10000000, 5000000, 90000, 1, 25000000]];
  const RC_NAMES = ['RC9 Puffer-Regelung', 'RC10 Pufferbits', 'RC11 Transferrate', 'RC12 Startverzögerung', 'RC6 Größen-RC', 'RC7 Größentoleranz'];
  // MG-Handbuch 10.11: RC6/RC7 = SIZE_ENABLE / SIZE_BIT_TOLERANCE (Dateigröße = Soll ± Toleranz in Bit),
  // RC9/RC10 = BUFFER_ENABLE / BUFFER_SIZE_BITS (Leaky-Bucket für begrenzte Kanäle), RC11 = Kanalrate Bit/s, RC12 = Startverzögerung (90-kHz-Ticks).
  const AUDIO_OK = [0, 48, 64, 96, 128, 192, 256, 320, 384]; // Vorschläge; 0 = nur Video; MG-Datenblatt: 8-384 kbit/s
  const AVSEL = 0x0c363;                           // moveq #1,d5 (0x7A01): MG ENC_INPUT_SELECT/ENC_AV_SELECT (Param 40/17), 1 = Audio+Video, 2 = nur Video
  const DEFAULTS = { video: 5000, audio: 384, width: 720, height: 576, widthN: 720, heightN: 480, p03: 2048, p04: 48, gop: [50, 50, 50], srate: 48000,
    rc7f: 5000, rc11f: 1000, rc9: 0, rc10: 1250000, rc12: 11250, rein: false, tf: [3, 3, 3] };
  // Harte Grenzen = was die Stellen technisch fassen (32-Bit-Werte, moveq-Byte). Alles andere sind Hinweise in der Oberfläche.
  const LIMITS = { video: [1, 858993], audio: [0, 4294967], size: [1, 65535], pages: [1, 65535], gop: [1, 4294967295], srate: [1, 4294967295], tf: [0, 127],
    rcf: [1, 4294967295], rc10: [1, 4294967295], rc12: [0, 4294967295] };

  const ledAddr = (led, k) => LED.base + LED.off[led] + k * LED.step;
  const need = (ok, msg) => { if (!ok) throw new Error(msg); };
  const at = (o) => '0x' + o.toString(16).toUpperCase().padStart(5, '0');
  const withDefaults = (s) => Object.assign({}, DEFAULTS, Object.fromEntries(Object.entries(s).filter(([, v]) => v !== null && v !== undefined)), { gop: (s.gop || DEFAULTS.gop).slice(), tf: (s.tf || DEFAULTS.tf).slice() });

  function applyDelta(orig, toAE) {
    const out = new Uint8Array(orig);
    for (const [o, oh, ah] of DELTA) {
      const from = unhex(toAE ? oh : ah), to = unhex(toAE ? ah : oh);
      for (let i = 0; i < from.length; i++) need(out[o + i] === from[i], 'Differenz passt nicht bei ' + at(o + i));
      out.set(to, o);
    }
    return out;
  }
  function knownName(sha) { const k = KNOWN.find(x => x[0] === sha); return k ? { name: k[1], status: k[2] } : null; }

  // Liest die Einstellungen aus einem AE-artigen Abbild (prüft die Befehlsworte).
  function readSettings(b) {
    const s = {};
    const readSites = (sites, what) => {
      const vals = sites.map(([o, op]) => { need(u16(b, o - 2) === op, what + ' nicht gefunden bei ' + at(o)); return u32(b, o); });
      need(vals.every(v => v === vals[0]), what + ' uneinheitlich'); return vals[0];
    };
    need(u16(b, KBPS[0] - 2) === MOVEL && u16(b, KBPS[1] - 2) === MOVEL, 'Videoziel nicht gefunden');
    s.video = u32(b, KBPS[0]); need(u32(b, KBPS[1]) === s.video, 'Videoziel uneinheitlich');
    need(u16(b, AUDIO - 2) === MOVEL, 'Audioanforderung nicht gefunden'); s.audio = u32(b, AUDIO);
    need(b[AVSEL - 1] === 0x7a && (b[AVSEL] === 1 || b[AVSEL] === 2), 'AV-Auswahl nicht gefunden');
    if (b[AVSEL] === 2) s.audio = 0;
    s.width = readSites(WIDTH, 'Breite'); s.height = readSites(HEIGHT, 'Höhe');
    s.widthN = readSites(WIDTH_N, 'Breite NTSC'); s.heightN = readSites(HEIGHT_N, 'Höhe NTSC');
    s.gop = GOP.map(o => { need(u16(b, o - 2) === MOVEL, 'GOP nicht gefunden'); return u32(b, o); });
    SRATE_TPL.forEach(([o, v]) => need(u32(b, o) === v, 'MP4-Audiovorlage nicht gefunden'));
    const sr = SRATE.map(([o, op]) => { need(op === null || u16(b, o - 2) === op, 'Abtastrate nicht gefunden bei ' + at(o)); return u32(b, o); });
    need(sr.every(v => v === sr[0]), 'Abtastrate uneinheitlich'); s.srate = sr[0];
    need(u32(b, MGHEAD) === 2 && u32(b, MGHEAD + 4) === 0 && u32(b, MGHEAD + 8) === 0 && u32(b, MGHEAD + 12) === 84, 'MG-Tabelle nicht gefunden');
    s.p03 = u32(b, P03); s.p04 = u32(b, P04);
    s.tf = TF.map(o => { need(b[o - 1] === MOVEQ, 'TF-Stufe nicht gefunden'); return b[o]; });
    s.led = [0, 1, 2].map(led => Array.from({ length: LED.n }, (_, k) => { const o = ledAddr(led, k); need(u16(b, o - 2) === MOVEL, 'RC-Block nicht gefunden'); return u32(b, o); }));
    s.rein = s.led[1].every((v, k) => v === s.led[0][k]) && s.led[2].every((v, k) => v === s.led[0][k]);
    const f = (v) => (s.video && v % s.video === 0) ? v / s.video : null;
    s.rc7f = f(s.led[0][5]); s.rc11f = f(s.led[0][2]); s.rc9 = s.led[0][0]; s.rc10 = s.led[0][1]; s.rc12 = s.led[0][3];
    return s;
  }

  // Setzt alle bekannten Stellen auf AE zurück; stimmt danach der Hash, war das Abbild ein AE-Abkömmling.
  function normalize(b) {
    const out = new Uint8Array(b);
    KBPS.forEach(o => put32(out, o, 5000)); RC7.forEach(o => put32(out, o, 25000000)); RC11.forEach(o => put32(out, o, 5000000));
    put32(out, AUDIO, 384); out[AVSEL] = 1;
    WIDTH.forEach(([o]) => put32(out, o, 720)); HEIGHT.forEach(([o]) => put32(out, o, 576)); WIDTH_N.forEach(([o]) => put32(out, o, 720)); HEIGHT_N.forEach(([o]) => put32(out, o, 480));
    GOP.forEach(o => put32(out, o, 50)); SRATE.forEach(([o]) => put32(out, o, 48000)); put32(out, P03, 2048); put32(out, P04, 48);
    TF.forEach(o => { out[o] = 3; });
    for (let led = 0; led < 3; led++) for (let k = 0; k < LED.n; k++) put32(out, ledAddr(led, k), LED_AE[led][k]);
    return out;
  }

  // Erkennt ein geladenes CFUPDATE.BIN und liefert, wenn möglich, das AE-Basisabbild.
  function identify(bytes) {
    const r = { size: bytes.length, sha: null, kind: 'unknown', known: null, settings: null, base: null, orig: null, note: '' };
    if (bytes.length !== SIZE) { r.note = 'Größe ' + bytes.length + ' Byte, erwartet ' + SIZE + '.'; return r; }
    r.sha = sha256(bytes); r.known = knownName(r.sha);
    if (r.sha === H_ORIG) {
      const ae = applyDelta(bytes, true); need(sha256(ae) === H_AE, 'Original → AE: Ergebnis stimmt nicht mit AE überein');
      r.kind = 'orig'; r.base = ae; r.orig = bytes; r.settings = readSettings(ae); return r;
    }
    try { r.settings = readSettings(bytes); } catch (e) { r.note = 'Keine AE-Struktur: ' + e.message; return r; }
    if (r.sha === H_AE) { r.kind = 'ae'; r.base = bytes; }
    else {
      const n = normalize(bytes);
      if (sha256(n) === H_AE) { r.kind = 'derived'; r.base = n; }
      else { r.kind = 'unknown'; r.note = 'AE-Struktur vorhanden, aber andere Code-Teile. Nicht als Basis geeignet.'; return r; }
    }
    r.orig = applyDelta(r.base, false); need(sha256(r.orig) === H_ORIG, 'AE → Original: Ergebnis stimmt nicht mit dem Original überein');
    return r;
  }

  // Nur technische Grenzen: ganze Zahlen, die in die Stellen passen (Video×5000 und Audio×1000 müssen 32 Bit bleiben).
  function checkSettings(s) {
    const int = (v, [lo, hi]) => Number.isInteger(v) && v >= lo && v <= hi;
    need(int(s.video, LIMITS.video), 'Videoziel: ganze Zahl 1 bis 858993 kbit/s (Video×5000 muss in 32 Bit passen).');
    need(int(s.audio, LIMITS.audio), 'Audio: 0 (aus) oder ganze Zahl bis 4294967 kbit/s.');
    [['width', 'Breite PAL'], ['height', 'Höhe PAL'], ['widthN', 'Breite NTSC'], ['heightN', 'Höhe NTSC']].forEach(([k, n]) => need(int(s[k], LIMITS.size), n + ': ganze Zahl 1 bis 65535.'));
    need(int(s.p03, LIMITS.pages) && int(s.p04, LIMITS.pages), 'MG-Puffer: ganze Zahl 1 bis 65535 Seiten.');
    need(Array.isArray(s.gop) && s.gop.length === 3 && s.gop.every(g => int(g, LIMITS.gop)), 'GOP: ganze Zahl ab 1 je LED.');
    need(int(s.srate, LIMITS.srate), 'Abtastrate: ganze Zahl in Hz.');
    need(int(s.rc7f, LIMITS.rcf) && s.video * s.rc7f <= 4294967295, 'Größentoleranz-Faktor: ganze Zahl, Video×Faktor muss in 32 Bit passen.');
    need(int(s.rc11f, LIMITS.rcf) && s.video * s.rc11f <= 4294967295, 'Transferraten-Faktor: ganze Zahl, Video×Faktor muss in 32 Bit passen.');
    need(s.rc9 === 0 || s.rc9 === 1, 'Puffer-Regelung: 0 oder 1.');
    need(int(s.rc10, LIMITS.rc10) && int(s.rc12, LIMITS.rc12), 'Pufferbits ab 1, Startverzögerung ab 0 (ganze Zahlen).');
    need(Array.isArray(s.tf) && s.tf.length === 3 && s.tf.every(t => int(t, LIMITS.tf)), 'TF-Stufe: ganze Zahl 0 bis 127 je LED (moveq-Byte).');
  }

  // Baut aus dem AE-Abbild die gewünschte Variante. Liefert Bytes, Patchliste, Hash.
  function build(ae, settings) {
    const s = withDefaults(settings);
    checkSettings(s);
    need(sha256(ae) === H_AE, 'Basis ist nicht das AE-Abbild');
    const out = new Uint8Array(ae), patches = [];
    const set32 = (o, oldV, newV, name, op) => {
      need(u16(out, o - 2) === op, 'Befehlswort vor ' + at(o) + ' unerwartet (' + name + ')');
      need(u32(out, o) === oldV, 'Alter Wert bei ' + at(o) + ' ist ' + u32(out, o) + ', erwartet ' + oldV + ' (' + name + ')');
      if (oldV !== newV) { put32(out, o, newV); patches.push({ o, name, old: oldV, neu: newV }); }
    };
    [[0x2e11e, 0], [0x2e140, 1250000], [0x2e184, 11250], [0x2e1a6, 1], [0x2e2fe, 1], [0x2e456, 1], [0x2e298, 5000000], [0x2e3f0, 10000000], [0x2e276, 1], [0x2e3ce, 1]]
      .forEach(([o, v]) => need(u16(out, o - 2) === MOVEL && u32(out, o) === v, 'Lagekontrolle fehlgeschlagen bei ' + at(o)));
    KBPS.forEach(o => set32(o, 5000, s.video, 'Videoziel kbit/s', MOVEL));
    RC7.forEach(o => set32(o, 25000000, s.video * s.rc7f, 'RC7 Größentoleranz (Video×' + s.rc7f + ')', MOVEL));
    RC11.forEach(o => set32(o, 5000000, s.video * s.rc11f, 'RC11 Transferrate (Video×' + s.rc11f + ')', MOVEL));
    set32(ledAddr(0, 0), 0, s.rc9, 'LED1 RC9 Puffer-Regelung (0 aus, 1 an)', MOVEL);
    set32(ledAddr(0, 1), 1250000, s.rc10, 'LED1 RC10 Pufferbits', MOVEL);
    set32(ledAddr(0, 3), 11250, s.rc12, 'LED1 RC12 Startverzögerung (90-kHz-Ticks)', MOVEL);
    if (s.audio === 0) {
      need(out[AVSEL - 1] === 0x7a && out[AVSEL] === 1, 'AV-Auswahl unerwartet bei ' + at(AVSEL));
      out[AVSEL] = 2; patches.push({ o: AVSEL, name: 'MG AV-Auswahl (Param 40/17): 1 = Audio+Video → 2 = nur Video', old: 1, neu: 2 });
    } else set32(AUDIO, 384, s.audio, 'Audioanforderung kbit/s', MOVEL);
    WIDTH.forEach(([o, op, name]) => set32(o, 720, s.width, name, op));
    HEIGHT.forEach(([o, op, name]) => set32(o, 576, s.height, name, op));
    WIDTH_N.forEach(([o, op, name]) => set32(o, 720, s.widthN, name, op));
    HEIGHT_N.forEach(([o, op, name]) => set32(o, 480, s.heightN, name, op));
    GOP.forEach((o, i) => set32(o, 50, s.gop[i], 'GOP-Länge LED' + (i + 1) + ' (MG Param 24)', MOVEL));
    SRATE_TPL.forEach(([o, v]) => need(u32(out, o) === v, 'MP4-Audiovorlage unerwartet bei ' + at(o)));
    SRATE.forEach(([o, op, name]) => { if (op === null) { need(u32(out, o) === 48000, 'Abtastrate unerwartet bei ' + at(o)); if (s.srate !== 48000) { put32(out, o, s.srate); patches.push({ o, name, old: 48000, neu: s.srate }); } } else set32(o, 48000, s.srate, name, op); });
    need(u32(out, MGHEAD) === 2 && u32(out, MGHEAD + 12) === 84 && u32(out, P03) === 2048 && u32(out, P04) === 48, 'MG-Tabelle unerwartet');
    if (s.p03 !== 2048) { put32(out, P03, s.p03); patches.push({ o: P03, name: 'MG-Videopuffer p03 (Seiten à 2 KB)', old: 2048, neu: s.p03 }); }
    if (s.p04 !== 48) { put32(out, P04, s.p04); patches.push({ o: P04, name: 'MG-Audiopuffer p04 (Seiten à 2 KB)', old: 48, neu: s.p04 }); }
    TF.forEach((o, i) => { need(out[o - 1] === MOVEQ && out[o] === 3, 'TF-Stufe unerwartet bei ' + at(o)); if (s.tf[i] !== 3) { out[o] = s.tf[i]; patches.push({ o, name: 'TF-Stufe LED' + (i + 1), old: 3, neu: s.tf[i] }); } });
    if (s.rein) for (let led = 1; led < 3; led++) for (let k = 0; k < LED.n; k++) {
      const src = ledAddr(0, k), dst = ledAddr(led, k), v = u32(out, src), old = u32(out, dst);
      need(u16(out, dst - 2) === MOVEL, 'RC-Block LED' + (led + 1) + ' unerwartet');
      if (old !== v) { put32(out, dst, v); patches.push({ o: dst, name: 'LED' + (led + 1) + ' ' + RC_NAMES[k] + ' wie LED1', old, neu: v }); }
    }
    for (let i = 0; i < SIZE; i++) if (out[i] !== ae[i] && !patches.some(p => i >= p.o && i < p.o + 4)) throw new Error('Unerwartete Änderung bei ' + at(i));
    return { bytes: out, patches, sha: sha256(out), known: knownName(sha256(out)) };
  }

  function label(settings) {
    const s = withDefaults(settings), D = DEFAULTS;
    const same = (k) => Array.isArray(D[k]) ? s[k].every((v, i) => v === D[k][i]) : s[k] === D[k];
    if (Object.keys(D).every(same)) return 'AE';
    let l = 'AE_V' + s.video + (s.audio === 0 ? '_NURVIDEO' : '_A' + s.audio);
    if (s.width !== 720 || s.height !== 576) l += '_B' + s.width + (s.height !== 576 ? 'x' + s.height : '');
    if (s.widthN !== 720 || s.heightN !== 480) l += '_N' + s.widthN + 'x' + s.heightN;
    if (!same('gop')) l += '_G' + (s.gop.every(g => g === s.gop[0]) ? s.gop[0] : s.gop.join('-'));
    if (s.srate !== 48000) l += '_SR' + s.srate;
    if (s.rc7f !== 5000) l += '_T' + s.rc7f;
    if (s.rc11f !== 1000) l += '_TR' + s.rc11f;
    if (s.rc9 !== 0 || s.rc10 !== 1250000 || s.rc12 !== 11250) l += '_B' + s.rc9 + '-' + s.rc10 + '-' + s.rc12;
    if (s.p03 !== 2048) l += '_VP' + s.p03;
    if (s.p04 !== 48) l += '_P' + s.p04;
    if (s.rein) l += '_REIN';
    if (!same('tf')) l += '_TF' + s.tf.join(s.tf.some(t => t > 9) ? '-' : '');
    return l;
  }
  const sumMbit = (s) => (s.video + s.audio) / 1000;

  // ---- ZIP lesen (stored + deflate) und schreiben (stored) -----------------------
  function listZip(buf) {
    const b = new Uint8Array(buf), dv = new DataView(buf);
    let eocd = -1;
    for (let i = b.length - 22; i >= Math.max(0, b.length - 65557); i--) if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    need(eocd >= 0, 'Kein ZIP-Archiv (Endrecord fehlt)');
    const count = dv.getUint16(eocd + 10, true), cdOff = dv.getUint32(eocd + 16, true);
    const entries = []; let p = cdOff;
    for (let i = 0; i < count; i++) {
      need(dv.getUint32(p, true) === 0x02014b50, 'ZIP-Verzeichnis beschädigt');
      const method = dv.getUint16(p + 10, true), crc = dv.getUint32(p + 16, true), csize = dv.getUint32(p + 20, true), usize = dv.getUint32(p + 24, true);
      const nlen = dv.getUint16(p + 28, true), elen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true), loff = dv.getUint32(p + 42, true);
      const name = new TextDecoder().decode(b.subarray(p + 46, p + 46 + nlen));
      entries.push({ name, method, crc, csize, usize, loff });
      p += 46 + nlen + elen + clen;
    }
    return entries;
  }
  async function readZipEntry(buf, e) {
    const b = new Uint8Array(buf), dv = new DataView(buf);
    need(dv.getUint32(e.loff, true) === 0x04034b50, 'ZIP-Eintrag beschädigt');
    const start = e.loff + 30 + dv.getUint16(e.loff + 26, true) + dv.getUint16(e.loff + 28, true);
    const raw = b.subarray(start, start + e.csize);
    let data;
    if (e.method === 0) data = new Uint8Array(raw);
    else if (e.method === 8) {
      need(typeof DecompressionStream === 'function', 'Dieser Browser kann das ZIP nicht entpacken. Bitte entpacken und die CFUPDATE.BIN direkt laden.');
      const ds = new DecompressionStream('deflate-raw');
      const ab = await new Response(new Blob([raw]).stream().pipeThrough(ds)).arrayBuffer();
      data = new Uint8Array(ab);
    } else throw new Error('ZIP-Methode ' + e.method + ' nicht unterstützt');
    need(data.length === e.usize, 'ZIP-Eintrag: Größe stimmt nicht');
    need(crc32(data) === e.crc, 'ZIP-Eintrag: CRC stimmt nicht');
    return data;
  }
  function makeZip(files) { // files: [{name, data: Uint8Array|string}]
    const enc = new TextEncoder(), parts = [], cd = []; let off = 0;
    const d = new Date(), dosTime = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1), dosDate = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    for (const f of files) {
      const data = typeof f.data === 'string' ? enc.encode(f.data) : f.data, name = enc.encode(f.name), crc = crc32(data);
      const lh = new Uint8Array(30 + name.length), v = new DataView(lh.buffer);
      v.setUint32(0, 0x04034b50, true); v.setUint16(4, 20, true); v.setUint16(6, 0x800, true); v.setUint16(8, 0, true);
      v.setUint16(10, dosTime, true); v.setUint16(12, dosDate, true); v.setUint32(14, crc, true); v.setUint32(18, data.length, true); v.setUint32(22, data.length, true);
      v.setUint16(26, name.length, true); v.setUint16(28, 0, true); lh.set(name, 30);
      const ch = new Uint8Array(46 + name.length), c = new DataView(ch.buffer);
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x800, true); c.setUint16(10, 0, true);
      c.setUint16(12, dosTime, true); c.setUint16(14, dosDate, true); c.setUint32(16, crc, true); c.setUint32(20, data.length, true); c.setUint32(24, data.length, true);
      c.setUint16(28, name.length, true); c.setUint32(42, off, true); ch.set(name, 46);
      parts.push(lh, data); cd.push(ch); off += lh.length + data.length;
    }
    const cdLen = cd.reduce((n, x) => n + x.length, 0), eocd = new Uint8Array(22), e = new DataView(eocd.buffer);
    e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true); e.setUint32(12, cdLen, true); e.setUint32(16, off, true);
    const total = off + cdLen + 22, out = new Uint8Array(total); let p = 0;
    for (const x of [...parts, ...cd, eocd]) { out.set(x, p); p += x.length; }
    return out;
  }

  return { SIZE, KNOWN, H_ORIG, H_AE, DEFAULTS, LIMITS, AUDIO_OK, RC_NAMES, sha256, hex, at, identify, readSettings, build, label, sumMbit, withDefaults, listZip, readZipEntry, makeZip, applyDelta };
})();
