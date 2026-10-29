#!/usr/bin/env python3
"""plot_odom — gráficas de odometría a partir de un bag de ROS 2 (RC-0, parte E).

INTRODUCCIÓN
------------
Recibe la carpeta de un bag (no un archivo) y genera dos PNG:

  <nombre>_xy.png       trayectoria x–y, relativa a la pose inicial y con ejes
                        iguales; ahí se ve el desvío lateral de una recta.
  <nombre>_theta_t.png  orientación θ(t) acumulada (desenrollada), en grados;
                        un giro de 360° llega a ±360°, no vuelve a 0.

Flujo:
  1. Leer `metadata.yaml` del bag y obtener `storage_identifier` (sqlite3 o
     mcap). El bag es una carpeta con ese metadata y uno o más archivos de datos.
  2. Elegir el topic de odometría. El Yahboom suele publicar /odom_raw y no
     /odom; si no se indica --topic se usa el único topic nav_msgs/msg/Odometry
     del bag, y si hay varios (o ninguno) el script falla listando lo que hay.
  3. Leer los mensajes con rosbag2_py y deserializarlos como Odometry.
  4. Calcular con odom_utils (funciones puras) y dibujar con matplotlib.

La lectura (paso 3) necesita ROS 2 con rosbag2_py: corre en el contenedor del
robot o en una máquina con ROS 2 Humble. El resto (cálculo y dibujo) no.

Uso:
  python3 capytown_esan/plot_odom.py bags/rc0_recta
  python3 capytown_esan/plot_odom.py bags/rc0_giro --topic /odom_raw --salida plots

Estado: la lectura con rosbag2_py NO se ha probado contra un bag real. Lo
verificado hasta ahora son las funciones puras y el dibujo con datos sintéticos.
"""

import argparse
import math
import os
import sys
from typing import List, Optional, Sequence, Tuple

try:  # ejecutado como script o como paquete
    import odom_utils as ou
except ImportError:  # pragma: no cover
    from capytown_esan import odom_utils as ou

TIPO_ODOM = "nav_msgs/msg/Odometry"


# --------------------------------------------------------------------------
# Lectura del bag (requiere ROS 2)
# --------------------------------------------------------------------------
def storage_id(bag: str) -> str:
    """Lee `storage_identifier` (sqlite3 o mcap) del metadata.yaml del bag."""
    meta = os.path.join(bag, "metadata.yaml")
    if not os.path.isfile(meta):
        raise FileNotFoundError(f"{bag} no es un bag de ROS 2: falta metadata.yaml")
    import yaml

    with open(meta) as f:
        return yaml.safe_load(f)["rosbag2_bagfile_information"]["storage_identifier"]


def _abrir(bag: str):
    from rosbag2_py import ConverterOptions, SequentialReader, StorageOptions

    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=bag, storage_id=storage_id(bag)),
        ConverterOptions("", ""),
    )
    return reader


def elegir_topic(topics_y_tipos: dict, pedido: Optional[str] = None) -> str:
    """Decide el topic de odometría. `topics_y_tipos` es {nombre: tipo}."""
    if pedido:
        if pedido not in topics_y_tipos:
            raise ValueError(
                f"el topic {pedido} no está en el bag. Topics del bag: "
                + (", ".join(f"{n} [{t}]" for n, t in sorted(topics_y_tipos.items())) or "(ninguno)")
            )
        return pedido
    odom = sorted(n for n, t in topics_y_tipos.items() if t == TIPO_ODOM)
    if len(odom) == 1:
        return odom[0]
    listado = ", ".join(f"{n} [{t}]" for n, t in sorted(topics_y_tipos.items())) or "(ninguno)"
    if not odom:
        raise ValueError(f"el bag no tiene ningún topic {TIPO_ODOM}. Topics del bag: {listado}")
    if "/odom" in odom:  # con odom_corrector activo coexisten /odom_raw y /odom: el reto usa /odom
        return "/odom"
    raise ValueError(f"hay varios topics de odometría ({', '.join(odom)}); indica cuál con --topic")


def leer_odometria(bag: str, topic: Optional[str] = None):
    """Devuelve (topic_usado, t, poses, vel) del bag.

    t: segundos relativos al primer mensaje; poses: [(x, y, yaw)];
    vel: [(twist.linear.x, twist.angular.z)].
    """
    from nav_msgs.msg import Odometry
    from rclpy.serialization import deserialize_message

    reader = _abrir(bag)
    tipos = {i.name: i.type for i in reader.get_all_topics_and_types()}
    usado = elegir_topic(tipos, topic)

    t, poses, vel = [], [], []
    while reader.has_next():
        nombre, data, stamp_ns = reader.read_next()
        if nombre != usado:
            continue
        m = deserialize_message(data, Odometry)
        q = m.pose.pose.orientation
        t.append(stamp_ns * 1e-9)
        poses.append((m.pose.pose.position.x, m.pose.pose.position.y, ou.quat_to_yaw(q.x, q.y, q.z, q.w)))
        vel.append((m.twist.twist.linear.x, m.twist.twist.angular.z))
    if len(t) < 2:
        raise ValueError(f"menos de 2 mensajes en {usado}: no hay trayectoria que graficar")
    t0 = t[0]
    return usado, [a - t0 for a in t], poses, vel


# --------------------------------------------------------------------------
# Resumen y dibujo (sin ROS)
# --------------------------------------------------------------------------
def resumen(t: Sequence[float], poses: Sequence[ou.Pose]) -> dict:
    norma, longitudinal, lateral = ou.desplazamiento(poses)
    theta = ou.yaw_relativo([p[2] for p in poses])
    return {
        "muestras": len(t),
        "duracion_s": t[-1] - t[0],
        "desplazamiento_m": norma,
        "longitudinal_m": longitudinal,
        "lateral_m": lateral,
        "theta_final_deg": math.degrees(theta[-1]),
        "reinicios": ou.detectar_reinicios(t, poses),
    }


def graficar(
    t: Sequence[float],
    poses: Sequence[ou.Pose],
    nombre: str,
    salida: str,
    topic: str = "",
) -> Tuple[str, str]:
    """Guarda <nombre>_xy.png y <nombre>_theta_t.png en `salida`. Devuelve las rutas."""
    import matplotlib

    matplotlib.use("Agg")  # sin pantalla: contenedor o SSH
    import matplotlib.pyplot as plt

    os.makedirs(salida, exist_ok=True)
    r = resumen(t, poses)
    sub = f"{topic} · {r['muestras']} muestras · {r['duracion_s']:.1f} s"

    # --- x–y, relativa al inicio y alineada con la orientación inicial
    pts = ou.trayectoria_relativa(poses)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(xs, ys, "-", color="tab:blue", label="trayectoria")
    ax.plot(xs[0], ys[0], "go", label="inicio")
    ax.plot(xs[-1], ys[-1], "rs", label="fin")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("adelante respecto a la orientación inicial [m]")
    ax.set_ylabel("lateral (izquierda +) [m]")
    ax.set_title(
        f"{nombre} — trayectoria x–y\n"
        f"desplazamiento {r['desplazamiento_m']:.3f} m · lateral {r['lateral_m']*100:+.1f} cm\n{sub}",
        fontsize=10,
    )
    ax.legend(loc="best")
    ruta_xy = os.path.join(salida, f"{nombre}_xy.png")
    fig.tight_layout()
    fig.savefig(ruta_xy, dpi=150)
    plt.close(fig)

    # --- θ(t) acumulada
    theta = [math.degrees(a) for a in ou.yaw_relativo([p[2] for p in poses])]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(t, theta, color="tab:orange")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("tiempo desde el primer mensaje [s]")
    ax.set_ylabel("θ acumulada [°]  (antihorario +)")
    ax.set_title(f"{nombre} — orientación θ(t)\nθ final {r['theta_final_deg']:+.1f}°\n{sub}", fontsize=10)
    ax.grid(True, alpha=0.3)
    ruta_th = os.path.join(salida, f"{nombre}_theta_t.png")
    fig.tight_layout()
    fig.savefig(ruta_th, dpi=150)
    plt.close(fig)
    return ruta_xy, ruta_th


# --------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Gráficas x–y y θ(t) de un bag de odometría.")
    ap.add_argument("bag", help="carpeta del bag (contiene metadata.yaml)")
    ap.add_argument("--topic", default=None, help="topic de odometría (por defecto: el único Odometry del bag)")
    ap.add_argument("--salida", default="plots", help="carpeta de salida de los PNG (por defecto: plots)")
    ap.add_argument("--nombre", default=None, help="prefijo de los PNG (por defecto: nombre de la carpeta del bag)")
    args = ap.parse_args(argv)

    bag = args.bag.rstrip("/\\")
    nombre = args.nombre or os.path.basename(bag)
    try:
        topic, t, poses, _ = leer_odometria(bag, args.topic)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    r = resumen(t, poses)
    print(f"bag: {bag} · topic: {topic} · almacenamiento: {storage_id(bag)}")
    print(
        f"muestras: {r['muestras']} · duración: {r['duracion_s']:.2f} s · "
        f"desplazamiento: {r['desplazamiento_m']:.4f} m "
        f"(longitudinal {r['longitudinal_m']:.4f} m, lateral {r['lateral_m']:+.4f} m) · "
        f"θ final: {r['theta_final_deg']:+.2f}°"
    )
    for i, msg in r["reinicios"]:
        print(f"AVISO: posible reinicio o pérdida de datos en la muestra {i}: {msg}", file=sys.stderr)

    for ruta in graficar(t, poses, nombre, args.salida, topic):
        print("guardado:", ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
