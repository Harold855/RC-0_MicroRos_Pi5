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
