# genixweb

Automatizaciones y skills de Claude Code para los sitios WordPress de Genix.

Dos cosas viven en `.claude/skills/`:

- **`wp-genix-publish`** — nuestra, documentada abajo.
- **18 skills oficiales de WordPress** (`wordpress-router`, `wp-*`, `wpds`, `blueprint`)
  copiadas de [WordPress/agent-skills](https://github.com/WordPress/agent-skills)
  bajo GPL-2.0-or-later. Cubren desarrollo de bloques, temas de bloques, plugins, REST
  API, WP-CLI, rendimiento, PHPStan y Playground. Detalle de procedencia y cómo
  actualizarlas en [`.claude/skills/VENDORED.md`](.claude/skills/VENDORED.md).

## `wp-genix-publish`

Skill de Claude Code que toma un HTML ya terminado (normalmente exportado de Claude
Design) y lo deja publicado como página de WordPress en el sitio correcto, sin que
WordPress rompa el CSS y sin romper el SEO.

Cubre el flujo completo:

1. Entrar a wp-admin por SSO de Hostinger, sin contraseña.
2. Extraer a archivo una imagen pegada en el chat.
3. Subir imágenes por la REST API (el selector de archivos del navegador falla).
4. Escribir el HTML sin que `wpautop` destroce el CSS, y con respaldo previo.
5. Arreglos del tema Hello Elementor: quitar el encajonado de 1140px y ocultar el
   título gris sin tocar el slug ni el SEO.
6. Auditar **todos** los CTAs, no sólo el principal.
7. Verificar que el guardado se aplicó de verdad (no un autoguardado).
8. Pedir confirmación antes de publicar.

### Instalación

Como skill personal (disponible en cualquier proyecto):

```bash
mkdir -p ~/.claude/skills
cp -r .claude/skills/wp-genix-publish ~/.claude/skills/
```

Dentro de este repo funciona sin copiar nada: vive en `.claude/skills/`.

### Uso

Basta con pedirlo en lenguaje natural:

> sube esto a WordPress
> publica esta página en triunfagenix
> esto lo hice en Claude Design, súbelo

### Estructura

```
.claude/skills/wp-genix-publish/
├── SKILL.md                        flujo de 10 pasos
├── references/
│   ├── sitios.md                   los 6 sitios y cómo elegir
│   ├── theme-fixes.md              full-bleed y ocultar título
│   ├── rest-api.md                 auth, endpoints, wpautop/KSES
│   └── troubleshooting.md          401/403, caché, Elementor, imágenes
└── scripts/
    ├── wp_rest.py                  cliente REST (stdlib)
    ├── check_ctas.py               auditoría de enlaces
    └── extract_pasted_images.py    imágenes pegadas en el chat → archivo
```

### Credenciales

Los scripts leen `WP_SITE`, `WP_USER` y `WP_APP_PASSWORD` del entorno.
`WP_APP_PASSWORD` es una **Application Password** de WordPress
(`/wp-admin/profile.php`), no la contraseña de la cuenta. **Nunca** se guarda en el
repo.
