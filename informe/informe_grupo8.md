# RC-0 - Primer arranque y calibración del robot

**Grupo 8 · S-003** | Integrantes: Jorge Rivera, Harold Payco, Sebastián Escobar  | Calibración: A1 «Torre» | Validación: A2 «Escalón» | ROS_DOMAIN_ID=8

## Predicción inicial

Registrada el 30/10/2026, antes de cualquier medición. Para una orden de **0.10 m/s durante 10 s** se predijo que el robot avanzaría **98 cm** medidos con cinta y que `/odom` marcaría **100 cm**. Si se usa como **b_eff** solo el ancho físico W, se predijo que el robot gira **menos de 360° físicamente** cuando `/odom` marque 360°, por el deslizamiento de las ruedas y un ancho efectivo mayor que W. Si dos grupos usan el mismo ROS_DOMAIN_ID, se predijo que sus nodos y tópicos se mezclarían en la misma red ROS 2 y habría interferencia.

## Parte A - Arranque

Se verificó la cadena placa → micro-ROS → ROS 2 y la disponibilidad de `/cmd_vel`, `/odom`, `/imu` y `/scan`. Frecuencias observadas: **/odom ≈ 11.1 Hz** e **/imu ≈ 23.5 a 25.0 Hz**. La placa del RosCar 4 traía `ROS_DOMAIN_ID = 20` (valor de fábrica); se escribió **8** con `config_robot.py` y se verificó el aislamiento: en el dominio 20 ya no aparece ningún nodo y en el 8 aparecen `/YB_Car_Node` y `/odom_corrector`.

## Parte B - Calibración lineal de r (A1, RosCar 4)

| Corrida | r [m] | d_real [m] | d_odom [m] | error | desvío lateral [m] |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 0.0311 | 0.957 | 0.9487 | 0.87 % | 0.010 |
| 2 | 0.0311 | 0.963 | 0.9453 | 1.83 % | 0.020 |
| 3 | 0.0311 | 0.965 | 0.9587 | 0.65 % | 0.021 |
| 4 | **0.03145** | 0.965 | 0.9602 | **0.50 %** | 0.022 |

Las corridas 1 a 3 se hicieron con el `r = 0.0311 m` de partida: promedio `d_real` = 0.9617 m, `d_odom` = 0.9509 m, error medio ≈ 1.1 %, y `d_odom < d_real` en las tres (el modelo subestima la distancia, así que `r` debe **aumentar**). Se ajustó `r` a **0.03145 m** (ajuste hecho por el grupo a partir de estos datos) y la corrida 4 dio 0.50 %. *Prueba de sensibilidad (no son corridas de calibración):* con r = 0.023 m (el radio geométrico) el error fue 27.9 %, con 0.021 m 33.3 % y con 0.025 m 20.4 %; confirman que `r` es un parámetro efectivo y no el radio medido con regla. Después se volvió a 0.03145 m. *Pendiente:* corridas de confirmación con r = 0.03145 m (tres, para E3).

## Parte C - Calibración de b_eff (A1, RosCar 4, con r = 0.03145 m)

Medidas físicas: **W = 0.135 m** (centro a centro), diámetro de rueda 4.6 cm. El ángulo real se midió con el **método de la cuerda** (δ = 2·arcsen(c/2L), L = 50 cm). Los giros preliminares con r = 0.0311 (b_eff = 0.2259: 413° y 405°; b_eff = 0.2008: 315° y 320°) se contradicen entre sí y se descartan como evidencia (ver `docs/registro_roscar4.md`).

| Iteración | b_eff usado [m] | Sentido | Ángulo real | /odom acum. | Error | b_eff propuesto [m] |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 9 | 0.2125 | antihorario | 352° | 360° | 2.22 % | 0.2173 |
| 10 | 0.2152 | antihorario | 375° | 360° | 4.17 % | 0.2066 |
| 11 | 0.2138 | antihorario | 358° | 360° | 0.56 % | 0.2150 |
| 12 | 0.2138 | antihorario | 358° | 360° | 0.56 % | 0.2150 |

Valor adoptado: **b_eff = 0.2138 m**, error 0.56 % en dos giros seguidos (< 1 %). El sentido del cambio es coherente: al aumentar `b_eff` el robot gira más antes de que `/odom` marque 360° (352° → 375°). Limitaciones: la serie no parte de W = 0.135 m (las iteraciones preliminares se hicieron con otros valores) y el paso de 1 mm de `b_eff` mueve el giro ≈ 1.7°, del orden de la resolución de la medida con cinta; los dos 358° son idénticos y no prueban repetibilidad por sí solos.

## Parte E y análisis final

**Predicción vs. medición (recta).** Se predijeron 98 cm con cinta y se midieron entre 95.7 y 96.5 cm (promedio 96.2 cm con r = 0.0311): la distancia real quedó a ~1.8 cm de lo predicho. Para `/odom` se predijeron 100 cm y se obtuvieron entre 94.5 y 95.9 cm. La predicción de odometría suponía los parámetros nominales del firmware (`r0 = 0.0325 m`); con `r = 0.0311 m`, `odom_corrector` escala la distancia por `r / r0 = 0.9569`, de modo que `/odom` marca menos que el nominal. **Giro:** la predicción (gira menos de 360° con b_eff = W) no se contrastó tal cual, porque la serie de la Parte C no partió de W; con los b_eff efectivos (≈ 0.21 m, bastante mayor que W = 0.135 m) el robot giró 352°–375° cuando `/odom` marcó 360°. Esto es coherente con que `b_eff` sea un parámetro efectivo (deslizamiento de las ruedas, huella de contacto) y no el ancho geométrico. La predicción del dominio se evalúa con la Parte A (dominio 20 vacío).

**Graficas Reconstruidas:** Las gráficas de A, B y C se encuentran en `plots/graficas_reconstruidas`, estas fueron reconstruidas, debido a que el grupo no consiguió descargar las gráficas generadas por /odom_util, pero gracias a la IA, logramos reconstruirlas, tal cual estaba la original (solo teníamos capturas en baja calidad de las originales). La D no tiene un gráfico exacto por falta de pruebas.

**Parámetros:** r = 0.03145 m (Parte B; inicial 0.0311) | b_eff = 0.2138 m (Parte C, inicial: 0.2259) | **Archivos:** setup_log.txt, linea_recta.csv, calibration_log.csv, validacion.csv, bags rosbag, plot_odom.py y gráficas

