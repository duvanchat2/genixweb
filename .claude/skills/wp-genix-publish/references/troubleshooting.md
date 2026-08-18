# Problemas conocidos

## 401 / 403 en la REST API

1. **`WP_SITE` con barra final o con `http://`.** Debe ser `https://dominio` sin barra.
2. **Application Password mal copiada.** Los espacios dan igual (los scripts los quitan),
   pero un carácter de menos no. Regenérala.
3. **`rest_no_route` en `/wp-json/`.** Los permalinks pueden estar en "simple". Prueba
   `<WP_SITE>/?rest_route=/wp/v2/users/me` — los scripts caen a esa forma automáticamente.
4. **Plugin de seguridad bloqueando la REST API o Basic Auth** (Wordfence, iThemes,
   "Disable REST API"). Se ve como 403 con cuerpo HTML en vez de JSON. Díselo al usuario y
   pregúntale antes de tocar nada: desactivar un plugin de seguridad es decisión suya.
5. **Hostinger/Cloudflare devolviendo un reto.** Cuerpo HTML con "Just a moment" o 405 del
   proxy → usa la vía nonce desde el navegador (`rest-api.md`).

## El `<style>` desaparece al guardar

Es KSES. Relee la página con `get-page --save-content` y compara. Comprueba con
`whoami` si el usuario tiene `unfiltered_html`. Si no la tiene:

- pide al usuario un login de administrador real (no editor);
- si es multisitio, hace falta el super admin;
- **no** metas el CSS en el `style.css` del tema como atajo.

## El CSS se ve con `<p>` y `<br>` dentro

Se guardó sin el envoltorio de bloque `<!-- wp:html -->`, o alguien reeditó la página en el
editor clásico. Vuelve a escribir con `set-content` (que envuelve) y no abras el editor
clásico sobre esa página.

## Guardé y la página pública no cambia

Por orden:

1. `verify` — ¿el contenido almacenado es el nuevo? Si no, fue un autoguardado: repite el
   `set-content` por REST.
2. **Caché.** Hostinger sirve caché propia y suele haber LiteSpeed Cache. Purga desde
   wp-admin (**LiteSpeed Cache → Toolbox → Purge All**) y/o desde hPanel
   (**Rendimiento → Caché → Purgar**). Reintenta con `curl -H 'Cache-Control: no-cache'`.
3. **Elementor.** Si la página tiene `_elementor_edit_mode = builder`, Elementor pinta su
   propio contenido y tu `content` queda ignorado. Crea una página nueva, o pide permiso
   para desvincular esa página de Elementor.

## La imagen se ve rota

- ¿El `src` quedó apuntando a una ruta local o a un `data:` URI? → paso 3b de la skill.
- ¿La subiste al sitio equivocado? Los subdominios son instalaciones separadas.
- ¿El `source_url` es `http://` mientras el sitio sirve `https://`? Cámbialo a `https://`
  o el navegador bloquea el contenido mixto.

## Scroll horizontal en móvil

Algún elemento del diseño se sale del viewport. Diagnóstico rápido en consola:

```js
[...document.querySelectorAll('body *')]
  .filter(el => el.getBoundingClientRect().right > window.innerWidth + 1)
  .slice(0, 20)
```

Si el culpable es del diseño (no del tema), **no lo parchees**: repórtalo al usuario, es un
cambio de diseño y esta skill no rediseña.

## Publiqué en el sitio equivocado

Pásalo a borrador de inmediato (`set-status <id> --status draft`), avisa al usuario, y
publícalo en el correcto. No borres la página: el borrador conserva el contenido.
