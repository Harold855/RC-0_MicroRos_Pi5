"""Pruebas de analizar_bag y de segmentos_movimiento con DATOS SINTÉTICOS (sin ROS ni robot)."""

import argparse
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "capytown_esan"))

import analizar_bag as ab  # noqa: E402
import odom_utils as ou  # noqa: E402

HZ = 50.0


def recta_sintetica(distancia, v=0.10, reposo_antes=1.0, reposo_despues=1.0, x0=0.0, y0=0.0, th0=0.0, deriva=0.0):
    """Odometría de una recta: reposo, movimiento a velocidad constante, reposo."""
    t, poses, vel = [], [], []
    n_antes, n_mov, n_desp = int(reposo_antes * HZ), int(distancia / v * HZ), int(reposo_despues * HZ)
    x = y = 0.0
    k = 0
    for i in range(n_antes + n_mov + n_desp):
        moviendo = n_antes <= i < n_antes + n_mov
        if moviendo:
            x += v / HZ
            y += deriva * v / HZ
        t.append(k / HZ)
        k += 1
        poses.append((x0 + x * math.cos(th0) - y * math.sin(th0), y0 + x * math.sin(th0) + y * math.cos(th0), th0))
        vel.append((v if moviendo else 0.0, 0.0))
    return t, poses, vel


def giro_sintetico(grados, w=0.5, signo=1.0, reposo=1.0):
    t, poses, vel = [], [], []
    n_r, n_m = int(reposo * HZ), int(math.radians(grados) / w * HZ)
    yaw = 0.0
    for i in range(n_r + n_m + n_r):
        mov = n_r <= i < n_r + n_m
        if mov:
            yaw += signo * w / HZ
        t.append(i / HZ)
        poses.append((0.0, 0.0, math.atan2(math.sin(yaw), math.cos(yaw))))
        vel.append((0.0, signo * w if mov else 0.0))
    return t, poses, vel


# ---------------------------------------------------------------- segmentos
def test_segmentos_dos_corridas_separadas():
    t = [i * 0.1 for i in range(40)]
    v = [0.0] * 5 + [0.1] * 10 + [0.0] * 10 + [0.1] * 10 + [0.0] * 5
    assert ou.segmentos_movimiento(t, v) == [(5, 14), (25, 34)]


def test_segmentos_fusiona_bache_corto_pero_no_reposo_largo():
    t = [i * 0.1 for i in range(20)]
    v = [0.1] * 5 + [0.0] * 2 + [0.1] * 5 + [0.0] * 8
    assert ou.segmentos_movimiento(t, v, hueco_s=0.5) == [(0, 11)]
    assert ou.segmentos_movimiento(t, v, hueco_s=0.1) == [(0, 4), (7, 11)]


def test_segmentos_sin_movimiento():
    assert ou.segmentos_movimiento([0, 1], [0.0, 0.0]) == []


# ---------------------------------------------------------------- análisis
def test_recta_mide_solo_el_tramo_aunque_el_robot_no_empiece_en_cero():
    t, poses, vel = recta_sintetica(0.95, x0=3.0, y0=-2.0, th0=math.radians(180))
    r = ab.analizar(t, poses, vel, "recta")
    assert r["d_odom_m"] == pytest.approx(0.95, abs=0.01)
    assert r["longitudinal_m"] == pytest.approx(0.95, abs=0.01)
    assert abs(r["lateral_m"]) < 1e-6


def test_recta_con_deriva_lateral():
    t, poses, vel = recta_sintetica(1.0, deriva=0.05)
    r = ab.analizar(t, poses, vel, "recta")
    assert r["lateral_m"] == pytest.approx(0.05, abs=0.005)
    assert r["d_odom_m"] > r["longitudinal_m"]


def test_dos_rectas_en_un_bag_se_separan_por_segmento():
    t1, p1, v1 = recta_sintetica(1.00, reposo_despues=2.0)
    t2, p2, v2 = recta_sintetica(0.90, reposo_antes=0.0, x0=p1[-1][0])
    off = t1[-1] + 1 / HZ
    t = t1 + [off + x for x in t2]
    poses, vel = p1 + p2, v1 + v2
    assert len(ab.listar_tramos(t, vel, "recta")) == 2
    assert ab.analizar(t, poses, vel, "recta", segmento=1)["d_odom_m"] == pytest.approx(1.00, abs=0.01)
    assert ab.analizar(t, poses, vel, "recta", segmento=2)["d_odom_m"] == pytest.approx(0.90, abs=0.01)
    with pytest.raises(ValueError, match="fuera de rango"):
        ab.analizar(t, poses, vel, "recta", segmento=3)


@pytest.mark.parametrize("signo", [1.0, -1.0])
def test_giro_360_con_signo(signo):
    t, poses, vel = giro_sintetico(360, signo=signo)
    r = ab.analizar(t, poses, vel, "giro")
    assert r["theta_odom_deg"] == pytest.approx(360.0 * signo, abs=2.0)


def test_giro_720_no_se_confunde_con_cero():
    t, poses, vel = giro_sintetico(720)
    assert ab.analizar(t, poses, vel, "giro")["theta_odom_deg"] == pytest.approx(720.0, abs=2.0)


def test_sin_movimiento_falla_con_mensaje_claro():
    t, poses, vel = [0.0, 0.1, 0.2], [(0, 0, 0)] * 3, [(0.0, 0.0)] * 3
    with pytest.raises(ValueError, match="no hay movimiento"):
        ab.analizar(t, poses, vel, "recta")


def test_reinicio_dentro_del_tramo_se_avisa():
    t, poses, vel = recta_sintetica(1.0)
    k = len(poses) // 2
    poses = poses[:k] + [(x - poses[k][0], y, th) for x, y, th in poses[k:]]  # la pose vuelve a ~0 a mitad de la corrida
    assert ab.analizar(t, poses, vel, "recta")["reinicios"]


# ---------------------------------------------------------------- CSV
def args(**kw):
    base = dict(corrida=None, r=None, d_real=None, desvio_m=None, desvio_de_odom=False, variante=None,
                valor_real=None, iteracion=None, b_eff_usado=None, theta_medido=None, b_eff_propuesto=None,
                denominador="reportado")
    base.update(kw)
    return argparse.Namespace(**base)


def test_fila_linea_recta_calcula_el_error_del_reto():
    t, poses, vel = recta_sintetica(0.95)
    r = ab.analizar(t, poses, vel, "recta")
    fila = ab.construir_fila("linea_recta", r, args(corrida=1, r=0.03, d_real=1.00, desvio_m=0.012))
    assert fila[0] == "1" and float(fila[3]) == pytest.approx(0.95, abs=0.01)
    assert float(fila[4]) == pytest.approx(5.0, abs=1.0)
    assert fila[5] == "0.0120"


def test_fila_exige_los_datos_medidos():
    t, poses, vel = recta_sintetica(0.95)
    r = ab.analizar(t, poses, vel, "recta")
    with pytest.raises(ValueError, match="--d-real"):
        ab.construir_fila("linea_recta", r, args(corrida=1, r=0.03))
    with pytest.raises(ValueError, match="desvío"):
        ab.construir_fila("linea_recta", r, args(corrida=1, r=0.03, d_real=1.0))


def test_fila_validacion_giro_usa_magnitud_del_angulo():
    t, poses, vel = giro_sintetico(360, signo=-1.0)  # horario, como A2
    r = ab.analizar(t, poses, vel, "giro")
    fila = ab.construir_fila("validacion", r, args(variante="A2", valor_real=350.0))
    assert fila[:2] == ["A2", "giro"]
    assert float(fila[4]) == pytest.approx(100 * (360 - 350) / 360, abs=0.7)


def test_fila_calibracion_no_calcula_b_eff_propuesto():
    t, poses, vel = giro_sintetico(360)
    r = ab.analizar(t, poses, vel, "giro")
    with pytest.raises(ValueError, match="--b-eff-propuesto"):
        ab.construir_fila("calibracion", r, args(iteracion=1, b_eff_usado=0.2, theta_medido=348.5))
    fila = ab.construir_fila("calibracion", r, args(iteracion=1, b_eff_usado=0.2, theta_medido=348.5, b_eff_propuesto=0.25))
    assert fila[-1] == "0.2500"  # el valor tecleado por el grupo, sin tocar


def test_anexar_crea_encabezado_en_archivo_con_solo_salto_de_linea(tmp_path):
    f = tmp_path / "linea_recta.csv"
    f.write_text("\n")  # como están hoy los CSV del repositorio
    ab.anexar_fila(str(f), "linea_recta", ["1", "0.03", "1.0", "0.95", "5.0", "0.01"])
    assert f.read_text().splitlines() == ["corrida,r,d_real,d_odom,error_%,desvio_lateral", "1,0.03,1.0,0.95,5.0,0.01"]


def test_anexar_no_sobrescribe_y_agrega(tmp_path):
    f = tmp_path / "v.csv"
    ab.anexar_fila(str(f), "validacion", ["A2", "recta", "1.0", "0.98", "2.0"])
    ab.anexar_fila(str(f), "validacion", ["A2", "giro", "355", "360", "1.4"])
    assert len(f.read_text().splitlines()) == 3


def test_anexar_rechaza_encabezado_distinto_sin_tocar_el_archivo(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("otra,cosa\n1,2\n")
    with pytest.raises(ValueError, match="encabezado"):
        ab.anexar_fila(str(f), "validacion", ["A2", "recta", "1", "1", "0"])
    assert f.read_text() == "otra,cosa\n1,2\n"
