#!/usr/bin/env python3
"""verificacion_entrega — comprueba el repositorio contra los entregables de RC-0.

INTRODUCCIÓN
------------
Revisa, sin ROS ni robot, que el repositorio tenga lo que pide el reto:
archivos, encabezados y filas de los CSV, los cuatro bags, los PNG por bag,
los valores finales en config/wheel_params.yaml, el README y el informe.

Estados:
  OK         cumple.
  PENDIENTE  todavía no hay datos o falta un paso (normal antes de las pruebas).
  ERROR      hay algo inconsistente (encabezado distinto, dato sintético, umbral no cumplido).
  AVISO      no se pudo comprobar o conviene revisarlo a mano.

Qué comprueba y qué NO:
  * Comprueba estructura y umbrales (error de recta final <= 2 %, de giro < 1 %).
    NO comprueba que las mediciones sean verdaderas ni que el robot esté calibrado.
  * Rechaza todo lo marcado como sintético (SINTETICO) en CSV, bags o PNG.
  * El umbral de giro usa la columna error_% de calibration_log.csv, calculada con
    la convención que el grupo haya elegido (por defecto sobre el ángulo reportado).

Uso:
  python3 scripts/verificacion_entrega.py            # informe; termina con error solo si hay ERROR
  python3 scripts/verificacion_entrega.py --final    # PENDIENTE y AVISO también cuentan como fallo
  python3 scripts/verificacion_entrega.py --raiz ruta/al/repo
"""

import argparse
import csv
import os
import re
import subprocess
import sys
from typing import List, Optional, Tuple

OK, PEND, ERR, AVISO = "OK", "PENDIENTE", "ERROR", "AVISO"
Item = Tuple[str, str, str]

ENC_RECTA = ["corrida", "r", "d_real", "d_odom", "error_%", "desvio_lateral"]
ENC_VALID = ["variante", "prueba", "valor_real", "valor_odom", "error_%"]
ENC_CALIB = ["iteracion", "b_eff_usado", "theta_reportado_deg", "theta_medido_deg", "error_%", "b_eff_propuesto"]
BAGS = ["rc0_recta", "rc0_giro", "rc0_val_recta", "rc0_val_giro"]
ROLES = ["Integración", "Control", "Planificación", "Percepción"]


def _leer(path: str) -> Optional[str]:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _csv(path: str):
    txt = _leer(path)
    if txt is None:
        return None, None
    filas = [r for r in csv.reader(txt.splitlines()) if r]
    return (filas[0] if filas else []), filas[1:]


def _num(x: str) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _sint(txt: str) -> bool:
    return "SINTETICO" in txt.upper()


# --------------------------------------------------------------------------
def revisar_csv(raiz: str) -> List[Item]:
    out: List[Item] = []
    for nombre, enc in (("linea_recta.csv", ENC_RECTA), ("calibration_log.csv", ENC_CALIB), ("validacion.csv", ENC_VALID)):
        ruta = os.path.join(raiz, nombre)
        cab, filas = _csv(ruta)
        if cab is None:
            out.append((ERR, nombre, "no existe"))
            continue
        if cab != enc:
            out.append((ERR, nombre, f"encabezado {cab}; se esperaba {enc}"))
            continue
        if _sint(_leer(ruta) or ""):
            out.append((ERR, nombre, "contiene datos marcados como SINTETICO"))
            continue
        out.append((OK, nombre + " (encabezado)", ""))
        col = enc.index("error_%")

        if nombre == "linea_recta.csv":
            if len(filas) < 3:
                out.append((PEND, nombre, f"{len(filas)} corrida(s); el reto pide al menos 3"))
            else:
                e = _num(filas[-1][col])
                if e is None:
                    out.append((ERR, nombre, "la última corrida no tiene error_% numérico"))
                elif e <= 2.0:
                    out.append((OK, nombre, f"{len(filas)} corridas; error final {e:.2f} % <= 2 %"))
                else:
                    out.append((ERR, nombre, f"error final {e:.2f} % > 2 %: falta ajustar r y repetir"))
        elif nombre == "calibration_log.csv":
            if not filas:
                out.append((PEND, nombre, "sin iteraciones de b_eff"))
            else:
                e = _num(filas[-1][col])
                if e is None:
                    out.append((ERR, nombre, "la última iteración no tiene error_% numérico"))
                elif e < 1.0:
                    out.append((OK, nombre, f"{len(filas)} iteraciones; error final {e:.2f} % < 1 %"))
                else:
                    out.append((ERR, nombre, f"error final {e:.2f} % >= 1 %: falta converger"))
        else:  # validacion
            pruebas = [f[1] for f in filas if len(f) > 1]
            nr, ng = pruebas.count("recta"), pruebas.count("giro")
            if nr >= 2 and ng >= 1:
                out.append((OK, nombre, f"{nr} recta(s) y {ng} giro(s)"))
            else:
                out.append((PEND, nombre, f"{nr} recta(s) y {ng} giro(s); el reto pide 2 rectas y 1 giro"))
            if any(f[0] != "A2" for f in filas if f):
                out.append((AVISO, nombre, "hay filas con variante distinta de A2 (S-003 valida en A2)"))
    return out


def revisar_bags_y_plots(raiz: str) -> List[Item]:
    out: List[Item] = []
    plots = os.path.join(raiz, "plots")
    pngs = sorted(os.listdir(plots)) if os.path.isdir(plots) else []
    for b in BAGS:
        d = os.path.join(raiz, "bags", b)
        if not os.path.isdir(d):
            out.append((PEND, f"bags/{b}/", "no existe todavía"))
        else:
            meta = _leer(os.path.join(d, "metadata.yaml"))
            datos = [f for f in os.listdir(d) if f.endswith((".db3", ".mcap"))]
            if meta is None:
                out.append((ERR, f"bags/{b}/", "falta metadata.yaml"))
            elif not datos:
                out.append((ERR, f"bags/{b}/", "no tiene archivos de datos (.db3 o .mcap)"))
            else:
                m = re.search(r"storage_identifier:\s*(\w+)", meta)
                sid = m.group(1) if m else "?"
                ext = {"sqlite3": ".db3", "mcap": ".mcap"}.get(sid)
                if ext and not any(f.endswith(ext) for f in datos):
                    out.append((ERR, f"bags/{b}/", f"metadata dice {sid} pero los datos son {datos}"))
                else:
                    out.append((OK, f"bags/{b}/", f"{sid}: {', '.join(datos)}"))
        for suf in ("_xy.png", "_theta_t.png"):
            if f"{b}{suf}" in pngs:
                out.append((OK, f"plots/{b}{suf}", ""))
            else:
                out.append((PEND, f"plots/{b}{suf}", "falta (plot_odom.py)"))
    carpeta_bags = os.path.join(raiz, "bags")
    nombres_bags = os.listdir(carpeta_bags) if os.path.isdir(carpeta_bags) else []
    if any(_sint(p) for p in pngs) or any(_sint(x) for x in nombres_bags):
        out.append((ERR, "bags/ o plots/", "hay archivos marcados SINTETICO: no son evidencia"))
    return out


def revisar_yaml(raiz: str) -> List[Item]:
    txt = _leer(os.path.join(raiz, "config", "wheel_params.yaml"))
    if txt is None or not txt.strip():
        return [(ERR, "config/wheel_params.yaml", "no existe o está vacío")]
    vals = {}
    for linea in txt.splitlines():
        m = re.match(r"\s*([A-Za-z_][\w]*)\s*:\s*([^#\s][^#]*?)\s*(#.*)?$", linea)
        if m:
            vals[m.group(1)] = m.group(2)
    out: List[Item] = []
    for etiqueta, claves in (("r (radio)", ("wheel_radius", "r", "radius")), ("b_eff (ancho de vía)", ("b_eff", "wheel_separation", "wheel_base"))):
        k = next((c for c in claves if c in vals), None)
        if k is None:
            out.append((AVISO, "config/wheel_params.yaml", f"no encuentro la clave de {etiqueta} ({'/'.join(claves)})"))
        elif _num(vals[k]) is None:
            out.append((PEND, "config/wheel_params.yaml", f"{k}: {vals[k]} (todavía sin valor calibrado)"))
        else:
            out.append((OK, "config/wheel_params.yaml", f"{k}: {vals[k]}"))
    return out


def revisar_readme(raiz: str) -> List[Item]:
    txt = _leer(os.path.join(raiz, "README.md"))
    if txt is None:
        return [(ERR, "README.md", "no existe")]
    out: List[Item] = []
    for k in ("S-003", "ROS_DOMAIN_ID", "A1", "A2"):
        out.append((OK if k in txt else ERR, "README.md", f"menciona {k}" if k in txt else f"no menciona {k}"))
    sin_def = [r for r in ROLES if r not in txt] or ("por definir" in txt.lower())
    out.append((PEND if sin_def else OK, "README.md", "roles de los integrantes " + ("sin completar" if sin_def else "completos")))
    pend = [l.strip() for l in txt.splitlines() if re.search(r"final", l, re.I) and re.search(r"pendiente", l, re.I)]
    out.append((PEND if pend else OK, "README.md", "r y b_eff finales " + ("pendientes" if pend else "anotados")))
    return out


def _paginas_pdf(ruta: str) -> Tuple[Optional[int], str]:
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader  # type: ignore
        return len(PdfReader(ruta).pages), "exacto"
    except ImportError:
        with open(ruta, "rb") as f:
            n = len(re.findall(rb"/Type\s*/Page(?![s\w])", f.read()))
        return (n or None), "estimado (sin pypdf)"
    except Exception as e:  # PDF dañado
        return None, f"no se pudo leer: {e}"


def revisar_otros(raiz: str) -> List[Item]:
    out: List[Item] = []
    sl = _leer(os.path.join(raiz, "setup_log.txt"))
    if sl is None or not sl.strip():
        out.append((PEND, "setup_log.txt", "no existe o está vacío (Parte A)"))
    else:
        falta = [k for k in ("ROS_DOMAIN_ID", "/imu") if k not in sl]
        hz = re.search(r"average rate", sl)
        if falta or not hz:
            out.append((AVISO, "setup_log.txt", "no veo " + ", ".join(falta + ([] if hz else ["frecuencia (average rate)"])) + "; revísalo a mano"))
        else:
            out.append((OK, "setup_log.txt", "tiene dominio, /imu y frecuencias"))
        if _sint(sl):
            out.append((ERR, "setup_log.txt", "marcado como SINTETICO"))

    pdf = os.path.join(raiz, "informe.pdf")
    if not os.path.isfile(pdf):
        out.append((PEND, "informe.pdf", "no existe (debe tener exactamente 1 página)"))
    else:
        n, como = _paginas_pdf(pdf)
        if n is None:
            out.append((AVISO, "informe.pdf", como))
        elif n == 1:
            out.append((OK, "informe.pdf", f"1 página ({como})"))
        else:
            out.append((ERR if como == "exacto" else AVISO, "informe.pdf", f"{n} páginas ({como}); debe ser exactamente 1"))

    out.append((OK if os.path.isfile(os.path.join(raiz, "capytown_esan", "plot_odom.py")) and
                os.path.getsize(os.path.join(raiz, "capytown_esan", "plot_odom.py")) > 100 else ERR,
                "capytown_esan/plot_odom.py", "existe" ))
    try:
        tags = subprocess.run(["git", "-C", raiz, "tag", "-l"], capture_output=True, text=True, timeout=10).stdout.split()
        out.append((OK if "v1.0-rc0" in tags else PEND, "tag git", "v1.0-rc0 " + ("presente" if "v1.0-rc0" in tags else "aún no creado")))
    except (OSError, subprocess.SubprocessError):
        out.append((AVISO, "tag git", "no se pudo consultar git"))
    nombre = os.path.basename(os.path.abspath(raiz))
    if not re.fullmatch(r"capytown_G\w+", nombre):
        out.append((AVISO, "nombre del repositorio", f"el reto pide capytown_G<n>; esta carpeta se llama {nombre} (revisa el nombre del repo remoto)"))
    return out


def verificar(raiz: str) -> List[Item]:
    return (revisar_csv(raiz) + revisar_bags_y_plots(raiz) + revisar_yaml(raiz)
            + revisar_readme(raiz) + revisar_otros(raiz))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Comprueba el repositorio contra los entregables de RC-0.")
    ap.add_argument("--raiz", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--final", action="store_true", help="PENDIENTE y AVISO también cuentan como fallo")
    a = ap.parse_args(argv)

    items = verificar(a.raiz)
    for estado, nombre, detalle in items:
        print(f"{estado:<10} {nombre}" + (f" — {detalle}" if detalle else ""))
    cuenta = {e: sum(1 for i in items if i[0] == e) for e in (OK, PEND, AVISO, ERR)}
    print("\nResumen: " + " · ".join(f"{k} {v}" for k, v in cuenta.items()))
    print("Recuerda: esto valida estructura y umbrales, no que las mediciones sean reales ni que el robot esté calibrado.")
    malo = cuenta[ERR] or (a.final and (cuenta[PEND] or cuenta[AVISO]))
    return 1 if malo else 0


if __name__ == "__main__":
    sys.exit(main())
