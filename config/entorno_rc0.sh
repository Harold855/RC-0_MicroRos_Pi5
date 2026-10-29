# Entorno RC-0 para la terminal ROS 2 (contenedor ros2_dev del RosCar o laptop con ROS 2).
# Uso:  source config/entorno_rc0.sh            # usa el dominio del Agent del robot (20)
#       RC0_DOMAIN_ID=8 source config/entorno_rc0.sh
# Solo exporta variables en ESTA terminal: no edita .bashrc, ni el Agent, ni el firmware.
#
# HALLAZGO: el contenedor micro_ros_agent del RosCar 8 corre con ROS_DOMAIN_ID=20
#   (docker inspect micro_ros_agent). Para VER los topics del robot hay que estar en ese dominio.
# El reto pide "equipo n -> n" (grupo 8 -> 8) y que Pi y placa coincidan. Cambiar el dominio del Agent es un
# cambio operativo que NO se hace sin el docente: preguntar si debe ser 20 (configuración del laboratorio)
# u 8, y cómo se cambia. Mientras tanto se trabaja en 20 y se anota el valor real en el README.
# El 92 del JetCobot era otro entorno y no se usa. Dominios aislados de prueba (fake_robot): 77.
export ROS_DOMAIN_ID="${RC0_DOMAIN_ID:-20}"
# Topic de odometría real: confirmarlo con parteA_contenedor.sh (/odom_raw del firmware y /odom si corre odom_corrector).
export ODOM_TOPIC="${ODOM_TOPIC:-}"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID  ODOM_TOPIC=${ODOM_TOPIC:-(sin definir: se autodetecta)}"
