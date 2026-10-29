#!/usr/bin/env bash
# Parte A — diagnóstico de SOLO LECTURA en el host (Pi 5 del RosCar, por SSH o desde la terminal de TigerVNC).
# No inicia ni detiene nada, no entra al contenedor, no usa sudo, no publica en /cmd_vel.
# Uso:  bash scripts/parteA_host.sh [setup_log.txt]
# Responde: ¿quién soy?, ¿qué contenedores hay?, ¿ya corre un micro-ROS Agent?, ¿existen los scripts del fabricante?

LOG="${1:-setup_log.txt}"

{
  echo "=============================================================="
  echo "RC-0 · Parte A · HOST · $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "=============================================================="
  echo "--- [PI HOST] identidad"
  echo "usuario: $(whoami)   host: $(hostname)"
  uname -a
  grep -E '^(PRETTY_NAME)=' /etc/os-release 2>/dev/null
  echo
  echo "--- [PI HOST] contenedores Docker (docker ps -a)"
  docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>&1
  echo
  echo "--- [PI HOST] ¿hay un micro-ROS Agent en marcha? (no lances otro: no dupliques el Agent)"
  ps aux | grep -i -E 'micro_ros_agent|micro-ros-agent|MicroXRCEAgent' | grep -v grep || echo "(no se ve ningún proceso Agent en el host; puede estar dentro del contenedor)"
  echo
  echo "--- [PI HOST] scripts del fabricante (solo existencia)"
  ls -l ~/ros2_humble.sh ~/start_agent_rpi5.sh ~/start_agent.sh ~/setup_workspace.sh 2>&1
  echo
  echo "--- [PI HOST] temperatura y subtensión de la Pi (no es la batería del RosCar; esa se anota a mano)"
  (vcgencmd measure_temp; vcgencmd get_throttled) 2>&1 || echo "(vcgencmd no disponible)"
  echo
  echo "--- Pendientes de observar a mano: ID del RosCar físico, estado de la batería, captura de rqt_graph."
} 2>&1 | tee -a "$LOG"

echo
echo "Salida añadida a $LOG (no se sobrescribió nada)."
