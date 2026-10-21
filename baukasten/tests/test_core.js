// Prueft den Kern des Baukastens ohne Browser (node >= 18).
//   PVT_ORIGINAL=/pfad/zu/CFUPDATE.BIN node tests/test_core.js
// PVT_ORIGINAL ist das unveraenderte Pinnacle-Update 01.00.46.03 (CFUPDATE.BIN, 245.760 Byte) oder
// das AE-Abbild. Ohne die Datei werden nur die Teile geprueft, die keine Firmware brauchen.
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const SRC = path.join(__dirname, '..', 'src');
const core = fs.readFileSync(path.join(SRC, 'core.js'), 'utf8').replace('/*DELTA*/', fs.readFileSync(path.join(SRC, 'delta.js'), 'utf8'));
const ctx = { TextDecoder, TextEncoder, Blob, Response, DecompressionStream: globalThis.DecompressionStream, console };
vm.createContext(ctx); vm.runInContext(core + '\nthis.CORE = CORE;', ctx);
const C = ctx.CORE;
let fails = 0, n = 0;
const ok = (c, m) => { n++; console.log((c ? 'OK   ' : 'FAIL ') + m); if (!c) fails++; };
const dv = (b) => new DataView(b.buffer, b.byteOffset, b.byteLength);

// ---- ohne Firmware: Pruefung der Einstellungen, Labels, ZIP ----------------------------------
ok(C.label(C.DEFAULTS) === 'AE', 'Label der Vorgabe ist AE');
ok(C.label({ video: 4500, audio: 96, width: 528, rein: true }) === 'AE_V4500_A96_B528_REIN', 'Label 4500/96/528/rein');
ok(C.label({ audio: 0, height: 288, gop: [25, 25, 25], srate: 32000, rc7f: 1000 }) === 'AE_V5000_NURVIDEO_B720x288_G25_SR32000_T1000', 'Label mit allen Zusaetzen: ' + C.label({ audio: 0, height: 288, gop: [25, 25, 25], srate: 32000, rc7f: 1000 }));
ok(C.sha256(new TextEncoder().encode('abc')) === 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad', 'SHA-256 Testvektor');
(async () => {
  const z = C.makeZip([{ name: 'a/b.txt', data: 'Hallo Umlaute äöü' }, { name: 'c.bin', data: new Uint8Array([1, 2, 3]) }]);
  const ab = z.buffer.slice(z.byteOffset, z.byteOffset + z.byteLength);
  const e = C.listZip(ab);
  const back = await C.readZipEntry(ab, e[0]);
  ok(e.length === 2 && new TextDecoder().decode(back) === 'Hallo Umlaute äöü', 'ZIP schreiben und wieder lesen');

  // ---- mit Firmware ----------------------------------------------------------------------------
  const p = process.env.PVT_ORIGINAL;
  if (!p || !fs.existsSync(p)) {
    console.log('(PVT_ORIGINAL nicht gesetzt oder nicht gefunden: Firmware-Pruefungen uebersprungen)');
    return done();
  }
  const img = new Uint8Array(fs.readFileSync(p));
  const id = C.identify(img);
  ok(id.kind === 'orig' || id.kind === 'ae', 'Datei erkannt als ' + id.kind + (id.known ? ' (' + id.known.name + ')' : ''));
  if (!id.base) return done();
  const ae = id.base;
  ok(C.sha256(ae) === C.H_AE, 'AE-Basis hat den bekannten Hash');
  if (id.kind === 'orig') ok(C.sha256(id.orig) === C.H_ORIG, 'Rueckweg AE -> Original ergibt das Original');
  // alle bekannten Builds aus ihren Einstellungen nachbauen -> Hash muss in der Tabelle stehen
  // (AB fehlt hier: seine LED2/LED3-Werte sind nicht als Einstellung abgebildet; er wird nur per Hash erkannt)
  const known = {
    'AE rein (LED2/LED3 wie LED1)': { rein: true },
    'AG_4900_128': { video: 4900, audio: 128 }, 'AG_4800_192': { video: 4800, audio: 192 }, 'AG_4500_128': { video: 4500, audio: 128 },
    'AH_4900_128_P04_256': { video: 4900, audio: 128, p04: 256 },
    'AI_528_4500_192': { video: 4500, audio: 192, width: 528 }, 'AI_528_4800_192': { video: 4800, audio: 192, width: 528 },
    'AI_528_4500_192_P04_256': { video: 4500, audio: 192, width: 528, p04: 256 },
    'AE_V5000_A96_B528_REIN': { video: 5000, audio: 96, width: 528, rein: true },
    'AE_V4500_A96_B528_REIN': { video: 4500, audio: 96, width: 528, rein: true },
    'AE_V4500_A96_B528_SR32000_REIN': { video: 4500, audio: 96, width: 528, rein: true, srate: 32000 }
  };
  for (const [name, s] of Object.entries(known)) {
    const k = C.KNOWN.find(x => x[1] === name);
    const b = C.build(ae, s);
    ok(k && b.sha === k[0], name + ': Nachbau ' + b.sha.slice(0, 12) + (k ? (b.sha === k[0] ? ' = Tabelle' : ' != Tabelle ' + k[0].slice(0, 12)) : ' (nicht in Tabelle)'));
    const rs = C.identify(b.bytes);
    ok(rs.kind === 'derived' && Object.keys(s).every(key => JSON.stringify(rs.settings[key]) === JSON.stringify(s[key])) && C.sha256(rs.base) === C.H_AE, '   wieder gelesen, Basis normalisiert = AE');
  }
  // freie Werte: nur technische Sperren
  for (const [st, name] of [[{ video: 3000 }, 'Video 3000'], [{ video: 12000, audio: 8 }, 'Video 12000 + Ton 8'], [{ audio: 0 }, 'nur Video'], [{ width: 530 }, 'Breite 530'],
    [{ height: 288, heightN: 240 }, 'Hoehe 288/240'], [{ widthN: 528, width: 528 }, 'Breite 528 beide Normen'], [{ gop: [1, 1000, 50] }, 'GOP 1/1000/50'],
    [{ tf: [0, 3, 127] }, 'TF 0/3/127'], [{ rc7f: 500, rc11f: 1100, rc9: 1, rc10: 2500000, rc12: 22500 }, 'Ratenregelung'], [{ srate: 24000 }, 'Abtastrate 24000']]) {
    try { const b = C.build(ae, st); const rs = C.identify(b.bytes); ok(rs.kind === 'derived' && Object.keys(st).every(k => JSON.stringify(rs.settings[k]) === JSON.stringify(st[k])), name + ' angenommen: ' + C.label(st) + ', ' + b.patches.length + ' Werte'); }
    catch (e) { ok(false, name + ' angenommen: ' + e.message); }
  }
  for (const [st, name] of [[{ video: 0 }, 'Video 0'], [{ video: 858994 }, 'Video 858994 (x5000 > 32 Bit)'], [{ audio: -1 }, 'Ton -1'], [{ width: 0 }, 'Breite 0'], [{ tf: [3, 3, 128] }, 'TF 128'],
    [{ gop: [0, 50, 50] }, 'GOP 0'], [{ video: 4800.5 }, 'Video 4800,5'], [{ rc7f: 0 }, 'RC7-Faktor 0']]) {
    try { C.build(ae, st); ok(false, name + ' abgelehnt'); } catch (e) { ok(true, name + ' abgelehnt: ' + e.message); }
  }
  // Einzelbyte-Patches
  const bv = C.build(ae, { audio: 0 }); let d = 0; for (let i = 0; i < ae.length; i++) if (ae[i] !== bv.bytes[i]) d++;
  ok(d === 1 && bv.bytes[0x0c362] === 0x7a && bv.bytes[0x0c363] === 2, 'nur Video: genau ein Byte (0x0C363: 1 -> 2)');
  const bs = C.build(ae, { srate: 32000 });
  ok(bs.patches.length === 3 && [0x0c67a, 0x1aa9e, 0x2aa0c].every(o => dv(bs.bytes).getUint32(o) === 32000), 'Abtastrate: drei Stellen');
  const br = C.build(ae, { rc9: 1, rc10: 2500000, rc12: 22500, rein: true });
  ok(dv(br.bytes).getUint32(0x2e11e) === 1 && dv(br.bytes).getUint32(0x2e140 + 0x2b0) === 2500000, 'Puffer-Regelung LED1 + rein nach LED3 kopiert');
  done();
})();

function done() { console.log(fails ? ('FEHLER: ' + fails + ' von ' + n) : ('ALLE ' + n + ' PRUEFUNGEN BESTANDEN')); process.exit(fails ? 1 : 0); }
