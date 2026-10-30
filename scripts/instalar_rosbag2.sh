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

# rosbag2 suele estar ya en /opt/ros/humble: solo hace falta cargar el entorno de ROS
[ -f /opt/ros/humble/setup.bash ] && source /opt/ros/humble/setup.bash
if command -v ros2 >/dev/null 2>&1 && ros2 bag record -h >/dev/null 2>&1; then
  PLUGINS="$(ros2 bag record -h 2>&1 | tr '\n' ' ' | grep -o '{my_test_plugin[^}]*}')"
  echo "rosbag2 YA ESTÁ instalado (almacenamiento: ${PLUGINS:-desconocido}). Con sqlite3 basta para el reto; mcap es opcional."
  echo "Si otra terminal no ve 'ros2 bag':  source /opt/ros/humble/setup.bash"
  exit 0
fi

[ "$(id -u)" -eq 0 ] || { echo "Ejecútalo como root dentro del contenedor (no uses sudo a ciegas en el host)."; exit 1; }
# ping no existe en el contenedor: se comprueba la resolución de nombres con python3
python3 -c "import socket; socket.gethostbyname('packages.ros.org')" >/dev/null 2>&1 || { echo "Sin internet (no se resuelve packages.ros.org). Conecta el robot a una red con salida o pide ayuda al docente."; exit 2; }

cat <<'EOF'
AVISO DE AISLAMIENTO: el Agent usa red "host" y dominio 20. Si el robot está conectado por Ethernet a una LAN
compartida, DDS puede descubrir robots de otros grupos (y ellos al tuyo, con /cmd_vel). Conecta el cable SOLO
para instalar, con el robot quieto, y desconéctalo al terminar. Si "ros2 node list" muestra nodos ajenos, para.

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
