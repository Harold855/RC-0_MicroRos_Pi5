# Entorno RC-0 para la terminal ROS 2 (contenedor ros2_dev del RosCar o laptop con ROS 2).
# Uso:  source config/entorno_rc0.sh            # fija ROS_DOMAIN_ID=8 (dominio del Grupo 8)
# Solo exporta variables en ESTA terminal: no edita .bashrc, ni el Agent, ni el firmware.
# DOMINIO DEL RETO: 8 (equipo n -> n; Grupo 8)
# PROCEDENCIA: los valores iniciales de la Parte A (setup_log.txt: topics, frecuencias, docker inspect) se
#   obtuvieron con ROS_DOMAIN_ID=20, que era el del Agent del RosCar 8 tal como se recibió.
# NOTA: este archivo solo fija el dominio de esta terminal. Mientras el Agent/la placa del robot sigan en 20,
#   en el dominio 8 no se verá ningún topic del robot (scripts/preflight.sh lo detecta y lo explica).
# Ensayos aislados con fake_robot: RC0_ENSAYO=1 RC0_DOMAIN_ID=77 source config/entorno_rc0.sh
DOMINIO_RETO=8
if [ "${RC0_ENSAYO:-0}" = "1" ] && [ -n "${RC0_DOMAIN_ID:-}" ]; then
  export ROS_DOMAIN_ID="$RC0_DOMAIN_ID"
  echo "AVISO: modo ENSAYO, ROS_DOMAIN_ID=$ROS_DOMAIN_ID (no es el dominio del reto: $DOMINIO_RETO)"
else
  [ -n "${RC0_DOMAIN_ID:-}" ] && [ "$RC0_DOMAIN_ID" != "$DOMINIO_RETO" ] && \
    echo "AVISO: se ignora RC0_DOMAIN_ID=$RC0_DOMAIN_ID; el reto usa $DOMINIO_RETO (para ensayos: RC0_ENSAYO=1)"
  export ROS_DOMAIN_ID="$DOMINIO_RETO"
fi
# Topic de odometría real: confirmarlo con parteA_contenedor.sh (/odom_raw del firmware y /odom si corre odom_corrector).
export ODOM_TOPIC="${ODOM_TOPIC:-}"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID  ODOM_TOPIC=${ODOM_TOPIC:-(sin definir: se autodetecta)}"
