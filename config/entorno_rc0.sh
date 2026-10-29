# Entorno RC-0 para la terminal ROS 2 (contenedor del RosCar o laptop con ROS 2).
# Uso:  source config/entorno_rc0.sh
# Solo exporta variables en ESTA terminal: no edita .bashrc ni toca el firmware.
#
# ROS_DOMAIN_ID = número de grupo, como pide el reto ("equipo n -> n").
# [VERIFICAR] La placa debe tener el mismo valor en su firmware; el docente aún no
# ha explicado cómo configurarlo. No intentes flashear nada por tu cuenta.
# El valor 92 del JetCobot era un dominio compartido del laboratorio: no se usa aquí.
export ROS_DOMAIN_ID=8
# Topic de odometría real: confirmarlo con parteA_contenedor.sh (suele ser /odom_raw).
export ODOM_TOPIC="${ODOM_TOPIC:-}"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID  ODOM_TOPIC=${ODOM_TOPIC:-(sin definir: se autodetecta)}"
