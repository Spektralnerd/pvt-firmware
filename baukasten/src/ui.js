(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const fmtM = (kb) => (kb / 1000).toFixed(2).replace('.', ',') + ' Mbit/s';
  const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const state = { fileName: '', candidates: [], chosen: null, built: null };
  const dlReady = (window.claude && typeof window.claude.use === 'function') ? window.claude.use('downloads').catch(() => null) : Promise.resolve(null);

  // ---------- Schritt 1: Datei ----------
  const drop = $('drop');
  ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
  drop.addEventListener('drop', e => { const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]; if (f) loadFile(f); });
  $('file').addEventListener('change', e => { const f = e.target.files && e.target.files[0]; if (f) loadFile(f); e.target.value = ''; });

  async function loadFile(file) {
    const ident = $('ident'); ident.hidden = false;
    ident.innerHTML = '<div class="status"><strong>Lese ' + esc(file.name) + ' …</strong></div>';
    state.fileName = file.name; state.candidates = []; state.chosen = null; state.built = null; renderResult(null);
    try {
      const buf = await file.arrayBuffer(); const b = new Uint8Array(buf);
      if (b.length >= 4 && b[0] === 0x50 && b[1] === 0x4b && b[2] === 3 && b[3] === 4) {
        const entries = CORE.listZip(buf).filter(e => /cfupdate\.bin$/i.test(e.name) || e.usize === CORE.SIZE);
        if (!entries.length) throw new Error('Im ZIP ist keine CFUPDATE.BIN (245.760 Byte).');
        for (const e of entries) {
          try { const data = await CORE.readZipEntry(buf, e); state.candidates.push({ name: e.name, id: CORE.identify(data) }); }
          catch (err) { state.candidates.push({ name: e.name, error: err.message }); }
        }
      } else {
        state.candidates.push({ name: file.name, id: CORE.identify(b) });
      }
    } catch (err) {
      ident.innerHTML = '<div class="status bad"><strong>Datei nicht verwendbar</strong>' + esc(err.message) + '</div>';
      updateBuildButton(); return;
    }
    const rank = { orig: 0, ae: 1, derived: 2, unknown: 3 };
    const usable = state.candidates.filter(c => c.id && c.id.base).sort((a, b) => rank[a.id.kind] - rank[b.id.kind]);
    state.chosen = usable[0] || null;
    renderIdent(); updateBuildButton();
  }

  function kindText(id) {
    switch (id.kind) {
      case 'orig': return { cls: 'ok', title: 'Original 01.00.46.03 erkannt', text: 'Die eingebaute Differenz macht daraus den Stand AE; der Hash des Ergebnisses stimmt mit AE überein.' };
      case 'ae': return { cls: 'ok', title: 'AE (Vorführstand) erkannt', text: 'Byteidentisch mit dem geprüften Vorführstand.' };
      case 'derived': return { cls: 'ok', title: (id.known ? id.known.name : 'Abkömmling von AE') + ' erkannt', text: 'Nur Zahlenwerte weichen von AE ab. Nach dem Zurücksetzen stimmt der Hash mit AE überein, die Datei taugt als Basis.' + (id.known ? ' Stand: ' + id.known.status + '.' : '') };
      default: return { cls: 'bad', title: id.known ? id.known.name + ' erkannt, als Basis nicht verwendbar' : 'Unbekannte Firmware', text: id.note || 'Weder Original noch AE-Struktur.' };
    }
  }
  function settingsHtml(s) {
    if (!s) return '';
    const led = (i) => s.led[i].map((v, k) => CORE.RC_NAMES[k].split(' ')[0] + '=' + v).join(' · ');
    return '<dl class="kv">' +
      '<dt>Videoziel</dt><dd>' + s.video + ' kbit/s</dd>' +
      '<dt>Audio</dt><dd>' + (s.audio === 0 ? 'aus (nur Video)' : s.audio + ' kbit/s') + '</dd>' +
      '<dt>Bildgröße</dt><dd>PAL ' + s.width + ' × ' + s.height + ' · NTSC ' + s.widthN + ' × ' + s.heightN + '</dd>' +
      '<dt>GOP je LED</dt><dd>' + s.gop.join(' / ') + '</dd>' +
      '<dt>Abtastrate</dt><dd>' + s.srate + ' Hz</dd>' +
      '<dt>Regelung LED1</dt><dd>RC7 ×' + s.rc7f + ' · RC11 ×' + s.rc11f + ' · Puffer ' + (s.rc9 ? 'an ' + s.rc10 + ' Bit, Start ' + s.rc12 : 'aus') + '</dd>' +
      '<dt>MG-Puffer</dt><dd>Video p03 ' + s.p03 + ' · Audio p04 ' + s.p04 + ' Seiten</dd>' +
      '<dt>TF je LED</dt><dd>' + s.tf.join(' / ') + '</dd>' +
      '<dt>LED1</dt><dd>' + led(0) + '</dd><dt>LED2</dt><dd>' + led(1) + '</dd><dt>LED3</dt><dd>' + led(2) + '</dd></dl>';
  }
  function renderIdent() {
    const ident = $('ident'); let html = '';
    if (state.candidates.length > 1) {
      html += '<p class="small muted" style="margin-top:12px">Mehrere CFUPDATE.BIN im Archiv. Basis für den Bau:</p><ul class="entries">';
      state.candidates.forEach((c, i) => {
        const ok = c.id && c.id.base, sel = c === state.chosen;
        html += '<li><label class="' + (sel ? 'sel' : '') + '"><input type="radio" name="cand" value="' + i + '"' + (sel ? ' checked' : '') + (ok ? '' : ' disabled') + '><span><strong class="mono small">' + esc(c.name) + '</strong><br><span class="small muted">' +
          esc(c.error ? 'Fehler: ' + c.error : (c.id.known ? c.id.known.name : (c.id.kind === 'unknown' ? 'unbekannt' : 'AE-Abkömmling')) + (ok ? '' : ' (nicht verwendbar)')) + '</span></span></label></li>';
      });
      html += '</ul>';
    }
    const c = state.chosen || state.candidates[0];
    if (c) {
      if (c.error) html += '<div class="status bad"><strong>' + esc(c.name) + '</strong>' + esc(c.error) + '</div>';
      else {
        const k = kindText(c.id);
        html += '<div class="status ' + k.cls + '"><strong>' + esc(k.title) + '</strong>' + esc(k.text) +
          (c.id.sha ? '<span class="hash" style="margin-top:8px">SHA-256 ' + c.id.sha + '</span>' : '') + settingsHtml(c.id.settings) +
          (c.id.kind === 'derived' ? '<p style="margin:10px 0 0"><button class="btn sm" type="button" id="takeOver">Einstellungen dieser Datei ins Formular übernehmen</button></p>' : '') + '</div>';
      }
    }
    ident.innerHTML = html;
    ident.querySelectorAll('input[name=cand]').forEach(r => r.addEventListener('change', () => { state.chosen = state.candidates[+r.value]; state.built = null; renderResult(null); renderIdent(); updateBuildButton(); }));
    const t = $('takeOver'); if (t) t.addEventListener('click', () => { setForm(c.id.settings); });
  }

  // ---------- Schritt 2: Einstellungen ----------
  const preset = (o) => CORE.withDefaults(o);
  const PRESETS = {
    ae: preset({}),
    ton96: preset({ video: 4500, audio: 96, width: 528, rein: true }),
    ton64: preset({ video: 4500, audio: 64, width: 528, rein: true }),
    nurvideo: preset({ audio: 0 }),
    ai528: preset({ video: 4800, audio: 192, width: 528 }),
    rein: preset({ rein: true })
  };
  const NUM = ['video', 'audio', 'width', 'height', 'widthN', 'heightN', 'p03', 'p04', 'srate', 'rc7f', 'rc11f', 'rc10', 'rc12'];
  const num = (id) => { const v = $(id).value.trim(); return v === '' ? NaN : Number(v); };
  function readForm() {
    const o = { rein: $('rein').checked, rc9: $('rc9').checked ? 1 : 0, gop: [num('gop1'), num('gop2'), num('gop3')], tf: [num('tf1'), num('tf2'), num('tf3')] };
    NUM.forEach(k => { o[k] = num(k); });
    return o;
  }
  function setForm(raw) {
    const s = CORE.withDefaults(raw);
    NUM.forEach(k => { $(k).value = String(s[k]); });
    $('rein').checked = !!s.rein; $('rc9').checked = s.rc9 === 1;
    [1, 2, 3].forEach(i => { $('gop' + i).value = String(s.gop[i - 1]); $('tf' + i).value = String(s.tf[i - 1]); });
    const D = CORE.DEFAULTS;
    if (s.widthN !== D.widthN || s.heightN !== D.heightN || s.p03 !== D.p03 || s.srate !== D.srate || s.gop.some(g => g !== 50) || s.tf.some(t => t !== 3)) $('expert').open = true;
    if (s.rc7f !== D.rc7f || s.rc11f !== D.rc11f || s.rc9 !== D.rc9 || s.rc10 !== D.rc10 || s.rc12 !== D.rc12) $('rcx').open = true;
    onChange();
  }
  $('presets').addEventListener('click', e => { const b = e.target.closest('button[data-preset]'); if (b) setForm(PRESETS[b.dataset.preset]); });
  $('form').addEventListener('input', onChange); $('form').addEventListener('change', onChange);
  $('form').addEventListener('submit', e => e.preventDefault());

  const fmtTick = (kb) => (kb / 1000).toFixed(kb % 500 ? 2 : 1).replace('.', ',');
  function renderBar(sum) {
    const ok = Number.isFinite(sum);
    $('sumVal').textContent = ok ? fmtM(sum) : '–';
    const lo = ok ? Math.min(4000, Math.max(0, Math.floor((sum - 500) / 500) * 500)) : 4000;
    const hi = ok ? Math.max(5500, Math.ceil((sum + 500) / 500) * 500) : 5500;
    const pos = (v) => Math.max(0, Math.min(100, (v - lo) / (hi - lo) * 100));
    const fill = $('sumFill'); fill.style.width = (ok ? pos(sum) : 0) + '%';
    fill.className = 'fill' + (ok && sum > 5250 ? ' bad' : ok && sum > 5050 ? ' warn' : '');
    $('markOk').style.left = pos(5050) + '%'; $('markWall').style.left = pos(5250) + '%';
    const span = hi - lo, step = span <= 2000 ? 500 : span <= 6000 ? 1000 : span <= 15000 ? 2500 : span <= 40000 ? 5000 : 20000;
    const ticks = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push([v, fmtTick(v), v === lo ? 'first' : v === hi ? 'last' : '']);
    if (pos(5250) > 4 && pos(5250) < 96) ticks.push([5250, '5,25 Mauer', 'wall']);
    ticks.sort((a, b) => a[0] - b[0]);
    // Kollisionen nach Pixeln auflösen: die Mauer-Marke gewinnt gegen Zwischenwerte, erste und letzte bleiben
    const W = $('ticks').clientWidth || 600, px = (v) => pos(v) / 100 * W, wide = (t) => t.length * 7.2;
    const kept = [];
    for (const t of ticks) {
      const k = kept[kept.length - 1];
      if (!k) { kept.push(t); continue; }
      const gap = px(t[0]) - px(k[0]), needed = (wide(k[1]) + wide(t[1])) / 2 + 8 - (k[2] === 'first' ? wide(k[1]) / 2 : 0) - (t[2] === 'last' ? wide(t[1]) / 2 : 0);
      if (gap >= needed) { kept.push(t); continue; }
      if (t[2] === 'wall' && k[2] !== 'first') kept[kept.length - 1] = t;
      else if (t[2] === 'last' && k[2] === 'wall') continue;
      else if (t[2] === 'last') kept[kept.length - 1] = t;
    }
    $('ticks').innerHTML = kept.map(([v, t, c]) => '<span class="' + c + '" style="left:' + pos(v) + '%">' + t + '</span>').join('');
  }
  function onChange() {
    state.built = null; renderResult(null);
    const s = readForm(); const sum = s.video + s.audio;
    renderBar(sum);
    const notes = [], D = CORE.DEFAULTS, L = CORE.LIMITS;
    const bad = (t) => notes.push(['bad', t]), warn = (t) => notes.push(['warn', t]), info = (t) => notes.push(['', t]);
    const intIn = (v, [lo, hi]) => Number.isInteger(v) && v >= lo && v <= hi;
    // technische Sperren (die einzigen, die den Bau verhindern)
    if (!intIn(s.video, L.video)) bad('Videoziel: ganze Zahl 1 bis 858993 kbit/s (Video×5000 muss in 32 Bit passen).');
    if (!intIn(s.audio, L.audio)) bad('Audio: 0 (aus) oder ganze Zahl bis 4294967 kbit/s.');
    [['width', 'Breite PAL'], ['height', 'Höhe PAL'], ['widthN', 'Breite NTSC'], ['heightN', 'Höhe NTSC']].forEach(([k, n]) => { if (!intIn(s[k], L.size)) bad(n + ': ganze Zahl 1 bis 65535.'); });
    if (!intIn(s.p03, L.pages) || !intIn(s.p04, L.pages)) bad('MG-Puffer: ganze Zahl 1 bis 65535 Seiten.');
    if (!s.gop.every(g => intIn(g, L.gop))) bad('GOP: ganze Zahl ab 1 je LED.');
    if (!intIn(s.srate, L.srate)) bad('Abtastrate: ganze Zahl in Hz.');
    if (!intIn(s.rc7f, L.rcf) || s.video * s.rc7f > 4294967295) bad('Größentoleranz-Faktor: ganze Zahl, Video×Faktor muss in 32 Bit passen.');
    if (!intIn(s.rc11f, L.rcf) || s.video * s.rc11f > 4294967295) bad('Transferraten-Faktor: ganze Zahl, Video×Faktor muss in 32 Bit passen.');
    if (!intIn(s.rc10, L.rc10) || !intIn(s.rc12, L.rc12)) bad('Pufferbits ab 1, Startverzögerung ab 0.');
    if (!s.tf.every(t => intIn(t, L.tf))) bad('TF: ganze Zahl 0 bis 127 je LED.');
    if (notes.length) { $('notes').innerHTML = notes.map(([c, t]) => '<li class="' + c + '">' + esc(t) + '</li>').join(''); updateBuildButton(); return; }
    // Hinweise aus Messungen und Datenblatt – sperren nichts
    if (sum > 5250) warn('Summe über der gemessenen Host-Mauer von 5,25 Mbit/s (AE mit Stille lief bis 5,02 fünf Stunden). Erwartung: leere Bilder in Phasen; mit echtem Ton sicher Aussetzer. Für den Versuch erlaubt.');
    else if (sum > 5050) warn('Summe über dem bewährten Niveau von 5,05 Mbit/s. Mit echtem Ton riskant; AE selbst liegt mit 384 kbit/s Ton rechnerisch bei 5,38 und brach ab.');
    else info('Summe unter dem bewährten Niveau: rechnerisch ' + Math.round(sum / 5250 * 100) + ' % der Mauer.');
    if (s.video > 10000) warn('Videoziel über dem MG-Datenblatt (64 kbit/s bis 10 Mbit/s). Der MG kann abweisen oder stillschweigend begrenzen; der Host wäre ohnehin weit über der Mauer.');
    if (s.video < 3600) info('Unter 3600: der ColdFire setzt MG-Param 10 auf 1 statt 2 (so laufen die Original-Stufen mit 768/1200/1500). Anderer Encoder-Modus, kein Fehler.');
    if (s.video < 64) warn('Videoziel unter dem MG-Minimum von 64 kbit/s.');
    if (s.audio === 0) warn('Nur Video – geprüft 20.10. (VID00012): Aufnahme makellos (60 s, 5,25 Mbit/s, 0 Aussetzer), aber der ColdFire schreibt den Index unvollständig (nur die letzten ~120 Tabelleneinträge), die Datei spielt nicht. mp4_reparatur.py aus dem Test-Paket baut den Index neu (1 Befehl, geprüft). Alternative ohne Reparatur: Ton 8 kbit/s (Blöcke 21 Byte) – ungeprüft.');
    else {
      if (s.audio < 8 || s.audio > 384) warn('Ton ' + s.audio + ' kbit/s liegt außerhalb des MG-Datenblatts (8–384). Der MG kann abweisen oder begrenzen.');
      if (s.audio >= 192) bad('Ton ' + s.audio + ' kbit/s: Blöcke über 450 Byte, der Tonpfad des ColdFire starb damit nach 20 s (VID00006/VID00007), unabhängig von der Videorate. Nur ohne Audiokabel brauchbar.');
      else if (s.audio > 96) warn('Ton ' + s.audio + ': Blöcke von ' + Math.round(s.audio * 1000 * 1024 / 48000 / 8) + ' Byte, am Gerät ungeprüft (96 = 256 Byte hält, 192 = 512 Byte nicht).');
      else if (!CORE.AUDIO_OK.includes(s.audio)) info('Ton ' + s.audio + ' kbit/s: Zwischenwert, der MG nimmt jede Zahl in Bit/s als Langzeit-Bitrate; Blöcke um ' + Math.round(s.audio * 1000 * 1024 / 48000 / 8) + ' Byte.');
      if (s.audio < 192 && s.video > 4600) warn('Mit echtem Ton kippte das Video bei 5000 + 96 (VID00008) ab etwa 4,9 Mbit/s realer Rate; 4500 + 96 lief mit 99 % Ton. Reserve einplanen.');
    }
    const sizeNotes = (w, h, srcW, srcH, norm, tested) => {
      if (w === srcW && h === srcH) return;
      if (w <= 16 || h <= 16) warn(norm + ': Werte 1–16 liest der MG als Teiler, nicht als Pixel (2 = halbe Größe auf ein Vielfaches von 16).');
      if (w > srcW || h > srcH) warn(norm + ': ' + w + '×' + h + ' ist größer als die Quelle (' + srcW + '×' + srcH + '). Laut MG-Handbuch muss der Zielwert kleiner als das Bild sein; der MG kann nicht hochskalieren.');
      if (w !== srcW) {
        if (w % 16) warn(norm + ': Breite ' + w + ' ist kein Vielfaches von 16. H.264 arbeitet in 16er-Blöcken, der MG rundet oder meldet „unsupported horizontal decimation“.');
        if (!tested.includes(w) && w > 16 && w < srcW) info(norm + ': Breite ' + w + ' ist am Gerät ungeprüft (bestätigt: 720, 528' + (norm === 'PAL' ? '' : ' nur PAL') + '). Der MG hat eigene Filtertabellen für 720, 640, 360 und 180, sonst den allgemeinen Skalierer (528 lief damit sauber).');
      }
      if (h !== srcH) {
        if (h % 16) warn(norm + ': Höhe ' + h + ' ist kein Vielfaches von 16 (bei Halbbildern 32).');
        warn(norm + ': Höhe ' + h + ' statt ' + srcH + ' ist am Gerät ungeprüft. Der MG skaliert senkrecht; bei Zeilensprung-Quelle ohne Halbbild-Verwurf (der ColdFire setzt INT_TO_PROG_SCALE nicht) ist Kammbildung oder Halbbild-Kodierung mit halber Höhe möglich. Die Original-Stufe LED1 lieferte 320×240 aus 576i, der Weg geht grundsätzlich.');
      }
    };
    sizeNotes(s.width, s.height, 720, 576, 'PAL', [720, 528]);
    sizeNotes(s.widthN, s.heightN, 720, 480, 'NTSC', [720]);
    if (s.widthN !== s.width) info('NTSC-Breite ' + s.widthN + ' ≠ PAL-Breite ' + s.width + ': die RC-Erweiterung prüft eine gemeinsame Breite (' + s.width + '), NTSC läuft dann ohne RC-Erweiterung – wie alle bisherigen 528er-Builds.');
    if (s.gop.some(g => g !== 50)) info('GOP ' + s.gop.join('/') + ' statt 50: am Gerät ungeprüft. Gemessen am AE-Material: I-Bilder sind 4 % der Bits, GOP ändern bewegt 1–2 %. Kurze GOP = robuster gegen Aussetzer, lange = etwas kleinere Datei.');
    if (s.srate !== 48000) {
      const blk = s.audio ? Math.round(s.audio * 1000 * 1024 / s.srate / 8) : 0, ps = (s.srate / 1024).toFixed(1).replace('.', ',');
      bad('Abtastrate ' + s.srate + ' Hz: am Gerät geprüft 20.10. (VID00011, 32000): der 256×fs-Takt kommt von außen und bleibt bei 48 kHz. Der MG bekommt 1,5× mehr Abtastwerte als eingestellt, läuft über und reißt das Video mit (50 % der Bilder leer/klein, Bitstromfehler, 23 s Bilder fehlen), Ton 1,5× zu langsam und ab 4 s tot. Kopfangaben (stsd/mdhd/AAC-Konfig) schreibt der ColdFire zwar richtig, aber der Wert ist kein Hebel – nur für weitere Versuche.' + (s.audio ? ' Blöcke rechnerisch ' + blk + ' Byte, ' + ps + ' je Sekunde.' : ''));
      if (![22050, 24000, 32000, 44100, 48000].includes(s.srate)) warn('Abtastrate ' + s.srate + ' steht nicht in der MG-Liste (22050, 24000, 32000, 44100, 48000).');
    }
    const rcLine = 'RC7 = ' + (s.video * s.rc7f).toLocaleString('de-DE') + ' Bit (±' + (s.rc7f / 1000).toLocaleString('de-DE') + ' s Video)';
    $('rcInfo').textContent = rcLine + ' · RC11 = ' + (s.video * s.rc11f).toLocaleString('de-DE') + ' Bit/s' + (s.rc9 ? ' · Puffer ' + (s.rc10 / 1000).toLocaleString('de-DE') + ' kBit = ' + (s.rc10 / (s.video * 1000)).toFixed(2).replace('.', ',') + ' s, Start ' + (s.rc12 / 90).toFixed(0) + ' ms' : ' · Puffer-Regelung aus (wie AE LED1)');
    if (s.rc7f !== 5000) warn('Größentoleranz ×' + s.rc7f + ' statt ×5000: ungeprüft. Kleiner = die Größenregelung zieht Ausreißer schneller zurück, Spitzen werden flacher; sehr klein (unter ×500 = 0,5 s) kann die Bildqualität bei Bewegung sichtbar schwanken.');
    if (s.rc11f !== 1000) warn('Transferrate ×' + s.rc11f + ' statt ×1000: ungeprüft; wirkt nur mit Puffer-Regelung (Abflussrate des Leaky-Bucket).');
    if (s.rc9) warn('Puffer-Regelung an: LED1 bekommt das Leaky-Bucket-Modell. AB lief so (1,25 MBit, 5 Mbit/s, 125 ms, am Gerät geprüft), AE hat es für LED1 abgeschaltet und nur die Größenregelung behalten. Der MG hält damit die Rate über das Pufferfenster unter der Transferrate – das Modell für den begrenzten USB-Pfad; andere Werte als die von AB sind ungeprüft.');
    if (s.p03 !== 2048) warn('Videopuffer p03 ' + s.p03 + ' Seiten: AB lief mit 832, sonst ungeprüft.');
    if (s.p04 !== 48) warn('Audiopuffer p04 ' + s.p04 + ' Seiten: ungeprüft am Gerät.');
    if (s.p03 + s.p04 > 2304) warn('p03 + p04 = ' + (s.p03 + s.p04) + ' Seiten übersteigt den belegten Speicherplan (2048 + 256 passten in der Emulation, 5025 von 5120 Seiten). Der MG könnte nicht starten.');
    if (s.rein) info('AE rein: LED2/LED3 am Gerät noch ungeprüft, LED1 bleibt wie AE.');
    if (s.tf.some(t => t > 3)) warn('TF über 3: bekannt sind die Stufen 0–3; größere Werte sind ungeprüft, der MG kann sie begrenzen oder abweisen.');
    else if (s.tf.some(t => t !== 3)) warn('TF unter 3: mehr Rauschen im Bild, höherer Bitbedarf bei gleichem Ziel.');
    $('notes').innerHTML = notes.map(([c, t]) => '<li class="' + c + '">' + esc(t) + '</li>').join('');
    updateBuildButton();
  }

  // ---------- Schritt 3: Bauen ----------
  function updateBuildButton() {
    const ok = !!(state.chosen && state.chosen.id && state.chosen.id.base);
    $('build').disabled = !ok;
    $('buildHint').textContent = ok ? 'Basis: ' + (state.chosen.id.kind === 'orig' ? 'Original → AE' : 'AE') + ' aus ' + state.chosen.name : 'Zuerst oben eine Firmware laden.';
  }
  $('build').addEventListener('click', () => {
    const s = readForm(); const res = $('result'); res.hidden = false;
    try {
      const id = state.chosen.id;
      const b = CORE.build(id.base, s);
      state.built = { s, b, label: CORE.label(s), base: id.base, orig: id.orig };
      renderResult(state.built);
    } catch (e) {
      state.built = null;
      res.innerHTML = '<div class="status bad"><strong>Bau abgebrochen</strong>' + esc(e.message) + '</div>';
    }
  });
  function renderResult(built) {
    const res = $('result');
    if (!built) { res.hidden = true; res.innerHTML = ''; return; }
    const { b, s, label } = built;
    const known = b.known;
    const badge = known ? (known.status.startsWith('am Gerät') || known.status.startsWith('LED1') ? '<span class="badge ok">' + esc(known.name + ' · ' + known.status) + '</span>' : '<span class="badge warn">' + esc(known.name + ' · ' + known.status) + '</span>')
      : '<span class="badge warn">neue Kombination · 0 Hardwaretests</span>';
    let html = '<div class="head"><div class="label">' + esc(label) + '</div>' + badge + '</div>' +
      '<span class="hash" style="margin-top:10px">SHA-256 ' + b.sha + '</span>' +
      '<p class="small muted" style="margin-top:8px">' + (b.patches.length ? b.patches.length + ' Werte geändert, sonst byteidentisch mit AE. Summe Video + Ton ' + fmtM(s.video + s.audio) + '.' : 'Keine Änderung gegenüber AE.') + '</p>';
    if (b.patches.length) {
      html += '<div class="tablewrap"><table><thead><tr><th class="mono">Offset</th><th>Wert</th><th class="mono">alt</th><th class="mono">neu</th></tr></thead><tbody>' +
        b.patches.map(p => '<tr><td class="mono">' + CORE.at(p.o) + '</td><td>' + esc(p.name) + '</td><td class="mono">' + p.old + '</td><td class="mono">' + p.neu + '</td></tr>').join('') + '</tbody></table></div>';
    }
    html += '<div class="actions"><button class="btn primary" type="button" id="save">ZIP speichern: PVT_' + esc(label) + '.zip</button><span id="saveMsg" class="muted"></span></div>' +
      '<p class="small muted" style="margin-top:8px">Inhalt: <code>01_INSTALL_' + esc(label) + '/CFUPDATE.BIN</code>' + (label === 'AE' ? '' : ', <code>02_RETURN_AE/CFUPDATE.BIN</code>') + ', <code>0' + (label === 'AE' ? '2' : '3') + '_RETURN_ORIGINAL/CFUPDATE.BIN</code>, <code>README_DE.txt</code>, <code>SHA256SUMS.txt</code>.</p>';
    res.innerHTML = html; res.hidden = false;
    $('save').addEventListener('click', saveZip);
  }
  function readme(built) {
    const { s, b, label } = built; const sum = s.video + s.audio;
    const k = b.known;
    return ['PVT FIRMWARE-BAUKASTEN - ' + label, 'Erzeugt am ' + new Date().toLocaleString('de-DE') + ' aus ' + state.fileName + ' (' + (state.chosen.id.kind === 'orig' ? 'Original 01.00.46.03 -> AE' : 'AE-Basis') + ').',
      'Basis: AE (Vorfuehrstand), Original-Update 01.00.46.03. Nur Zahlenwerte geaendert, kein neuer Code.',
      '', 'EINSTELLUNGEN',
      '  Videoziel        ' + s.video + ' kbit/s', (s.audio === 0 ? '  Ton              AUS - MG nur Video (ENC_INPUT_SELECT/ENC_AV_SELECT = 2), Audioanforderung bleibt 384 (wirkungslos)' : '  Audioanforderung ' + s.audio + ' kbit/s (AAC, MG-Objekt 3 / Opcode 41)'),
      '  Bildgroesse PAL  ' + s.width + ' x ' + s.height + (s.height === 576 ? 'i (Halbbilder)' : ' (MG skaliert senkrecht, ungeprueft)') + (s.width !== 720 ? ' - MG skaliert waagerecht' : ''),
      '  Bildgroesse NTSC ' + s.widthN + ' x ' + s.heightN + (s.widthN !== s.width ? ' (Breite != PAL: NTSC ohne RC-Erweiterung)' : ''),
      '  GOP-Laenge       LED1 ' + s.gop[0] + ' / LED2 ' + s.gop[1] + ' / LED3 ' + s.gop[2] + ' Bilder (AE 50)',
      '  Ratenregelung    RC7 Groessentoleranz = Video x ' + s.rc7f + ' = ' + (s.video * s.rc7f) + ' Bit; RC11 Transferrate = Video x ' + s.rc11f + ' = ' + (s.video * s.rc11f) + ' Bit/s;',
      '                   LED1 Puffer-Regelung ' + (s.rc9 ? 'AN, Pufferbits ' + s.rc10 + ', Startverzoegerung ' + s.rc12 + ' Ticks' : 'aus (AE)') + (s.rein ? ' - LED2/LED3 uebernehmen alles' : ' - LED2/LED3 wie AE (Puffer 5/10 MBit, Start 0,5/1 s)'),
      '  Abtastrate       ' + s.srate + ' Hz' + (s.srate !== 48000 ? ' (ungeprueft: MG-Parameter, Host-Konfiguration und MP4-Vorlage gemeinsam gesetzt; Takt von aussen und AAC-Konfigbyte offen - pvt_check Zeile Abtastrate)' : ' (AE)'),
      '  MG-Puffer        Video p03 = ' + s.p03 + ' Seiten (' + s.p03 * 2 + ' KB), Audio p04 = ' + s.p04 + ' Seiten (' + s.p04 * 2 + ' KB)',
      '  LED2/LED3        ' + (s.rein ? 'wie LED1 (AE rein)' : 'wie AE (LED2 Modell 5 Mbit/0,5 s, LED3 10 Mbit/1 s)'),
      '  TF-Stufe         LED1 ' + s.tf[0] + ' / LED2 ' + s.tf[1] + ' / LED3 ' + s.tf[2],
      '  Summe Video+Ton  ' + fmtM(sum) + ' (gemessene Host-Mauer 5,25; bewaehrt <= 5,05)' + (sum > 5250 ? ' - UEBER DER MAUER, Versuch' : ''),
      '', 'STAND', '  ' + (k ? k.name + ': ' + k.status : 'Neue Kombination, 0 Hardwaretests.'),
      '  Freigabe fuer lange Laeufe erst nach 30 min mit Ton und einem 4-GiB-Wechsel.',
      '', 'GEAENDERTE WERTE (Datei-Offset, alt -> neu)', ...(b.patches.length ? b.patches.map(p => '  ' + CORE.at(p.o) + '  ' + String(p.old).padStart(10) + ' -> ' + String(p.neu).padStart(10) + '  ' + p.name) : ['  keine (identisch mit AE)']),
      '', 'DATEIEN', '  01_INSTALL_' + label + '/CFUPDATE.BIN   SHA-256 ' + b.sha,
      ...(label === 'AE' ? [] : ['  02_RETURN_AE/CFUPDATE.BIN         SHA-256 ' + CORE.H_AE]),
      '  0' + (label === 'AE' ? '2' : '3') + '_RETURN_ORIGINAL/CFUPDATE.BIN   SHA-256 ' + CORE.H_ORIG,
      '', 'EINSPIELEN', '  1. Nur EINE CFUPDATE.BIN ins Hauptverzeichnis eines leeren FAT32-Sticks. Keine MGUPDATE.BIN, keine custom.txt/best.txt.',
      '  2. PVT aus, Netzteil und Geraete trennen, Stick rein, Netzteil dran - das PVT startet selbst.',
      '  3. USB-LED rot + MODE-LEDs blau blinkend = Update laeuft. Nichts trennen.',
      '  4. Alle LEDs blinken blau, dann Standby. MODE kurz druecken; Stick erst ziehen, wenn die USB-LED blau leuchtet.',
      '  5. 1-2 min auf LED1 aufnehmen, mit pvt_check.py pruefen: leer = 0, Ton minus Video < 0,2 s.', ...(s.audio === 0 ? ['  Nur Video: die Datei spielt erst nach  python3 mp4_reparatur.py VID0000x.MP4  (Index neu bauen, Test-Paket).'] : []),
      '', 'Experimentelle Firmware. Keine Herstellerfreigabe. Die Rueckkehrdatei hilft nur bei funktionierendem Updatepfad; Backups/Dumps behalten.', ''].join('\n');
  }
  async function saveZip() {
    const built = state.built; if (!built) return;
    const msg = $('saveMsg'); const btn = $('save'); btn.disabled = true; msg.textContent = 'Packe …';
    try {
      const { b, label } = built, dir = 'PVT_' + label + '/';
      const files = [{ name: dir + '01_INSTALL_' + label + '/CFUPDATE.BIN', data: b.bytes }];
      if (label !== 'AE') files.push({ name: dir + '02_RETURN_AE/CFUPDATE.BIN', data: built.base });
      files.push({ name: dir + '0' + (label === 'AE' ? '2' : '3') + '_RETURN_ORIGINAL/CFUPDATE.BIN', data: built.orig });
      files.push({ name: dir + 'README_DE.txt', data: readme(built) });
      files.push({ name: dir + 'SHA256SUMS.txt', data: files.filter(f => f.name.endsWith('.BIN')).map(f => CORE.sha256(f.data) + '  ' + f.name.slice(dir.length)).join('\n') + '\n' });
      const zip = CORE.makeZip(files); const fname = 'PVT_' + label + '.zip';
      const dl = await dlReady;
      if (dl) {
        msg.textContent = 'Bitte das Speichern bestätigen …';
        try { await dl.save({ filename: fname, data: new Blob([zip]) }); msg.textContent = 'Gespeichert: ' + fname; }
        catch (e) {
          if (e && e.code === 'declined') msg.textContent = 'Speichern abgebrochen.';
          else if (e && e.code === 'rate_limited') msg.textContent = 'Es ist noch eine Abfrage offen. Kurz warten, dann erneut.';
          else msg.textContent = 'Speichern hier nicht möglich (' + (e && e.message ? e.message : e) + '). Seite als HTML sichern und lokal im Browser öffnen, dort geht der Download direkt.';
        }
      } else {
        const url = URL.createObjectURL(new Blob([zip], { type: 'application/zip' }));
        const a = document.createElement('a'); a.href = url; a.download = fname; document.body.appendChild(a); a.click();
        setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);
        msg.textContent = 'Download gestartet: ' + fname + ' (' + Math.round(zip.length / 1024) + ' KB)';
      }
    } catch (e) { msg.textContent = 'Fehler: ' + e.message; }
    btn.disabled = false;
  }

  // ---------- Bekannte Builds ----------
  $('knownTable').querySelector('tbody').innerHTML = CORE.KNOWN.map(k => '<tr><td>' + esc(k[1]) + '</td><td>' + esc(k[2]) + '</td><td class="mono">' + k[0].slice(0, 16) + '…</td></tr>').join('');
  onChange();
})();
