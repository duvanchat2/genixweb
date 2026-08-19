---
name: wp-genix-publish
description: |
  Publish a standalone HTML page (exported from Claude Design / "Diseña con Claude") as a
  WordPress page on one of Duvan's Genix sites (genixacademy.com, academiagenix.com,
  triunfagenix.com, miraveoptica.com, productosdigitales.genixacademy.com,
  email.triunfagenix.com). Use whenever the user says things like "sube esto a WordPress",
  "publica esta página en Genix", "esto lo hice en Claude Design, súbelo", or pastes/attaches
  an exported HTML file plus asks it to go live. Covers: reaching wp-admin via Hostinger SSO
  (no password needed), extracting a pasted chat image to a real file, uploading media via
  the REST API (the browser file-upload tool is unreliable here), safely writing raw HTML
  into a WordPress page without wpautop corrupting it, and the Hello Elementor "boxed
  container" full-bleed fix. Do not use for building the design itself — only for taking an
  already-finished HTML export and getting it live on WordPress.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - AskUserQuestion
---

# Publishing a Claude-Design HTML page to Genix WordPress

This skill documents a working, battle-tested procedure. Every gotcha below was hit for real
in a live session — don't skip them, they are not theoretical.

## 0. Prerequisites — what you need from the user

- The exported HTML file (usually in `Downloads`, e.g. `*-wordpress.html`). Read it fully
  with `Read` before touching it.
- Which site it goes on. If not stated, ask — don't assume `genixacademy.com`. Known sites
  (from Hostinger hPanel → Sitios web):
  - `genixacademy.com` (main site)
  - `academiagenix.com`
  - `triunfagenix.com`
  - `miraveoptica.com`
  - `productosdigitales.genixacademy.com`
  - `email.triunfagenix.com`
- Any real destination links that should replace placeholders (payment links, CTAs).
- Any image the design references but doesn't embed. If the user pasted it directly in the
  chat (not as a file), see §2.

## 1. Get browser access to wp-admin (no password needed)

Duvan is logged into Hostinger in his real Chrome (via claude-in-chrome). Do **not** ask for
credentials — just drive the browser:

1. `navigate` to `https://hpanel.hostinger.com` (or reuse an existing tab) — session is
   already authenticated as user "genix".
2. Go to **Sitios web** in the left nav.
3. Find the target site's row and click **Admin WordPress**. This opens a **new tab** with an
   SSO link straight into `/wp-admin` — no login prompt. Grab that tab's `tabId` from the
   `tabs_context_mcp` response.
4. If you ever see a real password field, stop and tell the user — SSO should always work for
   these sites.

## 2. If the design references a pasted-in-chat image

The user often pastes a photo directly into the chat instead of giving a file path. That image
is NOT on disk by default, but it IS embedded as base64 in this session's transcript. Extract it:

```python
import json, base64, os
path = r'<this session's .jsonl under ~/.claude/projects/.../SESSION_ID.jsonl>'
with open(path, encoding='utf-8') as f:
    lines = f.readlines()
for line in lines:
    if '"type": "image"' in line.replace(' ', '') or ('"type":"image"' in line and 'base64' in line):
        obj = json.loads(line)
        # walk obj recursively looking for {"type":"image","source":{"type":"base64",...}}
        # the LAST user-role message with an image block is almost always the one just pasted
```
Find the block belonging to a `role: "user"` message near the end of the file (not older
screenshots from earlier in the session), decode it, `Read` it back as an image to confirm
it's the right one, then use it in §4. Give it a descriptive filename (e.g.
`terremoto-colombia-defensa-civil.jpg`), not a generic one — a WordPress REST upload with a
generic/mismatched name has been flaky in this environment for unclear reasons; a specific
slug-style name has always worked.

## 3. Prepare the HTML

Full exported files look like `<!doctype html><html><head>...<style>...</style></head>
<body>...<script>...</script></body></html>`.

You do **not** paste the whole document into WordPress. Strip the outer wrapper and keep only:
`<link>` font tags + `<style>...</style>` + everything inside `<body>` + the trailing
`<script>...</script>`. Do this with a small Python/Bash slice on line ranges, not by hand —
it's long and easy to mis-copy.

Apply any requested edits to the **source file first** (Edit tool), then re-extract, so the
extracted content and the source file never drift:
- Swap placeholder CTA links for the real payment/destination link — check for **every**
  occurrence (`grep -n "href="`), including any duplicate mentions in plain text like
  "seguro vía X" that name the old provider.
- Replace image placeholders with a real `<img src="...">` once you know the final media URL
  (see §4 — you'll know the URL before you even upload, since WP media URLs are
  predictable: `https://SITE/wp-content/uploads/YYYY/MM/filename.ext`).

## 4. Upload the image via the REST API — not the browser file-upload tool

`mcp__claude-in-chrome__file_upload` is unreliable in this environment: real, existing file
paths intermittently fail with a bogus `paths: expected array, received undefined` schema
error that has nothing to do with the actual input (confirmed reproducible — it's specific to
this tool/harness combo, not your JSON). Don't burn time debugging it. Use the REST API
instead:

1. In wp-admin, go to **Perfil** (`/wp-admin/profile.php`), scroll to **Contraseñas de
   aplicación**, type a throwaway name (e.g. `claude-upload-temp`), click **Añadir nueva
   contraseña de aplicación**.
2. Read the generated password precisely — zoom the screenshot on that exact row, don't guess
   from a blurry read. If unsure, revoke and generate a fresh one rather than retry-guessing.
3. Upload with curl (username is `admin` unless `wp-admin/users.php` shows otherwise — check,
   don't assume):

```bash
curl -s -u "admin:XXXX XXXX XXXX XXXX XXXX XXXX" \
  -X POST "https://SITE/wp-json/wp/v2/media" \
  -H "Content-Disposition: attachment; filename=descriptive-name.jpg" \
  -H "Content-Type: image/jpeg" \
  --data-binary @"/path/to/file.jpg" \
  -o response.json -w "HTTP_STATUS:%{http_code}\n"
```
A 201 means success; `response.json`'s `source_url` is the final image URL — use it in your
`<img>` tag (it will match the predictable path from §3).

4. **After you're done with the whole task**, go back to Perfil and click **Anular** on the
   throwaway application password (or **Anular todas**). Don't leave standing credentials.

## 5. Write the content into the WordPress page — the safe way

Create the page: `/wp-admin/post-new.php?post_type=page`. Type the title in the title field
normally (click + type is fine there — it's a plain textbox).

For the **body**, do NOT type character-by-character with the `computer` tool for anything
over a couple hundred characters — it's slow and, worse, has caused stray leftover characters
in past runs. Also don't blindly trust `ctrl+a` / `Backspace` combos on Gutenberg blocks —
one wrong Backspace on an empty paragraph block can cascade and wipe the entire page content
(happened in this exact workflow; recovered with `ctrl+z`, do that immediately if it happens,
don't try to "fix forward").

The reliable method:

1. Switch to the **whole-document raw code editor**: click the "⋮ Opciones" menu → **Editor
   de código** (or press `Ctrl+Shift+Alt+M` after clicking into the page body first so focus
   is on the document, not a floating menu). Confirm you're in it by checking
   `document.querySelectorAll('textarea').length === 2` via `javascript_tool` (index 0 =
   title, index 1 = body).
2. Set the body textarea's value via JS using the native setter trick, so React/Gutenberg
   picks up the change as if the user typed it:

```js
const ta = document.querySelectorAll('textarea')[1];
const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
nativeSetter.call(ta, YOUR_FULL_CONTENT_STRING);
ta.dispatchEvent(new Event('input', { bubbles: true }));
```
   This is the same trick used to fix stray characters later — same tool, same safety
   profile: it's editing a legitimate content field the user asked you to fill, not a
   restricted target, so it isn't blocked and it isn't a hack around anything.
3. Click **Guardar** (or **Publicar** on a fresh draft) via its `ref` from `find`, then
   **verify the save actually happened** by checking network requests:
   `read_network_requests` filtered on `pages/<ID>` — you want a 200 on
   `wp-json/wp/v2/pages/<ID>?_locale=user` (the real save), not just
   `.../pages/<ID>/autosaves` (autosave only, page stays stale). A single click sometimes
   only fires the autosave — click again and re-check if you only see the autosave request.
4. Load the live/preview URL and re-verify with `javascript_tool` (link counts, absence of
   stray text nodes, title) rather than trusting a screenshot alone — screenshots in this
   browser occasionally return a stale/cropped frame or the CDP call times out.

## 6. Known WordPress/theme gotchas to always check

**wpautop mangles raw HTML/CSS edits that create a blank line.** WordPress's `wpautop` filter
runs on page content and inserts `<p>`/`</p>` around anything that looks like a paragraph
break (blank line). If you inject a CSS fix into an existing `<style>` block later (e.g. via
the same JS-setter trick, inserting text before `</style>`), do **not** wrap it in a
leading/trailing newline — that creates the blank-line pattern and wpautop will splice literal
`</p>`/`<p>` text into the middle of your CSS, silently breaking just that rule (the browser's
CSS parser drops the malformed rule; nothing else warns you). Insert single-line, no
surrounding blank line — appended directly after the last rule's `}` with nothing but the new
rule and its own `}` before `</style>`. After any such edit, re-fetch the live page and check
`getComputedStyle` on the affected element rather than trusting that "it's in the `<style>`
tag now" means it applied.

**Hello Elementor / Elementor theme boxes page content to `max-width:1140px`.** A full-bleed
design (edge-to-edge colored sections, sticky navbar) will look "squeezed with margins" on
both desktop and mobile until you break out of it. Fix (add to the page's own `<style>`
block, single line per rule per the wpautop note above):
```css
.navbar,.hero,section.section,footer{width:100vw;margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw)}
body.wp-singular .site-main,body.wp-singular main{max-width:none!important;margin:0!important;padding:0!important}
```
Inner content wrappers (e.g. `.wrap` at ~760px, centered) stay as designed — only the
section-level background containers need to go full width.

**The theme's own gray page-title header (`.page-header` / `h1.entry-title`) shows above your
design** and looks out of place with a custom full-bleed page. Hide it with CSS — **never
change the WP page's actual Title field** to do this, that field drives the URL slug and SEO:
```css
body.page-id-<ID> .page-header{display:none!important;margin:0!important;padding:0!important}
```
Get `<ID>` from the page-id-NNNN class already on `<body>`, or from the `post=` query param
in the editor URL.

**Check every CTA's actual `href`, not just the visible label.** A design often has a "hero"
CTA pointing straight to the destination but secondary CTAs (sticky navbar button, mid-page
repeats) still on a same-page anchor like `href="#donar"`. If the user says a specific button
"doesn't have the link", it usually means exactly this — audit **all** matching buttons:
```js
Array.from(document.querySelectorAll('.navbar a, a.btn')).map(a => ({text:a.textContent.trim(), href:a.getAttribute('href')}))
```

## 7. Before publishing

Publishing a page is publishing public content — get explicit confirmation before flipping a
draft to Publish, per standard rules. If the page already ended up published earlier in the
flow (WordPress's "Guardar" on a page created via `post-new.php` can end up publish-status
depending on prior state — verify with `status` in the REST response or the button label:
"Guardar" = already published, "Publicar" = still a draft), say so plainly rather than
re-asking permission for something already live, and instead confirm the fixes look right.

## 8. Final deliverable

Give the user the clean permalink (e.g. `https://SITE/page-slug/`), not the `?page_id=X&preview=true`
query form, once it's actually published.

---

## 9. Helper scripts bundled with this skill

Added alongside the procedure above. They automate the fiddly steps; the browser procedure
stays the source of truth.

| Script | Reemplaza / automatiza |
|---|---|
| `scripts/extract_pasted_images.py --list` | §2 — recorre el transcript y escribe a archivo cada imagen pegada, la más reciente primero. Úsalo en vez de escribir a mano el recorrido del JSON. |
| `scripts/wp_rest.py upload-media <archivo>` | §4 — el mismo `curl`, con la Application Password leída del entorno y el `source_url` impreso. |
| `scripts/check_ctas.py page.html` | §6 — audita **todos** los `<a>` del HTML exportado antes de subir, agrupados por destino, y sale con código 1 si hay `#`, vacíos o placeholders. Hace en local lo que el snippet de `javascript_tool` hace en vivo. |
| `scripts/wp_rest.py verify <id> --file page.html` | §5.3 — compara lo que WordPress guardó de verdad contra tu archivo. Detecta el autoguardado que no se aplicó y el `<style>` que KSES borró. |

Variables de entorno: `WP_SITE`, `WP_USER`, `WP_APP_PASSWORD`. Nunca las escribas en un
archivo del repo.

### Camino alternativo, 100% REST (sin probar en vivo)

`wp_rest.py create-page` / `set-content` escriben el contenido por la REST API en vez de
manejar el editor de código en el navegador, envolviéndolo en un bloque `<!-- wp:html -->`
que desactiva `wpautop` en origen en vez de esquivarlo.

**No tiene historial de uso real.** El procedimiento por navegador de §1–§8 es el que ya
funcionó. Si usas el camino REST, verifica siempre con `verify` y con la página en vivo.

### Referencias

`references/sitios.md` · `references/theme-fixes.md` · `references/rest-api.md` ·
`references/troubleshooting.md`
