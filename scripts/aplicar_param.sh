#!/usr/bin/env bash
# Cambia EN CALIENTE un parámetro de odom_corrector (r o b_eff) con validación, confirmación y registro.
# Uso:  bash scripts/aplicar_param.sh <wheel_radius|wheel_separation> <valor_en_metros> ["nota"]
# Ej.:  bash scripts/aplicar_param.sh wheel_radius 0.0331 "tras las corridas 1-3"
#
# Este script NO calcula el valor nuevo: lo calcula el grupo (es pregunta de defensa).
# Solo evita errores de captura, pide confirmación, comprueba que el cambio se aplicó y lo anota en bitacora_params.csv.
# El cambio es en memoria: se pierde si se reinicia el contenedor. Al final, anota los valores finales en el YAML.

PARAM="${1:-}"; VALOR="${2:-}"; NOTA="${3:-}"
uso() { echo "Uso: bash scripts/aplicar_param.sh <wheel_radius|wheel_separation> <valor_en_metros> [\"nota\"]"; }
err() { echo "ERROR: $*" >&2; exit 2; }

[ -f /opt/ros/humble/setup.bash ] && source /opt/ros/humble/setup.bash
[ -f /root/yahboomcar_ws/install/setup.bash ] && source /root/yahboomcar_ws/install/setup.bash

[ -n "$PARAM" ] && [ -n "$VALOR" ] || { uso; exit 2; }
command -v ros2 >/dev/null 2>&1 || err "ros2 no está en el PATH: entra al contenedor (bash ~/ros2_humble.sh)"

case "$PARAM" in
  wheel_radius)     MIN=0.02; MAX=0.10; ETQ="r (radio de rueda)";;
  wheel_separation) MIN=0.10; MAX=0.50; ETQ="b_eff (ancho de vía efectivo)";;
  firmware_*)       err "'$PARAM' es del firmware y NO se toca nunca (r0 y b0 son fijos).";;
  *)                err "parámetro '$PARAM' no permitido. Solo wheel_radius o wheel_separation.";;
esac

case "$VALOR" in *,*) err "el valor '$VALOR' usa coma decimal: escribe punto (0.0331).";; esac
[[ "$VALOR" =~ ^[0-9]+([.][0-9]+)?$ ]] || err "el valor '$VALOR' no es un número válido (ej.: 0.0331)."
awk -v v="$VALOR" -v a="$MIN" -v b="$MAX" 'BEGIN{exit !(v>=a && v<=b)}' \
  || err "$VALOR está fuera del rango razonable [$MIN, $MAX] m para $ETQ. ¿Está en METROS (no cm ni mm)?"

timeout 10 ros2 node list 2>/dev/null | grep -qx "/odom_corrector" \
  || err "no existe el nodo /odom_corrector (¿bringup caído o dominio distinto? ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-sin_definir})."

ANTES="$(timeout 10 ros2 param get /odom_corrector "$PARAM" 2>/dev/null | awk '{print $NF}')"
[ -n "$ANTES" ] || err "no pude leer el valor actual de $PARAM en /odom_corrector."

echo "Parámetro : $PARAM  —  $ETQ"
echo "Actual    : $ANTES m"
echo "Nuevo     : $VALOR m"
echo "Recuerda: un solo parámetro a la vez (primero r, después b_eff) y no se cambia nada en A2 (validación)."
read -r -p "Escribe SI para aplicar: " RESP
[ "$RESP" = "SI" ] || { echo "Cancelado: no se cambió nada."; exit 5; }

SALIDA="$(timeout 15 ros2 param set /odom_corrector "$PARAM" "$VALOR" 2>&1)"
echo "$SALIDA" | grep -qi "successful" || err "el nodo rechazó el cambio: $SALIDA"

DESPUES="$(timeout 10 ros2 param get /odom_corrector "$PARAM" 2>/dev/null | awk '{print $NF}')"
awk -v a="$DESPUES" -v b="$VALOR" 'BEGIN{d=a-b; if(d<0)d=-d; exit !(d<1e-9)}' \
  || err "se aplicó, pero al releer vale '$DESPUES' y se esperaba '$VALOR'. Revisa a mano: ros2 param get /odom_corrector $PARAM"

LOG="bitacora_params.csv"
[ -s "$LOG" ] || echo "timestamp,parametro,antes,despues,nota" > "$LOG"
echo "$(date '+%Y-%m-%dT%H:%M:%S'),$PARAM,$ANTES,$DESPUES,${NOTA//,/;}" >> "$LOG"
echo "OK: $PARAM = $DESPUES m (antes $ANTES). Anotado en $LOG."
echo "Aviso: el cambio es solo en memoria; /odom ya usa el valor nuevo. Si se reinicia el contenedor vuelve al YAML."
