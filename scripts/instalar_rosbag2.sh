#!/usr/bin/env bash
# Parte A, paso 6: instala rosbag2 en el contenedor (Anexo A del reto). CAMBIA el contenedor: requiere aprobación.
# Uso (como root, DENTRO del contenedor, con internet):  bash scripts/instalar_rosbag2.sh
#
# - Si rosbag2 ya tiene sqlite3 y mcap, no hace nada.
# - Muestra lo que va a hacer y exige escribir SI.
# - Respalda /etc/apt/sources.list.d/ros2.list antes de reescribirlo.
# - Sigue el Anexo A del DOCX (no la diapositiva abreviada, que usa "||" donde corresponde ";").
# - La instalación vive en este contenedor: si lo recrean (docker rm) hay que repetirla.
# ESTADO: transcrito del reto, SIN probar en el robot. Léelo antes de ejecutarlo.

if command -v ros2 >/dev/null 2>&1; then
  LISTA="$(timeout 20 ros2 bag record --list-storage 2>&1)"
  if echo "$LISTA" | grep -q sqlite3 && echo "$LISTA" | grep -q mcap; then
    echo "rosbag2 ya está instalado con sqlite3 y mcap. Nada que hacer."; exit 0
  fi
fi

[ "$(id -u)" -eq 0 ] || { echo "Ejecútalo como root dentro del contenedor (no uses sudo a ciegas en el host)."; exit 1; }
ping -c 1 -W 3 packages.ros.org >/dev/null 2>&1 || { echo "Sin internet (no se resuelve packages.ros.org). Conecta el robot a una red con salida o pide ayuda al docente."; exit 2; }

cat <<'EOF'
Se va a:
  1. apt-key del F42ED6FBAB17C654        (clave GPG vencida; si dice "No such key", sigue)
  2. apt-get update; apt-get install -y curl
  3. descargar la clave oficial de ROS a /usr/share/keyrings/ros-archive-keyring.gpg
  4. reescribir /etc/apt/sources.list.d/ros2.list (con copia de seguridad .bak)
  5. apt-get clean && apt-get update
  6. apt-get install -y ros-humble-rosbag2 ros-humble-rosbag2-storage-mcap
EOF
read -r -p "Escribe SI para continuar: " R
[ "$R" = "SI" ] || { echo "Cancelado."; exit 5; }

apt-key del F42ED6FBAB17C654
apt-get update
apt-get install -y curl || exit $?
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg || exit $?
[ -f /etc/apt/sources.list.d/ros2.list ] && cp -n /etc/apt/sources.list.d/ros2.list /etc/apt/sources.list.d/ros2.list.bak
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" > /etc/apt/sources.list.d/ros2.list
apt-get clean && apt-get update || exit $?
apt-get install -y ros-humble-rosbag2 ros-humble-rosbag2-storage-mcap || exit $?

echo
echo "Comprobación (debe listar sqlite3 y mcap):"
ros2 bag record --list-storage
