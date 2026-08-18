# Sitios Genix

Todos alojados en Hostinger, tema base **Hello Elementor**. Confirma con el usuario antes
de escribir en cualquiera.

| Sitio | wp-admin | Notas |
|---|---|---|
| `genixacademy.com` | `https://genixacademy.com/wp-admin/` | Sitio principal |
| `academiagenix.com` | `https://academiagenix.com/wp-admin/` | |
| `triunfagenix.com` | `https://triunfagenix.com/wp-admin/` | |
| `miraveoptica.com` | `https://miraveoptica.com/wp-admin/` | Cliente distinto — extra cuidado |
| `productosdigitales.genixacademy.com` | `https://productosdigitales.genixacademy.com/wp-admin/` | Subdominio de genixacademy |
| `email.triunfagenix.com` | `https://email.triunfagenix.com/wp-admin/` | Subdominio de triunfagenix |

## Cómo elegir

- Si el usuario nombra el sitio, ese es. `"la academia"` es ambiguo entre
  `genixacademy.com` y `academiagenix.com`: **pregunta**.
- Si el usuario da una URL de la página destino, el dominio de esa URL manda.
- `miraveoptica.com` es de un cliente externo, no de Genix. Nunca lo elijas por inferencia:
  sólo si el usuario lo nombra.

## Verificación antes de escribir

```bash
export WP_SITE="https://<dominio>"
python3 scripts/wp_rest.py whoami
```

`whoami` imprime el dominio y el usuario con el que estás autenticado. Enséñaselo al
usuario antes del primer `set-content` sobre una página existente.

## Estructura típica

- Los subdominios (`productosdigitales.`, `email.`) son instalaciones WordPress separadas:
  credenciales, biblioteca de medios e IDs de página **no** se comparten con el dominio
  padre. Una imagen subida a `genixacademy.com` no sirve para
  `productosdigitales.genixacademy.com` salvo que enlaces la URL absoluta a propósito.
- Si un sitio resulta ser multisitio, la capability `unfiltered_html` sólo la tiene el
  super admin → ver `troubleshooting.md`.
