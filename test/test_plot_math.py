"""Pruebas de la matemática de odometría y del dibujo, con DATOS SINTÉTICOS.

No usan el robot ni ROS: verifican la lógica, no una calibración.
Ejecutar desde la raíz del repositorio:  python3 -m pytest test
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "capytown_esan"))

import odom_utils as ou  # noqa: E402
import plot_odom  # noqa: E402


def giro_sintetico(grados, n=361, paso_horario=False):
    """Poses (x=y=0) de un giro en sitio, con el yaw envuelto a (-π, π] como lo haría un cuaternión."""
    signo = -1.0 if paso_horario else 1.0
    yaws = []
    for i in range(n):
        a = signo * math.radians(grados) * i / (n - 1)
        yaws.append(math.atan2(math.sin(a), math.cos(a)))
    return yaws


# ---------------------------------------------------------------- yaw
def test_quat_to_yaw_cuaterniones_conocidos():
    assert ou.quat_to_yaw(0, 0, 0, 1) == pytest.approx(0.0)
    assert ou.quat_to_yaw(0, 0, math.sin(math.pi / 4), math.cos(math.pi / 4)) == pytest.approx(math.pi / 2)
    assert ou.quat_to_yaw(0, 0, -math.sin(math.pi / 4), math.cos(math.pi / 4)) == pytest.approx(-math.pi / 2)


def test_giro_antihorario_360_acumula_mas_2pi():
    rel = ou.yaw_relativo(giro_sintetico(360))
    assert rel[-1] == pytest.approx(2 * math.pi, abs=1e-6)
    assert max(rel) == pytest.approx(2 * math.pi, abs=1e-6)


def test_giro_horario_360_acumula_menos_2pi():
    rel = ou.yaw_relativo(giro_sintetico(360, paso_horario=True))
    assert rel[-1] == pytest.approx(-2 * math.pi, abs=1e-6)


def test_giro_720_acumula_4pi():
    assert ou.yaw_relativo(giro_sintetico(720, n=721))[-1] == pytest.approx(4 * math.pi, abs=1e-6)


def test_yaw_final_igual_al_inicial_no_implica_ausencia_de_giro():
    envuelto = giro_sintetico(360)
    assert envuelto[-1] == pytest.approx(envuelto[0], abs=1e-9)  # sin unwrap parece que no giró
    assert abs(ou.yaw_relativo(envuelto)[-1]) > 6.0  # con unwrap sí


def test_cruce_de_pi_no_produce_salto():
    envuelto = [math.radians(a) for a in (170, 175, 180, -175, -170)]
    rel = ou.yaw_relativo(envuelto)
    assert [round(math.degrees(a)) for a in rel] == [0, 5, 10, 15, 20]


def test_yaw_relativo_parte_de_cero_aunque_no_empiece_en_cero():
    rel = ou.yaw_relativo([math.radians(a) for a in (90, 100, 110)])
    assert rel[0] == 0.0
    assert math.degrees(rel[-1]) == pytest.approx(20.0)


def test_series_vacias():
    assert ou.unwrap_yaw([]) == []
    assert ou.yaw_relativo([]) == []


# ---------------------------------------------------------------- traslación
def test_recta_ideal_hacia_adelante():
    poses = [(0.1 * i, 0.0, 0.0) for i in range(11)]
    norma, lon, lat = ou.desplazamiento(poses)
    assert (norma, lon, lat) == (pytest.approx(1.0), pytest.approx(1.0), pytest.approx(0.0, abs=1e-12))


def test_recta_con_orientacion_inicial_no_nula_se_mide_en_marco_del_robot():
    th = math.radians(90)  # el robot mira hacia +Y del marco odom
    poses = [(0.0, 0.0, th), (0.0, 1.0, th)]
    norma, lon, lat = ou.desplazamiento(poses)
    assert lon == pytest.approx(1.0) and lat == pytest.approx(0.0, abs=1e-12) and norma == pytest.approx(1.0)


def test_desvio_lateral_signo_y_magnitud():
    izq = ou.desplazamiento([(0, 0, 0), (1.0, 0.03, 0)])
    der = ou.desplazamiento([(0, 0, 0), (1.0, -0.03, 0)])
    assert izq[2] == pytest.approx(0.03) and der[2] == pytest.approx(-0.03)
    assert izq[0] == pytest.approx(math.hypot(1.0, 0.03))


def test_la_pose_inicial_absoluta_no_afecta():
    a = ou.desplazamiento([(0, 0, 0), (1, 0, 0)])
    b = ou.desplazamiento([(5, -3, 0), (6, -3, 0)])
    assert a == pytest.approx(b)


def test_trayectoria_relativa_empieza_en_origen_y_recta_va_por_x():
    th = math.radians(30)
    poses = [(2 + 0.1 * i * math.cos(th), 1 + 0.1 * i * math.sin(th), th) for i in range(6)]
    pts = ou.trayectoria_relativa(poses)
    assert pts[0] == pytest.approx((0.0, 0.0))
    assert pts[-1] == pytest.approx((0.5, 0.0), abs=1e-9)


def test_desplazamiento_exige_dos_poses():
    with pytest.raises(ValueError):
        ou.desplazamiento([(0, 0, 0)])


# ---------------------------------------------------------------- errores
def test_error_lineal_definicion_del_reto():
    assert ou.error_pct_lineal(1.00, 0.95) == pytest.approx(5.0)
    assert ou.error_pct_lineal(1.00, 1.05) == pytest.approx(5.0)
    assert ou.error_pct_lineal(1.00, 1.00) == 0.0
    with pytest.raises(ValueError):
        ou.error_pct_lineal(0.0, 0.5)


def test_error_angular_reproduce_los_ejemplos_de_la_presentacion():
    # Ejemplos de la presentación de calibración (RC-1): son del docente, no del grupo.
    assert ou.error_pct_angular(360.0, 348.5) == pytest.approx(3.19, abs=0.005)
    assert ou.error_pct_angular(360.0, 356.2) == pytest.approx(1.06, abs=0.005)
    assert ou.error_pct_angular(360.0, 358.9) == pytest.approx(0.31, abs=0.005)


def test_error_angular_denominador_medido_difiere_y_sentido_no_importa():
    assert ou.error_pct_angular(360.0, 348.5, "medido") == pytest.approx(100 * 11.5 / 348.5)
    assert ou.error_pct_angular(-360.0, -348.5) == pytest.approx(ou.error_pct_angular(360.0, 348.5))
    with pytest.raises(ValueError):
        ou.error_pct_angular(360.0, 350.0, "otro")


# ---------------------------------------------------------------- ventanas y reinicios
def test_ventana_movimiento_ignora_reposo_antes_y_despues():
    t = list(range(10))
    v = [0, 0, 0.1, 0.1, 0.1, 0, 0, 0.1, 0, 0]
    assert ou.ventana_movimiento(t, v, umbral=0.01) == (2, 4)  # solo el primer tramo


def test_ventana_movimiento_sin_movimiento_devuelve_none():
    assert ou.ventana_movimiento([0, 1, 2], [0, 0, 0]) is None


def test_ventana_movimiento_giro_horario_usa_magnitud():
    assert ou.ventana_movimiento([0, 1, 2, 3], [0, -0.5, -0.5, 0]) == (1, 2)


def test_detectar_reinicio_por_salto_a_cero():
    t = [i * 0.02 for i in range(6)]
    # el robot avanza hasta 1.2 m y la pose vuelve a 0 en la muestra 3
    poses = [(1.0, 0, 0), (1.1, 0, 0), (1.2, 0, 0), (0, 0, 0), (0.01, 0, 0), (0.02, 0, 0)]
    avisos = ou.detectar_reinicios(t, poses, salto_max_m=0.5)
    assert [i for i, _ in avisos] == [3]


def test_detectar_hueco_temporal_y_odometria_limpia():
    poses = [(0.001 * i, 0, 0) for i in range(4)]
    assert ou.detectar_reinicios([0, 0.02, 0.04, 0.06], poses) == []
    assert [i for i, _ in ou.detectar_reinicios([0, 0.02, 3.0, 3.02], poses)] == [2]


# ---------------------------------------------------------------- elección de topic
def test_elegir_topic_unico_odometry():
    tipos = {"/odom_raw": plot_odom.TIPO_ODOM, "/cmd_vel": "geometry_msgs/msg/Twist"}
    assert plot_odom.elegir_topic(tipos) == "/odom_raw"


def test_elegir_topic_falla_listando_los_topics_del_bag():
    with pytest.raises(ValueError, match=r"/cmd_vel"):
        plot_odom.elegir_topic({"/cmd_vel": "geometry_msgs/msg/Twist"})
    with pytest.raises(ValueError, match=r"/odom.*no está"):
        plot_odom.elegir_topic({"/odom_raw": plot_odom.TIPO_ODOM}, pedido="/odom")


def test_elegir_topic_con_odom_y_odom_raw_prefiere_odom():
    tipos = {"/odom": plot_odom.TIPO_ODOM, "/odom_raw": plot_odom.TIPO_ODOM}  # odom_corrector activo
    assert plot_odom.elegir_topic(tipos) == "/odom"
    assert plot_odom.elegir_topic(tipos, pedido="/odom_raw") == "/odom_raw"


def test_elegir_topic_ambiguo_sin_odom_exige_indicarlo():
    tipos = {"/a": plot_odom.TIPO_ODOM, "/b": plot_odom.TIPO_ODOM}
    with pytest.raises(ValueError, match="--topic"):
        plot_odom.elegir_topic(tipos)


# ---------------------------------------------------------------- dibujo
def test_graficar_genera_dos_png_con_datos_sinteticos(tmp_path):
    pytest.importorskip("matplotlib")
    yaws = giro_sintetico(360)
    t = [i * 0.02 for i in range(len(yaws))]
    poses = [(0.0, 0.0, y) for y in yaws]
    xy, th = plot_odom.graficar(t, poses, "SINTETICO_giro", str(tmp_path), topic="/odom_raw")
    for ruta in (xy, th):
        assert os.path.getsize(ruta) > 1000
    assert xy.endswith("SINTETICO_giro_xy.png") and th.endswith("SINTETICO_giro_theta_t.png")


def test_resumen_de_recta_sintetica():
    poses = [(0.1 * i, 0.002 * i, 0.0) for i in range(11)]
    t = [0.1 * i for i in range(11)]
    r = plot_odom.resumen(t, poses)
    assert r["longitudinal_m"] == pytest.approx(1.0)
    assert r["lateral_m"] == pytest.approx(0.02)
    assert r["reinicios"] == []
