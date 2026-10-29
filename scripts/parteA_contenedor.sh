#!/usr/bin/env bash
# Parte A — diagnóstico de SOLO LECTURA dentro del contenedor ROS 2 (o en una máquina con ROS 2).
# No publica en /cmd_vel, no lanza bringup, no instala nada. Cada medición tiene tiempo límite.
# Uso:  bash scripts/parteA_contenedor.sh [setup_log.txt]
# Registra: dominio, nodos, topics con tipo, frecuencia de odometría e IMU, soporte de rosbag2.
# Los valores que aparezcan en las presentaciones (p. ej. ~50 Hz) NO son mediciones de tu robot: aquí se mide.

LOG="${1:-setup_log.txt}"
SEG="${HZ_SEGUNDOS:-10}"   # duración de cada medición de frecuencia

command -v ros2 >/dev/null 2>&1 || { echo "ros2 no está en el PATH: ¿estás en el contenedor y con el entorno cargado (source /opt/ros/humble/setup.bash)?"; exit 1; }

{
  echo "=============================================================="
  echo "RC-0 · Parte A · ROS 2 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "=============================================================="
  echo "--- [DOCKER ROS 2] entorno"
  echo "ROS_DISTRO=${ROS_DISTRO:-?}   ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-sin_exportar}   host=$(hostname)"
  echo
  echo "--- ros2 node list"
  timeout 10 ros2 node list 2>&1
  echo
  echo "--- ros2 topic list -t"
  TOPICS="$(timeout 10 ros2 topic list -t 2>&1)"
  echo "$TOPICS"
  echo
  echo "--- topics esperados (E1: /cmd_vel, odometría, /imu, /scan)"
  for t in /cmd_vel /imu /scan; do
    if echo "$TOPICS" | grep -q "^$t "; then echo "OK      $t"; else echo "FALTA   $t"; fi
  done
  ODOMS="$(echo "$TOPICS" | awk '$2=="[nav_msgs/msg/Odometry]"{print $1}')"
  if [ -z "$ODOMS" ]; then
    echo "FALTA   ningún topic nav_msgs/msg/Odometry (¿Agent caído, dominio distinto, bringup sin lanzar?). No se finge odometría."
  else
    echo "Odometría detectada: $(echo $ODOMS | tr '\n' ' ')"
    [ "$(echo "$ODOMS" | wc -l)" -gt 1 ] && echo "AVISO: hay más de un topic de odometría; averigua de dónde sale cada uno y acuerda cuál se evalúa."
  fi
  echo
  echo "--- frecuencias (${SEG} s cada una; salida de 'ros2 topic hz')"
  for t in $ODOMS /imu; do
    if echo "$TOPICS" | grep -q "^$t "; then
      echo ">> $t"
      timeout "$SEG" ros2 topic hz "$t" 2>&1 | tail -n 6
    fi
  done
  echo
  echo "--- tipos y QoS de la odometría (solo lectura)"
  for t in $ODOMS; do timeout 10 ros2 topic info "$t" --verbose 2>&1 | head -n 40; done
  echo
  echo "--- paquetes relevantes"
  ros2 pkg list 2>/dev/null | grep -E 'capytown|yahboom' || echo "(ninguno visible con ese nombre)"
  echo
  echo "--- rosbag2 (Anexo A del reto solo si falta; instalar es un cambio operativo: pedir aprobación)"
  timeout 20 ros2 bag record --list-storage 2>&1 | head -n 12
  echo
  echo "--- Aislamiento (E2): la lista de nodos/topics de arriba solo debe mostrar el robot propio."
  echo "--- Pendiente a mano: captura de rqt_graph y referencia a ella en este log."
} 2>&1 | tee -a "$LOG"

echo
echo "Salida añadida a $LOG (no se sobrescribió nada)."
