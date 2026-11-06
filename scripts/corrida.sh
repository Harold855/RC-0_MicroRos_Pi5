#!/usr/bin/env bash
# Corrida guiada para el Reto 0
# Tarea: comprueba el entorno, graba el bag, mueve el robot (con confirmación), para el bag, pide lo que se midió con cint o transportador y arma la fila del CSV. Cada paso que falla dice que falló y qué hacer.
#
# Uso (dentro del contenedor, en la raíz del repositorio, con el robot sin cargador):
#   bash scripts/corrida.sh recta      A1 <n> [--rapido]   # Parte B: recta de calibración -> linea_recta.csv
#   bash scripts/corrida.sh calibrar_b A1 <n> [--rapido]   # Parte C: giro con calibrate_beff del docente (graba el bag)
#   bash scripts/corrida.sh recta      A2 <n> [--rapido]   # Parte D: recta de validación  -> validacion.csv
# <n> = número de corrida/iteración (1, 2, 3...). --rapido salta el preflight (úsalo en repeticiones seguidas).
#
# no mueve el robot por su cuenta: secuencia_rc0.py (o calibrate_beff) sigue pidiendo confirmación; este script solo ordena los pasos. 
# no calcula ni aplica r/b_eff (ver scripts/aplicar_param.sh). 

cd "$(dirname "$0")/.." || exit 1
MODO="${1:-}"; VAR="${2:-}"; N="${3:-}"; RAPIDO=0
[ "${4:-}" = "--rapido" ] && RAPIDO=1

uso() {
  sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
}
err() { echo "ERROR: $*" >&2; exit 2; }

[ -n "$MODO" ] && [ -n "$VAR" ] && [ -n "$N" ] || { uso; exit 2; }
[[ "$N" =~ ^[0-9]+$ ]] && [ "$N" -ge 1 ] || err "<n>='$N' no es un número entero >= 1."

case "$MODO:$VAR" in
  recta:A1)      PREFIJO="rc0_recta_c$N";     CSV="linea_recta.csv"
                 POS="robot orientado al ESTE sobre B4–C4, con el eje de las ruedas sobre la línea A4|B4";;
  recta:A2)      PREFIJO="rc0_val_recta_c$N"; CSV="validacion.csv"
                 POS="robot orientado al OESTE sobre C4–D4, con el eje de las ruedas sobre la línea D4|E4";;
  giro:A2)       PREFIJO="rc0_val_giro_c$N";  CSV="validacion.csv"
                 POS="robot sobre la cruz del tile A1, cinta del chasis alineada con la del piso";;
  calibrar_b:A1) PREFIJO="rc0_giro_i$N";      CSV="calibration_log.csv"
                 POS="robot sobre la cruz del tile B2, cinta del chasis alineada con la del piso";;
  giro:A1)       err "en A1 el giro de calibración se hace con 'calibrar_b' (calibrate_beff mide y registra la iteración).";;
  calibrar_b:A2) err "en A2 NO se recalibra (validación sin tocar parámetros): usa 'giro A2'.";;
  *)             uso; err "combinación '$MODO $VAR' no válida.";;
esac

[ -f /opt/ros/humble/setup.bash ] && source /opt/ros/humble/setup.bash
[ -f /root/yahboomcar_ws/install/setup.bash ] && source /root/yahboomcar_ws/install/setup.bash
command -v ros2 >/dev/null 2>&1 || err "ros2 no está en el PATH: entra al contenedor (bash ~/ros2_humble.sh)."
[ -f capytown_esan/analizar_bag.py ] || err "no encuentro capytown_esan/analizar_bag.py: ejecuta desde la raíz del repo."

# ------------------------------------------ 1. Verificacion con preflight ------------------------------------------------------
if [ "$RAPIDO" -eq 0 ]; then
  bash scripts/preflight.sh || { echo; echo "ERROR: el preflight tiene FALLAS. No se mueve nada." >&2; exit 1; }
else
  echo "(preflight omitido por --rapido)"
fi

leer_param() { timeout 10 ros2 param get /odom_corrector "$1" 2>/dev/null | awk '{print $NF}'; }
leer_bat()   { timeout 6 ros2 topic echo /battery --once 2>/dev/null | awk '/data:/{print $2}'; }
R_USADO="$(leer_param wheel_radius)"; B_USADO="$(leer_param wheel_separation)"
[ -n "$R_USADO" ] && [ -n "$B_USADO" ] || err "no pude leer wheel_radius/wheel_separation de /odom_corrector (¿el nodo estara caído?)"

# --------------------------------- 2. Una lista de comprobación física ----------------------------------------------
cat <<EOF

CORRIDA $PREFIJO   (r = $R_USADO m · b_eff = $B_USADO m)
Antes de seguir, confirma TODO:
  1. Cargador desconectado del robot 
  2. Zona despejada, $POS.
  3. Un integrante con la cinta métrica o transportador para medir lo que faltó o sobró. Opcional: Un integrante listo para frenar o levantar el robot (ante cualquier error)
  4. teleop_key cerrado.
EOF
read -r -p "Escribe SI cuando todo esté listo (otra cosa cancela): " RESP
[ "$RESP" = "SI" ] || { echo "Cancelado: no se hizo nada."; exit 5; }

BAT_A="$(leer_bat)"; echo "batería antes (valor crudo): ${BAT_A:-?}"

# ------------------------------------ 3. El bag en segundo plano ----------------------------------------------------
LOGBAG="$(mktemp /tmp/rc0_bag.XXXXXX)"; BAGPID=""
limpiar() {
  if [ -n "${BAGPID:-}" ] && kill -0 "$BAGPID" 2>/dev/null; then
    kill -INT "$BAGPID" 2>/dev/null
    for _ in $(seq 1 20); do kill -0 "$BAGPID" 2>/dev/null || break; sleep 0.5; done
    kill -TERM "$BAGPID" 2>/dev/null
  fi
  BAGPID=""
}
trap limpiar EXIT
trap 'echo; echo "Interrumpido (Ctrl+C): se cierra el bag."; exit 130' INT

mkdir -p bags
bash scripts/grabar_bag.sh "$PREFIJO" bags </dev/null >"$LOGBAG" 2>&1 &
BAGPID=$!
LISTO=0
for _ in $(seq 1 24); do
  grep -q 'Recording\.\.\.' "$LOGBAG" 2>/dev/null && { LISTO=1; break; }
  kill -0 "$BAGPID" 2>/dev/null || break
  sleep 0.5
done
if [ "$LISTO" -ne 1 ]; then
  echo "ERROR: el bag no llegó a empezar a grabar. Salida de grabar_bag.sh:" >&2; tail -n 8 "$LOGBAG" >&2; BAGPID=""; exit 3
fi
BAGDIR="$(sed -n 's/.*->  *\(bags\/[^ ]*\).*/\1/p' "$LOGBAG" | head -1)"
[ -n "$BAGDIR" ] || { echo "ERROR: no pude leer el nombre del bag en $LOGBAG:" >&2; tail -n 5 "$LOGBAG" >&2; exit 3; }
echo "bag grabando en: $BAGDIR"
sleep 1

# ------------------------------ 4. El movimiento (siempre con confirmación propia de cada programa) ------------------------------
SEQ=( ${RC0_SECUENCIA_CMD:-python3 capytown_esan/secuencia_rc0.py} )
CAL=( ${RC0_CALIB_CMD:-ros2 run capytown_esan calibrate_beff} )
RC=0
case "$MODO" in
  recta)      "${SEQ[@]}" --ros-args -p modo:=recta -p dry_run:=false -p confirmar_movimiento:=true; RC=$? ;;
  giro)       "${SEQ[@]}" --ros-args -p modo:=giro -p sentido:=horario -p dry_run:=false -p confirmar_movimiento:=true; RC=$? ;;
  calibrar_b) echo "calibrate_beff: pulsa ENTER cuando lo pida y, al terminar, mide el ángulo real con el transportador."
              "${CAL[@]}" --ros-args -p b_eff:="$B_USADO" -p odom_topic:=/odom -p target_angle_deg:=360.0 -p angular_vel:=0.5; RC=$? ;;
esac

if [ "$MODO" != "calibrar_b" ] && [ "$RC" -ne 0 ]; then
  case "$RC" in
    1) MSG="el dry-run/diagnóstico previo no estaba limpio";;
    2) MSG="parámetros u odometría inválidos";;
    3) MSG="faltó confirmar_movimiento";;
    4) MSG="no llega odometría (/odom): revisa Agent, dominio y odom_corrector";;
    5) MSG="cancelado en la confirmación (no escribiste MOVER)";;
    6) MSG="la prueba se abortó o se interrumpió a mitad";;
    7) MSG="el diagnóstico previo tenía FALLAS (otro publicador en /cmd_vel, nadie escucha...)";;
    *) MSG="error inesperado (el mensaje de arriba dice cuál)";;
  esac
  echo "ATENCIÓN: secuencia_rc0.py terminó con código $RC: $MSG." >&2
  read -r -p "¿Seguir de todos modos con la medición y el análisis? (s/n, por defecto n): " SEGUIR
  if [ "$SEGUIR" != "s" ]; then limpiar; echo "Corrida descartada. El bag queda en $BAGDIR (no se borra)."; exit 6; fi
fi

# -------------------------------------- 5. Parar el bag y comprobarlo -------------------------------------------------
limpia
BAT_D="$(leer_bat)"; echo "batería después (valor crudo): ${BAT_D:-?}"
[ -f "$BAGDIR/metadata.yaml" ] && ls "$BAGDIR"/*.db3 >/dev/null 2>&1 \
  || { echo "ERROR: el bag $BAGDIR quedó incompleto (sin metadata.yaml o sin .db3): se cortó la grabación." >&2; exit 3; }
INFO="$(ros2 bag info "$BAGDIR" 2>&1)"
echo "$INFO" | grep -E 'Duration|Messages' || true
CMDN="$(echo "$INFO" | sed -n 's/.*\/cmd_vel .*Count: \([0-9]*\).*/\1/p' | head -1)"
if [ "$MODO" != "calibrar_b" ] && { [ -z "$CMDN" ] || [ "$CMDN" -eq 0 ]; }; then
  echo "AVISO: el bag NO tiene mensajes de /cmd_vel: la secuencia no publicó o el bag no los vio. Revisa antes de medir." >&2
fi

# ---------------------------------------- 6. Lo que se medio y la fila del CSV -------------------------------------------
pedir() {  # pedir "texto" VARIABLE min max "pista"
  local intento v
  for intento in 1 2 3; do
    read -r -p "$1: " v
    v="${v//,/.}"
    if [[ "$v" =~ ^[0-9]+([.][0-9]+)?$ ]] && awk -v v="$v" -v a="$3" -v b="$4" 'BEGIN{exit !(v>=a && v<=b)}'; then
      printf -v "$2" '%s' "$v"; return 0
    fi
    echo "  valor inválido '$v': $5 (rango $3 a $4). Intento $intento/3." >&2
  done
  return 1
}

RES="sin_fila"
if [ "$MODO" = "calibrar_b" ]; then
  echo
  echo "calibrate_beff ya escribió su fila en calibration_log.csv (en $(pwd)). Últimas líneas:"
  tail -n 3 calibration_log.csv 2>/dev/null || echo "(no existe calibration_log.csv: ¿calibrate_beff terminó sin llegar a pedir el ángulo medido?)"
  echo "OJO: ese script escribe siempre 'iteracion = 1'; corrígelo a mano a $N en la última fila."
  echo "El b_eff propuesto lo decide el grupo; se aplica con:  bash scripts/aplicar_param.sh wheel_separation <valor>"
  RES="calibrate_beff"
else
  ANA=( ${RC0_ANALIZAR_CMD:-python3 capytown_esan/analizar_bag.py} )
  if [ "$MODO" = "recta" ]; then
    pedir "d_real medida con CINTA, en METROS (p. ej. 0.985)" D_REAL 0.05 5 "¿está en metros? 98 cm = 0.98" || err "sin d_real válida. El bag está en $BAGDIR; repite el análisis a mano."
    pedir "desvío lateral medido con cinta, en METROS (p. ej. 0.012; solo la magnitud)" DESVIO 0 0.5 "1.2 cm = 0.012" || err "sin desvío válido."
    read -r -p "lado del desvío (izq/der/ninguno): " LADO
    if [ "$VAR" = "A1" ]; then
      ARGS=(--prueba recta --d-real "$D_REAL" --csv linea_recta --corrida "$N" --r "$R_USADO" --desvio-m "$DESVIO")
    else
      ARGS=(--prueba recta --d-real "$D_REAL" --csv validacion --variante A2 --valor-real "$D_REAL")
    fi
  else
    pedir "ángulo físico MEDIDO con transportador, en GRADOS (p. ej. 355.5; magnitud, 720 = dos vueltas)" THETA 10 1500 "¿grados, no radianes?" || err "sin ángulo válido."
    read -r -p "¿se pasó o se quedó corto de la vuelta? (pasó/corto/exacto): " LADO
    ARGS=(--prueba giro --csv validacion --variante A2 --valor-real "$THETA")
  fi
  echo
  "${ANA[@]}" "$BAGDIR" "${ARGS[@]}"; RCA=$?
  if [ "$RCA" -ne 0 ]; then
    echo "ERROR: el análisis falló (código $RCA; el motivo está arriba). El bag sigue en $BAGDIR; corrige y repite SOLO el análisis con analizar_bag.py." >&2
    RES="analisis_fallido"
  else
    read -r -p "¿Escribir esta fila en $CSV? (s/n): " W
    if [ "$W" = "s" ]; then
      "${ANA[@]}" "$BAGDIR" "${ARGS[@]}" --escribir "$CSV" && RES="fila_escrita" || RES="escritura_fallida"
    else
      RES="fila_no_escrita"
    fi
  fi
fi

# ------------------------------------------- 7. Bitácora ----------------------------------------------------------------
read -r -p "nota de la corrida (opcional, Enter para omitir): " NOTA
BL="bitacora_corridas.csv"
[ -s "$BL" ] || echo "timestamp,modo,variante,n,bag,bateria_antes,bateria_despues,r,b_eff,resultado,observacion,nota" > "$BL"
echo "$(date +%FT%T),$MODO,$VAR,$N,$BAGDIR,${BAT_A:-},${BAT_D:-},$R_USADO,$B_USADO,$RES,${LADO:-},${NOTA//,/;}" >> "$BL"

echo
echo "=== listo: $PREFIJO · resultado: $RES · bitácora: $BL"
echo "Siguiente: gráficas -> python3 capytown_esan/plot_odom.py $BAGDIR   ·   copia el bag fuera del robot (docs/guia_trabajo_roscar.md §4)."
echo "Si el error supera el umbral, el grupo decide el nuevo valor y lo aplica con scripts/aplicar_param.sh."
