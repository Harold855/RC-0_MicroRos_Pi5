#!/usr/bin/env bash
# Copia una corrida elegida al nombre exacto que exige el reto. No renombra ni borra la original.
# Uso:  bash scripts/fijar_bag_final.sh bags/rc0_recta_c3_20261029_130501 rc0_recta
# Nombres finales válidos: rc0_recta  rc0_giro  rc0_val_recta  rc0_val_giro
# Rechaza el trabajo si el destino ya existe (no sobrescribe) o si el origen no es un bag.

ORIGEN="${1:?Uso: fijar_bag_final.sh <carpeta_bag_origen> <nombre_final>}"
FINAL="${2:?Falta el nombre final (rc0_recta, rc0_giro, rc0_val_recta o rc0_val_giro)}"

case "$FINAL" in
  rc0_recta|rc0_giro|rc0_val_recta|rc0_val_giro) ;;
  *) echo "ERROR: nombre final no válido: $FINAL"; exit 2 ;;
esac
case "$ORIGEN" in
  *SINTETICO*|*sintetico*) echo "ERROR: un bag sintético no puede ser un entregable."; exit 2 ;;
esac
[ -f "$ORIGEN/metadata.yaml" ] || { echo "ERROR: $ORIGEN no es un bag (falta metadata.yaml)."; exit 2; }
ls "$ORIGEN"/*.db3 "$ORIGEN"/*.mcap 2>/dev/null | grep -q . || { echo "ERROR: $ORIGEN no tiene archivos de datos (.db3 o .mcap)."; exit 2; }

DESTINO="$(dirname "$ORIGEN")/$FINAL"
[ -e "$DESTINO" ] && { echo "ERROR: $DESTINO ya existe; no se sobrescribe. Muévelo tú a mano si de verdad quieres reemplazarlo."; exit 3; }

cp -r "$ORIGEN" "$DESTINO" && echo "Copiado: $ORIGEN -> $DESTINO (el original sigue intacto)"
