#!/usr/bin/env python3
"""analizar_bag — de un bag de odometría a los números que van a los CSV (RC-0).

INTRODUCCIÓN
------------
En el laboratorio solo se mide con cinta y transportador; este script saca del
bag lo que dice la odometría y calcula el error contra lo medido:

  recta : d_odom (norma del desplazamiento x–y), componente longitudinal y
          desvío lateral, entre el inicio y el fin del tramo en que el robot
          se movió.
  giro  : θ_odom acumulada (con unwrap, en grados, con signo: + antihorario).

El tramo de movimiento se detecta con la velocidad de la propia odometría
(|twist.linear.x| para rectas, |twist.angular.z| para giros) y no con la pose
absoluta: así reposicionar el robot a mano antes o después, o un reinicio del
bringup, no contaminan la medida. Un bag con varias corridas se separa con
--segmento N (use --listar para ver los tramos).

Por defecto IMPRIME y no escribe nada. Solo con --escribir añade UNA fila al CSV
indicado (nunca sobrescribe; si el archivo tiene contenido, su encabezado debe
coincidir exactamente). La regla para corregir `r` o `b_eff` NO está aquí: la
deduce el grupo; --b-eff-propuesto se teclea, no se calcula.

Unidades: las distancias van en METROS y los ángulos en GRADOS en los CSV
(los encabezados del reto no llevan unidades; dígalo en el README).
Error lineal: 100·|d_real − d_odom|/d_real. Error angular: por defecto sobre el
ángulo reportado (--denominador medido para el otro). [VERIFICAR con el docente]

Ejemplos:
  python3 capytown_esan/analizar_bag.py bags/rc0_recta --prueba recta --listar
  python3 capytown_esan/analizar_bag.py bags/rc0_recta --prueba recta --d-real 0.985
  python3 capytown_esan/analizar_bag.py bags/rc0_recta --prueba recta --d-real 0.985 \\
      --csv linea_recta --corrida 1 --r 0.0325 --desvio-m 0.012 --escribir linea_recta.csv

(El valor de r del ejemplo es inventado; use el que tenga el robot.)
Estado: la lectura del bag usa plot_odom.leer_odometria (rosbag2_py), sin probar
con un bag real. Todo lo demás está probado con datos sintéticos.
"""

import argparse
import csv
import math
import os
import sys
from typing import Dict, List, Optional, Sequence

try:
    import odom_utils as ou
except ImportError:  # pragma: no cover
    from capytown_esan import odom_utils as ou

ENCABEZADOS = {
    "linea_recta": ["corrida", "r", "d_real", "d_odom", "error_%", "desvio_lateral"],
    "validacion": ["variante", "prueba", "valor_real", "valor_odom", "error_%"],
    # El reto no fija este encabezado; es una propuesta del contexto del proyecto.
    "calibracion": ["iteracion", "b_eff_usado", "theta_reportado_deg", "theta_medido_deg", "error_%", "b_eff_propuesto"],
}


# --------------------------------------------------------------------------
# Cálculo (puro)
# --------------------------------------------------------------------------
def analizar(
    t: Sequence[float],
    poses: Sequence[ou.Pose],
    vel: Sequence[Sequence[float]],
    prueba: str,
    segmento: int = 1,
    umbral: Optional[float] = None,
) -> Dict:
    """Mide un tramo de movimiento. prueba: 'recta' o 'giro'. segmento: 1 = primero."""
    if prueba not in ("recta", "giro"):
        raise ValueError("prueba debe ser 'recta' o 'giro'")
    if umbral is None:
        umbral = 0.01 if prueba == "recta" else 0.02  # m/s y rad/s
    col = 0 if prueba == "recta" else 1
    magnitud = [v[col] for v in vel]
    tramos = ou.segmentos_movimiento(t, magnitud, umbral)
    if not tramos:
        raise ValueError(
            f"la velocidad de la odometría nunca supera {umbral}: no hay movimiento de tipo '{prueba}' en el bag"
        )
    if not 1 <= segmento <= len(tramos):
        raise ValueError(f"segmento {segmento} fuera de rango: el bag tiene {len(tramos)} tramo(s)")
    i0, i1 = tramos[segmento - 1]
    # la pose justo antes de arrancar y la primera en reposo después son los extremos reales
    a = max(i0 - 1, 0)
    b = min(i1 + 1, len(poses) - 1)
    tramo = list(poses[a : b + 1])
    norma, lon, lat = ou.desplazamiento(tramo)
    theta = math.degrees(ou.yaw_relativo([p[2] for p in tramo])[-1])
    return {
        "prueba": prueba,
        "segmento": segmento,
        "tramos_en_el_bag": len(tramos),
        "t_inicio_s": t[a],
        "t_fin_s": t[b],
        "d_odom_m": norma,
        "longitudinal_m": lon,
        "lateral_m": lat,
        "theta_odom_deg": theta,
        "reinicios": ou.detectar_reinicios(t[a : b + 1], tramo),
    }


def listar_tramos(t, vel, prueba, umbral=None):
    umbral = umbral if umbral is not None else (0.01 if prueba == "recta" else 0.02)
    col = 0 if prueba == "recta" else 1
    return ou.segmentos_movimiento(t, [v[col] for v in vel], umbral)


# --------------------------------------------------------------------------
# CSV (nunca sobrescribe)
# --------------------------------------------------------------------------
def _fmt(x) -> str:
    return f"{x:.4f}" if isinstance(x, float) else str(x)


def construir_fila(tipo: str, r: Dict, a: argparse.Namespace) -> List[str]:
    """Arma la fila del CSV `tipo`. Falla con un mensaje claro si falta un dato."""

    def exige(*nombres):
        faltan = [n for n in nombres if getattr(a, n) is None]
        if faltan:
            raise ValueError("para --csv " + tipo + " falta: " + ", ".join("--" + n.replace("_", "-") for n in faltan))

    if tipo == "linea_recta":
        exige("corrida", "r", "d_real")
        if a.desvio_m is None and not a.desvio_de_odom:
            raise ValueError("indica el desvío lateral medido con cinta (--desvio-m) o usa --desvio-de-odom")
        desvio = a.desvio_m if a.desvio_m is not None else abs(r["lateral_m"])
        err = ou.error_pct_lineal(a.d_real, r["d_odom_m"])
        return [str(a.corrida), _fmt(float(a.r)), _fmt(float(a.d_real)), _fmt(r["d_odom_m"]), _fmt(err), _fmt(float(desvio))]
    if tipo == "validacion":
        exige("variante", "valor_real")
        if r["prueba"] == "recta":
            odom, err = r["d_odom_m"], ou.error_pct_lineal(a.valor_real, r["d_odom_m"])
        else:
            odom = abs(r["theta_odom_deg"])
            err = ou.error_pct_angular(odom, a.valor_real, a.denominador)
        return [a.variante, r["prueba"], _fmt(float(a.valor_real)), _fmt(float(odom)), _fmt(err)]
    if tipo == "calibracion":
        exige("iteracion", "b_eff_usado", "theta_medido", "b_eff_propuesto")
        rep = abs(r["theta_odom_deg"])
        err = ou.error_pct_angular(rep, a.theta_medido, a.denominador)
        return [str(a.iteracion), _fmt(float(a.b_eff_usado)), _fmt(rep), _fmt(float(a.theta_medido)), _fmt(err), _fmt(float(a.b_eff_propuesto))]
    raise ValueError(f"tipo de CSV desconocido: {tipo}")


def anexar_fila(ruta: str, tipo: str, fila: List[str]) -> str:
    """Añade `fila` a `ruta`. Crea el encabezado si el archivo no existe o solo tiene espacios."""
    encabezado = ENCABEZADOS[tipo]
    contenido = ""
    if os.path.exists(ruta):
        with open(ruta, newline="") as f:
            contenido = f.read()
    if contenido.strip():
        primera = next(csv.reader([contenido.splitlines()[0]]))
        if primera != encabezado:
            raise ValueError(
                f"el encabezado de {ruta} es {primera} y se esperaba {encabezado}: no se escribe nada"
            )
        modo, necesita_salto = "a", not contenido.endswith("\n")
    else:
        modo, necesita_salto = "w", False  # vacío o solo saltos de línea: no hay datos que perder
    with open(ruta, modo, newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if necesita_salto:
            f.write("\n")
        if modo == "w":
            w.writerow(encabezado)
        w.writerow(fila)
    return ruta


# --------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Números de un bag de odometría para los CSV de RC-0.")
    ap.add_argument("bag", help="carpeta del bag")
    ap.add_argument("--prueba", choices=["recta", "giro"], required=True)
    ap.add_argument("--topic", default=None, help="topic de odometría (por defecto: el único Odometry del bag)")
    ap.add_argument("--segmento", type=int, default=1, help="tramo de movimiento a medir (1 = primero)")
    ap.add_argument("--umbral", type=float, default=None, help="umbral de velocidad para detectar movimiento")
    ap.add_argument("--listar", action="store_true", help="solo lista los tramos de movimiento y sale")
    ap.add_argument("--d-real", type=float, dest="d_real", help="distancia medida con cinta [m]")
    ap.add_argument("--theta-real", type=float, dest="theta_real", help="ángulo medido con transportador [°] (magnitud)")
    ap.add_argument("--denominador", choices=["reportado", "medido"], default="reportado")
    ap.add_argument("--csv", choices=sorted(ENCABEZADOS), help="qué fila armar")
    ap.add_argument("--escribir", metavar="ARCHIVO.csv", help="añade la fila a este CSV (sin esto, solo se muestra)")
    g = ap.add_argument_group("datos para las filas del CSV")
    g.add_argument("--corrida", type=int)
    g.add_argument("--r", type=float, help="radio de rueda usado en la corrida [m]")
    g.add_argument("--desvio-m", type=float, dest="desvio_m", help="desvío lateral medido con cinta [m]")
    g.add_argument("--desvio-de-odom", action="store_true", dest="desvio_de_odom",
                   help="usar el desvío lateral de la odometría en lugar del medido")
    g.add_argument("--variante", help="A1 o A2 (validacion.csv)")
    g.add_argument("--valor-real", type=float, dest="valor_real", help="valor medido [m] (recta) o [°] (giro)")
    g.add_argument("--iteracion", type=int)
    g.add_argument("--b-eff-usado", type=float, dest="b_eff_usado")
    g.add_argument("--theta-medido", type=float, dest="theta_medido")
    g.add_argument("--b-eff-propuesto", type=float, dest="b_eff_propuesto", help="lo calcula el grupo, no este script")
    a = ap.parse_args(argv)
    if a.theta_real is not None and a.theta_medido is None:
        a.theta_medido = a.theta_real

    try:
        import plot_odom  # lee el bag (necesita rosbag2_py)

        topic, t, poses, vel = plot_odom.leer_odometria(a.bag.rstrip("/\\"), a.topic)
        if a.listar:
            for k, (i0, i1) in enumerate(listar_tramos(t, vel, a.prueba, a.umbral), 1):
                print(f"tramo {k}: t = {t[i0]:.2f}–{t[i1]:.2f} s ({t[i1]-t[i0]:.2f} s)")
            return 0
        r = analizar(t, poses, vel, a.prueba, a.segmento, a.umbral)
        print(f"bag: {a.bag} · topic: {topic} · tramo {r['segmento']}/{r['tramos_en_el_bag']} "
              f"(t = {r['t_inicio_s']:.2f}–{r['t_fin_s']:.2f} s)")
        if a.prueba == "recta":
            print(f"d_odom = {r['d_odom_m']:.4f} m · longitudinal = {r['longitudinal_m']:.4f} m · "
                  f"lateral (odom) = {r['lateral_m']:+.4f} m")
            if a.d_real is not None:
                print(f"error lineal = {ou.error_pct_lineal(a.d_real, r['d_odom_m']):.2f} %  (d_real = {a.d_real} m)")
        else:
            print(f"θ_odom = {r['theta_odom_deg']:+.2f}° (+ antihorario)")
            if a.theta_medido is not None:
                e = ou.error_pct_angular(r["theta_odom_deg"], a.theta_medido, a.denominador)
                print(f"error angular = {e:.2f} %  (denominador: {a.denominador}; θ medido = {a.theta_medido}°)")
        for i, msg in r["reinicios"]:
            print(f"AVISO: posible reinicio o pérdida de datos dentro del tramo (muestra {i}): {msg}", file=sys.stderr)

        if a.csv:
            fila = construir_fila(a.csv, r, a)
            print(f"fila {a.csv}: {','.join(ENCABEZADOS[a.csv])}\n         {','.join(fila)}")
            if a.escribir:
                print("añadida a", anexar_fila(a.escribir, a.csv, fila))
            else:
                print("(no se escribió nada: falta --escribir ARCHIVO.csv)")
        elif a.escribir:
            raise ValueError("--escribir necesita --csv para saber qué fila armar")
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
