# Atajos RC-0: comandos cortos, sin rutas ni símbolos especiales que teclear.
# Uso (una vez por terminal, dentro de ros2_dev; con Tab se completa la ruta):
#     source /root/yahboomcar_ws/rc0_rama/config/atajos_rc0.sh
# Solo define funciones en ESTA terminal: no edita .bashrc ni nada del sistema.
# Escribe  ayuda  para ver la lista. Los nombres de bag se dan sin "bags/".
# Seguridad: nada se mueve por defecto. "secuencia ... mover" quita el dry-run, pero la secuencia sigue
# exigiendo escribir MOVER y la cuenta atrás; solo con el robot a la vista y una persona lista para frenar.

# ROS 2 base (ahí vive rosbag2) y workspace: solo en esta terminal
[ -f /opt/ros/humble/setup.bash ] && source /opt/ros/humble/setup.bash
[ -f /root/yahboomcar_ws/install/setup.bash ] && source /root/yahboomcar_ws/install/setup.bash
RC0_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Dominio del reto: 8 (Grupo 8). Los valores iniciales de la Parte A se tomaron con 20 (el del Agent tal como llegó).
# Para ensayos con fake_robot: RC0_ENSAYO=1 RC0_DOMAIN_ID=77 antes del source.
if [ "${RC0_ENSAYO:-0}" = "1" ] && [ -n "${RC0_DOMAIN_ID:-}" ]; then export ROS_DOMAIN_ID="$RC0_DOMAIN_ID"
else export ROS_DOMAIN_ID=8; fi

rc0()       { cd "$RC0_DIR" || return; }                                                      # ir al repo
parteA()    { (cd "$RC0_DIR" && bash scripts/parteA_contenedor.sh "$@"); }                    # diagnóstico, solo lectura
grabar()    { (cd "$RC0_DIR" && bash scripts/grabar_bag.sh "${1:?uso: grabar rc0_recta_c1}"); }  # graba un bag (Ctrl+C termina)
fijar()     { (cd "$RC0_DIR" && bash scripts/fijar_bag_final.sh "bags/${1:?uso: fijar <bag> rc0_recta}" "${2:?falta el nombre final}"); }
graficar()  { (cd "$RC0_DIR" && python3 capytown_esan/plot_odom.py "bags/${1:?uso: graficar <bag>}" "${@:2}"); }
analizar()  { (cd "$RC0_DIR" && python3 capytown_esan/analizar_bag.py "bags/${1:?uso: analizar <bag> --prueba recta ...}" "${@:2}"); }
preflight() { (cd "$RC0_DIR" && bash scripts/preflight.sh "$@"); }                          # comprobaciones antes de mover (solo lectura)
corrida()   { (cd "$RC0_DIR" && bash scripts/corrida.sh "$@"); }                            # corrida guiada: corrida recta A1 1
aplicar()   { (cd "$RC0_DIR" && bash scripts/aplicar_param.sh "$@"); }                      # cambia r o b_eff en caliente, con registro
verificar() { (cd "$RC0_DIR" && python3 scripts/verificacion_entrega.py "$@"); }
tablas()    { (cd "$RC0_DIR" && python3 scripts/generar_tablas_informe.py "$@"); }
bateria()   { timeout 10 ros2 topic echo /battery --once; }                                   # lee la batería (solo lectura)
# Lanza odom_corrector (no mueve el robot) con el wheel_params.yaml FUENTE del paquete del docente: valores iniciales
# de la calibración r=0.0311 m, b_eff=0.2259 m (confirmados por el grupo). Sin el argumento cargaría la copia instalada
# (0.031256 / 0.2450), que alguien editó. Ocupa la terminal: déjala abierta. Otro archivo: RC0_YAML=<ruta> bringup
bringup() {
  local y="${RC0_YAML:-/root/yahboomcar_ws/src/capytown_esan/config/wheel_params.yaml}"
  if [ ! -f "$y" ]; then   # sin el archivo, odom_corrector arrancaría con r=r0 y b_eff=b0 (k=1) y solo avisaría en el log del launch
    echo "ERROR: no existe el YAML de parámetros: $y"
    echo "  Busca el del robot:  find /root/yahboomcar_ws -name wheel_params.yaml   y lánzalo con:  RC0_YAML=<ruta> bringup"
    return 1
  fi
  ros2 launch capytown_esan bringup.launch.py wheel_params:="$y"
}

secuencia() {   # secuencia recta|giro_a1|giro_a2 [mover] [-p otro:=valor ...]
  local preset="${1:?uso: secuencia recta|giro_a1|giro_a2 [mover]}"; shift
  local args=()
  case "$preset" in
    recta)   args=(-p modo:=recta -p odom_topic:=/odom) ;;
    giro_a1) args=(-p modo:=giro -p sentido:=antihorario -p odom_topic:=/odom) ;;   # A1: antihorario
    giro_a2) args=(-p modo:=giro -p sentido:=horario -p odom_topic:=/odom) ;;       # A2: horario
    *) echo "preset desconocido: $preset (recta, giro_a1, giro_a2)"; return 2 ;;
  esac
  if [ "${1:-}" = "mover" ]; then shift; args+=(-p dry_run:=false -p confirmar_movimiento:=true); fi
  (cd "$RC0_DIR" && python3 capytown_esan/secuencia_rc0.py --ros-args "${args[@]}" "$@")
}

ayuda() {
  cat <<'AYUDA'
preflight               comprobaciones de solo lectura antes de mover (nodos, topics, batería, parámetros)
corrida <modo> <A1|A2> <n>   corrida guiada con bag + medición + fila de CSV:
                        corrida recta A1 1 · corrida calibrar_b A1 1 · corrida recta A2 1 · corrida giro A2 1  (añade --rapido para saltar el preflight)
aplicar <wheel_radius|wheel_separation> <valor>   cambia r o b_eff en caliente (valida, confirma y registra)
rc0                     ir a la carpeta del repo
parteA                  diagnóstico de solo lectura (añade a setup_log.txt)
bateria                 lee /battery una vez
bringup                 lanza odom_corrector con el YAML inicial del docente (r=0.0311, b_eff=0.2259); deja la terminal abierta
grabar <prefijo>        graba un bag antes de mover, p. ej.  grabar rc0_recta_c1   (Ctrl+C termina)
secuencia recta         DRY-RUN de la recta (no mueve);  secuencia recta mover   -> movimiento real, pide MOVER
secuencia giro_a1       giro antihorario (A1);  giro_a2 = horario (A2);  mismo "mover"
graficar <bag>          dos PNG en plots/        analizar <bag> --prueba recta --listar
fijar <bag> <final>     copia a rc0_recta | rc0_giro | rc0_val_recta | rc0_val_giro
verificar | tablas      qué falta para entregar | tablas del informe
(el <bag> es el nombre de la carpeta dentro de bags/; con Tab se completa)
AYUDA
}
echo "Atajos RC-0 cargados (ROS_DOMAIN_ID=$ROS_DOMAIN_ID). Escribe: ayuda"
