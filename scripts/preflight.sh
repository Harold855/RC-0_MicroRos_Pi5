#!/usr/bin/env bash
# Comprobaciones de SOLO LECTURA antes de mover el robot. No publica en /cmd_vel ni cambia nada.
# Uso (dentro del contenedor ros2_dev, en la raíz del repo):  bash scripts/preflight.sh
# Cada línea es OK / AVISO / FALLA con el motivo y qué hacer. Termina con código != 0 si hay alguna FALLA.

FALLAS=0; AVISOS=0
ok()    { echo "OK      $*"; }
aviso() { echo "AVISO   $*"; AVISOS=$((AVISOS+1)); }
falla() { echo "FALLA   $*"; FALLAS=$((FALLAS+1)); }

[ -f /opt/ros/humble/setup.bash ] && source /opt/ros/humble/setup.bash
[ -f /root/yahboomcar_ws/install/setup.bash ] && source /root/yahboomcar_ws/install/setup.bash

echo "=== PREFLIGHT RC-0 · $(date '+%Y-%m-%d %H:%M:%S') (si la fecha está mal, el reloj de la Pi está desfasado)"

if ! command -v ros2 >/dev/null 2>&1; then
  falla "ros2 no está en el PATH: ¿estás DENTRO del contenedor? (bash ~/ros2_humble.sh)"; echo "=== $FALLAS falla(s)"; exit 1
fi
ros2 bag record -h >/dev/null 2>&1 && ok "rosbag2 disponible" || falla "ros2 bag no existe: falta 'source /opt/ros/humble/setup.bash'"

if [ -z "${ROS_DOMAIN_ID:-}" ]; then falla "ROS_DOMAIN_ID sin definir: source config/atajos_rc0.sh (fija 8)"
elif [ "$ROS_DOMAIN_ID" != "8" ]; then falla "ROS_DOMAIN_ID=$ROS_DOMAIN_ID: el reto del Grupo 8 usa 8. Haz: source config/atajos_rc0.sh"
else ok "ROS_DOMAIN_ID=8 (dominio del reto; los valores iniciales de la Parte A se tomaron con 20)"; fi

# El descubrimiento de nodos micro-ROS puede tardar tras reconectar la placa (caso visto: 1.ª lectura sin /YB_Car_Node, 2.ª con él): se reintenta.
NODOS=""
for _i in $(seq 1 "${RC0_REINTENTOS:-3}"); do
  NODOS="$(timeout 10 ros2 node list 2>/dev/null)"
  echo "$NODOS" | grep -qx "/YB_Car_Node" && break
  [ "$_i" -lt "${RC0_REINTENTOS:-3}" ] && sleep 2
done
if echo "$NODOS" | grep -qx "/YB_Car_Node"; then ok "placa conectada (/YB_Car_Node)"
else
  falla "no aparece /YB_Car_Node: Agent/placa sin conexión en el dominio $ROS_DOMAIN_ID. Revisa el cable USB de la placa y, SOLO con permiso del docente, el botón RST del ESP32"
  if [ "$ROS_DOMAIN_ID" = "8" ] && ROS_DOMAIN_ID=20 timeout 10 ros2 node list 2>/dev/null | grep -qx "/YB_Car_Node"; then
    falla "el robot SÍ aparece en el dominio 20: el Agent/placa siguen en 20. Para usar 8 hay que cambiar el dominio del Agent en el robot (acción del grupo con autorización del docente; este script no la hace)"
  fi
fi
echo "$NODOS" | grep -qx "/odom_corrector" && ok "odom_corrector corriendo (publica /odom)" \
  || falla "no corre /odom_corrector: no habrá /odom. Debe arrancar con el contenedor; revisa con el docente antes de lanzarlo a mano"
echo "$NODOS" | grep -qx "/teleop_key" && falla "teleop_key está abierto: ciérralo (q en su terminal, o pkill -f teleop_key); publicaría en /cmd_vel a la vez"
AJENOS="$(echo "$NODOS" | grep -vxE '/YB_Car_Node|/odom_corrector|/teleop_key|/secuencia_rc0|/calibrate_beff|/rosbag2_recorder|/rosbag2_player|/rqt_gui_py_node_[0-9]+|^$')"
[ -n "$AJENOS" ] && aviso "nodos no esperados: $(echo $AJENOS | tr '\n' ' ') (¿otro grupo en la red? ¿cable Ethernet conectado? Si no son tuyos, para y avisa)"

TOPICS="$(timeout 10 ros2 topic list 2>/dev/null)"
for t in /cmd_vel /odom /odom_raw; do
  echo "$TOPICS" | grep -qx "$t" && ok "topic $t" || falla "falta el topic $t"
done
for t in /battery /imu /scan; do
  echo "$TOPICS" | grep -qx "$t" && ok "topic $t" || aviso "falta el topic $t (no bloquea las pruebas)"
done

INFO="$(timeout 10 ros2 topic info /cmd_vel 2>/dev/null)"
PUBS="$(echo "$INFO" | awk '/Publisher count:/{print $3}')"; SUBS="$(echo "$INFO" | awk '/Subscription count:/{print $3}')"
if [ "${PUBS:-0}" -gt 0 ] 2>/dev/null; then falla "ya hay $PUBS publicador(es) en /cmd_vel (otro nodo de movimiento abierto)"; else ok "nadie más publica en /cmd_vel"; fi
if [ "${SUBS:-0}" -ge 1 ] 2>/dev/null; then ok "/cmd_vel tiene $SUBS suscriptor(es) (driver de la placa)"; else falla "nadie escucha /cmd_vel: el robot no se movería"; fi

# Ventana de 8 s: el arranque del 'echo' (descubrimiento) se come 1-2 s y con 4 s dio lecturas de 9 a 32 mensajes con /odom sano (11 Hz).
# La medición fiable de frecuencia es 'parteA' (ros2 topic hz); esto solo detecta un /odom mudo o muy lento.
N="$(PYTHONUNBUFFERED=1 timeout 8 ros2 topic echo /odom --no-arr 2>/dev/null | grep -c '^---')"
if [ "${N:-0}" -eq 0 ]; then falla "/odom no publica en 8 s: si /odom_raw sí publica, odom_corrector está caído; si tampoco, revisa Agent/placa"
elif [ "$N" -lt 40 ]; then aviso "/odom llega lento: $N mensajes en 8 s (lo normal ≈ 11 Hz → ~65-88); mide con 'parteA' (ros2 topic hz) antes de alarmarte"
else ok "/odom publica: $N mensajes en 8 s (lectura aproximada; la frecuencia oficial la da parteA)"; fi

R="$(timeout 10 ros2 param get /odom_corrector wheel_radius 2>/dev/null | awk '{print $NF}')"
B="$(timeout 10 ros2 param get /odom_corrector wheel_separation 2>/dev/null | awk '{print $NF}')"
[ -n "$R" ] && ok "wheel_radius (r) actual = $R m" || aviso "no pude leer wheel_radius de /odom_corrector"
[ -n "$B" ] && ok "wheel_separation (b_eff) actual = $B m" || aviso "no pude leer wheel_separation de /odom_corrector"

BAT="$(timeout 6 ros2 topic echo /battery --once 2>/dev/null | awk '/data:/{print $2}')"
[ -n "$BAT" ] && ok "batería (valor crudo de /battery) = $BAT  [unidad por confirmar; anótalo en cada corrida]" || aviso "no pude leer /battery"

LIBRE="$(df -Pk . 2>/dev/null | awk 'NR==2{print int($4/1024)}')"
if [ -n "$LIBRE" ] && [ "$LIBRE" -lt 300 ] 2>/dev/null; then falla "quedan solo ${LIBRE} MB de disco en esta carpeta: libera espacio antes de grabar bags"; else ok "espacio libre: ${LIBRE:-?} MB"; fi

for f in linea_recta.csv calibration_log.csv validacion.csv; do
  [ -f "$f" ] || aviso "no existe $f aquí: ¿estás en la raíz del repo? (cd /root/yahboomcar_ws/rc0_v2)"
done

echo "=== resumen: $FALLAS falla(s), $AVISOS aviso(s)"
[ "$FALLAS" -eq 0 ]
