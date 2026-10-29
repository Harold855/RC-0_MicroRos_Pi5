"""Pruebas de verificacion_entrega y generar_tablas_informe con repositorios FALSOS en carpetas temporales.

Los datos de aquí son de juguete: verifican la lógica de la comprobación, no una calibración.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import generar_tablas_informe as gt  # noqa: E402
import verificacion_entrega as ve  # noqa: E402

CAB_R = "corrida,r,d_real,d_odom,error_%,desvio_lateral\n"
CAB_C = "iteracion,b_eff_usado,theta_reportado_deg,theta_medido_deg,error_%,b_eff_propuesto\n"
CAB_V = "variante,prueba,valor_real,valor_odom,error_%\n"


def estados(items, nombre_contiene):
    return [e for e, n, d in items if nombre_contiene in n or nombre_contiene in d]


def repo(tmp_path, recta=CAB_R, calib=CAB_C, valid=CAB_V):
    (tmp_path / "linea_recta.csv").write_text(recta)
    (tmp_path / "calibration_log.csv").write_text(calib)
    (tmp_path / "validacion.csv").write_text(valid)
    return str(tmp_path)


# ---------------------------------------------------------------- CSV
def test_csv_solo_con_encabezado_esta_pendiente_no_error(tmp_path):
    items = ve.revisar_csv(repo(tmp_path))
    assert not [i for i in items if i[0] == ve.ERR]
    assert [i for i in items if i[0] == ve.PEND]


def test_encabezado_incorrecto_es_error(tmp_path):
    items = ve.revisar_csv(repo(tmp_path, recta="corrida,r,d_real\n"))
    assert [i for i in items if i[0] == ve.ERR and "linea_recta" in i[1]]


def test_recta_con_tres_corridas_y_error_final_bajo_ok(tmp_path):
    filas = "1,0.03,1.0,0.90,10.0,0.01\n2,0.033,1.0,0.97,3.0,0.01\n3,0.034,1.0,0.99,1.0,0.01\n"
    items = ve.revisar_csv(repo(tmp_path, recta=CAB_R + filas))
    assert (ve.OK, "linea_recta.csv") in [(e, n) for e, n, _ in items if "encabezado" not in n]


def test_recta_con_error_final_alto_es_error(tmp_path):
    filas = "1,0.03,1.0,0.90,10.0,0.01\n2,0.03,1.0,0.95,5.0,0.01\n3,0.03,1.0,0.96,4.0,0.01\n"
    items = ve.revisar_csv(repo(tmp_path, recta=CAB_R + filas))
    assert [i for i in items if i[0] == ve.ERR and "> 2 %" in i[2]]


def test_calibracion_exige_convergencia_menor_a_1_porciento(tmp_path):
    mal = CAB_C + "1,0.2,360,348.5,3.19,0.2066\n2,0.2066,360,356.2,1.06,0.2088\n"
    bien = mal + "3,0.2088,360,358.9,0.31,0.2094\n"
    assert [i for i in ve.revisar_csv(repo(tmp_path, calib=mal)) if i[0] == ve.ERR]
    assert not [i for i in ve.revisar_csv(repo(tmp_path, calib=bien)) if i[0] == ve.ERR]


def test_validacion_pide_dos_rectas_y_un_giro(tmp_path):
    incompleta = CAB_V + "A2,recta,1.0,0.98,2.0\n"
    completa = incompleta + "A2,recta,1.0,1.01,1.0\nA2,giro,355,360,1.4\n"
    assert [i for i in ve.revisar_csv(repo(tmp_path, valid=incompleta)) if i[0] == ve.PEND and "validacion" in i[1]]
    assert [i for i in ve.revisar_csv(repo(tmp_path, valid=completa)) if i[0] == ve.OK and i[1] == "validacion.csv"]


def test_dato_sintetico_en_csv_es_error(tmp_path):
    items = ve.revisar_csv(repo(tmp_path, recta=CAB_R + "SINTETICO_1,0.03,1.0,1.0,0,0\n"))
    assert [i for i in items if i[0] == ve.ERR and "SINTETICO" in i[2]]


def test_variante_distinta_de_A2_avisa(tmp_path):
    items = ve.revisar_csv(repo(tmp_path, valid=CAB_V + "A4,recta,1.0,1.0,0\n"))
    assert [i for i in items if i[0] == ve.AVISO]


# ---------------------------------------------------------------- bags y plots
def bag(tmp_path, nombre, storage="sqlite3", ext=".db3", con_datos=True, con_meta=True):
    d = tmp_path / "bags" / nombre
    d.mkdir(parents=True)
    if con_meta:
        (d / "metadata.yaml").write_text(f"rosbag2_bagfile_information:\n  storage_identifier: {storage}\n")
    if con_datos:
        (d / f"{nombre}_0{ext}").write_bytes(b"x")


def test_bag_valido_y_plots(tmp_path):
    bag(tmp_path, "rc0_recta")
    (tmp_path / "plots").mkdir()
    (tmp_path / "plots" / "rc0_recta_xy.png").write_bytes(b"x")
    items = ve.revisar_bags_y_plots(str(tmp_path))
    assert (ve.OK, "bags/rc0_recta/") in [(e, n) for e, n, _ in items]
    assert (ve.OK, "plots/rc0_recta_xy.png") in [(e, n) for e, n, _ in items]
    assert (ve.PEND, "plots/rc0_recta_theta_t.png") in [(e, n) for e, n, _ in items]
    assert (ve.PEND, "bags/rc0_giro/") in [(e, n) for e, n, _ in items]


def test_bag_sin_metadata_o_sin_datos_o_con_almacenamiento_incoherente(tmp_path):
    bag(tmp_path, "rc0_recta", con_meta=False)
    bag(tmp_path, "rc0_giro", con_datos=False)
    bag(tmp_path, "rc0_val_recta", storage="mcap", ext=".db3")
    items = ve.revisar_bags_y_plots(str(tmp_path))
    err = [n for e, n, _ in items if e == ve.ERR]
    assert set(err) == {"bags/rc0_recta/", "bags/rc0_giro/", "bags/rc0_val_recta/"}


def test_bag_sintetico_se_rechaza(tmp_path):
    bag(tmp_path, "SINTETICO_recta")
    assert [i for i in ve.revisar_bags_y_plots(str(tmp_path)) if i[0] == ve.ERR]


# ---------------------------------------------------------------- yaml, readme, informe
def test_yaml_plantilla_pendiente_y_con_valores_ok(tmp_path):
    (tmp_path / "config").mkdir()
    y = tmp_path / "config" / "wheel_params.yaml"
    y.write_text("wheel_radius: null   # r\nb_eff: null\n")
    assert [e for e, *_ in ve.revisar_yaml(str(tmp_path))] == [ve.PEND, ve.PEND]
    y.write_text("wheel_radius: 0.0335\nb_eff: 0.2094  # m\n")
    assert [e for e, *_ in ve.revisar_yaml(str(tmp_path))] == [ve.OK, ve.OK]
    y.write_text("")
    assert ve.revisar_yaml(str(tmp_path))[0][0] == ve.ERR


def test_yaml_con_clave_wheel_separation_se_reconoce(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "wheel_params.yaml").write_text("wheel_radius: 0.03\nwheel_separation: 0.21\n")
    assert [e for e, *_ in ve.revisar_yaml(str(tmp_path))] == [ve.OK, ve.OK]


def test_readme_pendiente_y_completo(tmp_path):
    (tmp_path / "README.md").write_text("S-003 A1 A2 ROS_DOMAIN_ID 8\nroles: por definir\n- r final: pendiente\n")
    items = ve.revisar_readme(str(tmp_path))
    assert not [i for i in items if i[0] == ve.ERR] and [i for i in items if i[0] == ve.PEND]
    (tmp_path / "README.md").write_text(
        "S-003 A1 A2 ROS_DOMAIN_ID 8\nIntegración: A, Control: B, Planificación: C, Percepción: D\nr final: 0.033 m\n"
    )
    assert all(e == ve.OK for e, *_ in ve.revisar_readme(str(tmp_path)))


def test_informe_pdf_estimacion_de_paginas(tmp_path):
    uno = b"%PDF-1.4\n1 0 obj\n<< /Type /Pages /Count 1 >>\nendobj\n2 0 obj\n<< /Type /Page >>\nendobj\n"
    dos = uno + b"3 0 obj\n<< /Type /Page >>\nendobj\n"
    p = tmp_path / "informe.pdf"
    p.write_bytes(uno)
    n, como = ve._paginas_pdf(str(p))
    p.write_bytes(dos)
    n2, _ = ve._paginas_pdf(str(p))
    if "estimado" in como:  # sin pypdf: heurística
        assert (n, n2) == (1, 2)


def test_setup_log_pendiente_o_con_datos(tmp_path):
    assert ve.revisar_otros(str(tmp_path))[0][0] == ve.PEND
    (tmp_path / "setup_log.txt").write_text("ROS_DOMAIN_ID=8\n/imu\naverage rate: 49.9\n")
    assert ve.revisar_otros(str(tmp_path))[0][0] == ve.OK


def test_main_termina_con_error_solo_si_hay_error_y_final_exige_todo(tmp_path):
    raiz = repo(tmp_path)
    (tmp_path / "README.md").write_text("S-003 A1 A2 ROS_DOMAIN_ID\nroles: por definir\nr final: pendiente\n")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "wheel_params.yaml").write_text("wheel_radius: null\nb_eff: null\n")
    (tmp_path / "capytown_esan").mkdir()
    (tmp_path / "capytown_esan" / "plot_odom.py").write_text("# " + "x" * 200)
    assert ve.main(["--raiz", raiz]) == 0          # solo pendientes
    assert ve.main(["--raiz", raiz, "--final"]) == 1
    (tmp_path / "linea_recta.csv").write_text("mal\n")
    assert ve.main(["--raiz", raiz]) == 1


# ---------------------------------------------------------------- tablas del informe
def test_tablas_sin_datos_no_inventan(tmp_path):
    md = gt.generar(repo(tmp_path))
    assert md.count("(sin datos)") == 3


def test_tablas_con_datos_reales_de_juguete(tmp_path):
    md = gt.generar(repo(tmp_path, recta=CAB_R + "1,0.03,1.0,0.95,5.0,0.01\n"))
    assert "| 1 | 0.03 | 1.0 | 0.95 | 5.0 | 0.01 |" in md and md.count("(sin datos)") == 2


def test_tablas_rechazan_sinteticos_y_encabezados_raros(tmp_path):
    with pytest.raises(ValueError, match="SINTETICO"):
        gt.generar(repo(tmp_path, recta=CAB_R + "SINTETICO,0.03,1,1,0,0\n"))
    with pytest.raises(ValueError, match="encabezado"):
        gt.generar(repo(tmp_path, valid="a,b\n1,2\n"))
