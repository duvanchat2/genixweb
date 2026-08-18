---
name: wp-genix-publish
description: Publish a standalone HTML page (exported from Claude Design / "Diseña con Claude") as a WordPress page on one of Duvan's Genix sites (genixacademy.com, academiagenix.com, triunfagenix.com, miraveoptica.com, productosdigitales.genixacademy.com, email.triunfagenix.com). Use whenever the user says things like "sube esto a WordPress", "publica esta página en Genix", "esto lo hice en Claude Design, súbelo", "ponlo en vivo", "súbelo a la web", or pastes/attaches an exported HTML file plus asks for it to go live. Covers reaching wp-admin via Hostinger SSO (no password needed), extracting a pasted chat image to a real file, uploading media via the WordPress REST API (the browser file-upload tool is unreliable here), safely writing raw HTML into a page without wpautop corrupting the CSS, the Hello Elementor "boxed container" full-bleed fix, hiding the theme title without breaking the slug/SEO, auditing every CTA link, and verifying the save actually landed. Do NOT use for building the design itself — only for taking an already-finished HTML export and getting it live on WordPress.
---

# Publicar una página HTML en WordPress (sitios Genix)

Toma un HTML ya terminado (normalmente exportado de Claude Design) y lo deja publicado
en el sitio WordPress correcto, sin romper el CSS y sin romper el SEO.

**Habla con el usuario en español.** Las instrucciones de abajo son para ti; los mensajes
al usuario van en español, cortos y concretos.

**No rediseñes.** Esta skill no cambia el diseño. Si algo del HTML está roto, dilo y
pregunta — no lo "mejores" por tu cuenta. Las únicas ediciones permitidas sin preguntar
son las de esta guía: rutas de imágenes, links de CTA que el usuario te dio, y el CSS de
arreglo del tema.

## Orden de trabajo

Sigue estos pasos en orden. Cada uno tiene su sección más abajo.

1. Confirmar sitio destino y si es página nueva o reemplazo
2. Dejar el HTML en un archivo local
3. Imágenes: extraer las pegadas en el chat y subirlas por REST
4. Entrar a wp-admin por SSO de Hostinger
5. Conseguir credenciales REST (Application Password)
6. Escribir el HTML en la página sin que wpautop lo destroce
7. Arreglos de tema (full-bleed + ocultar título)
8. Auditar todos los CTAs
9. Verificar que el guardado se aplicó de verdad
10. Confirmar con el usuario antes de publicar

---

## 1. Confirmar destino

Antes de tocar nada, ten claro:

- **Qué sitio.** Ver `references/sitios.md`. Si el usuario no lo dijo y hay ambigüedad,
  pregunta con `AskUserQuestion` — no adivines: publicar en el sitio equivocado es visible
  para sus clientes.
- **Página nueva o reemplazo.** Si es reemplazo, pide/confirma la URL exacta o el ID.
- **Slug deseado** si es nueva.

Si la página destino ya existe y fue hecha con Elementor (tiene meta `_elementor_edit_mode`
= `builder`), escribir en `content` por REST **no se verá**: Elementor renderiza su propio
dato. En ese caso crea una página nueva o avísale al usuario antes de continuar.
`scripts/wp_rest.py get-page` te dice si la página tiene datos de Elementor.

## 2. Dejar el HTML en un archivo

Guarda el export en el scratchpad como `page.html`. Trabaja siempre sobre el archivo,
nunca pegando HTML gigante en comandos.

Si el usuario adjuntó el archivo, úsalo tal cual. Si lo pegó en el chat, escríbelo a
archivo primero con un heredoc `<<'EOF'` (comillas simples: evita que bash expanda `$`).

## 3. Imágenes

### 3a. Imágenes pegadas en el chat

Cuando el usuario pega una captura en la conversación, la imagen vive en el transcript de
la sesión como base64, no como archivo. Extráela:

```bash
python3 scripts/extract_pasted_images.py --out-dir "$SCRATCH/img"
```

Lista las que encuentre (más reciente primero) y confirma con el usuario cuál es si hay
varias. `--list` sólo enumera sin escribir archivos.

### 3b. Subirlas a la Biblioteca de Medios

**Usa la REST API, no el selector de archivos del navegador.** El file-picker de la
automatización de navegador falla o se cuelga con el uploader de WP.

```bash
python3 scripts/wp_rest.py upload-media "$SCRATCH/img/hero.png" \
  --title "Hero curso X" --alt "Portada del curso X"
```

Devuelve el `id` y el `source_url`. **Reemplaza en `page.html` todo `src` local, `data:`
URI o URL externa por el `source_url` devuelto.** Una imagen que sigue apuntando a un
archivo local o a un `data:` URI enorme es un fallo: la primera se ve rota, la segunda
infla la fila de la base de datos.

Verifica después de reemplazar que no queden rutas locales:

```bash
grep -nEo 'src="[^"]*"' page.html | grep -vE 'https?://' || echo "OK: sin rutas locales"
```

## 4. Entrar a wp-admin (SSO de Hostinger)

No pidas contraseña de WordPress. La ruta es:

1. Abre `https://hpanel.hostinger.com/` (la sesión de Hostinger del usuario ya suele estar
   activa en el navegador).
2. Ve a la lista de sitios/hosting y elige el dominio correcto.
3. Usa el botón de acceso al panel de WordPress (según la versión de hPanel aparece como
   **Admin Panel**, **Editar sitio web** o **Panel de WordPress**). Ese botón hace login
   automático y te deja dentro de `/wp-admin`.

Si la sesión de Hostinger no está activa, **no intentes adivinar credenciales**: pídele al
usuario que inicie sesión en hPanel y avísale que sigues cuando esté dentro.

Comprueba que estás dentro pidiendo `/wp-admin/` y confirmando que responde el dashboard,
no la pantalla de login.

## 5. Credenciales REST

Los pasos 3b, 6 y 9 usan la REST API. La forma estable de autenticarte es una
**Application Password** (no la contraseña real de la cuenta):

1. En wp-admin: **Usuarios → Perfil** (`/wp-admin/profile.php`).
2. Baja a **Application Passwords**, nombre `claude-publish`, **Add New**.
3. Copia la contraseña generada (formato `xxxx xxxx xxxx xxxx xxxx xxxx`).

Exporta las variables antes de usar los scripts:

```bash
export WP_SITE="https://academiagenix.com"
export WP_USER="<usuario admin>"
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
```

Reglas:
- **Nunca** escribas la Application Password en un archivo del repo, en un commit, ni en
  un mensaje que quede en el historial de GitHub. Sólo en variables de entorno de la sesión.
- Si el usuario prefiere no crear una, existe la ruta alternativa por nonce desde el
  navegador ya logueado — ver `references/rest-api.md`.
- Si la REST API devuelve 401/403 en un sitio, ver `references/troubleshooting.md`.

Prueba rápida de que funciona:

```bash
python3 scripts/wp_rest.py whoami
```

## 6. Escribir el HTML sin que WordPress lo rompa

Este es el paso donde históricamente se rompe todo. Dos mecanismos de WordPress atacan tu
HTML:

**`wpautop`** — convierte saltos de línea dobles en `<p>` y simples en `<br>`. Sobre un
bloque `<style>` multilinea eso mete `<p>`/`<br>` dentro del CSS y **el estilo deja de
aplicar**. Es exactamente el bug que rompió el CSS antes.

**KSES** — si el usuario que guarda no tiene la capability `unfiltered_html`, WordPress
borra `<style>`, `<script>`, `<iframe>` y muchos atributos al guardar. En un WordPress de
sitio único los administradores sí la tienen; en multisitio sólo el super admin.

La solución que funciona: **envolver todo el HTML en un bloque Custom HTML** y guardarlo
por REST. Cuando el contenido tiene bloques, el core de WordPress quita `wpautop` del
filtro `the_content`, así que el CSS sobrevive intacto.

`scripts/wp_rest.py set-content` hace ese envoltorio por ti:

```bash
# Página nueva, siempre en borrador primero
python3 scripts/wp_rest.py create-page --file page.html \
  --title "Curso X" --slug "curso-x" --status draft

# O reemplazar el contenido de una existente
python3 scripts/wp_rest.py set-content 1234 --file page.html --status draft
```

Reglas duras:

- **Siempre `--status draft` en la primera escritura.** Publicar es el paso 10, con
  confirmación del usuario.
- **Nunca edites contenido pegando en el editor del navegador.** Es donde se pierde
  contenido por accidente (selección incompleta, autoguardado a medias).
- **Antes de sobrescribir una página existente, guarda un respaldo:**
  ```bash
  python3 scripts/wp_rest.py get-page 1234 --save-content backup-1234.html
  ```
  Dile al usuario dónde quedó el respaldo. Si algo sale mal, se restaura con
  `set-content 1234 --file backup-1234.html --raw`.
- El script rechaza escribir un contenido vacío o sospechosamente más corto que el
  respaldo salvo que pases `--allow-shrink`. No lo pases sin preguntar.

## 7. Arreglos de tema

Dos arreglos que **siempre** hacen falta en estos sitios (tema Hello Elementor). Los
detalles y el CSS exacto están en `references/theme-fixes.md` — léelo antes de aplicarlos.

**a) Quitar el encajonado de 1140px.** El tema mete el contenido en un contenedor
angosto y el diseño full-bleed se ve como una columna en el centro. Dos vías, en orden
de preferencia:
1. Cambiar el template de la página a `elementor_header_footer` (ancho completo,
   conservando header y footer) o `elementor_canvas` (sin header ni footer). Se hace por
   REST con `--template`.
2. Si no hay Elementor o el template no basta, CSS acotado a esa página (`.page-id-N`)
   dentro del mismo bloque HTML.

**b) Ocultar el título gris del tema sin tocar el slug ni el SEO.** El título de
WordPress aparece encima del diseño y sobra, porque el HTML ya trae su propio hero.
**Nunca vacíes el campo de título** para ocultarlo: eso cambia el permalink, rompe
breadcrumbs y deja el SEO sin título. Se oculta con CSS acotado a `.page-id-N`.

Ambos se aplican con:

```bash
python3 scripts/wp_rest.py apply-theme-fix 1234 --full-bleed --hide-title
```

Después **mira la página renderizada** (no sólo el editor) y confirma que el diseño llega
de borde a borde y que no hay título duplicado. Si el encajonado persiste, `theme-fixes.md`
trae un snippet de consola para identificar qué elemento está poniendo el `max-width`.

## 8. Auditar los CTAs

No basta con revisar el botón principal. Revisa **todos** los enlaces:

```bash
python3 scripts/check_ctas.py page.html
```

Marca como fallo: `href="#"`, `href=""`, `javascript:void(0)`, `example.com`,
placeholders tipo `TU-LINK`/`your-link`/`TODO`, y `http://` en un sitio que sirve HTTPS.

Presenta al usuario la lista agrupada por destino ("6 botones → checkout X, 1 botón →
`#`") y pide el link real para los que falten. Corrige en `page.html` y vuelve a subir con
`set-content`. Un botón secundario apuntando a `#` es una venta perdida silenciosa.

## 9. Verificar que el guardado se aplicó

El editor de WordPress guarda **autoguardados** en una revisión aparte: la pantalla puede
decir "guardado" y la página pública seguir con el contenido viejo. No confíes en la UI.

```bash
python3 scripts/wp_rest.py verify 1234 --file page.html
```

Compara el contenido realmente almacenado contra tu archivo y reporta diferencias. Además:

- Trae la URL pública con `curl -s <url> | grep -c "<marca única del diseño>"` y confirma
  que la marca aparece.
- Si hay caché (LiteSpeed/Hostinger), purga y vuelve a comprobar; ver `troubleshooting.md`.

Si `verify` marca diferencias, **no digas que quedó listo**: reporta qué se perdió. Si
falta un `<style>` o desaparecieron atributos, es KSES → paso 5/6.

## 10. Publicar

Cuando el borrador esté verificado:

1. Dale al usuario la URL de preview del borrador.
2. Pregunta explícitamente si publica. **No publiques sin ese sí**, salvo que el usuario
   ya haya dicho "publícalo" para esta página en concreto en esta conversación.
3. Publica:
   ```bash
   python3 scripts/wp_rest.py set-status 1234 --status publish
   ```
4. Vuelve a verificar la URL pública ya publicada y entrega el link final.

## Nunca

- Publicar sin confirmación.
- Vaciar el título para ocultarlo (rompe slug y SEO).
- Sobrescribir una página existente sin respaldo previo.
- Pegar HTML largo a mano en el editor del navegador.
- Editar `style.css` del tema o archivos del tema padre para arreglar una sola página.
- Desactivar plugins o cambiar ajustes globales del sitio para que encaje un diseño.
- Guardar la Application Password en un archivo del repo o en un commit.
- Tocar un sitio distinto al confirmado en el paso 1.

## Archivos de esta skill

| Archivo | Cuándo leerlo |
|---|---|
| `references/sitios.md` | Elegir sitio, URLs de wp-admin, notas por sitio |
| `references/theme-fixes.md` | Paso 7: CSS exacto, templates, cómo diagnosticar el encajonado |
| `references/rest-api.md` | Auth alternativa por nonce, endpoints, formato de `content` |
| `references/troubleshooting.md` | 401/403, KSES, caché, Elementor, imágenes rotas |
| `scripts/extract_pasted_images.py` | Paso 3a |
| `scripts/wp_rest.py` | Pasos 3b, 5, 6, 7, 9, 10 |
| `scripts/check_ctas.py` | Paso 8 |
