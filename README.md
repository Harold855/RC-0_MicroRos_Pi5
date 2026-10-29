# RC-0_MicroRos_Pi5
Reto 0 del Proyecto CapyTown, usando un RosCar (Robot MicroRos_Pi5), donde se prueba arranque, calibración de r,  giro en sitio, validación de segunda variante y gráficas.

## Datos del grupo (borrador, por completar)
- Integrantes y roles (Integración / Control / Planificación / Percepción): *por definir*
- Sección: **S-003** · Variantes: **A1 «Torre»** (calibración) y **A2 «Escalón»** (validación)
- RosCar: **8** (Wi-Fi `RosCar8`)
- `ROS_DOMAIN_ID`: **8** *(pendiente de confirmar con el docente cómo configurarlo en la placa)*
- `r` final: *pendiente* · `b_eff` final: *pendiente*
- Tópico de odometría real: *por confirmar en el robot (`/odom_raw` o `/odom`)*
- Error angular: se calcula dividiendo por el ángulo reportado *(por confirmar con el docente)*

| Prueba | A1 (calibración) | A2 (validación) |
|---|---|---|
| Recta de 1.0 m | B4–C4, oeste → este | C4–D4, este → oeste |
| Giro de 360° | tile B2, antihorario | tile A1, horario |

## Estado
- Hecho (sin robot, con datos sintéticos): `capytown_esan/odom_utils.py`, `capytown_esan/plot_odom.py`, `test/test_plot_math.py`, scripts de diagnóstico de la Parte A.
- No verificado: lectura de bags reales con `rosbag2_py`, comportamiento del RosCar, calibración. Nada de lo anterior es evidencia de calibración.

## Cómo reproducir
```bash
# [PC] pruebas sin robot (necesitan pytest; matplotlib para la prueba de dibujo)
python3 -m pytest test

# [DOCKER ROS 2] gráficas de un bag (dos PNG en plots/)
python3 capytown_esan/plot_odom.py bags/rc0_recta

# [PI HOST] y [DOCKER ROS 2] Parte A: diagnóstico de solo lectura, añade a setup_log.txt
bash scripts/parteA_host.sh
source config/entorno_rc0.sh && bash scripts/parteA_contenedor.sh
```
