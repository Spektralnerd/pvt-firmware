#!/usr/bin/env python3
"""Funktionstest der fertigen Seite in Chromium ohne Fenster (Playwright), inklusive Download.

    pip install playwright && playwright install chromium
    PVT_ORIGINAL_ZIP=/pfad/PVT1.00.46.03.zip python3 tests/smoke.py

Vorher  python3 build.py  ausfuehren. Ohne PVT_ORIGINAL_ZIP wird nur geprueft, dass die Seite ohne
Fehler laedt und die Formularlogik arbeitet; mit dem Original-ZIP werden Erkennung, Bau, Download
und der Hash des bekannten Builds AE_V4500_A96_B528_REIN geprueft.
"""
import asyncio
import hashlib
import io
import os
import sys
import zipfile

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.exit("playwright fehlt:  pip install playwright && playwright install chromium")

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "file://" + os.path.join(os.path.dirname(HERE), "dist", "PVT_Firmware_Baukasten.html")
ORIGZIP = os.environ.get("PVT_ORIGINAL_ZIP")
OUT = os.path.join(HERE, "_smoke_out")
KNOWN_4500_96_528_REIN = "13508fa0b54fdd72fcb88738b69f0ed294b3599dc462655fe0d65fe0405a8960"


async def main():
    os.makedirs(OUT, exist_ok=True)
    fails = []
    async with async_playwright() as p:
        br = await p.chromium.launch()
        ctx = await br.new_context(viewport={"width": 1100, "height": 900}, accept_downloads=True)
        page = await ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(PAGE)
        await page.wait_for_timeout(400)
        # Formular ohne Datei: Summe, Hinweise, technische Sperre
        await page.fill("#video", "6000")
        notes = await page.text_content("#notes")
        if "Mauer" not in notes:
            fails.append("Hinweis auf die Mauer fehlt bei 6000")
        await page.fill("#video", "0")
        if "ganze Zahl" not in (await page.text_content("#notes")):
            fails.append("technische Sperre bei Video 0 fehlt")
        await page.fill("#video", "5000")
        if not await page.is_disabled("#build"):
            fails.append("Bauen darf ohne Datei nicht moeglich sein")
        if ORIGZIP and os.path.exists(ORIGZIP):
            await page.set_input_files("#file", ORIGZIP)
            await page.wait_for_function("document.getElementById('ident').textContent.includes('Original 01.00.46.03 erkannt')", timeout=20000)
            await page.click("button[data-preset=ton96]")
            await page.click("#build")
            await page.wait_for_selector("#result:not([hidden]) .label")
            label = (await page.text_content("#result .label")).strip()
            async with page.expect_download(timeout=20000) as dl_info:
                await page.click("#save")
            dl = await dl_info.value
            path = os.path.join(OUT, dl.suggested_filename)
            await dl.save_as(path)
            z = zipfile.ZipFile(path)
            inst = [n for n in z.namelist() if "01_INSTALL" in n][0]
            h = hashlib.sha256(z.read(inst)).hexdigest()
            print("Label:", label, "| ZIP:", dl.suggested_filename, "| Hash:", h[:16])
            if label != "AE_V4500_A96_B528_REIN" or h != KNOWN_4500_96_528_REIN:
                fails.append("bekannter Build nicht reproduziert")
            if not any(n.endswith("README_DE.txt") for n in z.namelist()) or not any("RETURN_ORIGINAL" in n for n in z.namelist()):
                fails.append("README oder Rueckkehrdatei fehlt im ZIP")
            # nur Video + Ratenregelung: baut, Label stimmt
            await page.fill("#audio", "0")
            await page.evaluate("document.getElementById('rcx').open = true")
            await page.fill("#rc7f", "1000")
            await page.click("#build")
            await page.wait_for_selector("#result:not([hidden]) .label")
            label2 = (await page.text_content("#result .label")).strip()
            if label2 != "AE_V4500_NURVIDEO_B528_T1000_REIN":
                fails.append("Label nur Video/RC7 unerwartet: " + label2)
        else:
            print("(PVT_ORIGINAL_ZIP nicht gesetzt: Bau und Download uebersprungen)")
        await page.set_viewport_size({"width": 400, "height": 800})
        w = await page.evaluate("document.documentElement.scrollWidth")
        if w > 400:
            fails.append("waagerechter Ueberlauf bei 400 px: %d" % w)
        await page.screenshot(path=os.path.join(OUT, "phone.png"), full_page=True)
        errs = [e for e in errors]
        if errs:
            fails.append("Seitenfehler: " + "; ".join(errs)[:200])
        await br.close()
    if fails:
        print("FEHLER:\n  " + "\n  ".join(fails))
        sys.exit(1)
    print("SMOKE OK")


asyncio.run(main())
