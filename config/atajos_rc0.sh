# Atajos RC-0: comandos cortos, sin rutas ni símbolos especiales que teclear.
# Uso (una vez por terminal, dentro de ros2_dev; con Tab se completa la ruta):
#     source /root/yahboomcar_ws/rc0_rama/config/atajos_rc0.sh
# Solo define funciones en ESTA terminal: no edita .bashrc ni nada del sistema.
# Escribe  ayuda  para ver la lista. Los nombres de bag se dan sin "bags/".
# Seguridad: nada se mueve por defecto. "secuencia ... mover" quita el dry-run, pero la secuencia sigue
# exigiendo escribir MOVER y la cuenta atrás; solo con el robot a la vista y una persona lista para frenar.

RC0_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROS_DOMAIN_ID="${RC0_DOMAIN_ID:-${ROS_DOMAIN_ID:-20}}"

rc0()       { cd "$RC0_DIR" || return; }                                                      # ir al repo
parteA()    { (cd "$RC0_DIR" && bash scripts/parteA_contenedor.sh "$@"); }                    # diagnóstico, solo lectura
grabar()    { (cd "$RC0_DIR" && bash scripts/grabar_bag.sh "${1:?uso: grabar rc0_recta_c1}"); }  # graba un bag (Ctrl+C termina)
fijar()     { (cd "$RC0_DIR" && bash scripts/fijar_bag_final.sh "bags/${1:?uso: fijar <bag> rc0_recta}" "${2:?falta el nombre final}"); }
graficar()  { (cd "$RC0_DIR" && python3 capytown_esan/plot_odom.py "bags/${1:?uso: graficar <bag>}" "${@:2}"); }
analizar()  { (cd "$RC0_DIR" && python3 capytown_esan/analizar_bag.py "bags/${1:?uso: analizar <bag> --prueba recta ...}" "${@:2}"); }
verificar() { (cd "$RC0_DIR" && python3 scripts/verificacion_entrega.py "$@"); }
tablas()    { (cd "$RC0_DIR" && python3 scripts/generar_tablas_informe.py "$@"); }
bateria()   { timeout 10 ros2 topic echo /battery --once; }                                   # lee la batería (solo lectura)

secuencia() {   # secuencia recta|giro_a1|giro_a2 [mover] [-p otro:=valor ...]
  local preset="${1:?uso: secuencia recta|giro_a1|giro_a2 [mover]}"; shift
  local args=()
  case "$preset" in
    recta)   args=(-p modo:=recta) ;;
    giro_a1) args=(-p modo:=giro -p sentido:=antihorario) ;;   # A1: antihorario
    giro_a2) args=(-p modo:=giro -p sentido:=horario) ;;       # A2: horario
    *) echo "preset desconocido: $preset (recta, giro_a1, giro_a2)"; return 2 ;;
  esac
  if [ "${1:-}" = "mover" ]; then shift; args+=(-p dry_run:=false -p confirmar_movimiento:=true); fi
  (cd "$RC0_DIR" && python3 capytown_esan/secuencia_rc0.py --ros-args "${args[@]}" "$@")
}

ayuda() {
  cat <<'AYUDA'
rc0                     ir a la carpeta del repo
parteA                  diagnóstico de solo lectura (añade a setup_log.txt)
bateria                 lee /battery una vez
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
