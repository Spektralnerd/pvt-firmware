#!/usr/bin/env python3
"""Baut den PVT Firmware-Baukasten aus den Quellen in src/ zu einer einzigen HTML-Datei.

    python3 build.py            -> dist/PVT_Firmware_Baukasten.html (eigenstaendig, offline)
    python3 build.py --artefakt -> dist/pvt_firmware_baukasten_artefakt.html (Variante fuer claude.ai-Artefakte:
                                   ohne <html>/<head>-Geruest, mit dem Artefakt-Viewport-Hinweis)

Reihenfolge: page_head.html, page_body.html, <script>core.js (mit eingesetzter Differenz aus delta.js)</script>,
<script>ui.js</script>. Es gibt keine Abhaengigkeiten; die Datei laeuft in jedem aktuellen Browser per Doppelklick.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
DIST = os.path.join(HERE, "dist")


def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return f.read()


def core_full():
    core, delta = read("core.js"), read("delta.js")
    assert core.count("/*DELTA*/") == 1, "core.js braucht genau eine /*DELTA*/-Marke"
    return core.replace("/*DELTA*/", delta)


def assemble(artefakt=False):
    head, body = read("page_head.html"), read("page_body.html")
    scripts = "<script>\n" + core_full() + "\n</script>\n<script>\n" + read("ui.js") + "\n</script>\n"
    if artefakt:
        return head + body + scripts
    head = head.replace(
        "<title>",
        '<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<title>', 1)
    head = head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    head = head.replace("</style>\n", "</style>\n<style>img{max-width:100%}[hidden]{display:none!important}body{margin:0}</style>\n</head>\n<body>\n", 1)
    return head + body + scripts + "</body>\n</html>\n"


def main():
    os.makedirs(DIST, exist_ok=True)
    artefakt = "--artefakt" in sys.argv
    out = os.path.join(DIST, "pvt_firmware_baukasten_artefakt.html" if artefakt else "PVT_Firmware_Baukasten.html")
    html = assemble(artefakt)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("geschrieben:", out, "(%d Byte)" % len(html.encode("utf-8")))


if __name__ == "__main__":
    main()
