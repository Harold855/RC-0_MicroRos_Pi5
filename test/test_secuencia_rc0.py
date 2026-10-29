"""Pruebas de la lógica de secuencia_rc0 (plan, topes de seguridad y criterio de parada). Sin ROS ni robot."""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "capytown_esan"))

import secuencia_rc0 as sq  # noqa: E402


def plan(**kw):
    return sq.validar_y_planear(**kw)


# ---------------------------------------------------------------- plan
def test_recta_por_defecto_replica_el_anexo_b():
    p = plan(modo="recta")
    assert (p["vx"], p["wz"], p["parada_por"]) == (0.10, 0.0, "tiempo")
    assert p["duracion_esperada_s"] == 10.0 and p["mensajes_aprox"] == 100


def test_giro_por_defecto_es_por_odometria_con_360():
    p = plan(modo="giro")
    assert p["parada_por"] == "odometria" and p["target_angle_deg"] == 360.0
    assert p["duracion_esperada_s"] == pytest.approx(2 * math.pi / 0.5)


def test_sentido_define_el_signo_de_omega_y_no_el_de_v():
    assert plan(modo="giro", sentido="antihorario")["wz"] == +0.5
    assert plan(modo="giro", sentido="horario")["wz"] == -0.5
    assert plan(modo="giro", sentido="horario")["vx"] == 0.0
    assert plan(modo="recta")["wz"] == 0.0


@pytest.mark.parametrize("kw", [
    dict(modo="recta", v=0.25),          # sobre el tope
    dict(modo="recta", v=-0.10),         # marcha atrás no permitida
    dict(modo="recta", v=0.0),
    dict(modo="giro", omega=1.5),
    dict(modo="giro", omega=-0.5),       # el sentido va en 'sentido'
    dict(modo="giro", target_angle_deg=0.0),
    dict(modo="recta", duracion=0.0),
    dict(modo="vuelta"),
    dict(modo="giro", sentido="izquierda"),
    dict(modo="recta", rate_hz=0.5),
    dict(modo="recta", parada_por="magia"),
])
def test_parametros_inseguros_se_rechazan(kw):
    with pytest.raises(ValueError):
        plan(**kw)


def test_duracion_total_tiene_tope_absoluto():
    with pytest.raises(ValueError, match="duraría"):
        plan(modo="recta", duracion=200.0)
    with pytest.raises(ValueError, match="duraría"):
        plan(modo="giro", omega=0.05, target_angle_deg=720.0)


def test_720_grados_a_0_5_rad_s_cabe_en_el_tope():
    p = plan(modo="giro", target_angle_deg=720.0)
    assert p["duracion_esperada_s"] == pytest.approx(4 * math.pi / 0.5)
    assert p["duracion_max_s"] <= sq.TIEMPO_MAX_ABS


# ---------------------------------------------------------------- acumulador
def test_acumulador_giro_horario_cruzando_pi():
    a = sq.Acumulador()
    for g in range(0, -361, -5):  # 0 → -360° en pasos de 5°, yaw envuelto
        y = math.atan2(math.sin(math.radians(g)), math.cos(math.radians(g)))
        a.actualizar(0, 0, y)
    assert math.degrees(a.theta) == pytest.approx(-360.0, abs=1e-6)


def test_acumulador_distancia_desde_la_primera_pose_y_reinicio():
    a = sq.Acumulador()
    for x in (5.0, 5.3, 5.6):
        a.actualizar(x, 2.0, 0.0)
    assert a.dist == pytest.approx(0.6)
    a.reiniciar_referencia()
    a.actualizar(5.6, 2.0, 0.0)
    assert a.dist == 0.0


# ---------------------------------------------------------------- criterio de parada
def acum(dist=0.0, grados=0.0):
    a = sq.Acumulador()
    a.dist, a.theta = dist, math.radians(grados)
    return a


def test_recta_por_tiempo_termina_a_la_duracion_y_no_mira_la_odometria():
    p = plan(modo="recta")
    assert sq.motivo_de_fin(p, 9.9, acum(), None, 1.0) is None
    assert sq.motivo_de_fin(p, 10.0, acum(), None, 1.0).startswith("completado")


def test_recta_por_odometria_para_a_la_distancia():
    p = plan(modo="recta", parada_por="odometria", distancia_m=1.0)
    assert sq.motivo_de_fin(p, 3.0, acum(dist=0.99), 0.02, 1.0) is None
    assert sq.motivo_de_fin(p, 10.0, acum(dist=1.00), 0.02, 1.0).startswith("completado")


@pytest.mark.parametrize("signo", [1, -1])
def test_giro_por_odometria_para_en_el_angulo_en_cualquier_sentido(signo):
    p = plan(modo="giro")
    assert sq.motivo_de_fin(p, 5.0, acum(grados=signo * 359.0), 0.02, 1.0) is None
    assert sq.motivo_de_fin(p, 12.0, acum(grados=signo * 360.5), 0.02, 1.0).startswith("completado")


def test_odometria_que_se_corta_aborta_la_prueba_por_odometria():
    p = plan(modo="giro")
    assert sq.motivo_de_fin(p, 3.0, acum(grados=100), 1.5, 1.0).startswith("ABORTADO")
    assert sq.motivo_de_fin(p, 3.0, acum(grados=100), None, 1.0).startswith("ABORTADO")


def test_giro_que_nunca_llega_al_angulo_se_corta_por_duracion_maxima():
    p = plan(modo="giro")  # p. ej. el script lee un topic cuyo yaw no crece
    assert sq.motivo_de_fin(p, p["duracion_max_s"] - 0.1, acum(grados=10), 0.02, 1.0) is None
    assert "duración máxima" in sq.motivo_de_fin(p, p["duracion_max_s"], acum(grados=10), 0.02, 1.0)


def test_giro_por_tiempo_termina_a_target_sobre_omega():
    p = plan(modo="giro", parada_por="tiempo")
    assert sq.motivo_de_fin(p, p["duracion_esperada_s"] - 0.1, acum(), None, 1.0) is None
    assert sq.motivo_de_fin(p, p["duracion_esperada_s"], acum(), None, 1.0).startswith("completado")
