#!/usr/bin/env python3
"""secuencia_rc0 — secuencia de recta o giro para RC-0 (rol Planificación).

INTRODUCCIÓN
------------
Publica Twist en /cmd_vel para las pruebas del reto, con seguridad por defecto:

  * dry_run:=true (por defecto): solo imprime el plan y comprueba que haya
    odometría. NO crea el publicador de /cmd_vel: es imposible que mueva el robot.
  * Para mover hace falta confirmar_movimiento:=true Y escribir MOVER en la
    terminal (salvo sin_prompt:=true), con cuenta atrás. Lo activa la persona
    que está junto al robot, con el área despejada.
  * Velocidades con tope duro (|v| ≤ 0.20 m/s, |ω| ≤ 1.0 rad/s) y duración
    máxima: ningún parámetro puede dejar el robot girando o avanzando sin fin.
  * Al terminar, por cualquier causa (fin normal, odometría que se corta,
    Ctrl+C, excepción) se envían varios Twist en cero.
  * Una parada por software NO es un corte de energía: depende del enlace.
    Operador al lado y el robot a la vista. [VERIFICAR] si el firmware tiene
    watchdog de /cmd_vel y qué hace el botón de reinicio.

Modos y criterio de parada (parada_por):
  recta, tiempo      v durante `duracion` s a `rate_hz` (por defecto 0.10 m/s,
                     10 s, 10 Hz = Anexo B del reto). Igual que ros2 topic pub,
                     pero con temporizador y parada garantizada.
  recta, odometria   avanza hasta que la odometría marque `distancia_m`.
                     (Ayuda para el bonus de 1 m; el error real contra la cinta
                     dependerá de la calibración y de cuánto patine al frenar.)
  giro,  odometria   gira hasta que |θ acumulada| de la odometría alcance
                     `target_angle_deg` (por defecto 360°).
  giro,  tiempo      gira durante target/ω segundos, sin mirar la odometría.

Sentido del giro: `sentido:=antihorario` (+Z, ω > 0) o `sentido:=horario`
(ω < 0); `omega` siempre es positivo. En S-003: calibración A1 antihorario,
validación A2 horario. Ojo: el sentido no cambia el signo de v; el robot avanza
hacia donde mira, así que antes de la recta hay que comprobar su orientación.

Si la odometría deja de llegar durante una prueba por odometría (>
`odom_timeout_s`), se aborta y se frena. Durante una recta por tiempo solo se avisa.
Con odometría real, tras parar se imprime lo que midió el propio nodo; los
números para los CSV salen del bag con analizar_bag.py.

Uso (el bag se graba aparte, ANTES de mover):
  # dry-run
  python3 capytown_esan/secuencia_rc0.py --ros-args -p modo:=recta
  # movimiento real, supervisado
  python3 capytown_esan/secuencia_rc0.py --ros-args -p modo:=giro -p sentido:=horario \\
      -p dry_run:=false -p confirmar_movimiento:=true

Los parámetros numéricos se pasan con decimales (-p omega:=1.0, no 1).

Estado: la lógica (validación, plan, criterio de parada) está probada con
pytest; el nodo ROS 2 NO se ha ejecutado contra ROS ni contra el robot.
"""

import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

try:
    import odom_utils as ou
except ImportError:  # pragma: no cover
    from capytown_esan import odom_utils as ou

V_MAX = 0.20  # m/s, tope duro
W_MAX = 1.0  # rad/s, tope duro
TIEMPO_MAX_ABS = 90.0  # s, ninguna prueba dura más
TIPO_ODOM = "nav_msgs/msg/Odometry"
PARADA_N = 5  # Twist en cero al terminar


# --------------------------------------------------------------------------
# Lógica pura (probada con pytest)
# --------------------------------------------------------------------------
def validar_y_planear(
    modo: str,
    sentido: str = "antihorario",
    v: float = 0.10,
    omega: float = 0.5,
    duracion: float = 10.0,
    distancia_m: float = 1.0,
    target_angle_deg: float = 360.0,
    parada_por: str = "",
    rate_hz: float = 10.0,
) -> Dict:
    """Valida los parámetros y devuelve el plan. Lanza ValueError si algo no es seguro."""
    if modo not in ("recta", "giro"):
        raise ValueError("modo debe ser 'recta' o 'giro'")
    if sentido not in ("antihorario", "horario"):
        raise ValueError("sentido debe ser 'antihorario' o 'horario'")
    parada = parada_por or ("tiempo" if modo == "recta" else "odometria")
    if parada not in ("tiempo", "odometria"):
        raise ValueError("parada_por debe ser 'tiempo' u 'odometria'")
    if not 1.0 <= rate_hz <= 50.0:
        raise ValueError("rate_hz debe estar entre 1 y 50")

    if modo == "recta":
        if not 0.0 < v <= V_MAX:
            raise ValueError(f"v debe estar en (0, {V_MAX}] m/s (solo hacia adelante)")
        if parada == "tiempo":
            if duracion <= 0:
                raise ValueError("duracion debe ser > 0")
            esperado = duracion
        else:
            if distancia_m <= 0:
                raise ValueError("distancia_m debe ser > 0")
            esperado = distancia_m / v
        wz = 0.0
        vx = v
    else:
        if not 0.0 < omega <= W_MAX:
            raise ValueError(f"omega debe estar en (0, {W_MAX}] rad/s; use 'sentido' para el signo")
        if target_angle_deg <= 0:
            raise ValueError("target_angle_deg debe ser > 0")
        vx = 0.0
        wz = omega if sentido == "antihorario" else -omega
        esperado = math.radians(target_angle_deg) / omega

    # por tiempo: dura exactamente lo esperado; por odometría: margen para no cortar una prueba sana
    maximo = esperado if parada == "tiempo" and modo == "recta" else 1.5 * esperado + 3.0
    if maximo > TIEMPO_MAX_ABS:
        raise ValueError(f"la prueba duraría hasta {maximo:.0f} s (> {TIEMPO_MAX_ABS:.0f} s): revise los parámetros")
    return {
        "modo": modo, "sentido": sentido, "parada_por": parada, "vx": vx, "wz": wz,
        "rate_hz": rate_hz, "duracion_esperada_s": esperado, "duracion_max_s": maximo,
        "distancia_m": distancia_m, "target_angle_deg": target_angle_deg,
        "mensajes_aprox": int(round(esperado * rate_hz)),
    }


class Acumulador:
    """Distancia y ángulo recorridos según la odometría, desde la primera pose recibida."""

    def __init__(self) -> None:
        self.inicio: Optional[Tuple[float, float]] = None
        self.dist = 0.0
        self.theta = 0.0  # rad, con signo (+ antihorario), acumulado sin saltos
        self._ultimo_yaw: Optional[float] = None

    def actualizar(self, x: float, y: float, yaw: float) -> None:
        if self.inicio is None:
            self.inicio = (x, y)
            self._ultimo_yaw = yaw
            return
        self.dist = math.hypot(x - self.inicio[0], y - self.inicio[1])
        d = yaw - self._ultimo_yaw
        d = math.atan2(math.sin(d), math.cos(d))  # diferencia mínima en (-π, π]
        self.theta += d
        self._ultimo_yaw = yaw

    def reiniciar_referencia(self) -> None:
        """Pone a cero el recorrido: llamar justo antes de empezar a mover."""
        self.inicio = None
        self.dist = 0.0
        self.theta = 0.0
        self._ultimo_yaw = None


def motivo_de_fin(plan: Dict, transcurrido: float, acum: Acumulador, edad_odom: Optional[float], odom_timeout_s: float) -> Optional[str]:
    """None si se sigue; si no, el motivo de parada."""
    if plan["modo"] == "recta" and plan["parada_por"] == "tiempo":
        if transcurrido >= plan["duracion_esperada_s"]:
            return "completado: duración alcanzada"
        return None
    if plan["parada_por"] == "odometria":
        if edad_odom is None or edad_odom > odom_timeout_s:
            return "ABORTADO: la odometría dejó de llegar"
        if plan["modo"] == "recta" and acum.dist >= plan["distancia_m"]:
            return "completado: distancia de odometría alcanzada"
        if plan["modo"] == "giro" and abs(math.degrees(acum.theta)) >= plan["target_angle_deg"]:
            return "completado: ángulo de odometría alcanzado"
    elif plan["modo"] == "giro" and transcurrido >= plan["duracion_esperada_s"]:  # giro por tiempo
        return "completado: duración alcanzada"
    if transcurrido >= plan["duracion_max_s"]:
        return "ABORTADO: duración máxima superada"
    return None


# --------------------------------------------------------------------------
# Nodo ROS 2 (necesita rclpy; no probado aquí)
# --------------------------------------------------------------------------
def _ahora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def ejecutar() -> int:
    import rclpy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from rclpy.node import Node

    class Secuencia(Node):
        def __init__(self) -> None:
            super().__init__("secuencia_rc0")
            p = self.declare_parameter
            self.modo = p("modo", "recta").value
            self.sentido = p("sentido", "antihorario").value
            self.v = p("v", 0.10).value
            self.omega = p("omega", 0.5).value
            self.duracion = p("duracion", 10.0).value
            self.distancia_m = p("distancia_m", 1.0).value
            self.target = p("target_angle_deg", 360.0).value
            self.parada_por = p("parada_por", "").value
            self.rate_hz = p("rate_hz", 10.0).value
            self.dry_run = p("dry_run", True).value
            self.confirmar = p("confirmar_movimiento", False).value
            self.sin_prompt = p("sin_prompt", False).value
            self.odom_topic = p("odom_topic", "").value
            self.odom_timeout_s = p("odom_timeout_s", 1.0).value
            self.cuenta_atras = p("cuenta_atras_s", 3).value
            self.bitacora = p("bitacora", "").value

            self.plan = validar_y_planear(
                self.modo, self.sentido, self.v, self.omega, self.duracion,
                self.distancia_m, self.target, self.parada_por, self.rate_hz,
            )
            self.acum = Acumulador()
            self.ultimo_odom: Optional[float] = None
            self.pub = None
            self.sub = None

        # ---- odometría
        def resolver_topic(self, espera_s: float = 3.0) -> str:
            if self.odom_topic:
                return self.odom_topic
            fin = time.monotonic() + espera_s
            while True:
                rclpy.spin_once(self, timeout_sec=0.2)
                odom = sorted(n for n, ts in self.get_topic_names_and_types() if TIPO_ODOM in ts)
                if odom or time.monotonic() > fin:
                    break
            if len(odom) > 1 and "/odom" in odom:  # odom_corrector: coexisten /odom_raw y /odom
                return "/odom"
            if len(odom) != 1:
                raise RuntimeError(
                    "no se pudo elegir la odometría: topics nav_msgs/Odometry vistos = " + (", ".join(odom) or "ninguno")
                    + ". Indique odom_topic:=/odom_raw (o el que corresponda)."
                )
            return odom[0]

        def _cb_odom(self, m: Odometry) -> None:
            q = m.pose.pose.orientation
            self.acum.actualizar(m.pose.pose.position.x, m.pose.pose.position.y, ou.quat_to_yaw(q.x, q.y, q.z, q.w))
            self.ultimo_odom = time.monotonic()

        def suscribir(self, topic: str) -> None:
            self.sub = self.create_subscription(Odometry, topic, self._cb_odom, 10)

        def esperar_odom(self, espera_s: float = 5.0) -> bool:
            fin = time.monotonic() + espera_s
            while time.monotonic() < fin and self.ultimo_odom is None:
                rclpy.spin_once(self, timeout_sec=0.1)
            return self.ultimo_odom is not None

        # ---- movimiento
        def _twist(self, vx: float, wz: float) -> Twist:
            msg = Twist()
            msg.linear.x = float(vx)
            msg.angular.z = float(wz)
            return msg

        def parar(self) -> None:
            if self.pub is None:
                return
            try:
                for _ in range(PARADA_N):
                    self.pub.publish(self._twist(0.0, 0.0))
                    time.sleep(0.05)
            except Exception:  # el contexto puede estar ya cerrado
                pass

        def correr(self) -> Tuple[str, str, str]:
            self.pub = self.create_publisher(Twist, "/cmd_vel", 10)
            self.acum.reiniciar_referencia()  # el recorrido se cuenta desde AQUÍ
            periodo = 1.0 / self.rate_hz
            inicio_iso = _ahora()
            t0 = time.monotonic()
            siguiente = t0
            motivo = None
            try:
                while motivo is None:
                    rclpy.spin_once(self, timeout_sec=0.0)
                    ahora = time.monotonic()
                    if ahora >= siguiente:
                        self.pub.publish(self._twist(self.plan["vx"], self.plan["wz"]))
                        siguiente += periodo
                    edad = None if self.ultimo_odom is None else ahora - self.ultimo_odom
                    motivo = motivo_de_fin(self.plan, ahora - t0, self.acum, edad, self.odom_timeout_s)
                    time.sleep(0.002)
            except KeyboardInterrupt:
                motivo = "INTERRUMPIDO por el operador (Ctrl+C)"
            except Exception as e:  # noqa: BLE001
                motivo = f"ABORTADO por excepción: {e!r}"
            finally:
                self.parar()
            return inicio_iso, _ahora(), motivo

        def anotar(self, fila: Dict) -> None:
            if not self.bitacora:
                return
            nuevo = not os.path.exists(self.bitacora) or os.path.getsize(self.bitacora) == 0
            claves = list(fila)
            with open(self.bitacora, "a", newline="") as f:
                if nuevo:
                    f.write(",".join(claves) + "\n")
                f.write(",".join(str(fila[k]).replace(",", ";") for k in claves) + "\n")

    rclpy.init()
    nodo = None
    try:
        nodo = Secuencia()
        pl = nodo.plan
        print("=== PLAN ===")
        print(f"modo={pl['modo']} sentido={pl['sentido']} parada_por={pl['parada_por']}")
        print(f"Twist: linear.x={pl['vx']:+.3f} m/s · angular.z={pl['wz']:+.3f} rad/s a {pl['rate_hz']:.0f} Hz")
        print(f"duración esperada ≈ {pl['duracion_esperada_s']:.1f} s · máxima {pl['duracion_max_s']:.1f} s · ~{pl['mensajes_aprox']} mensajes")
        if pl["modo"] == "recta":
            print("Recuerde: el robot avanza hacia donde mira. Compruebe su orientación y la línea de inicio.")

        topic = nodo.resolver_topic()
        nodo.suscribir(topic)
        hay = nodo.esperar_odom()
        print(f"odometría: {topic} → {'recibiendo' if hay else 'SIN MENSAJES'}")

        if nodo.dry_run:
            print("DRY-RUN: no se publicó nada en /cmd_vel. Para mover: -p dry_run:=false -p confirmar_movimiento:=true")
            return 0 if hay else 1
        if not nodo.confirmar:
            print("No se mueve: falta -p confirmar_movimiento:=true", file=sys.stderr)
            return 3
        if not hay:
            print("No se mueve: no llega odometría (revise Agent, dominio y topic).", file=sys.stderr)
            return 4
        print("\n*** MOVIMIENTO REAL: área despejada, operador junto al robot, bag grabando. ***")
        if not nodo.sin_prompt and input("Escriba MOVER y pulse ENTER (otra cosa cancela): ").strip() != "MOVER":
            print("Cancelado.")
            return 5
        for s in range(int(nodo.cuenta_atras), 0, -1):
            print(f"  {s}...")
            time.sleep(1.0)
        inicio, fin, motivo = nodo.correr()
        print(f"inicio {inicio} · fin {fin}\n{motivo}")
        print(f"odometría del nodo (referencia, no evidencia): d = {nodo.acum.dist:.4f} m · θ = {math.degrees(nodo.acum.theta):+.2f}°")
        nodo.anotar({
            "inicio": inicio, "fin": fin, "modo": pl["modo"], "sentido": pl["sentido"],
            "parada_por": pl["parada_por"], "vx": pl["vx"], "wz": pl["wz"], "motivo": motivo,
            "d_nodo_m": f"{nodo.acum.dist:.4f}", "theta_nodo_deg": f"{math.degrees(nodo.acum.theta):.2f}",
        })
        return 0 if motivo.startswith("completado") else 6
    except (ValueError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except EOFError:
        print("Cancelado: no hay terminal interactiva para confirmar (use una terminal real).", file=sys.stderr)
        return 5
    finally:
        if nodo is not None:
            nodo.parar()
            nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(ejecutar())
