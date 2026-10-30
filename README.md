# RC-0_MicroRos_Pi5
Reto 0 del Proyecto CapyTown, usando un RosCar (Robot MicroRos_Pi5), donde se prueba arranque, calibración de r,  giro en sitio, validación de segunda variante y gráficas.

## Datos del grupo (borrador, por completar)
- Integrantes y roles (Integración / Control / Planificación / Percepción): *por definir*
- Sección: **S-003** · Variantes: **A1 «Torre»** (calibración) y **A2 «Escalón»** (validación)
- RosCar: **8** (Wi-Fi `RosCar8`)
- `ROS_DOMAIN_ID`: el Agent del RosCar 8 corre con **20** (`docker inspect micro_ros_agent`); el reto pide el número de grupo (**8**). *Pendiente: preguntar al docente cuál debe ser y cómo cambiarlo.* Hasta entonces se trabaja en 20.
- `r` final: *pendiente* · `b_eff` final: *pendiente*
- Tópico de odometría real: *por confirmar en el robot (`/odom_raw` o `/odom`)*
- Unidades de los CSV: distancias en metros y ángulos en grados (los encabezados del reto no llevan unidades).
- Error angular: se calcula dividiendo por el ángulo reportado *(por confirmar con el docente)*

| Prueba | A1 (calibración) | A2 (validación) |
|---|---|---|
| Recta de 1.0 m | B4–C4, oeste → este | C4–D4, este → oeste |
| Giro de 360° | tile B2, antihorario | tile A1, horario |

## Estado
- Hecho (sin robot, con datos sintéticos): `odom_utils.py`, `plot_odom.py`, `analizar_bag.py`, `secuencia_rc0.py` (en `capytown_esan/`), sus pruebas en `test/`, los scripts de la Parte A y de manejo de bags, `verificacion_entrega.py`, `generar_tablas_informe.py`, la hoja de campo y las plantillas del informe.
- Los tres CSV tienen su encabezado y ninguna fila: no hay datos todavía. `config/wheel_params.yaml` es una plantilla con `null`.
- No verificado: lectura de bags reales con `rosbag2_py`, el nodo de `secuencia_rc0.py` contra ROS 2 real (solo se probó su lógica y un nodo simulado), comportamiento del RosCar, calibración. Nada de lo anterior es evidencia de calibración.

## Cómo reproducir
```bash
# [PC] pruebas sin robot (necesitan pytest; matplotlib para la prueba de dibujo)
python3 -m pytest test

# [DOCKER ROS 2] gráficas de un bag (dos PNG en plots/)
python3 capytown_esan/plot_odom.py bags/rc0_recta

# [DOCKER ROS 2] números de un bag para los CSV (imprime; solo escribe con --escribir)
python3 capytown_esan/analizar_bag.py bags/rc0_recta --prueba recta --listar
python3 capytown_esan/analizar_bag.py bags/rc0_recta --prueba recta --d-real <metros_con_cinta>

# [DOCKER ROS 2] secuencia de prueba: por defecto NO mueve (dry-run). Ver el encabezado del archivo.
python3 capytown_esan/secuencia_rc0.py --ros-args -p modo:=recta

# [DOCKER ROS 2] grabar un bag con nombre único (antes de mover) y fijar el entregable final
bash scripts/grabar_bag.sh rc0_recta_c1
bash scripts/fijar_bag_final.sh bags/<bag_elegido> rc0_recta

# [PC] ¿qué falta para entregar? y tablas del informe a partir de los CSV reales
python3 scripts/verificacion_entrega.py
python3 scripts/generar_tablas_informe.py

# [PI HOST] y [DOCKER ROS 2] Parte A: diagnóstico de solo lectura, añade a setup_log.txt
bash scripts/parteA_host.sh
source config/entorno_rc0.sh && bash scripts/parteA_contenedor.sh
```

## Para el laboratorio
`config/atajos_rc0.sh` (comandos cortos: `source` una vez y escribe `ayuda`) · `docs/guia_trabajo_roscar.md` (conexión y copias de seguridad) · `docs/hoja_de_campo_rc0.md` (qué anotar en cada parte) · `informe/predicciones.md` (escribir y commitear **antes** de medir).
