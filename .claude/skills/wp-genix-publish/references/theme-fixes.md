# Arreglos de tema (Hello Elementor)

Dos problemas aparecen siempre al meter un HTML full-bleed en estos sitios.
El SKILL.md §6 manda: esto lo amplía, no lo contradice.

## A. El encajonado (~1140px)

**Síntoma:** el diseño se ve como una columna angosta centrada, con franjas a los lados, en
escritorio y en móvil, aunque el HTML use `width:100%`.

**Causa:** Hello Elementor mete el contenido de la página en un contenedor con
`max-width:1140px`.

### El arreglo probado

Es el de §6 del SKILL.md. Va en el propio `<style>` de la página, **una regla por línea y sin
línea en blanco alrededor** (ver §6 sobre wpautop):

```css
.navbar,.hero,section.section,footer{width:100vw;margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw)}
body.wp-singular .site-main,body.wp-singular main{max-width:none!important;margin:0!important;padding:0!important}
```

Dos cosas importantes:

- **Ajusta la primera lista de selectores al HTML real.** `.navbar,.hero,section.section,footer`
  son los contenedores de sección de un export concreto. Mira el HTML y usa los suyos.
- **Los envoltorios internos se quedan como están.** Si el diseño tiene un `.wrap` centrado a
  ~760px, no lo toques: sólo los contenedores de sección con fondo van a ancho completo.

El truco de `width:100vw` + `margin-left:calc(50% - 50vw)` saca el elemento de su contenedor
sin tocar el tema. Es reversible y no afecta a ninguna otra página.

### Si aun así persiste

Ejecuta esto sobre la página renderizada para ver qué elemento sigue poniendo el `max-width`:

```js
[...document.querySelectorAll('body *')]
  .map(el => ({el, s: getComputedStyle(el)}))
  .filter(({s}) => s.maxWidth !== 'none' && parseFloat(s.maxWidth) < 1400)
  .map(({el, s}) => `${el.tagName.toLowerCase()}.${[...el.classList].join('.')} → ${s.maxWidth}`)
```

Añade ese selector a la segunda regla. **No toques `style.css` del tema.**

### Alternativa: cambiar el template de la página

Si Elementor está instalado registra estos templates, que quitan el encajonado sin CSS:

| Template | Qué hace |
|---|---|
| `elementor_header_footer` | Ancho completo, **conserva** header y footer del sitio |
| `elementor_canvas` | Lienzo limpio: **sin** header ni footer del tema |
| `elementor_theme` | Layout normal del tema (el encajonado) |

```bash
python3 scripts/wp_rest.py set-template 1234 --template elementor_canvas
```

**Sin historial de uso real en estos sitios.** El CSS de arriba es el que ya funcionó. Si
pruebas el template, verifica la página en vivo antes de darla por buena, y pregunta al
usuario si quiere conservar el menú del sitio: `canvas` lo elimina.

## B. El título gris del tema

**Síntoma:** encima del diseño aparece el título de WordPress (`h1.entry-title`, normalmente
dentro de `<header class="page-header">`), que sobra porque el HTML ya trae su propio hero.

**Nunca lo arregles vaciando el campo de título.** Ese campo alimenta el slug/permalink, el
título de SEO, breadcrumbs y los menús. Vaciarlo rompe todo eso.

```css
body.page-id-<ID> .page-header{display:none!important;margin:0!important;padding:0!important}
```

El `<ID>` sale de la clase `page-id-NNNN` que ya está en el `<body>`, o del parámetro `post=`
de la URL del editor.

Con `elementor_canvas` el tema no imprime título y este arreglo sobra — pero dejarlo puesto no
hace daño y protege si alguien cambia el template después.

## Verificación

Después de cualquiera de los dos, carga la **URL pública** (no el editor) y comprueba con
`getComputedStyle` sobre el elemento afectado, no de vista:

```js
getComputedStyle(document.querySelector('.hero')).width
document.body.scrollWidth > window.innerWidth   // debe ser false: sin scroll horizontal
```

Que la regla esté dentro del `<style>` no significa que se haya aplicado: si wpautop la partió
(§6), el parser de CSS la descarta en silencio.
