#!/usr/bin/env bash
# Graba un bag de RC-0 con nombre único y el topic de odometría real.
# Uso (en el contenedor, ANTES de mover el robot; Ctrl+C para terminar):
#   bash scripts/grabar_bag.sh rc0_recta_c1            # -> bags/rc0_recta_c1_20261029_130501/
#   ODOM_TOPIC=/odom_raw bash scripts/grabar_bag.sh rc0_giro_i2 otra_carpeta
# Graba: odometría, /cmd_vel y /tf (como pide el reto). No mueve el robot.
# Nunca sobrescribe: el nombre lleva fecha y hora, y se rechaza si la carpeta existe.

PREFIJO="${1:?Uso: grabar_bag.sh <prefijo> [carpeta_salida]   (p. ej. rc0_recta_c1)}"
SALIDA="${2:-bags}"

command -v ros2 >/dev/null 2>&1 || { echo "ros2 no está en el PATH: ¿contenedor y entorno cargado?"; exit 1; }

TOPIC="${ODOM_TOPIC:-}"
if [ -z "$TOPIC" ]; then
  ODOMS="$(timeout 10 ros2 topic list -t 2>/dev/null | awk '$2=="[nav_msgs/msg/Odometry]"{print $1}')"
  N="$(printf '%s' "$ODOMS" | grep -c .)"
  if [ "$N" -eq 0 ]; then
    echo "ERROR: no hay ningún topic nav_msgs/msg/Odometry. ¿Agent caído, dominio distinto o bringup sin lanzar?"; exit 2
  elif [ "$N" -gt 1 ]; then
    echo "ERROR: hay varios topics de odometría:"; echo "$ODOMS"; echo "Elige uno:  ODOM_TOPIC=<topic> bash scripts/grabar_bag.sh $PREFIJO"; exit 2
  fi
  TOPIC="$ODOMS"
fi

mkdir -p "$SALIDA" || exit 1
NOMBRE="$SALIDA/${PREFIJO}_$(date +%Y%m%d_%H%M%S)"
if [ -e "$NOMBRE" ]; then echo "ERROR: $NOMBRE ya existe; no se sobrescribe."; exit 3; fi

echo "Grabando: $TOPIC /cmd_vel /tf  ->  $NOMBRE"
echo "Ctrl+C para terminar. Al acabar, revisa:  ros2 bag info $NOMBRE"
exec ros2 bag record "$TOPIC" /cmd_vel /tf -o "$NOMBRE"
