# Notas sobre los archivos del docente (`capytown_esan`)

Archivos revisados: `calibrate_beff.py`, `odom_corrector.py`, `fake_robot.py`, `teleop_key.py`, `run_square.py`, `error_odom.py`, `__init__.py` (vacío).
**No hemos visto** `bringup.launch.py` ni el `wheel_params.yaml` real: ahí está lo que falta por confirmar. Estas notas describen lo que el código *hace*; que el robot lo ejecute así es **[VERIFICAR]**.

## `odom_corrector.py` — dónde se aplican `r` y `b_eff`
- Suscribe `/odom_raw` (firmware) y publica **`/odom`** (+ TF `odom → base_footprint`). El firmware conserva sus valores fijos `r0` y `b0` (`firmware_wheel_radius`, `firmware_wheel_separation`).
- Parámetros ROS: `wheel_radius` (r) y `wheel_separation` (b_eff). Los cambia en caliente (`ros2 param set /odom_corrector wheel_radius <valor>`) o desde el YAML al relanzar.
- Re-escala la odometría con factores `k_lin` (distancia) y `k_ang` (giro) calculados a partir de esos parámetros (líneas 72-78 y 112-146). **Lee ese código y deduce qué reporta `/odom` antes y después de cambiar `r` o `b_eff`**: es la base de las preguntas de defensa 5 a 8.
- Consecuencias: `/odom` depende del YAML; `/odom_raw` no. Si el nodo no está corriendo, **no existe `/odom`**. Hay que registrar qué valores de arranque tenía.
- La pose se acumula con incrementos de `/odom_raw`: si el robot se reinicia y `/odom_raw` vuelve a 0, `/odom` da un salto (lo detecta `detectar_reinicios`). `/odom_reset` (std_msgs/Empty) pone a cero la pose del corrector.
- Su mensaje de aviso dice `ROS_DOMAIN_ID=20`, y **el contenedor `micro_ros_agent` del RosCar 8 efectivamente corre con 20**. El reto pide el número de grupo (8): preguntar al docente cuál debe usarse y cómo cambiarlo; no tocar el Agent.

## `calibrate_beff.py`
- Parámetros: `b_eff` (por defecto 0.24; **debe coincidir con el YAML**), `target_angle_deg` (360), `angular_vel` (0.5, + = antihorario), `cmd_vel_topic`, **`odom_topic` (por defecto `/odom`)**.
- Si `/odom` no llega en 10 s, avisa y **sale sin mover el robot**. Si `/odom` desaparece a mitad del giro, sigue girando hasta el tiempo máximo (3 × lo esperado ≈ 38 s a 0.5 rad/s): tener a alguien listo para frenar.
- Acumula `|Δyaw|` hasta llegar al objetivo: **funciona con `angular_vel` negativo** (horario). En A1 se usa positivo (antihorario).
- Es interactivo: ENTER para empezar y luego pide el ángulo medido con transportador.
- **Error angular = |medido − objetivo| / objetivo**: el denominador es el objetivo (el ángulo "reportado"). Coincide con lo que usan nuestras herramientas por defecto.
- Escribe `calibration_log.csv` **en el directorio desde el que lo lances**, con el encabezado
  `timestamp,iteracion,b_eff_antes,objetivo_deg,medido_deg,b_eff_despues,error_pct` (la columna `iteracion` vale siempre 1 por ejecución).
  Ese es ahora el encabezado de nuestro `calibration_log.csv`, para que no se mezclen formatos.
- Imprime la corrección propuesta de `b_eff` y el sentido (más/menos). **Entiende por qué antes de aplicarla**; la defensa pregunta esto.
- Con `odom_corrector` activo, lánzalo con `-p b_eff:=<valor del YAML>` y deja `odom_topic:=/odom`. Si solo existiera `/odom_raw`: `-p odom_topic:=/odom_raw`.

## `fake_robot.py` — simulador para probar sin motores
Suscribe `/cmd_vel` y publica `/odom` (integra la ω comandada), `/odom_true` y `/true_yaw_deg` (el giro "físico" = ω · b_model / b_true). Sirve para ensayar de punta a punta, con ROS 2 real, **nuestras herramientas y la calibración**:

```bash
# [DOCKER ROS 2] terminal 1 — dominio AISLADO del robot real (no uses 8 ni 20)
export ROS_DOMAIN_ID=77
ros2 topic list        # debe mostrar solo /rosout y /parameter_events; si aparece algo más, NO sigas
python3 <ruta_a>/fake_robot.py --ros-args -p b_eff_true:=0.27

# terminal 2, mismo dominio
export ROS_DOMAIN_ID=77
bash scripts/grabar_bag.sh SIMULADO_giro          # luego, en otra terminal:
python3 capytown_esan/secuencia_rc0.py --ros-args -p modo:=giro -p dry_run:=false -p confirmar_movimiento:=true
```
Después `plot_odom.py` y `analizar_bag.py` sobre ese bag prueban la lectura con `rosbag2_py` real. **Nada de eso es evidencia**: el bag se llama `SIMULADO_*` y `verificacion_entrega.py` lo rechaza como dato sintético si se cuela en `bags/` (usa el prefijo `SINTETICO` si prefieres que lo marque automáticamente).

## Lo demás
- `teleop_key.py`: `w/s` adelante/atrás (**`s` es marcha atrás**), `a/d` giro izq/der, espacio o `k` frena, `q` sale. Publica continuamente: soltar la tecla da velocidad 0. Mueve el robot: solo con permiso y supervisión.
- `run_square.py` y `error_odom.py`: cuadrado en lazo abierto (RC-1). Fuera de alcance. (`error_odom` lee solo bags `sqlite3`.)
- `__init__.py` vacío: `capytown_esan` es un paquete Python; nuestra carpeta `capytown_esan/` también lleva uno, pero **no** es un paquete ROS instalable: se ejecuta con `python3 capytown_esan/<archivo>.py`.

## Qué confirmar en el robot (solo lectura)
```bash
# [PI HOST]
cat ~/ros2_humble.sh ~/start_agent_rpi5.sh
ls ~/reset_esp32.sh
docker inspect micro_ros_agent --format '{{.Config.Env}} {{.Config.Cmd}}'
docker inspect ros2_dev --format '{{.Config.Env}} {{.Mounts}}'
```

## Lo confirmado en el RosCar 8 (salida real de la Pi)
- Contenedores: `micro_ros_agent` (`microros/micro-ros-agent:humble`) y `ros2_dev` (`yahboomtechnology/ros-humble:4.1.2`).
- Agent: `serial --dev /dev/ttyUSB0 -b 921600 -v4`, `ROS_DOMAIN_ID=20`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `MICROROS_DISABLE_SHM=1`.
- `~/ros2_humble.sh` solo hace `docker start ros2_dev` y `docker exec -it -e DISPLAY ros2_dev bash`: **no crea contenedores**. `ros2_dev` sobrevive a reinicios (`--restart unless-stopped`) y conserva lo que se instale dentro; el workspace vive en `/home/pi/yahboomcar_ws` (host).
- Existe `~/reset_esp32.sh` (lo mencionan los scripts del docente para reconectar la placa).

## Más hallazgos (segunda salida de la Pi)
- `~/start_agent_rpi5.sh` es una versión del laboratorio ("rebaño"): **no crea contenedores nuevos**, asegura que `micro_ros_agent` exista y corra con `ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-20}` y muestra sus logs. El original de fábrica (efímero, dominio 0) está en `start_agent_rpi5.sh.orig`. Si los topics no traen datos: botón RST del ESP32. **El dominio 20 parece una configuración deliberada del laboratorio para todos los robots.** [Probable] Preguntar al docente si el dominio "del grupo" (E2) debe ser 20 u 8.
- `ros2_dev` monta `/home/pi/yahboomcar_ws` (host) en `/root/yahboomcar_ws` (contenedor), además de `/dev`, `/dev/shm` y `/tmp/.X11-unix` (la GUI, p. ej. `rqt_graph`, sale por el escritorio remoto). Copiar el repo a esa carpeta del host lo hace visible dentro, sin `docker cp`.
- Al entrar al contenedor imprime `MY_DOMAIN_ID: 20`. Con el Agent en marcha y SIN bringup, `ros2 topic list -t` (dominio 20) muestra: `/battery` (UInt16), `/beep` (UInt16), `/cmd_vel` (Twist), `/imu` (Imu), `/odom_raw` (Odometry), `/scan` (LaserScan), `/servo_s1` y `/servo_s2` (Int32). **No hay `/odom`**: `odom_corrector` no está corriendo todavía.
- `/battery` permite registrar la carga de cada corrida (`grabar_bag.sh` lo graba). Unidad **[VERIFICAR]** (`ros2 topic echo /battery --once`). No publiques en `/beep`, `/servo_s1`, `/servo_s2`.

## Parte A en el contenedor (salida real, RosCar 8, reloj de la Pi desfasado)
- Nodo de la placa: `/YB_Car_Node`. `/odom_raw`: RELIABLE, VOLATILE, 0 suscriptores. `/imu` medida ≈ 24.1–24.3 Hz (no 50). Frecuencia de `/odom_raw`: pendiente de medir (el script la perdía por un traceback; corregido).
- **rosbag2 NO está instalado en `ros2_dev`** (`ros2 bag` no existe). El robot no tiene internet por `RosCar8`: hace falta salida a internet (p. ej. Ethernet del laboratorio) o una instalación alternativa del docente. **Bloquea la grabación de los 4 bags.**
- `capytown_esan` instalado en `/root/yahboomcar_ws/install/capytown_esan` (`share/`: `config`, `launch`). Pendiente: leer `launch/bringup.launch.py` y `config/wheel_params.yaml` reales.
- `/battery` = 73 (unidad por confirmar: ¿0.1 V o %?).

## `bringup.launch.py` y `wheel_params.yaml` reales (leídos en el robot)
- `bringup.launch.py` lanza **solo** `odom_corrector` (con `config/wheel_params.yaml`, argumento `wheel_params:=<ruta>`). No incluye el Agent (contenedor aparte) ni el bringup de Yahboom (su EKF publicaría otro `/odom`). **No publica `/cmd_vel`: no mueve el robot.** Hay también `launch/sim.launch.py` (simulación).
- YAML (`/**: ros__parameters`): `wheel_radius 0.0325`, `wheel_separation 0.2400`, `firmware_wheel_radius 0.0325`, `firmware_wheel_separation 0.2400`, `encoder_ticks_per_rev 1320`, `max_linear_vel 0.30`, `max_angular_vel 1.50`, `publish_tf true`. Al arrancar r = r0 y b = b0, así que `/odom` = `/odom_raw`.
- El comentario del YAML trae las reglas de corrección; el grupo debe poder derivarlas del código de `odom_corrector.py`. Cambios en caliente: `ros2 param set /odom_corrector <param> <valor>`; la copia que lee el robot es la de `install/` (¿refleja `src/`? por confirmar).
- **`/odom_raw` sin mensajes en 10 s** (mientras `/imu` publica a ~24 Hz). Diagnóstico pendiente (`topic echo --once`, `hz` 30 s); el docente indica `~/reset_esp32.sh` / botón RST si no publica.
- El contenedor no tiene `ping`: usar `python3 -c "import socket; print(socket.gethostbyname('packages.ros.org'))"`.

## `/odom_raw` y red del robot (mediciones del 30-oct-2026)
- Un mensaje de `/odom_raw` con el robot quieto: `frame_id: odom_frame`, `child_frame_id: base_footprint`, pose ≈ (1.5 mm, 0.2 mm, yaw 6.3°) **acumulada desde el arranque del firmware**, twist 0, **covarianzas no nulas** (0.001 pose, 0.0001 twist). Stamp de julio 2026 (reloj desfasado).
- `ros2 topic hz /odom_raw` (10 s y 30 s) no mostró ninguna línea mientras `/imu` daba ≈ 24 Hz: frecuencia de `/odom_raw` **sin medir**. Pendiente: contar mensajes con `echo --no-arr` y mirar los stamps.
- Red del RosCar 8: `eth0` DOWN (sin cable), `wlan0` 10.42.0.1/24 (punto de acceso), sin ruta por defecto; `ros2_dev` en red `host`. **Sin internet**: rosbag2 solo se instala conectando `eth0` a una red con salida (cambio de red: consultar al docente).

## Instalar rosbag2 y aislamiento (30-oct-2026)
- El puerto RJ45 de la Pi 5 está libre (foto); `eth0` DOWN. Para instalar rosbag2 hay que conectarlo a una toma del laboratorio con DHCP e internet (con permiso del docente).
- **Riesgo:** Agent en red `host` + dominio 20 (probablemente igual en toda la flota) ⇒ en una LAN compartida DDS puede exponer `/cmd_vel` entre robots. Conectar solo para instalar, robot quieto, y desconectar; comprobar `ros2 node list` antes.
- Medición de frecuencia por tubería falla por el búfer de Python (`timeout` mata a `ros2 topic echo/hz` antes de vaciarlo): usar `PYTHONUNBUFFERED=1`.

## 30-oct-2026 (tarde): teleop y bringup activos
- El grupo hizo `colcon build --packages-select capytown_esan --symlink-install` en `/root/yahboomcar_ws` (terminó bien; avisos de setuptools). Con symlink-install, `install/` apunta a `src/`: **editar el YAML de `src/capytown_esan/config` cambia lo que lee el robot al relanzar `odom_corrector`**. Hacer copia previa (`~/yahboomcar_ws/wheel_params.original.yaml`).
- Nodos: `/YB_Car_Node`, `/odom_corrector`. Topics: `/battery /beep /cmd_vel /imu /odom /odom_raw /odom_reset /parameter_events /rosout /scan /servo_s1 /servo_s2 /tf`.
- `teleop_key` movió el robot (cadena `/cmd_vel` → motores verificada). Sin mediciones de cinta ni bags.
- Pendiente: rosbag2 (bloquea la grabación), frecuencias de `/odom` y `/odom_raw`, dry-run de `secuencia_rc0.py` contra ROS real.

## Evidencia de la Parte A (30-oct-2026, RosCar 8)
- Nodos: `/YB_Car_Node`, `/odom_corrector` (y `/teleop_key` si hay una terminal con teleop abierta). Todos los topics esperados presentes (`/cmd_vel /imu /odom /odom_raw /scan`, además de `/battery /beep /odom_reset /tf /servo_s1 /servo_s2`).
- **Frecuencias medidas con `ros2 topic hz`:** `/odom` ≈ 11.0 Hz (min 0.068 s, max 0.149 s), `/odom_raw` ≈ 11.1 Hz, `/imu` ≈ 22.1 Hz. Con 11 Hz hay ~2.6° por muestra a 0.5 rad/s: el frenado de un giro puede pasarse unos grados (relevante para el bonus de 720°, ≤ 5°).
- **El bringup arranca solo:** `ros2 launch capytown_esan bringup.launch.py` (PID 500, 29 min de vida) lo lanza el contenedor; `odom_corrector` lee `install/capytown_esan/share/capytown_esan/config/wheel_params.yaml`. No relanzarlo (duplicaría el nodo).
- **E2:** dominio 20 → ve el robot; dominio 8 → lista vacía (aislamiento lógico). Valor "correcto" (20 u 8) pendiente del docente.
- `teleop_key` no tiene tope de velocidad: llegó a 0.23 m/s y 1.14 rad/s con `+`. `secuencia_rc0.py` limita a 0.20 m/s y 1.0 rad/s.
- Pendiente de la Parte A: captura de `rqt_graph`, rosbag2, dominio y dry-run de `secuencia recta` contra ROS real.

## rosbag2 (30-oct-2026, noche)
- **rosbag2 ya estaba instalado** en `/opt/ros/humble` (`rosbag2`, `rosbag2_py`, `rosbag2_storage`, `rosbag2_transport`...): lo que faltaba era `source /opt/ros/humble/setup.bash` en esa terminal. Los intentos de `apt` fallaron todos (sin internet); no se instaló nada. `import rosbag2_py` → OK.
- Almacenamiento disponible: **solo `sqlite3`** (más un plugin de prueba); **no hay `mcap`**. Basta con sqlite3: el reto acepta ambos y `plot_odom.py` lee el formato de `metadata.yaml`.
- `ros2 bag record --list-storage` (Anexo A del reto) **no existe en esta versión**; los plugins se ven en `ros2 bag record -h` (`-s {my_test_plugin,sqlite3}`).
- Bag de prueba válido: `Storage id: sqlite3`, 12 s, 134 mensajes de `/odom` (≈ 11.2 Hz) y 134 de `/tf`. `/cmd_vel` no se grabó porque `rosbag2` ignora por defecto los topics sin publicador: `grabar_bag.sh` usa `--include-unpublished-topics`.
- Se tocaron las fuentes de apt (y se revirtieron; copia en `/root/apt_backup`). Comprobar con `diff` que quedaron igual que el original. El reloj de la Pi ya está en hora.

## Tubería verificada con ROS 2 real (30-oct-2026, 23:10, robot quieto)
- `bash scripts/grabar_bag.sh prueba_pipeline /tmp/pruebas` → bag `sqlite3` de 28.8 s: `/odom` 320, `/odom_raw` 321, `/tf` 320, `/battery` 28 (≈ 1 Hz), `/cmd_vel` 0 (suscrito desde el inicio).
- `plot_odom.py` leyó el bag con `rosbag2_py`, eligió `/odom` solo (preferencia sobre `/odom_raw`) y generó los dos PNG; `matplotlib` existe en el contenedor.
- Con el robot quieto `/odom` da desplazamiento 0 y θ 0° (arranca en cero), mientras `/odom_raw` conserva el acumulado del firmware. **Sin verificar aún:** gráficas con movimiento real, `analizar_bag.py` y `secuencia_rc0.py` contra ROS real.
