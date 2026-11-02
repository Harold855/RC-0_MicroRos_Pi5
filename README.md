# bags/

Cada bag de ROS 2 es una **carpeta** (con `metadata.yaml` y un `.db3` o `.mcap`), no un archivo.

Entregables exactos (carpetas finales):

| Carpeta | Contenido | Variante |
|---|---|---|
| `rc0_recta/` | Rectas de calibración de `r` | A1 |
| `rc0_giro/` | Último giro de calibración de `b_eff` | A1 |
| `rc0_val_recta/` | Dos rectas de validación | A2 |
| `rc0_val_giro/` | Un giro de validación | A2 |

Cómo trabajar:
- Graba cada corrida en su propio bag con nombre único: `scripts/grabar_bag.sh rc0_recta_c1` (no sobrescribe).
- Las carpetas con nombre final se **copian** de la corrida elegida: `scripts/fijar_bag_final.sh <bag> rc0_recta`. No se renombra ni se borra nada.
- Copia los bags fuera del robot después de cada corrida (`docs/guia_trabajo_roscar.md`, sección 4).
- No se versionan bags de prueba ni sintéticos como si fueran evidencia (`SINTETICO_*` no se entrega).
