#!/usr/bin/env python3
"""Extrae a archivos las imágenes que el usuario pegó en el chat de Claude Code.

Una imagen pegada en la conversación vive como base64 dentro del transcript JSONL de la
sesión (`~/.claude/projects/<proyecto>/<sesion>.jsonl`), no como archivo en disco.

    python3 scripts/extract_pasted_images.py --list
    python3 scripts/extract_pasted_images.py --out-dir /ruta/img [--limit 5]

Las imágenes salen numeradas de más reciente a más antigua: `pasted-1.png` es la última
que pegó el usuario. Confirma con él cuál es si hay varias.
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import sys

EXTENSIONS = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg",
    "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg",
}


def transcripts(explicit: str | None):
    if explicit:
        return [explicit]
    root = os.path.expanduser("~/.claude/projects")
    files = glob.glob(os.path.join(root, "*", "*.jsonl"))
    return sorted(files, key=os.path.getmtime, reverse=True)


def walk(node):
    """Devuelve los bloques de imagen base64 que haya en cualquier nivel del JSON."""
    if isinstance(node, dict):
        source = node.get("source")
        if node.get("type") == "image" and isinstance(source, dict) and source.get("data"):
            yield source
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def collect(paths):
    found = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                for line_no, line in enumerate(handle, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    for source in walk(entry):
                        found.append({
                            "transcript": path,
                            "line": line_no,
                            "media_type": source.get("media_type", "image/png"),
                            "data": source["data"],
                            "timestamp": entry.get("timestamp", ""),
                        })
        except OSError as exc:
            print(f"No se pudo leer {path}: {exc}", file=sys.stderr)
    found.reverse()  # más reciente primero
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=".")
    parser.add_argument("--transcript", help="ruta a un .jsonl concreto")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--list", action="store_true", help="sólo listar, sin escribir")
    args = parser.parse_args()

    images = collect(transcripts(args.transcript))[: args.limit]
    if not images:
        print("No hay imágenes pegadas en el transcript de esta sesión.\n"
              "Si el usuario adjuntó un archivo en vez de pegarlo, úsalo directamente.")
        return 1

    if not args.list:
        os.makedirs(args.out_dir, exist_ok=True)

    for index, image in enumerate(images, 1):
        extension = EXTENSIONS.get(image["media_type"], ".bin")
        size = len(image["data"]) * 3 // 4
        name = f"pasted-{index}{extension}"
        if args.list:
            print(f"{name}  {image['media_type']}  ~{size // 1024} KB  "
                  f"{image['timestamp']}  ({os.path.basename(image['transcript'])}:{image['line']})")
            continue
        destination = os.path.join(args.out_dir, name)
        with open(destination, "wb") as handle:
            handle.write(base64.b64decode(image["data"]))
        print(f"{destination}  {image['media_type']}  {os.path.getsize(destination) // 1024} KB "
              f" {image['timestamp']}")

    if not args.list:
        print("\n`pasted-1` es la más reciente. Confirma con el usuario cuál usar y súbela con "
              "`wp_rest.py upload-media`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
