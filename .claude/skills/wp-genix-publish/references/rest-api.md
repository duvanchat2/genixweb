# REST API de WordPress — notas de uso

## Autenticación

### Application Password (preferida)

Header `Authorization: Basic base64(usuario:app_password)`. Requiere HTTPS (todos estos
sitios lo tienen). Se crea en `/wp-admin/profile.php` → **Application Passwords**.

Variables que leen los scripts:

```
WP_SITE           https://dominio (sin barra final)
WP_USER           login del usuario admin
WP_APP_PASSWORD   la contraseña generada (con o sin espacios)
```

Se revoca desde el mismo panel cuando termines, si el usuario lo prefiere.

### Alternativa: cookie + nonce desde el navegador ya logueado

Si el usuario no quiere crear una Application Password y ya estás dentro de wp-admin por
SSO, puedes llamar la REST API desde la consola del navegador reutilizando la cookie de
sesión, firmando con el nonce:

```js
// el nonce está expuesto en wp-admin
const nonce = wpApiSettings.nonce;            // en pantallas del editor
// subir media
await fetch('/wp-json/wp/v2/media', {
  method: 'POST',
  headers: {
    'X-WP-Nonce': nonce,
    'Content-Disposition': 'attachment; filename="hero.png"',
    'Content-Type': 'image/png'
  },
  body: fileBlob
}).then(r => r.json());
```

Limitaciones: el nonce caduca (~12–24 h), y necesitas ejecutar JS en la pestaña logueada.
Por eso la Application Password es la vía por defecto.

## Endpoints usados

| Acción | Método | Ruta |
|---|---|---|
| Identidad actual | GET | `/wp-json/wp/v2/users/me?context=edit` |
| Listar páginas | GET | `/wp-json/wp/v2/pages?search=...&status=any&context=edit` |
| Leer página | GET | `/wp-json/wp/v2/pages/<id>?context=edit` |
| Crear página | POST | `/wp-json/wp/v2/pages` |
| Actualizar página | POST | `/wp-json/wp/v2/pages/<id>` |
| Subir media | POST | `/wp-json/wp/v2/media` |

`context=edit` es imprescindible para leer `content.raw` (sin él sólo devuelve
`content.rendered`, que ya pasó por los filtros y **no** sirve para comparar ni para
respaldo).

## Formato del contenido

Al escribir, manda JSON con `content` como string. Para que WordPress lo trate como
bloques y por tanto **no** le aplique `wpautop`, el contenido debe ir envuelto:

```html
<!-- wp:html -->
...tu HTML íntegro, con <style> incluido...
<!-- /wp:html -->
```

Detalle del core: `do_blocks()` corre en el filtro `the_content` con prioridad 9 y, si el
contenido tiene bloques, **quita** `wpautop` del filtro para ese render. Por eso el
envoltorio es lo que salva el CSS.

## KSES / `unfiltered_html`

Si el usuario autenticado no tiene la capability `unfiltered_html`, la REST API pasa el
contenido por `wp_filter_post_kses` al guardar: desaparecen `<style>`, `<script>`,
`<iframe>` y atributos como `onclick`. Síntoma: guardas, no da error, y al releer con
`get-page` falta el `<style>`.

- WordPress de sitio único: administrador y editor **sí** la tienen.
- Multisitio: sólo el super admin.
- Algunos plugins de seguridad la revocan → `troubleshooting.md`.

## Subida de media

Se sube el binario crudo con dos headers:

```
Content-Disposition: attachment; filename="hero.png"
Content-Type: image/png
```

No uses `multipart/form-data` ni el `<input type=file>` del navegador: el uploader de
wp-admin falla de forma intermitente desde automatización.

La respuesta trae `id` y `source_url`. Usa siempre `source_url` en el HTML (URL absoluta),
no una ruta relativa.

## Estados

`status` acepta `draft`, `publish`, `pending`, `private`. Escribe siempre en `draft`
primero. La URL de previsualización de un borrador es
`<WP_SITE>/?page_id=<id>&preview=true`.
