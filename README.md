# RC-0: Primer arranque y calibración del RosCar 4

Desarrollo del reto 0 del Proyecto CapyTown con el robot **MicroROS-Pi5 (RosCar 4)** (Raspberry Pi 5 con una placa ESP32-S3, ROS 2 Humble y micro-ROS).
Nuestro grupo pone en ejecución al robot, verifica la cadena **placa → micro-ROS → ROS 2**, y calibra los dos parámetros del modelo cinemático
que se usarán en los retos posteriores: el radio de rueda **r** y el ancho de vía efectivo **b_eff**.

## Equipo 
Número| Integrante | Parte realizado | Rol Asignado | 
|---|---|---|---|
|1| Jorge Rivera| parte A | Control |
|2| Harold Payco| parte B | Integración y planificacion |
|3| Sebastian Escobar | parte C | Percepcion |

## Datos 

|---|---|
| Sección | **S-003** |
| Variantes | **A1 «Torre»** (calibración, Partes B y C) · **A2 «Escalón»** (validación, Parte D) |
| Robot | **RosCar 4** (hostname `roscar4`, escritorio remoto `10.42.0.1::5900`). Reemplaza al RosCar 8, |
| `ROS_DOMAIN_ID` | **8** (equipo n → ROS_DOMAIN:n), en la Pi y en la placa. La placa del RosCar 4 venía con 20, el valor de fábrica de Yahboom |
| `r` (adoptado) | **0.03145 m** (inicial del docente: 0.0311 m) |
| `b_eff` (adoptado) | **0.2138 m** (inicial común: 0.2259 m) |
| Medidas físicas | Ancho entre ruedas W = 0.135 m (centro a centro; 0.150 m exterior, 0.113 m interior) con un diámetro de rueda 4.6 cm |
| Odometría evaluada | `/odom` (la publica `odom_corrector` a partir de `/odom_raw` del firmware) |

| | A1 (calibrar) | A2 (validar) |
|---|---|---|
| Recta de 1.0 m | B4–C4, oeste → este (inicio B4, fin C4) | C4–D4, este → oeste (inicio D4, fin C4) |
| Giro de 360° | tile B2, antihorario (`angular.z` +) | tile A1, horario (`angular.z` −) |

## Explicacion del reto 

El modelo es un **diferencial equivalente** (el robot tiene 4 ruedas sin dirección): la odometría que publica el firmware se re escala con dos factores,

- `k_lin = r / r0` sobre la distancia,
- `k_ang = (r / r0) · (b0 / b_eff)` sobre el giro,

donde `r0 = 0.0325 m` y `b0 = 0.24 m` son los valores que el firmware asume. Se calibra **un parámetro a la vez**:
primero `r` con una recta de 1.0 m (criterio: error ≤ 2 %), después `b_eff` con giros de 360° (criterio: error < 1 %), y se valida en la segunda variante **sin recalibrar**.
Se predice por escrito, antes de medir, qué se espera (`informe/predicciones.md`). 

## Estructura del repositorio

| Carpeta / archivo | Contenido |
|---|---|
| `capytown_esan/` | Código propio en Python |
| `scripts/` | Scripts de laboratorio (Parte A, sesión de medición, bags, verificación) |
| `config/` | `entorno_rc0.sh` y `atajos_rc0.sh` (dominio 8 y comandos cortos), `wheel_params.yaml` (parámetros del modelo) |
| `bags/` | Bags de ROS 2: una carpeta por corrida y los cuatro bags finales |
| `plots/` | Gráficas de los bags (x-y y θ(t)) y gráficas de resumen de la Parte B (`parteB_*.png`) |
| `informe/` | `predicciones.md`, `informe_grupo8.md/.pdf` (informe de 1 página) e `informe_plantilla.md` |
| `docs/` | Guías de trabajo, plan de la sesión, hoja de campo, notas del código del docente y registro de la sesión |
| `test/` | Pruebas automáticas con datos sintéticos |
| `linea_recta.csv`, `calibration_log.csv`, `validacion.csv`, `setup_log.txt` | Resultados de cada parte |

## Códigos

**Códigos propios**

| Archivo | Qué hace |
|---|---|
| `capytown_esan/odom_utils.py` | Matemática de odometría: yaw desde el cuaternión, desenvolvimiento del ángulo, desplazamiento longitudinal y lateral, errores, detección del tramo de movimiento y de reinicios |
| `capytown_esan/plot_odom.py` | Lee un bag (formato tomado de su `metadata.yaml`) y genera dos PNG: trayectoria x-y y orientación θ(t) |
| `capytown_esan/analizar_bag.py` | Del bag a los números de los CSV: `d_odom`, desvío lateral, ángulo acumulado y error; escribe la fila solo si se pide |
| `capytown_esan/secuencia_rc0.py` | Secuencia de recta y de giro con tope de velocidad, diagnóstico previo, parada por odometría y confirmación explícita antes de mover (por defecto no mueve) |
| `scripts/parteA_host.sh`, `parteA_contenedor.sh` | Diagnóstico de solo lectura de la Parte A (host y contenedor); añade a `setup_log.txt` |
| `scripts/preflight.sh` | Comprobaciones antes de mover: dominio, nodos, topics, suscriptores de `/cmd_vel`, `/odom`, `r` y `b_eff` vivos, batería, disco |
| `scripts/corrida.sh` | Corrida guiada: preflight, lista de comprobación, bag, movimiento, medición con cinta, análisis y fila de CSV |
| `scripts/aplicar_param.sh` | Cambia `wheel_radius` o `wheel_separation` , valida, pide confirmación y deja registro |
| `scripts/grabar_bag.sh`, `fijar_bag_final.sh`, `respaldar_bags.sh` | Grabación con nombre único, copia al nombre final del entregable y respaldo |
| `scripts/instalar_rosbag2.sh` | Comprobación de rosbag2 (instalación solo si falta y con aprobación) |
| `scripts/verificacion_entrega.py`, `generar_tablas_informe.py` | Revisión de lo que contiene la entrega y tablas del informe a partir de los CSV |
| `config/atajos_rc0.sh` | Comandos cortos: `preflight`, `corrida`, `aplicar`, `bringup`, `parteA`, `grabar`, `secuencia`, `graficar`, `analizar`, `fijar`, `verificar`, `tablas`, `ayuda` |

**Códigos compartidos** (paquete `capytown_esan` instalado en el robot, sin modificar sus algoritmos): `odom_corrector` (aplica `r` y `b_eff` a `/odom_raw` y publica `/odom` y `tf`),
`calibrate_beff` (giro hasta acumular el ángulo objetivo y cálculo de `b_eff`), `teleop_key`, `fake_robot`, `error_odom`, `run_square`, `bringup.launch.py`. 

## Las partes

### Parte A — Arranque
**¿Qué es lo que se hace?** Se enciende el robot y se verifica la cadena placa → micro-ROS → ROS 2: nodo de la placa, topics `/cmd_vel`, `/odom`, `/imu`, `/scan`, frecuencias de `/odom` e `/imu`,
dominio igual en la Pi y la placa, aislamiento (solo se ve el robot propio), rosbag2 y `rqt_graph`. Resultado: `setup_log.txt`.

**Desarrollo (RosCar 4).**
1. *Cambio de robot* El trabajo empezó con el RosCar 8, pero cuando conocimos que se compartía con otro grupo de la misma sección sección, el grupo buscó y continuó con el **RosCar 4**, repitiendo las Partes A y B. `r` y `b_eff` se volvieron a calibrar en este nuevo carrito.
2. *Identificación* Raspberry Pi 5 y ESP32-S3 unidos por serie (`/dev/ttyUSB0`, 921600). El micro-ROS Agent corre como el contenedor `micro_ros_agent` (política `unless-stopped`); el trabajo con ROS 2 se hace en el contenedor `ros2_dev`.
3. *Dominio* La placa venía en `ROS_DOMAIN_ID = 20`. Para usar el dominio del grupo (8) se escribió el valor con `config_robot.py` (línea 496) con el Agent detenido y el botón de reinicio de la placa (los intentos sin esas condiciones nos devolvían `None`), se cambió el `.bashrc` del contenedor y se verificó que `/YB_Car_Node` aparezca en el dominio 8 y el 20 queda vacío (E2). Respaldos de los archivos originales (`*.orig_dominio20`).
4. *Bringup y parámetros iniciales* Este robot trae un paquete compilado por otro grupo (`src/Grupo7-S003`) y no el `wheel_params.yaml` del docente; no se usan ni se copian sus parámetros. Se lanza `odom_corrector` con el YAML común de todos los carros (copia en el repo): `r = 0.0311 m`, `b_eff = 0.2259 m`, es decir `k_lin = 0.9569` y `k_ang = 1.0167`. El código instalado de `odom_corrector.py` y `calibrate_beff.py` coincide por `sha256` con el del docente.
5. *Topics* `/battery`, `/beep`, `/cmd_vel`, `/imu`, `/odom`, `/odom_raw`, `/odom_reset`, `/scan`, `/servo_s1`, `/servo_s2`, `/tf`. `/odom_raw` la publica el firmware (`YB_Car_Node`) y `/odom` la publica `odom_corrector`; por eso se evalúa `/odom`.
6. *Frecuencias* (`ros2 topic hz`, dominio 8):

   | Topic | Frecuencia medida |
   |---|---|
   | `/odom` | 11.16 y 11.09 Hz |
   | `/odom_raw` | 11.05 y 11.11 Hz |
   | `/imu` | 24.91 Hz |

7. *rosbag2 y `rqt_graph`.* rosbag2 con `sqlite3`. El grafo muestra `/cmd_vel`, `/beep`, `/servo_s1`, `/servo_s2` → `/YB_Car_Node` → `/battery`, `/imu`, `/scan`, `/odom_raw`; y `/odom_raw` + `/odom_reset` → `/odom_corrector` → `/odom`, `/tf`.
8. *Predicciones.* Escritas antes de cualquier medición en `informe/predicciones.md` (recta de 10 s a 0.10 m/s, giro con `b_eff = W` y dos grupos con el mismo dominio).

**Archivos:** `setup_log.txt` (nodos, topics con tipo, frecuencias, QoS, E2 y nota del cambio de dominio), `plots/rqt_graph_roscar4.png`, `config/entorno_rc0.sh`, `config/atajos_rc0.sh`, `informe/predicciones.md`. Detalle y salidas de terminal: `docs/registro_roscar4.md`.

### Parte B — Recta de 1.0 m: calibración de `r`
**¿Qué es lo que se hace?** En la variante A1, de oeste a este sobre B4–C4, se manda `linear.x = 0.10 m/s` durante 10 s, con un bag grabando, y se mide con cinta la distancia real `d_real`. `analizar_bag.py` obtiene `d_odom` del bag y el error
`|d_real − d_odom| / d_real`. Solo se ajusta `r`; `b_eff` no se toca. Resultado: `linea_recta.csv` y el bag `rc0_recta`.

**Desarrollo (RosCar 4).**
1. *Preparación* Cinta masking marcado en el inicio (borde A4|B4) y en el fin (borde C4|D4) de las dos cartulinas amarillas. El robot se coloca con la marca del chasis sobre la línea de inicio, centrado en el carril y mirando al este, la wincha queda extendida a lo largo del carril, lejos de las ruedas. El segundo integrante calibro y mando la ejecucion, el primero midio.
2. *Corrida.* `corrida recta A1 N` hace el preflight, pide confirmar la lista de seguridad (cargador desconectado, zona despejada, persona lista para frenar), graba el bag, ejecuta la secuencia con cuenta atrás y exige escribir `MOVER` antes de publicar en `/cmd_vel`.
3. *Medición.* `d_real` con cinta métrica, de la línea de inicio a la misma marca del chasis; desvío lateral y su lado. `d_odom` sale del bag: desplazamiento entre el inicio y el fin del tramo en que el robot se movió.
4. *Corridas con el `r` inicial* (`r = 0.0311 m`):

   | Corrida | `d_real` (m) | `d_odom` (m) | Error | Desvío (cinta) |
   |---|---|---|---|---|
   | 1 | 0.957 | 0.9487 | 0.87 % | 0.010 m |
   | 2 | 0.963 | 0.9453 | 1.83 % | 0.020 m, izquierda |
   | 3 | 0.965 | 0.9587 | 0.65 % | 0.021 m, izquierda |

   Promedio: `d_real` = 0.9617 m, `d_odom` = 0.9509 m, error medio ≈ 1.1 %; en las tres, `d_odom < d_real`.
5. *Ajuste de `r`.* El corrector multiplica la distancia por `k_lin = r/r0`; como `d_odom` quedó por debajo de `d_real`, se deduce un `r` ligeramente mayor, a partir del promedio de las tres corridas: **`r = 0.03145 m`** (+1.1 %, que coincide con el error medio). Se aplicó con `aplicar wheel_radius` y se repitió la recta.
6. *Corrida con el `r` ajustado:*

   | Corrida | `r` (m) | `d_real` (m) | `d_odom` (m) | Error | Desvío (cinta) |
   |---|---|---|---|---|---|
   | 4 | **0.03145** | 0.965 | 0.9602 | **0.50 %** | 0.022 m, derecha |

7. *Prueba de sensibilidad (corridas 5 y 6).* Con `r` muy distintos, `d_odom` resultó **proporcional a `r`**:

   | Corrida | `r` (m) | `d_real` (m) | `d_odom` (m) | Error | `d_odom / r` |
   |---|---|---|---|---|---|
   | 5 | 0.0230 | 0.960 | 0.6926 | 27.85 % | 30.1 |
   | 5 (repetida) | 0.0210 | 0.955 | 0.6368 | 33.32 % | 30.3 |
   | 6 | 0.0250 | 0.960 | 0.7637 | 20.45 % | 30.6 |
   | 4 (referencia) | 0.03145 | 0.965 | 0.9602 | 0.50 % | 30.5 |

   Esto confirma `k_lin ∝ r` y que el **radio geométrico de la rueda (0.023 m) no sirve como `r`**: `r` es un parámetro efectivo que se calibra con la recta. Estas corridas son pruebas del comportamiento del modelo, no parte de la calibración final; se conservan en el CSV (la etiqueta «5» está repetida; en la corrida 5 el desvío se tecleó 0.18 m, probablemente 0.018 m).
8. *Nota técnica.* La odometría que imprime el nodo de la secuencia es menor que la del bag, porque el nodo deja de contar al terminar la orden y el bag incluye lo que el robot avanza hasta detenerse. La cinta también mide hasta donde se detuvo, así que el valor del bag es el comparable.

**Resultado:** `r = 0.03145 m` (error de la recta 0.50 %, bajo el 2 % del reto).

**Archivos:** `linea_recta.csv` (`corrida, r, d_real, d_odom, error_%, desvio_lateral`), `bags/rc0_recta_cN_<fecha>/` (cada corrida), `bags/rc0_recta/` (bag final), `bitacora_corridas.csv` (batería, parámetros y resultado de cada corrida), `bitacora_params.csv` (cada cambio de `r` o `b_eff`).

### Parte C — Giro en sitio: calibración de `b_eff`
**¿Qué es lo que se hace?** Sobre la cartulina celeste (tile B2 de A1), con `r` fijo, el robot gira en sitio en sentido antihorario hasta que `/odom` acumule 360° (`calibrate_beff`, `angular_vel = 0.5 rad/s`). Se mide con cinta el ángulo físico real y el programa calcula el `b_eff` propuesto; se aplica y se repite hasta que el error sea menor del 1 %.
El error angular es `|medido − objetivo| / objetivo`.

**Método de medida.** Una cruz de cinta en el centro del tile marca la posición y la orientación inicial; una línea de cinta en el chasis se alinea con ella. Con el robot detenido y sin tocarlo, se tiende una tira de cinta sobre la línea del chasis, se marcan puntos a L = 50 cm del centro sobre la línea de referencia y sobre esa tira, se mide la cuerda `c` entre ellos y `δ = 2·arcsen(c / 2L)`; el ángulo total es 360° ± δ. Con un video se confirma que fue una sola vuelta. (El método de las dos distancias con `arctan`, usado al principio, solo vale para ángulos pequeños.)

**Desarrollo (RosCar 4).**
1. *Medidas físicas* Ancho entre ruedas centro a centro **W = 0.135 m** (exterior 0.150 m, interior 0.113 m; coherentes: (0.150 + 0.113)/2 = 0.1315 m) y diámetro de rueda 4.6 cm. `b_eff` y `r` no coinciden con la geometría: son parámetros efectivos (en un robot de cuatro ruedas sin dirección el deslizamiento hace que `b_eff` sea mayor que W).
2. *Serie preliminar* (con `r = 0.0311`, `b_eff = 0.2259` y luego 0.2008): giros de 413°, 405°, 315° y 320°. Las cuatro mediciones se contradecían entre sí (error de medición cercano a ±45°), por lo que **no se usaron para calibrar**.
3. *Serie con `r = 0.03145` ya fijo.* Se partió del candidato `b_eff = 0.2125 m` (calculado por el grupo con los giros preliminares):

   | `b_eff` usado (m) | Ángulo medido | Error | `b_eff` propuesto (m) |
   |---|---|---|---|
   | 0.2125 | 352° | 2.22 % | 0.2173 |
   | 0.2152 | 375° | 4.17 % | 0.2066 |
   | **0.2138** | **358°** | **0.56 %** | 0.2150 |
   | **0.2138** (repetición) | **358°** | **0.56 %** | 0.2150 |

   El valor intermedio 0.2138 dio error 0.56 % en dos giros (`i11` e `i12`, `/odom` acumuló 361.8° y 361.5°). El giro de 375° con 0.2152 desentona (se esperaban ~360°) y se considera una lectura atípica.
4. *Comprobación.* Entre 0.2125 y 0.2138, el giro medido cambió de 352° a 358°, como predice la proporcionalidad entre el giro físico y `b_eff`.

**Resultado:** `b_eff = 0.2138 m` (error 0.56 % < 1 %). La proporción `b_eff / W ≈ 1.58` es de la magnitud esperada para un robot de ruedas sin dirección.

**Archivos:** `calibration_log.csv` (`timestamp, iteracion, b_eff_antes, objetivo_deg, medido_deg, b_eff_despues, error_pct`), `bags/rc0_giro/` (bag del último giro), `config/wheel_params.yaml` (valores adoptados: `r = 0.03145`, `b_eff = 0.2138`).

### Parte D — Validación en la segunda variante
**¿Qué es lo que se hace?** En la variante A2, con `r` y `b_eff` fijos y sin recalibrar: dos rectas de 1.0 m sobre C4–D4 (este → oeste, inicio D4|E4, fin B4|C4) y un giro de 360° en el tile A1 en sentido horario. Se mide cuánto se sostiene la calibración en otro montaje y se compara con el último error de A1. 
Comandos: `corrida recta A2 N` y `corrida giro A2 N` (el giro horario usa `secuencia_rc0.py`, `angular.z` negativo).

**Archivos:** `validacion.csv` (`variante, prueba, valor_real, valor_odom, error_%`), `bags/rc0_val_recta/`, `bags/rc0_val_giro/`.

### Parte E — Gráficas e informe
**¿Qué es lo que se hace?** `plot_odom.py` lee cada bag final y genera dos PNG: la trayectoria x-y y la orientación θ(t) (con el ángulo desenvuelto, de modo que 360° se ve como 360° y no como 0°). Con los CSV, `generar_tablas_informe.py` arma las tablas del informe de una página: predicción, recta, `b_eff`, validación y explicación de las diferencias entre predicción y medición. Las gráficas de B y C se encuentran en `plots/`. La D no tiene un gráfico exacto por falta de pruebas

**Archivos:** `plots/`, `informe.pdf`.

## Archivos resultantes por parte

| Parte | Archivos |
|---|---|
| A | `setup_log.txt`, `informe/predicciones.md`, `config/entorno_rc0.sh` |
| B | `linea_recta.csv`, `bags/rc0_recta/`, `bitacora_corridas.csv` |
| C | `calibration_log.csv`, `bags/rc0_giro/`, `config/wheel_params.yaml` |
| D | `validacion.csv`, `bags/rc0_val_recta/`, `bags/rc0_val_giro/` |
| E | `plots/`, `capytown_esan/plot_odom.py`, `informe.pdf` |

## Aclaración sobre uso de IA y trabajo en equipo
**¿Dónde se usó?** Realización de códigos y scripts para el desarrollo del reto 0 (proyecto CapyTown), estructura de la documentación e informe requeridos.


**¿Qué trabajo realizó el grupo?** El grupo realizó las mediciones, ejecuciones de comandos, pruebas y calibraciones de los parámetros, a parte del cirucito físico. El segundo integrante se encargó de todo el repositorio (incluyendo códigos, documentos, estructura y subida de los archivos correspondientes obtenidos durante las reservas de laboratorio), además de la verificación de todos los archivos dentro de este. 
