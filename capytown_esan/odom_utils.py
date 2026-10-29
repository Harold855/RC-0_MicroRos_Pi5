"""odom_utils — matemática de odometría para RC-0 (sin dependencias de ROS).

INTRODUCCIÓN
------------
/odom_raw (o /odom) entrega, por cada mensaje nav_msgs/Odometry, una pose
(x, y, orientación como cuaternión) acumulada desde que arrancó el bringup.
Para calibrar el robot no importa dónde está en el mapa, sino cuánto se movió
entre el inicio y el final de una prueba. Por eso este módulo trabaja siempre
con magnitudes RELATIVAS a la pose inicial del tramo.

Tres ideas que sostienen todo lo demás:

1. Yaw desde el cuaternión. La orientación llega como (x, y, z, w); en el plano
   solo interesa el giro alrededor de Z: yaw = atan2(2(wz + xy), 1 - 2(y² + z²)).
   El resultado vive en (-π, π].

2. Desenrollar (unwrap). Un giro de 360° termina con el mismo yaw con el que
   empezó, y cruzar ±π produce un salto de 2π en la gráfica. Sin desenrollar,
   un giro completo parece "no giro". Al desenrollar se suma o resta 2π cada vez
   que hay un salto, y el ángulo acumulado sí vale ±2π tras una vuelta
   (positivo = antihorario, negativo = horario, con Z hacia arriba).

3. Distancia recorrida = norma del desplazamiento (x, y) entre inicio y fin,
   no la coordenada x final. El desvío lateral es la componente perpendicular a
   la orientación inicial.

Convenciones (documentarlas también en el README):
- Unidades internas: metros y radianes. Los grados solo se usan en tablas.
- Error lineal (lo define el reto): 100 · |d_real − d_odom| / d_real.
- Error angular: el reto RC-0 no fija el denominador. Los ejemplos de la
  presentación de calibración solo cuadran dividiendo por el ángulo REPORTADO.
  Aquí es el valor por defecto, pero se puede elegir. [VERIFICAR con el docente]

Este módulo NO contiene la regla para corregir `r` ni `b_eff`: esa regla la
deduce el grupo a partir del modelo diferencial (se pregunta en la defensa).
"""

import math
from typing import List, Optional, Sequence, Tuple

Pose = Tuple[float, float, float]  # (x [m], y [m], yaw [rad])


# --------------------------------------------------------------------------
# Orientación
# --------------------------------------------------------------------------
def quat_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """Yaw (rad, en (-π, π]) de un cuaternión; ignora roll y pitch."""
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def unwrap_yaw(yaws: Sequence[float]) -> List[float]:
    """Desenrolla una serie de yaw: elimina los saltos de ±2π entre muestras.

    Supone que entre dos muestras consecutivas el robot gira menos de π; con
    odometría a decenas de Hz y ω ≈ 0.5 rad/s se cumple con mucho margen.
    """
    out: List[float] = []
    offset = 0.0
    prev: Optional[float] = None
    for a in yaws:
        if prev is not None:
            delta = a - prev
            if delta > math.pi:
                offset -= 2.0 * math.pi
            elif delta < -math.pi:
                offset += 2.0 * math.pi
        out.append(a + offset)
        prev = a
    return out


def yaw_relativo(yaws: Sequence[float]) -> List[float]:
    """Yaw desenrollado y referido al primero: θ_rel(t) = unwrap(yaw) − unwrap(yaw)[0]."""
    u = unwrap_yaw(yaws)
    if not u:
        return []
    return [a - u[0] for a in u]


# --------------------------------------------------------------------------
# Traslación
# --------------------------------------------------------------------------
def desplazamiento(poses: Sequence[Pose]) -> Tuple[float, float, float]:
    """(norma, longitudinal, lateral) entre la primera y la última pose.

    longitudinal: componente a lo largo de la orientación inicial (adelante > 0).
    lateral: componente perpendicular; > 0 es hacia la izquierda del robot.
    """
    if len(poses) < 2:
        raise ValueError("se necesitan al menos 2 poses")
    x0, y0, th0 = poses[0]
    x1, y1, _ = poses[-1]
    dx, dy = x1 - x0, y1 - y0
    longitudinal = dx * math.cos(th0) + dy * math.sin(th0)
    lateral = -dx * math.sin(th0) + dy * math.cos(th0)
    return math.hypot(dx, dy), longitudinal, lateral


def trayectoria_relativa(poses: Sequence[Pose]) -> List[Tuple[float, float]]:
    """Puntos (x, y) en el marco del robot al inicio: origen en la pose inicial,
    eje +X hacia donde miraba el robot. Así una recta ideal es una línea sobre
    +X y el desvío lateral se ve directamente en Y."""
    if not poses:
        return []
    x0, y0, th0 = poses[0]
    c, s = math.cos(th0), math.sin(th0)
    return [((x - x0) * c + (y - y0) * s, -(x - x0) * s + (y - y0) * c) for x, y, _ in poses]


# --------------------------------------------------------------------------
# Errores
# --------------------------------------------------------------------------
def error_pct_lineal(d_real: float, d_odom: float) -> float:
    """Error del reto: 100 · |d_real − d_odom| / d_real."""
    if d_real == 0:
        raise ValueError("d_real no puede ser 0")
    return 100.0 * abs(d_real - d_odom) / abs(d_real)


def error_pct_angular(theta_rep: float, theta_med: float, denominador: str = "reportado") -> float:
    """Error angular en %, con magnitudes (el sentido no entra).

    denominador: "reportado" (por defecto; reproduce los ejemplos de la
    presentación de calibración) o "medido". Usar la MISMA convención en el
    CSV, las gráficas y el informe.
    """
    rep, med = abs(theta_rep), abs(theta_med)
    if denominador == "reportado":
        base = rep
    elif denominador == "medido":
        base = med
    else:
        raise ValueError("denominador debe ser 'reportado' o 'medido'")
    if base == 0:
        raise ValueError("el denominador del error no puede ser 0")
    return 100.0 * abs(rep - med) / base


# --------------------------------------------------------------------------
# Segmentación y control de calidad
# --------------------------------------------------------------------------
def ventana_movimiento(
    t: Sequence[float],
    velocidad: Sequence[float],
    umbral: float = 0.01,
) -> Optional[Tuple[int, int]]:
    """Índices (inicio, fin) del primer tramo en que |velocidad| > umbral.

    Sirve para recortar la parte en que el robot se mueve y que reposicionar el
    robot a mano antes o después no contamine la medida. `velocidad` puede ser
    |twist.linear.x| (rectas) o |twist.angular.z| (giros) de la odometría, o
    el /cmd_vel remuestreado. Devuelve None si nunca supera el umbral.
    """
    if len(t) != len(velocidad):
        raise ValueError("t y velocidad deben tener la misma longitud")
    inicio = None
    for i, v in enumerate(velocidad):
        if abs(v) > umbral:
            inicio = i
            break
    if inicio is None:
        return None
    fin = inicio
    for i in range(inicio, len(velocidad)):
        if abs(velocidad[i]) > umbral:
            fin = i
        else:
            break
    return inicio, fin


def detectar_reinicios(
    t: Sequence[float],
    poses: Sequence[Pose],
    salto_max_m: float = 0.5,
    hueco_max_s: float = 1.0,
) -> List[Tuple[int, str]]:
    """Índices donde la odometría parece haberse reiniciado o perdido datos.

    Los RosCar pueden reiniciarse durante las pruebas y la pose vuelve a
    (0, 0, 0). Se marca como sospechoso:
      - un salto de posición entre muestras mayor que `salto_max_m`;
      - un hueco temporal mayor que `hueco_max_s`.
    """
    if len(t) != len(poses):
        raise ValueError("t y poses deben tener la misma longitud")
    avisos: List[Tuple[int, str]] = []
    for i in range(1, len(poses)):
        salto = math.hypot(poses[i][0] - poses[i - 1][0], poses[i][1] - poses[i - 1][1])
        if salto > salto_max_m:
            avisos.append((i, f"salto de posición de {salto:.3f} m"))
        hueco = t[i] - t[i - 1]
        if hueco > hueco_max_s:
            avisos.append((i, f"hueco temporal de {hueco:.2f} s"))
    return avisos
