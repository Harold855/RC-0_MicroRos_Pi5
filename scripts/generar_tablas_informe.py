#!/usr/bin/env python3
"""generar_tablas_informe — tablas (b), (c) y (d) del informe a partir de los CSV reales.

INTRODUCCIÓN
------------
El informe de 1 página lleva tres tablas: la recta de calibración, las iteraciones de
b_eff y la validación en la segunda variante. Este script las imprime en Markdown
leyendo linea_recta.csv, calibration_log.csv y validacion.csv, para no teclearlas.

  * No inventa nada: si un CSV no tiene filas, la tabla dice "(sin datos)".
  * Rechaza CSV marcados como SINTETICO.
  * No redacta la predicción ni la interpretación: eso lo escribe el grupo.

Uso:
  python3 scripts/generar_tablas_informe.py            # imprime en pantalla
  python3 scripts/generar_tablas_informe.py > informe/tablas.md
"""

import csv
import os
import sys
from typing import List, Tuple

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

TABLAS = [
    ("b) Recta de calibración (A1)", "linea_recta.csv",
     ["corrida", "r", "d_real", "d_odom", "error_%", "desvio_lateral"],
     ["Corrida", "r [m]", "d_real [m]", "d_odom [m]", "Error [%]", "Desvío lateral [m]"]),
    ("c) Calibración de b_eff (A1, giro de 360°)", "calibration_log.csv",
     ["iteracion", "b_eff_usado", "theta_reportado_deg", "theta_medido_deg", "error_%", "b_eff_propuesto"],
     ["Iter.", "b_eff usado [m]", "θ reportado [°]", "θ medido [°]", "Error [%]", "b_eff propuesto [m]"]),
    ("d) Validación sin recalibrar (A2)", "validacion.csv",
     ["variante", "prueba", "valor_real", "valor_odom", "error_%"],
     ["Variante", "Prueba", "Valor real", "Valor odom", "Error [%]"]),
]


def leer(ruta: str, encabezado: List[str]) -> List[List[str]]:
    with open(ruta, encoding="utf-8") as f:
        texto = f.read()
    if "SINTETICO" in texto.upper():
        raise ValueError(f"{os.path.basename(ruta)} contiene datos marcados SINTETICO: no se usan en el informe")
    filas = [r for r in csv.reader(texto.splitlines()) if r]
    if not filas:
        return []
    if filas[0] != encabezado:
        raise ValueError(f"{os.path.basename(ruta)}: encabezado {filas[0]}, se esperaba {encabezado}")
    return filas[1:]


def tabla_md(titulo: str, cabeceras: List[str], filas: List[List[str]]) -> str:
    out = [f"**{titulo}**", ""]
    if not filas:
        out.append("(sin datos)")
        return "\n".join(out) + "\n"
    out.append("| " + " | ".join(cabeceras) + " |")
    out.append("|" + "|".join("---" for _ in cabeceras) + "|")
    out += ["| " + " | ".join(f) + " |" for f in filas]
    return "\n".join(out) + "\n"


def generar(raiz: str = RAIZ) -> str:
    bloques = []
    for titulo, archivo, enc, cab in TABLAS:
        ruta = os.path.join(raiz, archivo)
        filas = leer(ruta, enc) if os.path.exists(ruta) else []
        bloques.append(tabla_md(titulo, cab, filas))
    return "\n".join(bloques)


if __name__ == "__main__":
    try:
        print(generar(sys.argv[1] if len(sys.argv) > 1 else RAIZ))
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
