# bags/

Cada bag de ROS 2 es una **carpeta** (con `metadata.yaml` y un `.db3` o `.mcap`), no un archivo.

Entregables exactos (carpetas finales):

| Carpeta | Contenido | Variante |
|---|---|---|
| `rc0_recta/` | Rectas de calibración de `r` | A1 |
| `rc0_giro/` | Último giro de calibración de `b_eff` | A1 |
| `rc0_val_recta/` | Dos rectas de validación | A2 |
| `rc0_val_giro/` | Un giro de validación | A2 |


