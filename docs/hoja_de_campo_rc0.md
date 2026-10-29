# Hoja de campo RC-0 — RosCar 8 (S-003: A1 calibra, A2 valida)

Se llena **durante** la sesión, a mano o pegando salidas. Lo que se mide con cinta o transportador se anota aquí
primero y de aquí pasa a `analizar_bag.py`. Nada se rellena con valores ideales ni "de memoria".
Orden obligatorio: **primero `r` (recta), después `b_eff` (giro). Un solo parámetro a la vez.**

## 0. Antes de empezar
- [ ] Predicciones escritas y **commiteadas** antes de medir (`informe/predicciones.md`).
- [ ] Cartulinas armadas. Longitud real de la recta (borde a borde de las líneas de cinta): ______ m (debe ser 1.00 m; si no, anótala y úsala).
- [ ] Cinta métrica, regla, transportador, cinta masking, cargador cerca.
- [ ] Fecha: ________ · Operador: ________ · Equipo: Pi 400 / laptop (tachar) · Wi-Fi `RosCar8`

## 1. Parte A — arranque
| Ítem | Resultado |
|---|---|
| Robot identificado (n.º 8) / batería al empezar | |
| `ROS_DOMAIN_ID` en la Pi / en la placa (cómo se comprobó) | |
| ¿Ya había un Agent corriendo? ¿Cuál lanzó el bringup? | |
| Topic de odometría real (`/odom_raw` o `/odom`) | |
| Frecuencia de odometría / de `/imu` (`ros2 topic hz`, valor medido) | |
| `/cmd_vel` y `/scan` presentes | |
| Aislamiento: `ros2 topic list` solo muestra el robot propio | |
| rosbag2: sqlite3 y mcap listados (`scripts/instalar_rosbag2.sh` si falta) | |
| Captura de `rqt_graph` (nombre del archivo) | |
| Dónde está `wheel_params.yaml` y claves reales de r y b_eff | |
| ¿`calibrate_beff` lee `/odom` u `/odom_raw`? ¿Acepta velocidad negativa? | |

## 2. Parte B — recta de 1.0 m en A1 (B4–C4, oeste → este) · calibra `r`
Antes de cada corrida: eje de ruedas sobre la línea de inicio (A4|B4), robot orientado al este, bag grabando
(`bash scripts/grabar_bag.sh rc0_recta_cN`), batería anotada.

| Corrida | r usado [m] | Bag | Batería | d_real [m] (cinta) | Desvío lateral [m] (cinta, lado) | Notas |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

Para cada una: `python3 capytown_esan/analizar_bag.py bags/<bag> --prueba recta --d-real <d_real> --csv linea_recta --corrida N --r <r> --desvio-m <desvío> --escribir linea_recta.csv`
Si el error supera 2 %: el grupo decide el nuevo `r` (regla deducida por el grupo), lo aplica y reinicia el bringup (con autorización), y se repite.
Corrida final elegida → `bash scripts/fijar_bag_final.sh bags/<bag> rc0_recta`.

## 3. Parte C — giro de 360° en A1 (tile B2, antihorario) · calibra `b_eff`
- Ancho físico W medido con regla: ______ m (entre qué puntos: __________________)
- `r` fijo = ______ m (el final de la Parte B). Cinta en el chasis y en el piso alineadas; cruz en el centro del tile.
- Mide el ángulo real **con el sentido y el número de vueltas**: "10° de diferencia" no dice si fueron 350° o 370°.

| Iter. | b_eff usado [m] | θ reportado [°] | θ medido [°] | ¿Pasó o se quedó corto? | Error [%] | b_eff propuesto [m] |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

Cada iteración: `analizar_bag.py bags/<bag> --prueba giro --csv calibracion --iteracion N --b-eff-usado <x> --theta-medido <°> --b-eff-propuesto <y> --escribir calibration_log.csv`
(el propuesto lo calcula el grupo). El **último** giro, grabado → `fijar_bag_final.sh ... rc0_giro`. Valor final → `config/wheel_params.yaml` (+ el del robot).

## 4. Parte D — validación en A2, sin tocar parámetros
- r = ______ m · b_eff = ______ m (congelados; **no se corrigen aunque el error crezca**)
- Recta A2: C4–D4, **este → oeste** (inicio D4|E4, fin B4|C4). Comprobar que el robot **mira al oeste**.
- Giro A2: tile A1, **horario** (usar `secuencia_rc0.py -p sentido:=horario`; no `calibrate_beff`).

| Prueba | Bag | Batería | Valor real (cinta / transportador) | Notas |
|---|---|---|---|---|
| Recta 1 | | | | |
| Recta 2 | | | | |
| Giro 360° horario | | | | |

`analizar_bag.py ... --csv validacion --variante A2 --valor-real <x> --escribir validacion.csv` (con `--segmento 1/2` si las dos rectas están en un bag).
Bags finales: `rc0_val_recta`, `rc0_val_giro`.

## 5. Parte E y cierre
- [ ] `python3 capytown_esan/plot_odom.py bags/<bag>` para los 4 bags finales (8 PNG en `plots/`).
- [ ] Bags y CSV **copiados fuera del robot** (laptop / Pi 400) antes de apagar.
- [ ] `python3 scripts/verificacion_entrega.py` sin ERROR.
- [ ] Robot dejado como estaba, apagado y a cargar.

## 6. Bonus (solo frente al docente, en A2, sin recalibrar)
Giro de 720° con error ≤ 5° y recta de 1.0 m con error ≤ 1 % (1 cm). Para 720°:
`-p modo:=giro -p sentido:=horario -p target_angle_deg:=720.0 -p dry_run:=false -p confirmar_movimiento:=true`.
Cuenta las dos vueltas en el piso con la cinta de referencia.
