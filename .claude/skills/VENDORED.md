# Skills de terceros incluidas aquí

Las 18 skills `wordpress-router`, `wp-*`, `wpds` y `blueprint` **no son nuestras**:
vienen de un repositorio oficial de WordPress y están copiadas tal cual.

- Origen: https://github.com/WordPress/agent-skills
- Commit: `d87ee6916e740c7960b6959220c0481a41b320c7`
- Licencia: GPL-2.0-or-later (ver `LICENSE-wordpress-agent-skills`)
- Copiadas el: 2026-08-18

`wp-genix-publish` sí es nuestra y no tiene nada que ver con ese repositorio.

## Por qué están todas y no sólo unas pocas

Se referencian entre sí con rutas relativas de hermanas
(`../../wp-abilities-api/references/...`), así que quitar una rompe enlaces en otras.
Si sobra alguna, bórrala y comprueba que ninguna otra la enlace:

```bash
grep -rn "\.\./\.\./<nombre-de-la-skill>/" .claude/skills/
```

## Actualizarlas

```bash
npx skills add WordPress/agent-skills --list
```

o volver a copiar desde un clon nuevo del repositorio de origen, y actualizar el commit
de arriba.
