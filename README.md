# RC-0 · Primer arranque y calibración del RosCar 8

Desarrollo del reto 0 del Proyecto CapyTown con el robot **MicroROS-Pi5(ROScar)** (Raspberry Pi 5 con una placa ESP32-S3, ROS 2 Humble y micro-ROS).
Nuestro grupo pone en ejecución al robot, verifica la cadena **placa → micro-ROS → ROS 2**, y calibra los dos parámetros del modelo cinemático
que se usarán en los retos posteriores: el radio de rueda **r** y el ancho de vía efectivo **b_eff**.

## Equipo y trabajo realizado

| Integrante | Rol en RC-0 | Trabajo realizado |
|---|---|---|
| *(nombre completo)* | parte A |
| *(nombre completo)* | parte B y E |
| *(nombre completo)* | parte C |

## Datos 

| | |
|---|---|
| Sección | **S-003** |
| Variantes | **A1 «Torre»** (calibración, Partes B y C) · **A2 «Escalón»** (validación, Parte D, sin recalibrar) |
| Robot | **RosCar 8** (Wi-Fi `RosCar8`, escritorio remoto `10.42.0.1::5900`) |
| `ROS_DOMAIN_ID` | **8** (equipo n → n), en la Pi y en la placa. Las primeras mediciones de la Parte A se hicieron con 20, el valor de fábrica de Yahboom |
| `r` | 0.0311 m (usado en las corridas de la Parte B) |
| `b_eff` | 0.2259 m (valor de partida de la Parte C) |
| Odometría evaluada | `/odom` (la publica `odom_corrector` a partir de `/odom_raw` del firmware) |
| Unidades de los CSV | distancias en metros y ángulos en grados |

| | A1 (calibrar) | A2 (validar) |
|---|---|---|
| Recta de 1.0 m | B4–C4, oeste → este (inicio A4\|B4, fin C4\|D4) | C4–D4, este → oeste (inicio D4\|E4, fin B4\|C4) |
| Giro de 360° | tile B2, antihorario (`angular.z` +) | tile A1, horario (`angular.z` −) |

## Explicacion del reto 

Antes de pedirle al robot que navegue hay que saber cuánto se puede confiar en él. El modelo es un **diferencial equivalente** (el robot tiene 4 ruedas sin dirección):
la odometría que publica el firmware se re-escala con dos factores,

- `k_lin = r / r0` sobre la distancia,
- `k_ang = (r / r0) · (b0 / b_eff)` sobre el giro,

donde `r0 = 0.0325 m` y `b0 = 0.24 m` son los valores que el firmware asume. Se calibra **un parámetro a la vez**:
primero `r` con una recta de 1.0 m (criterio: error ≤ 2 %), después `b_eff` con giros de 360° (criterio: error < 1 %), y se valida en la segunda variante **sin recalibrar**.
Se predice por escrito, antes de medir, qué se espera (`informe/predicciones.md`). Fuera de alcance: cuadrado e IMU (RC-1), cámara y carril (RC-2), LiDAR (RC-3 en adelante).

## Flujo del repositorio

```
 Placa ESP32-S3 ──serie──▶ micro-ROS Agent (contenedor micro_ros_agent) ──▶ ROS 2 (dominio 8)
                                                                              │ /odom_raw, /imu, /scan, /cmd_vel
                                                                              ▼
 bringup.launch.py ─▶ odom_corrector (r, b_eff de wheel_params.yaml) ─▶ /odom
                                                                              │
 preflight.sh ─▶ corrida.sh ─┬─ grabar_bag.sh ─▶ bags/rc0_<prueba>_cN_<fecha>/
 (comprobaciones)            ├─ secuencia_rc0.py / calibrate_beff ─▶ movimiento (con confirmación)
                             └─ medición con cinta ─▶ analizar_bag.py ─▶ linea_recta.csv · calibration_log.csv · validacion.csv
 aplicar_param.sh ─▶ cambia r o b_eff en caliente (y deja bitácora)
 fijar_bag_final.sh ─▶ bags/rc0_recta · rc0_giro · rc0_val_recta · rc0_val_giro
 plot_odom.py ─▶ plots/*.png (x-y y θ-t)         verificacion_entrega.py · generar_tablas_informe.py ─▶ informe
```

## Estructura del repositorio

| Carpeta / archivo | Contenido |
|---|---|
| `capytown_esan/` | Código propio en Python (ver «Códigos») |
| `scripts/` | Scripts de laboratorio (Parte A, sesión de medición, bags, verificación) |
| `config/` | `entorno_rc0.sh` y `atajos_rc0.sh` (dominio 8 y comandos cortos), `wheel_params.yaml` (parámetros del modelo) |
| `bags/` | Bags de ROS 2: una carpeta por corrida y los cuatro bags finales |
| `plots/` | Gráficas de los bags |
| `informe/` | `predicciones.md` e `informe_plantilla.md` |
| `docs/` | Guías de trabajo, plan de la sesión, hoja de campo, notas del código del docente y registro de la sesión |
| `test/` | Pruebas automáticas con datos sintéticos |
| `linea_recta.csv`, `calibration_log.csv`, `validacion.csv`, `setup_log.txt` | Resultados de cada parte |

## Códigos

**Código propio**

| Archivo | Qué hace |
|---|---|
| `capytown_esan/odom_utils.py` | Matemática de odometría: yaw desde el cuaternión, desenvolvimiento del ángulo, desplazamiento longitudinal y lateral, errores, detección del tramo de movimiento y de reinicios |
| `capytown_esan/plot_odom.py` | Lee un bag (formato tomado de su `metadata.yaml`) y genera dos PNG: trayectoria x-y y orientación θ(t) |
| `capytown_esan/analizar_bag.py` | Del bag a los números de los CSV: `d_odom`, desvío lateral, ángulo acumulado y error; escribe la fila solo si se pide |
| `capytown_esan/secuencia_rc0.py` | Secuencia de recta y de giro con tope de velocidad, diagnóstico previo, parada por odometría y confirmación explícita antes de mover (por defecto no mueve) |
| `scripts/parteA_host.sh`, `parteA_contenedor.sh` | Diagnóstico de solo lectura de la Parte A (host y contenedor); añade a `setup_log.txt` |
| `scripts/preflight.sh` | Comprobaciones antes de mover: dominio, nodos, topics, suscriptores de `/cmd_vel`, `/odom`, `r` y `b_eff` vivos, batería, disco |
| `scripts/corrida.sh` | Corrida guiada: preflight, lista de comprobación, bag, movimiento, medición con cinta, análisis y fila de CSV |
| `scripts/aplicar_param.sh` | Cambia `wheel_radius` o `wheel_separation` en caliente, valida, pide confirmación y deja registro |
| `scripts/grabar_bag.sh`, `fijar_bag_final.sh`, `respaldar_bags.sh` | Grabación con nombre único, copia al nombre final del entregable y respaldo |
| `scripts/instalar_rosbag2.sh` | Comprobación de rosbag2 (instalación solo si falta y con aprobación) |
| `scripts/verificacion_entrega.py`, `generar_tablas_informe.py` | Revisión de lo que contiene la entrega y tablas del informe a partir de los CSV |
| `config/atajos_rc0.sh` | Comandos cortos: `preflight`, `corrida`, `aplicar`, `bringup`, `parteA`, `grabar`, `secuencia`, `graficar`, `analizar`, `fijar`, `verificar`, `tablas`, `ayuda` |

**Códigos compartidos** (paquete `capytown_esan` instalado en el robot, sin modificar sus algoritmos): `odom_corrector` (aplica `r` y `b_eff` a `/odom_raw` y publica `/odom` y `tf`),
`calibrate_beff` (giro hasta acumular el ángulo objetivo y cálculo de `b_eff`), `teleop_key`, `fake_robot`, `error_odom`, `run_square`, `bringup.launch.py`. 

## Cómo reproducir

```bash
# [PC] pruebas con datos sintéticos (verifican la lógica, no son datos de calibración)
python3 -m pytest test

# [DOCKER ROS 2] entorno y comandos cortos (fija ROS_DOMAIN_ID=8 en esa terminal)
source config/atajos_rc0.sh
bringup                                  # lanza odom_corrector con el wheel_params.yaml; la terminal queda ocupada
preflight                                # comprobaciones antes de mover
parteA                                   # diagnóstico de la Parte A (añade a setup_log.txt)
corrida recta A1 1                       # corrida guiada de la Parte B
corrida calibrar_b A1 1                  # corrida guiada de la Parte C
corrida recta A2 1 · corrida giro A2 1   # Parte D
aplicar wheel_radius <metros>            # cambia r en caliente
graficar <bag>                           # dos PNG en plots/
verificar · tablas                       # estado de la entrega y tablas del informe
```

## Las partes

### Parte A — Arranque
**Qué se hace.** Se enciende el robot y se verifica la cadena placa → micro-ROS → ROS 2: nodo de la placa, topics `/cmd_vel`, `/odom`, `/imu`, `/scan`, frecuencias de `/odom` e `/imu`,
dominio igual en la Pi y la placa, aislamiento (solo se ve el robot propio), rosbag2 y `rqt_graph`. Resultado: `setup_log.txt`.

**Desarrollo.**
1. *Identificación.* RosCar 8: Raspberry Pi 5 y ESP32-S3 unidos por serie (`/dev/ttyUSB0`, 921600). El micro-ROS Agent corre como el contenedor `micro_ros_agent` (política de reinicio `unless-stopped`, arranca con la Pi); el trabajo con ROS 2 se hace en el contenedor `ros2_dev`.
2. *Dominio.* La placa venía con `ROS_DOMAIN_ID = 20` (valor de fábrica de Yahboom, usado como ejemplo en los códigos del docente). Con el robot en 20, el dominio 8 salía vacío: la prueba de aislamiento. Para usar el dominio del grupo (8) se escribió el valor en la placa con `config_robot.py` (`set_ros_domain_id(8)`, con respaldo del original), se reinició la placa y se cambió también el `.bashrc` del contenedor. El script devolvió `domain_id: 8`. Después de eso, `/YB_Car_Node` aparece en el dominio 8 y el 20 queda vacío. Procedimiento completo en `docs/guia_trabajo_roscar.md` §2b.
3. *Bringup.* `ros2 launch capytown_esan bringup.launch.py` lanza solo `odom_corrector` (el Agent ya corre como contenedor y no se duplica). Se lanza con el `wheel_params.yaml` del paquete del docente: `r = 0.0311 m`, `b_eff = 0.2259 m` (con `r0 = 0.0325` y `b0 = 0.24`), es decir `k_lin = 0.9569` y `k_ang = 1.0167`.
4. *Topics.* `/battery`, `/beep`, `/cmd_vel`, `/imu`, `/odom`, `/odom_raw`, `/odom_reset`, `/scan`, `/servo_s1`, `/servo_s2`, `/tf`. `/odom_raw` la publica el firmware (`YB_Car_Node`) y `/odom` la publica `odom_corrector`; por eso se evalúa `/odom`.
5. *Frecuencias* (`ros2 topic hz`, dominio 8):

   | Topic | Frecuencia medida |
   |---|---|
   | `/odom` | ≈ 11.1 Hz |
   | `/odom_raw` | ≈ 11.1 Hz |
   | `/imu` | 23.5 a 25.0 Hz (22.1 Hz en la primera medición, con el dominio 20) |

6. *rosbag2.* Disponible con almacenamiento `sqlite3`. La cadena `grabar_bag.sh` → bag → `plot_odom.py` se comprobó con el robot quieto antes de empezar las corridas.
7. *Predicciones.* Escritas antes de cualquier medición en `informe/predicciones.md` (recta de 10 s a 0.10 m/s, giro con `b_eff = W` y dos grupos con el mismo dominio).

**Archivos:** `setup_log.txt` (nodos, topics con tipo, frecuencias, QoS y conexiones de la odometría, y nota del cambio de dominio), `config/entorno_rc0.sh`, `config/atajos_rc0.sh`, `informe/predicciones.md`. Las salidas de terminal de la sesión están en `docs/registro_sesion_2026-11-02.md`.

### Parte B — Recta de 1.0 m: calibración de `r`
**Qué se hace.** En la variante A1, de oeste a este sobre B4–C4, se manda `linear.x = 0.10 m/s` durante 10 s, con un bag grabando, y se mide con cinta la distancia real `d_real`. `analizar_bag.py` obtiene `d_odom` del bag y el error
`|d_real − d_odom| / d_real`. Se repite 3 veces. Solo se ajusta `r`; `b_eff` no se toca. Resultado: `linea_recta.csv` y el bag `rc0_recta`.

**Desarrollo.**
1. *Preparación.* Cinta masking marcando el inicio (borde A4|B4) y el fin (borde C4|D4) de las dos cartulinas amarillas. El robot se coloca con el eje de las ruedas sobre la línea de inicio, centrado en el carril y mirando al este. Una persona opera y frena; otra mide.
2. *Corrida.* `corrida recta A1 N` hace el preflight, pide confirmar la lista de seguridad (cargador desconectado, zona despejada, persona lista para frenar), graba el bag, ejecuta la secuencia con cuenta atrás y exige escribir `MOVER` antes de publicar en `/cmd_vel`.
3. *Medición.* `d_real` con cinta métrica, desde la línea de inicio hasta la misma marca del chasis; desvío lateral y su lado. `d_odom` sale del bag: desplazamiento entre el inicio y el fin del tramo en que el robot se movió.
4. *Resultados* (`r = 0.0311 m`, `b_eff = 0.2259 m`):

   | Corrida | Bag | `d_real` (m) | `d_odom` (m) | Error | Desvío (cinta) |
   |---|---|---|---|---|---|
   | 1 | `rc0_recta_c1_20261031_053920` | 0.975 | 0.9561 | 1.94 % | 0.018 m, derecha |
   | 2 | `rc0_recta_c2_20261031_054648` | 0.979 | 0.9541 | 2.54 % | 0.022 m |
   | 3 | `rc0_recta_c3_20261031_054915` | 0.964 | 0.9557 | 0.86 % | 0.018 m, derecha |

5. *Lectura.* El promedio de las tres corridas es `d_real` = 0.9727 m y `d_odom` = 0.9553 m, con un error ≈ 1.8 %; una corrida (la 2) supera el 2 %. En las tres corridas `d_odom < d_real`. `d_odom` es muy repetible (0.9541 a 0.9561 m, 2 mm de dispersión), mientras que `d_real` varía 1.5 cm entre corridas, comparable a la tolerancia del 2 % (2 cm sobre 1 m): la medición con cinta y el patinaje pesan tanto como el parámetro. El robot se desvía 1.8 a 2.2 cm a la derecha, y la odometría lo ve en dos de las tres corridas.
6. *Nota técnica.* La odometría que imprime el nodo de la secuencia (≈ 0.938 m) es menor que la del bag (≈ 0.956 m), porque el nodo deja de contar al terminar la orden y el bag incluye lo que el robot avanza hasta detenerse. La cinta también mide hasta donde se detuvo, así que el valor del bag es el comparable.

**Archivos:** `linea_recta.csv` (`corrida, r, d_real, d_odom, error_%, desvio_lateral`), `bags/rc0_recta_cN_<fecha>/` (cada corrida), `bags/rc0_recta/` (bag final), `bitacora_corridas.csv` (batería, parámetros y resultado de cada corrida), `bitacora_params.csv` (cada cambio de `r` o `b_eff`, si lo hubo).

### Parte C — Giro en sitio: calibración de `b_eff`
**Qué se hace.** Sobre la cartulina celeste (tile B2 de A1), con `r` fijo, el robot gira en sitio en sentido antihorario hasta que `/odom` acumule 360° (`calibrate_beff`, `angular_vel = 0.5 rad/s`). Se mide con cinta el ángulo físico real y el programa calcula el `b_eff` propuesto; se aplica y se repite hasta que el error sea menor del 1 %.
El error angular es `|medido − objetivo| / objetivo`.

**Método.** Una cruz de cinta en el centro del tile marca la posición y la orientación inicial; una línea de cinta en el chasis se alinea con ella. Después del giro se mide cuánto falta o sobra de la vuelta con la separación entre la línea del chasis y la del piso en dos distancias al centro (25 y 75 cm): `δ = arctan(Δseparación / 50 cm)`. El ángulo total es 360° ± δ según si el robot se pasó o se quedó corto. Se corrige solo `b_eff` (`aplicar wheel_separation`), nunca el objetivo ni el tiempo: lo que se calibra es la relación entre lo que dice `/odom` y lo que gira el robot.

**Archivos:** `calibration_log.csv` (`timestamp, iteracion, b_eff_antes, objetivo_deg, medido_deg, b_eff_despues, error_pct`), `bags/rc0_giro/` (bag del último giro), `config/wheel_params.yaml` (valores adoptados).

### Parte D — Validación en la segunda variante
**Qué se hace.** En la variante A2, con `r` y `b_eff` fijos y sin recalibrar: dos rectas de 1.0 m sobre C4–D4 (este → oeste, inicio D4|E4, fin B4|C4) y un giro de 360° en el tile A1 en sentido horario. Se mide cuánto se sostiene la calibración en otro montaje y se compara con el último error de A1.
Comandos: `corrida recta A2 N` y `corrida giro A2 N` (el giro horario usa `secuencia_rc0.py`, `angular.z` negativo).

**Archivos:** `validacion.csv` (`variante, prueba, valor_real, valor_odom, error_%`), `bags/rc0_val_recta/`, `bags/rc0_val_giro/`.

### Parte E — Gráficas e informe
**Qué se hace.** `plot_odom.py` lee cada bag final y genera dos PNG: la trayectoria x-y y la orientación θ(t) (con el ángulo desenvuelto, de modo que 360° se ve como 360° y no como 0°). Con los CSV, `generar_tablas_informe.py` arma las tablas del informe de una página: predicción, recta, `b_eff`, validación y explicación de las diferencias entre predicción y medición.

**Archivos:** `plots/` (8 PNG: dos por cada bag final), `informe.pdf`.

## Archivos resultantes por parte

| Parte | Archivos |
|---|---|
| A | `setup_log.txt`, `informe/predicciones.md`, `config/entorno_rc0.sh` |
| B | `linea_recta.csv`, `bags/rc0_recta/`, `bitacora_corridas.csv` |
| C | `calibration_log.csv`, `bags/rc0_giro/`, `config/wheel_params.yaml` |
| D | `validacion.csv`, `bags/rc0_val_recta/`, `bags/rc0_val_giro/` |
| E | `plots/` (8 PNG), `capytown_esan/plot_odom.py`, `informe.pdf` |

## Notas técnicas
- **Un parámetro a la vez:** `r` primero y `b_eff` después, porque `k_ang` depende de los dos.
- **Seguridad:** nada mueve el robot por defecto. `secuencia_rc0.py` y `corrida.sh` piden confirmación explícita, limitan la velocidad (0.20 m/s y 1.0 rad/s) y paran por odometría; el cargador se desconecta solo durante el movimiento.
- **Reloj de la Pi:** está desfasado, así que las fechas de logs y bags no son fiables; el orden de las corridas lo da el número de corrida.
- **Valores en caliente:** `aplicar_param.sh` cambia `r` y `b_eff` solo en la memoria de `odom_corrector`; al relanzar el bringup se cargan los de `wheel_params.yaml`.
