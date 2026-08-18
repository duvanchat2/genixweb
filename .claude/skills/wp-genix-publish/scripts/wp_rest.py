#!/usr/bin/env python3
"""Cliente REST mínimo de WordPress para publicar páginas HTML en los sitios Genix.

Sólo stdlib. Autenticación por Application Password:

    export WP_SITE="https://academiagenix.com"
    export WP_USER="admin"
    export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"

Comandos:
    whoami
    list-pages [--search TEXTO] [--limit N]
    get-page <id|slug> [--save-content ARCHIVO]
    create-page --file HTML --title T [--slug S] [--status draft] [--template T]
    set-content <id> --file HTML [--status S] [--raw] [--allow-shrink]
    set-status <id> --status publish|draft|pending|private
    set-template <id> --template elementor_canvas|elementor_header_footer|elementor_theme|""
    apply-theme-fix <id> [--full-bleed] [--hide-title]
    upload-media ARCHIVO [--title T] [--alt A]
    verify <id> --file HTML
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BLOCK_OPEN = "<!-- wp:html -->"
BLOCK_CLOSE = "<!-- /wp:html -->"
FIX_START = "<!-- wp-genix-publish:theme-fix start -->"
FIX_END = "<!-- wp-genix-publish:theme-fix end -->"


class WPError(RuntimeError):
    pass


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise WPError(f"Falta la variable de entorno {name}. Ver el paso 5 de la skill.")
    return value


def site() -> str:
    return env("WP_SITE").rstrip("/")


def auth_header() -> str:
    user = env("WP_USER")
    # Las Application Passwords se muestran con espacios; WordPress los ignora.
    password = env("WP_APP_PASSWORD").replace(" ", "")
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request(method: str, route: str, *, params=None, body=None, headers=None, raw_body=None):
    """Llama la REST API. Cae a ?rest_route= si /wp-json no está enrutado."""
    base = site()  # valida WP_SITE antes que las credenciales
    params = dict(params or {})
    headers = dict(headers or {})
    headers.setdefault("Authorization", auth_header())
    headers.setdefault("Accept", "application/json")
    headers.setdefault("User-Agent", "wp-genix-publish/1.0")

    payload = raw_body
    if body is not None:
        payload = json.dumps(body).encode()
        headers.setdefault("Content-Type", "application/json")

    for style in ("pretty", "query"):
        if style == "pretty":
            url = f"{base}/wp-json{route}"
            query = params
        else:
            url = f"{base}/"
            query = dict(params, rest_route=route)
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"

        req = urllib.request.Request(url, data=payload, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                text = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", "replace")
            if exc.code == 404 and style == "pretty" and "rest_no_route" not in text:
                continue  # puede ser permalinks simples: reintenta con ?rest_route=
            raise WPError(_explain(exc.code, text, url)) from None
        except urllib.error.URLError as exc:
            raise WPError(f"No se pudo conectar con {url}: {exc.reason}") from None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            snippet = text.strip()[:300]
            raise WPError(
                f"{url} no devolvió JSON. ¿Un plugin de seguridad o un proxy está "
                f"interceptando la REST API?\nRespuesta: {snippet}"
            ) from None
    raise WPError(f"No se encontró la ruta REST {route}")


def _explain(code: int, text: str, url: str) -> str:
    try:
        detail = json.loads(text).get("message", text)
    except json.JSONDecodeError:
        detail = text.strip()[:300]
    hints = {
        401: "Credenciales rechazadas: revisa WP_USER y WP_APP_PASSWORD.",
        403: "Prohibido: falta permiso, o un plugin de seguridad bloquea la REST API.",
        404: "No existe esa página/ruta.",
        413: "El archivo es demasiado grande para el límite de subida del servidor.",
    }
    hint = hints.get(code, "")
    return f"HTTP {code} en {url}\n{detail}\n{hint}\nMás en references/troubleshooting.md"


# ---------------------------------------------------------------- contenido

def wrap(html: str) -> str:
    """Envuelve el HTML en un bloque Custom HTML para que wpautop no lo toque."""
    html = html.strip()
    if html.startswith(BLOCK_OPEN):
        return html
    return f"{BLOCK_OPEN}\n{html}\n{BLOCK_CLOSE}"


def unwrap(content: str) -> str:
    content = content.strip()
    if content.startswith(BLOCK_OPEN) and content.endswith(BLOCK_CLOSE):
        content = content[len(BLOCK_OPEN):-len(BLOCK_CLOSE)]
    return content.strip()


def strip_fix(content: str) -> str:
    return re.sub(
        re.escape(FIX_START) + r".*?" + re.escape(FIX_END),
        "",
        content,
        flags=re.DOTALL,
    ).strip()


def normalize(html: str) -> str:
    """Normaliza para comparar: quita envoltorio, bloque de fix y espacios."""
    return re.sub(r"\s+", " ", strip_fix(unwrap(html))).strip()


def read_html(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


# ------------------------------------------------------------------ páginas

def find_page(ref: str) -> dict:
    if str(ref).isdigit():
        return request("GET", f"/wp/v2/pages/{ref}", params={"context": "edit"})
    pages = request(
        "GET", "/wp/v2/pages",
        params={"slug": ref, "status": "any", "context": "edit", "per_page": 5},
    )
    if not pages:
        raise WPError(f"No hay ninguna página con slug '{ref}' en {site()}")
    return pages[0]


def describe(page: dict) -> dict:
    content = page.get("content", {}).get("raw", "") or page.get("content", {}).get("rendered", "")
    meta = page.get("meta") or {}
    rendered = (page.get("content") or {}).get("rendered", "") or ""
    # `_elementor_edit_mode` es meta protegida y a menudo no viaja por REST, así que
    # esto es una heurística: confírmalo en el editor antes de dar por hecho que no.
    elementor = (
        str(meta.get("_elementor_edit_mode", "")) == "builder"
        or "elementor-element" in rendered
    )
    return {
        "id": page.get("id"),
        "title": (page.get("title") or {}).get("raw") or (page.get("title") or {}).get("rendered"),
        "slug": page.get("slug"),
        "status": page.get("status"),
        "link": page.get("link"),
        "template": page.get("template") or "(por defecto del tema)",
        "modified_gmt": page.get("modified_gmt"),
        "content_chars": len(content),
        "has_style_tag": "<style" in content.lower(),
        "wrapped_in_html_block": content.strip().startswith(BLOCK_OPEN),
        "has_theme_fix": FIX_START in content,
        "built_with_elementor_probable": elementor,
        "preview": f"{site()}/?page_id={page.get('id')}&preview=true",
    }


def write_page(page_id, fields: dict) -> dict:
    return request("POST", f"/wp/v2/pages/{page_id}", body=fields, params={"context": "edit"})


# ------------------------------------------------------------------ comandos

def cmd_whoami(args):
    me = request("GET", "/wp/v2/users/me", params={"context": "edit"})
    caps = me.get("capabilities") or {}
    unfiltered = bool(caps.get("unfiltered_html"))
    out = {
        "site": site(),
        "user": me.get("slug"),
        "name": me.get("name"),
        "roles": me.get("roles"),
        "unfiltered_html": unfiltered,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if not unfiltered:
        print(
            "\nAVISO: este usuario NO tiene unfiltered_html. WordPress borrará <style> y "
            "<script> al guardar. Ver references/troubleshooting.md antes de subir.",
            file=sys.stderr,
        )


def cmd_list_pages(args):
    params = {"context": "edit", "status": "any", "per_page": args.limit, "orderby": "modified"}
    if args.search:
        params["search"] = args.search
    for page in request("GET", "/wp/v2/pages", params=params):
        info = describe(page)
        print(f"{info['id']:>6}  {info['status']:<8} {info['slug']:<40} {info['link']}")


def cmd_get_page(args):
    page = find_page(args.page)
    print(json.dumps(describe(page), indent=2, ensure_ascii=False))
    if args.save_content:
        content = page.get("content", {}).get("raw", "")
        with open(args.save_content, "w", encoding="utf-8") as handle:
            handle.write(content)
        print(f"\nRespaldo guardado en {args.save_content} ({len(content)} caracteres)")


def cmd_create_page(args):
    html = read_html(args.file)
    fields = {
        "title": args.title,
        "content": html if args.raw else wrap(html),
        "status": args.status,
    }
    if args.slug:
        fields["slug"] = args.slug
    if args.template:
        fields["template"] = args.template
    page = request("POST", "/wp/v2/pages", body=fields, params={"context": "edit"})
    print(json.dumps(describe(page), indent=2, ensure_ascii=False))


def cmd_set_content(args):
    page = find_page(args.page)
    current = page.get("content", {}).get("raw", "") or ""
    html = read_html(args.file)
    if not html.strip():
        raise WPError("El archivo está vacío. Me niego a borrar el contenido de la página.")

    new_body = html if args.raw else wrap(html)
    if len(normalize(new_body)) < len(normalize(current)) * 0.5 and current.strip():
        if not args.allow_shrink:
            raise WPError(
                f"El contenido nuevo ({len(normalize(new_body))} chars) es menos de la mitad "
                f"del actual ({len(normalize(current))} chars). Haz un respaldo con "
                f"`get-page {page['id']} --save-content backup.html`, confirma con el usuario "
                f"y repite con --allow-shrink si es intencional."
            )

    # conserva el bloque de arreglo de tema si ya existía
    fix = re.search(re.escape(FIX_START) + r".*?" + re.escape(FIX_END), current, re.DOTALL)
    if fix and FIX_START not in new_body:
        new_body = insert_fix(new_body, fix.group(0))

    fields = {"content": new_body}
    if args.status:
        fields["status"] = args.status
    updated = write_page(page["id"], fields)
    print(json.dumps(describe(updated), indent=2, ensure_ascii=False))
    _report_verification(updated, html)


def cmd_set_status(args):
    page = find_page(args.page)
    updated = write_page(page["id"], {"status": args.status})
    print(json.dumps(describe(updated), indent=2, ensure_ascii=False))


def cmd_set_template(args):
    page = find_page(args.page)
    updated = write_page(page["id"], {"template": args.template})
    print(json.dumps(describe(updated), indent=2, ensure_ascii=False))


def build_fix_block(page_id, full_bleed: bool, hide_title: bool) -> str:
    rules = []
    if full_bleed:
        rules.append(
            f"body.page-id-{page_id} .site-main,\n"
            f"body.page-id-{page_id} .page-content,\n"
            f"body.page-id-{page_id} .entry-content,\n"
            f"body.page-id-{page_id} main,\n"
            f"body.page-id-{page_id} article,\n"
            f"body.page-id-{page_id} .container {{\n"
            "  max-width: 100% !important;\n"
            "  width: 100% !important;\n"
            "  padding-left: 0 !important;\n"
            "  padding-right: 0 !important;\n"
            "  margin-left: 0 !important;\n"
            "  margin-right: 0 !important;\n"
            "}"
        )
    if hide_title:
        rules.append(
            f"body.page-id-{page_id} .page-header,\n"
            f"body.page-id-{page_id} .entry-header,\n"
            f"body.page-id-{page_id} .entry-title {{ display: none !important; }}"
        )
    return f"{FIX_START}\n<style>\n" + "\n".join(rules) + f"\n</style>\n{FIX_END}"


def insert_fix(content: str, block: str) -> str:
    """Inserta o reemplaza el bloque de arreglo. Idempotente: nunca lo duplica."""
    if FIX_START in content:
        return re.sub(
            re.escape(FIX_START) + r".*?" + re.escape(FIX_END),
            lambda _: block, content, flags=re.DOTALL,
        )
    if content.rstrip().endswith(BLOCK_CLOSE):
        return content.rstrip()[: -len(BLOCK_CLOSE)].rstrip() + f"\n{block}\n{BLOCK_CLOSE}"
    return f"{content}\n{block}".strip()


def cmd_apply_theme_fix(args):
    if not (args.full_bleed or args.hide_title):
        raise WPError("Indica al menos --full-bleed o --hide-title.")
    page = find_page(args.page)
    page_id = page["id"]
    block = build_fix_block(page_id, args.full_bleed, args.hide_title)
    content = insert_fix(page.get("content", {}).get("raw", "") or "", block)

    updated = write_page(page_id, {"content": content})
    info = describe(updated)
    print(json.dumps(info, indent=2, ensure_ascii=False))
    if not info["has_theme_fix"]:
        raise WPError(
            "El bloque de arreglo no quedó guardado: KSES borró el <style>. "
            "Revisa `whoami` → unfiltered_html. Ver references/troubleshooting.md"
        )
    print("\nAhora abre la URL pública y comprueba el resultado renderizado, no el editor.")


def cmd_upload_media(args):
    path = args.file
    if not os.path.isfile(path):
        raise WPError(f"No existe el archivo {path}")
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    filename = os.path.basename(path)
    with open(path, "rb") as handle:
        data = handle.read()
    media = request(
        "POST", "/wp/v2/media",
        raw_body=data,
        headers={
            "Content-Type": mime,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
    fields = {}
    if args.title:
        fields["title"] = args.title
    if args.alt:
        fields["alt_text"] = args.alt
    if fields:
        media = request("POST", f"/wp/v2/media/{media['id']}", body=fields)
    print(json.dumps(
        {"id": media["id"], "source_url": media["source_url"], "mime_type": media.get("mime_type")},
        indent=2, ensure_ascii=False,
    ))
    print("\nUsa source_url (absoluta) en el HTML. No dejes rutas locales ni data: URIs.")


def _report_verification(page: dict, expected_html: str) -> bool:
    stored = page.get("content", {}).get("raw", "") or ""
    want, got = normalize(expected_html), normalize(stored)
    if want == got:
        print("\nOK: el contenido almacenado coincide con el archivo.")
        return True
    print("\nDIFERENCIAS entre el archivo y lo que WordPress guardó:", file=sys.stderr)
    print(f"  archivo: {len(want)} chars | guardado: {len(got)} chars", file=sys.stderr)
    for tag in ("<style", "<script", "<iframe", "<svg", "onclick"):
        if tag in want.lower() and tag not in got.lower():
            print(f"  falta {tag} → KSES lo borró (ver troubleshooting.md)", file=sys.stderr)
    if len(got) < len(want):
        print("  el contenido guardado es más corto: probable filtrado o guardado parcial.",
              file=sys.stderr)
    return False


def cmd_verify(args):
    page = find_page(args.page)
    print(json.dumps(describe(page), indent=2, ensure_ascii=False))
    ok = _report_verification(page, read_html(args.file))
    if not ok:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami").set_defaults(func=cmd_whoami)

    p = sub.add_parser("list-pages")
    p.add_argument("--search")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list_pages)

    p = sub.add_parser("get-page")
    p.add_argument("page")
    p.add_argument("--save-content")
    p.set_defaults(func=cmd_get_page)

    p = sub.add_parser("create-page")
    p.add_argument("--file", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--slug")
    p.add_argument("--status", default="draft")
    p.add_argument("--template")
    p.add_argument("--raw", action="store_true", help="no envolver en bloque wp:html")
    p.set_defaults(func=cmd_create_page)

    p = sub.add_parser("set-content")
    p.add_argument("page")
    p.add_argument("--file", required=True)
    p.add_argument("--status")
    p.add_argument("--raw", action="store_true")
    p.add_argument("--allow-shrink", action="store_true")
    p.set_defaults(func=cmd_set_content)

    p = sub.add_parser("set-status")
    p.add_argument("page")
    p.add_argument("--status", required=True,
                   choices=["draft", "publish", "pending", "private"])
    p.set_defaults(func=cmd_set_status)

    p = sub.add_parser("set-template")
    p.add_argument("page")
    p.add_argument("--template", required=True)
    p.set_defaults(func=cmd_set_template)

    p = sub.add_parser("apply-theme-fix")
    p.add_argument("page")
    p.add_argument("--full-bleed", action="store_true")
    p.add_argument("--hide-title", action="store_true")
    p.set_defaults(func=cmd_apply_theme_fix)

    p = sub.add_parser("upload-media")
    p.add_argument("file")
    p.add_argument("--title")
    p.add_argument("--alt")
    p.set_defaults(func=cmd_upload_media)

    p = sub.add_parser("verify")
    p.add_argument("page")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    try:
        args.func(args)
    except WPError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
