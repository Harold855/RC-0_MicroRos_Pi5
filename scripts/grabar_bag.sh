#!/usr/bin/env bash
# Graba un bag de RC-0 con nombre único y la(s) odometría(s) real(es): /odom_raw y/o /odom.
# Uso (en el contenedor, ANTES de mover el robot; Ctrl+C para terminar):
#   bash scripts/grabar_bag.sh rc0_recta_c1            # -> bags/rc0_recta_c1_20261029_130501/
#   ODOM_TOPIC=/odom_raw bash scripts/grabar_bag.sh rc0_giro_i2 otra_carpeta
# Graba: odometría, /cmd_vel y /tf (como pide el reto). No mueve el robot.
# Nunca sobrescribe: el nombre lleva fecha y hora, y se rechaza si la carpeta existe.

PREFIJO="${1:?Uso: grabar_bag.sh <prefijo> [carpeta_salida]   (p. ej. rc0_recta_c1)}"
SALIDA="${2:-bags}"

command -v ros2 >/dev/null 2>&1 || { echo "ros2 no está en el PATH: ¿contenedor y entorno cargado?"; exit 1; }

TOPIC="${ODOM_TOPIC:-}"   # uno o varios, separados por espacios; por defecto, TODOS los nav_msgs/Odometry
if [ -z "$TOPIC" ]; then
  TOPIC="$(timeout 10 ros2 topic list -t 2>/dev/null | awk '$2=="[nav_msgs/msg/Odometry]"{print $1}' | tr '\n' ' ')"
  if [ -z "${TOPIC// /}" ]; then
    echo "ERROR: no hay ningún topic nav_msgs/msg/Odometry. ¿Agent caído, dominio distinto o bringup sin lanzar?"; exit 2
  fi
fi

mkdir -p "$SALIDA" || exit 1
NOMBRE="$SALIDA/${PREFIJO}_$(date +%Y%m%d_%H%M%S)"
if [ -e "$NOMBRE" ]; then echo "ERROR: $NOMBRE ya existe; no se sobrescribe."; exit 3; fi

echo "Grabando: $TOPIC /cmd_vel /tf  ->  $NOMBRE   (si salen /odom_raw y /odom, se graban ambos)"
echo "Ctrl+C para terminar. Al acabar, revisa:  ros2 bag info $NOMBRE"
# shellcheck disable=SC2086  (TOPIC puede ser una lista)
exec ros2 bag record $TOPIC /cmd_vel /tf -o "$NOMBRE"
