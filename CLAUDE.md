# CLAUDE.md — RC-0 «Primer arranque y calibración» · Grupo 8 · RosCar 8

Idioma de trabajo: español. Este archivo resume el contexto vigente; si algo contradice a los documentos del docente, mandan ellos.

## Hechos vigentes (los contextos antiguos decían S-004: está superado)
- Robot: Yahboom MicroROS-Pi5 (Raspberry Pi 5 + ESP32-S3, ROS 2 Humble, micro-ROS). **RosCar 8**, Wi-Fi `RosCar8`, VNC `10.42.0.1::5900`.
- **Sección S-003:** calibra en **A1 «Torre»**, valida en **A2 «Escalón»**.

  | | A1 (calibrar) | A2 (validar, sin recalibrar) |
  |---|---|---|
  | Recta 1.0 m | B4–C4, oeste → este (inicio A4\|B4, fin C4\|D4) | C4–D4, este → oeste (inicio D4\|E4, fin B4\|C4) |
  | Giro 360° | tile B2, **antihorario** (`angular.z` +) | tile A1, **horario** (`angular.z` −) |

- **Dominio ROS:** el contenedor `micro_ros_agent` del RosCar 8 corre con `ROS_DOMAIN_ID=20` (verificado con `docker inspect`); el reto pide "equipo n → n" (8). Hasta que el docente diga cuál y cómo cambiarlo, se trabaja en **20** (`config/entorno_rc0.sh`); no se toca el Agent. El 92 del JetCobot no se usa.
- Repo: el reto pide `capytown_G<n>` con tag `v1.0-rc0`; el nombre actual es `RC-0_MicroRos_Pi5` → renombrar antes de entregar (confirmar con el docente).
- Quien trabaja: el grupo, desde el Pi 400 (Ubuntu) o una laptop, por TigerVNC/SSH. El Wi-Fi del robot probablemente no tiene internet.
- El docente permite IA para código y depuración; la nota depende de la **defensa individual sin código a la vista**: el autor debe entender todo lo que se genere.

## Reglas de trabajo
1. Cada comando indica dónde corre: `[PC]`, `[PI HOST]` o `[DOCKER ROS 2]`.
2. **Descubrir antes de asumir:** no inventar contenedor, topics, claves del YAML, usuario SSH ni valores. Si no está confirmado, decirlo y proponer cómo comprobarlo.
3. **Nunca mover el robot por iniciativa propia.** Todo movimiento (`/cmd_vel`, `calibrate_beff`, teleop, `secuencia_rc0.py` con `dry_run:=false`) lo ejecuta una persona junto al robot, con zona despejada y forma de detenerlo.
4. **No cambiar el sistema sin aprobación:** `sudo`, `apt`, `docker run/stop/commit`, `.bashrc`, dominio, firmware, `wheel_params.yaml` del robot, reinicio de bringup/Agent. No duplicar el micro-ROS Agent.
5. **No inventar datos.** Ningún CSV, bag, gráfica, predicción ni medición se fabrica; los datos sintéticos se marcan `SINTETICO` y no son evidencia.
6. **Las predicciones las escribe el grupo antes de medir** y no se editan después.
7. **Las reglas de corrección de `r` y `b_eff` las deduce el grupo** (pregunta de defensa). Guiar con preguntas y ayudar a verificar con datos; no entregarlas hechas.
8. Un parámetro a la vez: primero `r` (recta), luego `b_eff` (giro). En A2 no se corrige nada.
9. No `git push`, `git tag` ni borrar archivos/bags sin que el grupo lo pida. Nunca credenciales en el repo.
10. Fuera de alcance: cuadrado (RC-1), IMU/EKF, cámara/carril (RC-2), LiDAR/navegación (RC-3+).
11. Distinguir siempre: *tests en verde* ≠ *integración con ROS* ≠ *comportamiento físico observado*. Un test no es una calibración.

## Mapa del repositorio
- `capytown_esan/`: `odom_utils.py` (matemática), `plot_odom.py` (E6), `analizar_bag.py` (bag → CSV), `secuencia_rc0.py` (recta/giro con dry-run por defecto).
- `scripts/`: Parte A (`parteA_host.sh`, `parteA_contenedor.sh`, `instalar_rosbag2.sh`), bags (`grabar_bag.sh`, `fijar_bag_final.sh`, `respaldar_bags.sh`), `verificacion_entrega.py`, `generar_tablas_informe.py`.
- `docs/`: `guia_trabajo_roscar.md`, `hoja_de_campo_rc0.md`, `notas_codigo_docente.md`. `informe/`: predicciones y plantilla. `test/`: `python3 -m pytest test`.

## Pendientes por verificar en el robot
Qué `launch` levanta `odom_corrector` y con qué valores de arranque (YAML real) · qué dominio usa de verdad la placa (el docente menciona 20; nosotros usamos 8) · si el Agent (contenedor `micro_ros_agent`, serie `/dev/ttyUSB0`) arranca solo · definición del error angular (el script del docente divide por el objetivo) · watchdog de `/cmd_vel` y efecto del botón de reinicio · usuario SSH (`pi`) y entorno ROS dentro de `ros2_dev` · internet en `RosCar8` (no hay) · reloj de la Pi desfasado (fechas de logs/bags no fiables).

Hallazgos del código del docente: ver `docs/notas_codigo_docente.md` (`r` y `b_eff` se aplican en `odom_corrector`, no en el firmware; `calibrate_beff` admite giro horario y escribe su propio `calibration_log.csv`).

## Estado
Hecho solo con datos sintéticos y sin ROS real: ver `README.md`. Aún no se ha tocado el robot.
