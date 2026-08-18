# Arreglos de tema (Hello Elementor)

Dos problemas aparecen siempre al meter un HTML full-bleed en estos sitios.

## A. El encajonado (~1140px)

**Síntoma:** el diseño se ve como una columna angosta centrada, con franjas blancas a los
lados, aunque el HTML usa `width:100%`.

**Causa:** algún ancestro del contenido (el `<main>`/`<article>` del tema, o el contenedor
"boxed" de Elementor) tiene `max-width` y padding lateral.

### Vía 1 — Cambiar el template de la página (preferida)

Si Elementor está instalado, registra estos templates de página:

| Template | Qué hace |
|---|---|
| `elementor_header_footer` | Ancho completo, **conserva** header y footer del sitio |
| `elementor_canvas` | Lienzo limpio: **sin** header ni footer del tema |
| `elementor_theme` | Layout normal del tema (el encajonado) |

Para una landing exportada de Claude Design que ya trae su propio nav y footer,
`elementor_canvas` suele ser lo correcto. Si el usuario quiere conservar el menú del sitio,
`elementor_header_footer`.

```bash
python3 scripts/wp_rest.py set-template 1234 --template elementor_canvas
```

Pregunta al usuario cuál quiere si el HTML trae su propio menú/footer: es una decisión
visible, no técnica.

### Vía 2 — CSS acotado a la página

Cuando no hay Elementor, o el template no elimina el cap, mete este CSS **dentro del mismo
bloque HTML de la página** (sustituye `N` por el ID real):

```css
body.page-id-N .site-main,
body.page-id-N .page-content,
body.page-id-N .entry-content,
body.page-id-N main,
body.page-id-N article,
body.page-id-N .container {
  max-width: 100% !important;
  width: 100% !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
```

`apply-theme-fix --full-bleed` inyecta exactamente ese bloque con el ID correcto.

**Acota siempre con `body.page-id-N`.** Sin ese prefijo el CSS se aplicaría a esa página
únicamente igual (está inline), pero si alguien lo mueve a "CSS adicional" del
personalizador reventaría el resto del sitio. El prefijo lo hace seguro por construcción.

### Si el cap persiste

Ejecuta esto en la consola del navegador sobre la página renderizada para descubrir qué
elemento lo está poniendo:

```js
[...document.querySelectorAll('body *')]
  .map(el => ({el, s: getComputedStyle(el)}))
  .filter(({s}) => s.maxWidth !== 'none' && parseFloat(s.maxWidth) < 1400)
  .map(({el, s}) => `${el.tagName.toLowerCase()}.${[...el.classList].join('.')} → ${s.maxWidth}`)
```

Añade el selector que devuelva a la lista del CSS de arriba. No toques `style.css` del tema.

## B. El título gris del tema

**Síntoma:** encima del diseño aparece el título de WordPress (`<h1 class="entry-title">`,
a veces dentro de `<header class="page-header">`), duplicando el hero del HTML.

**Nunca lo arregles vaciando el campo de título.** El título alimenta el slug/permalink, el
`<title>` de SEO, breadcrumbs, el listado del admin y los menús. Vaciarlo rompe todo eso.

Arréglalo con CSS acotado:

```css
body.page-id-N .page-header,
body.page-id-N .entry-title,
body.page-id-N .entry-header { display: none !important; }
```

`apply-theme-fix --hide-title` inyecta ese bloque.

Con `elementor_canvas` el tema no imprime título, así que este arreglo sobra — pero
aplicarlo igual no hace daño y protege si luego cambian el template.

## Cómo se inyectan

`apply-theme-fix` escribe un bloque marcado dentro del contenido de la página:

```html
<!-- wp-genix-publish:theme-fix start -->
<style> ... </style>
<!-- wp-genix-publish:theme-fix end -->
```

Es idempotente: reemplaza el bloque anterior si ya existe, no lo duplica. Y es reversible:
borrar ese bloque deja la página como estaba.

## Verificación

Después de aplicar, carga la **URL pública** (no el editor) y comprueba:

- el diseño llega de borde a borde en escritorio;
- no hay título duplicado;
- en móvil no aparece scroll horizontal (`document.body.scrollWidth > window.innerWidth`
  debe ser falso).
