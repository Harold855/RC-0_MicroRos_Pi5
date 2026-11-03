# RC-0 - Primer arranque y calibración del robot

**Grupo 8 · S-003** | Integrantes: H.L.P.E, R.S.E.R, J.D.R.N | Calibración: A1 «Torre» | Validación: A2 «Escalón» | ROS_DOMAIN_ID=8

## Predicción inicial

Registrada el 30/10/2026, antes de cualquier medición. Para una orden de **0.10 m/s durante 10 s** se predijo que el robot avanzaría **98 cm** medidos con cinta y que `/odom` marcaría **100 cm**. Si se usa como **b_eff** solo el ancho físico W, se predijo que el robot gira **menos de 360° físicamente** cuando `/odom` marque 360°, por el deslizamiento de las ruedas y un ancho efectivo mayor que W. Si dos grupos usan el mismo ROS_DOMAIN_ID, se predijo que sus nodos y tópicos se mezclarían en la misma red ROS 2 y habría interferencia.

## Parte A - Arranque

Se verificó la cadena placa → micro-ROS → ROS 2 y la disponibilidad de `/cmd_vel`, `/odom`, `/imu` y `/scan`. Frecuencias observadas: **/odom ≈ 11.1 Hz** e **/imu ≈ 23.5 a 25.0 Hz**. La placa traía `ROS_DOMAIN_ID = 20` (valor de fábrica); se escribió **8** con `config_robot.py` y se verificó el aislamiento: en el dominio 20 ya no aparece ningún nodo y en el 8 aparecen `/YB_Car_Node` y `/odom_corrector`.

## Parte B - Calibración lineal de r (A1)

| Corrida | r [m] | d_real [m] | d_odom [m] | error | desvío lateral [m] |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 0.0311 | 0.960 | 0.9596 | 0.04 % | 0.030 |
| 2 | 0.0311 | 0.979 | 0.9541 | 2.54 % | 0.022 |
| 3 | 0.0311 | 0.964 | 0.9557 | 0.86 % | 0.018 |

Las tres corridas se hicieron con **r = 0.0311 m** (valor de partida). Promedio: `d_real` = 0.9677 m, `d_odom` = 0.9565 m, error medio ≈ **1.1 %**; una corrida (la 2) supera el 2 %. En las tres, `d_odom ≤ d_real`. `d_odom` es muy repetible (5 mm de dispersión) y `d_real` varía 1.9 cm entre corridas, comparable a la tolerancia del 2 %.

## Parte C - Calibración de b_eff (A1)

| Iteración | b_eff usado [m] | Sentido | Ángulo real | /odom acum. | Error | b_eff propuesto [m] |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| | | | | | | |

## Parte D - Validación sin recalibrar (A2)

| Prueba | Valor real | Valor /odom | Error |
|:---:|:---:|:---:|:---:|
| Recta 1 | | | |
| Recta 2 | | | |
| Giro 360° (horario) | | | |

## Parte E y análisis final

**Predicción vs. medición (recta).** Se predijeron 98 cm con cinta y se midieron entre 96.0 y 97.9 cm (promedio 96.8 cm): la distancia real quedó a ~1.2 cm de lo predicho. Para `/odom` se predijeron 100 cm, y se obtuvieron entre 95.4 y 96.0 cm. La predicción de odometría suponía los parámetros nominales del firmware (`r0 = 0.0325 m`); con el `r = 0.0311 m` de partida, `odom_corrector` escala la distancia por `r / r0 = 0.9569`, de modo que `/odom` marca menos que el nominal. Las predicciones del giro y del dominio se evalúan con las Partes C y D.

**Parámetros:** r = 0.0311 m (Parte B) | b_eff de partida = 0.2259 m | **Archivos:** setup_log.txt, linea_recta.csv, calibration_log.csv, validacion.csv, bags rosbag, plot_odom.py y gráficas
