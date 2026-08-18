#!/usr/bin/env python3
"""Audita TODOS los enlaces de un HTML antes de publicarlo.

    python3 scripts/check_ctas.py page.html [--site https://academiagenix.com]

Agrupa los enlaces por destino y marca los que están rotos o sin terminar. Sale con
código 1 si encuentra alguno, para que no se publique sin querer.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from html.parser import HTMLParser

PLACEHOLDER_PATTERNS = [
    (re.compile(r"^\s*$"), "href vacío"),
    (re.compile(r"^#$"), "href='#' (sin destino)"),
    (re.compile(r"^javascript:", re.I), "javascript: (no navega)"),
    (re.compile(r"example\.(com|org)", re.I), "dominio de ejemplo"),
    (re.compile(r"(tu[-_]?link|your[-_]?link|link[-_]?aqui|url[-_]?aqui|todo|xxx+|lorem)", re.I),
     "placeholder sin reemplazar"),
    (re.compile(r"^https?://localhost|^https?://127\.0\.0\.1|^file://", re.I), "URL local"),
]

CTA_HINTS = re.compile(
    r"(compr|inscrib|unir|empez|acceso|acceder|quiero|reserv|agend|descarg|checkout|"
    r"suscri|apunt|entrar|obtener|pagar|whatsapp)", re.I)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []          # (href, texto, clases)
        self.forms = []
        self._stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self._stack.append({"href": attrs.get("href", ""),
                                "class": attrs.get("class", ""),
                                "text": []})
        elif tag == "form":
            self.forms.append(attrs.get("action", ""))

    def handle_data(self, data):
        if self._stack:
            self._stack[-1]["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._stack:
            link = self._stack.pop()
            self.links.append((link["href"], " ".join(link["text"]).strip(), link["class"]))


def classify(href: str, site: str | None):
    for pattern, reason in PLACEHOLDER_PATTERNS:
        if pattern.search(href):
            return "ROTO", reason
    if href.startswith("#"):
        return "OK", "ancla interna"
    if href.startswith(("mailto:", "tel:")):
        return "OK", "contacto"
    if href.startswith("http://"):
        return "AVISO", "http:// en un sitio HTTPS → contenido mixto"
    if href.startswith("/"):
        return "AVISO", "ruta relativa: verifica que exista en el sitio destino"
    if href.startswith("https://"):
        return "OK", ""
    return "AVISO", "destino no reconocido"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file")
    parser.add_argument("--site", help="dominio destino, para avisar de rutas relativas")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as handle:
        html = handle.read()

    parser_ = LinkParser()
    parser_.feed(html)

    if not parser_.links:
        print("No se encontró ningún <a> en el archivo. ¿Es el HTML correcto?")
        return 1

    grouped: "OrderedDict[str, list]" = OrderedDict()
    for href, text, css in parser_.links:
        grouped.setdefault(href, []).append((text, css))

    broken, warnings = [], []
    print(f"{len(parser_.links)} enlaces, {len(grouped)} destinos distintos\n")
    for href, uses in grouped.items():
        status, reason = classify(href, args.site)
        marker = {"OK": "  ok ", "AVISO": " !! ", "ROTO": "FALLA"}[status]
        shown = href if href.strip() else "(vacío)"
        print(f"{marker} {shown}   ×{len(uses)}" + (f"   [{reason}]" if reason else ""))
        for text, css in uses[:6]:
            label = " ".join(text.split())[:70] or "(sin texto)"
            flag = " ←CTA" if CTA_HINTS.search(text) or CTA_HINTS.search(css) else ""
            print(f"        · {label}{flag}")
        if len(uses) > 6:
            print(f"        · … y {len(uses) - 6} más")
        if status == "ROTO":
            broken.append((href, reason, len(uses)))
        elif status == "AVISO":
            warnings.append((href, reason, len(uses)))

    for action in parser_.forms:
        status, reason = classify(action, args.site)
        print(f"\n<form action=\"{action or '(vacío)'}\">  {status} {reason}")
        if status == "ROTO":
            broken.append((action or "(form vacío)", reason, 1))

    print()
    if broken:
        print(f"{len(broken)} destino(s) SIN LINK REAL — pide al usuario la URL correcta "
              f"antes de publicar:", file=sys.stderr)
        for href, reason, count in broken:
            print(f"  - {href or '(vacío)'} ({count} botón/es): {reason}", file=sys.stderr)
        return 1
    if warnings:
        print(f"{len(warnings)} aviso(s) para revisar, ningún link roto.")
    else:
        print("Todos los enlaces apuntan a un destino real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
