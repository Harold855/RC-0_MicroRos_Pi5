#!/usr/bin/env bash
# Trae los bags del robot a ESTE equipo (laptop con Ubuntu/WSL o Pi 400). Nunca borra nada en el robot
# y siempre escribe en una carpeta nueva con fecha: no sobrescribe respaldos anteriores.
# Uso:  bash scripts/respaldar_bags.sh <usuario>@10.42.0.1:<ruta_de_bags_en_el_host> [carpeta_destino]
# Ej.:  bash scripts/respaldar_bags.sh <usuario>@10.42.0.1:~/rc0_respaldo/bags
# (Desde PowerShell en Windows usa directamente:  scp -r <usuario>@10.42.0.1:~/rc0_respaldo/bags .\respaldo_bags )
# Los bags se copian antes del host al exterior con docker cp: ver docs/guia_trabajo_roscar.md, sección 4.

ORIGEN="${1:?Uso: respaldar_bags.sh <usuario>@<host>:<ruta_remota> [carpeta_destino]}"
BASE="${2:-respaldo_bags}"
DESTINO="$BASE/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DESTINO" || exit 1

echo "Copiando $ORIGEN -> $DESTINO"
if command -v rsync >/dev/null 2>&1; then
  rsync -av --ignore-existing "$ORIGEN/" "$DESTINO/" || exit $?
else
  scp -r "$ORIGEN/." "$DESTINO/" || exit $?
fi

echo
echo "Comprobación: cada bag debe tener metadata.yaml y datos (.db3/.mcap)"
for d in "$DESTINO"/*/; do
  [ -d "$d" ] || continue
  if [ -f "$d/metadata.yaml" ] && ls "$d"/*.db3 "$d"/*.mcap 2>/dev/null | grep -q .; then echo "OK        $d"; else echo "INCOMPLETO $d"; fi
done
