"""Pruebas de los scripts de laboratorio (preflight, aplicar_param, corrida) con un `ros2` FALSO.

Solo verifican el flujo, las validaciones y los mensajes de error: no hay robot ni ROS. No son evidencia de nada.
"""

import os
import shutil
import stat
import subprocess
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..")
pytestmark = pytest.mark.skipif(shutil.which("bash") is None or sys.platform.startswith("win"), reason="requiere bash (Linux)")

ROS2_FALSO = r'''#!/usr/bin/env bash
D="${MOCK_DIR:?}"
case "$1 $2" in
  "node list")  if [ -f "$D/nodes_${ROS_DOMAIN_ID}" ]; then cat "$D/nodes_${ROS_DOMAIN_ID}"; else cat "$D/nodes"; fi ;;
  "topic list") awk -v t="${3:-}" '{ if (t=="-t") print $1" ["$2"]"; else print $1 }' "$D/topics" ;;
  "topic info") printf 'Type: x\nPublisher count: %s\nSubscription count: %s\n' "${MOCK_PUBS:-0}" "${MOCK_SUBS:-1}" ;;
  "topic echo") if [ "$3" = "/battery" ]; then printf 'data: %s\n---\n' "${MOCK_BAT:-73}"; else for i in $(seq 1 "${MOCK_ODOM_N:-40}"); do printf 'header:\n---\n'; done; fi ;;
  "param get")  f="$D/param_$4"; if [ -f "$f" ]; then v="$(cat "$f")"; else case "$4" in wheel_radius) v=0.0325;; *) v=0.24;; esac; fi; echo "Double value is: $v" ;;
  "param set")  if [ -n "${MOCK_SET_FAIL:-}" ]; then echo "Setting parameter failed"; else echo "$5" > "$D/param_$4"; echo "Set parameter successful"; fi ;;
  "bag record")
      [ "$3" = "-h" ] && { echo "usage: ros2 bag record"; exit 0; }
      out=""; while [ $# -gt 0 ]; do [ "$1" = "-o" ] && out="$2"; shift; done
      mkdir -p "$out"; echo "rosbag2_bagfile_information:" > "$out/metadata.yaml"; : > "${out}/$(basename "$out")_0.db3"
      echo "[INFO] [rosbag2_recorder]: Recording..."
      sleep 60 & P=$!; trap 'kill $P 2>/dev/null; exit 0' INT TERM; wait ;;
  "bag info")   printf 'Duration: 5.0s\nMessages: 100\nTopic: /cmd_vel | Type: geometry_msgs/msg/Twist | Count: %s | Serialization Format: cdr\n' "${MOCK_CMDN:-50}" ;;
  *) exit 0 ;;
esac
'''

ANALIZAR_FALSO = '#!/usr/bin/env bash\necho "ANALIZAR $*"\nexit "${MOCK_ANALIZAR_RC:-0}"\n'


def _ejecutable(ruta, texto):
    with open(ruta, "w") as f:
        f.write(texto)
    os.chmod(ruta, os.stat(ruta).st_mode | stat.S_IEXEC)


@pytest.fixture
def lab(tmp_path):
    """Copia del repo (scripts + capytown_esan) con un ros2 falso en el PATH."""
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(os.path.join(RAIZ, "scripts"), repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(RAIZ, "capytown_esan"), repo / "capytown_esan", ignore=shutil.ignore_patterns("__pycache__"))
    for csv in ("linea_recta.csv", "calibration_log.csv", "validacion.csv"):
        (repo / csv).write_text("x\n")
    bindir, mock = tmp_path / "bin", tmp_path / "mock"
    bindir.mkdir()
    mock.mkdir()
    _ejecutable(bindir / "ros2", ROS2_FALSO)
    _ejecutable(bindir / "fake_analizar", ANALIZAR_FALSO)
    _ejecutable(bindir / "fake_ok", "#!/usr/bin/env bash\necho SECUENCIA_OK\nexit 0\n")
    _ejecutable(bindir / "fake_fail7", "#!/usr/bin/env bash\necho SECUENCIA_FALLA\nexit 7\n")
    (mock / "nodes").write_text("/YB_Car_Node\n/odom_corrector\n")
    (mock / "topics").write_text("/cmd_vel geometry_msgs/msg/Twist\n/odom nav_msgs/msg/Odometry\n/odom_raw nav_msgs/msg/Odometry\n"
                                 "/battery std_msgs/msg/UInt16\n/imu sensor_msgs/msg/Imu\n/scan sensor_msgs/msg/LaserScan\n")

    class Lab:
        pass

    L = Lab()
    L.repo, L.mock, L.bin = repo, mock, bindir

    def correr(args, entrada="", extra_env=None, cwd=None):
        env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", MOCK_DIR=str(mock), ROS_DOMAIN_ID="8", RC0_REINTENTOS="1")
        env.update({k: str(v) for k, v in (extra_env or {}).items()})
        return subprocess.run(["bash"] + args, input=entrada, capture_output=True, text=True, env=env,
                              cwd=str(cwd or repo), timeout=90)

    L.correr = correr
    return L


# ---------------------------------------------------------------- preflight
def test_preflight_sano(lab):
    r = lab.correr(["scripts/preflight.sh"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK      placa conectada" in r.stdout and "0 falla(s)" in r.stdout
    assert "wheel_radius (r) actual = 0.0325" in r.stdout


def test_preflight_detecta_teleop_y_publicador_en_cmd_vel(lab):
    (lab.mock / "nodes").write_text("/YB_Car_Node\n/odom_corrector\n/teleop_key\n")
    r = lab.correr(["scripts/preflight.sh"], extra_env={"MOCK_PUBS": 1})
    assert r.returncode == 1
    assert "teleop_key está abierto" in r.stdout and "ya hay 1 publicador" in r.stdout


def test_preflight_sin_placa_ni_corrector_da_pistas(lab):
    (lab.mock / "nodes").write_text("")
    r = lab.correr(["scripts/preflight.sh"])
    assert r.returncode == 1
    assert "no aparece /YB_Car_Node" in r.stdout and "no corre /odom_corrector" in r.stdout


def test_preflight_exige_dominio_8(lab):
    r = lab.correr(["scripts/preflight.sh"], extra_env={"ROS_DOMAIN_ID": "20"})
    assert r.returncode == 1 and "usa 8" in r.stdout


def test_preflight_avisa_si_el_robot_sigue_en_dominio_20(lab):
    (lab.mock / "nodes_8").write_text("")
    (lab.mock / "nodes_20").write_text("/YB_Car_Node\n/odom_corrector\n")
    r = lab.correr(["scripts/preflight.sh"])
    assert r.returncode == 1 and "SÍ aparece en el dominio 20" in r.stdout


def test_entorno_fija_8_y_solo_admite_otro_en_modo_ensayo():
    def dom(**env):
        r = subprocess.run(["bash", "-c", "source config/entorno_rc0.sh >/dev/null; echo $ROS_DOMAIN_ID"], cwd=RAIZ,
                           capture_output=True, text=True, env=dict(os.environ, **env))
        return r.stdout.strip()
    assert dom() == "8"
    assert dom(RC0_DOMAIN_ID="20") == "8"
    assert dom(RC0_ENSAYO="1", RC0_DOMAIN_ID="77") == "77"


def test_preflight_odom_mudo_y_nodo_ajeno(lab):
    (lab.mock / "nodes").write_text("/YB_Car_Node\n/odom_corrector\n/robot_de_otro_grupo\n")
    r = lab.correr(["scripts/preflight.sh"], extra_env={"MOCK_ODOM_N": 0})
    assert r.returncode == 1
    assert "/odom no publica" in r.stdout and "nodos no esperados: /robot_de_otro_grupo" in r.stdout


# ---------------------------------------------------------------- aplicar_param
def test_aplicar_param_ok_y_bitacora(lab):
    r = lab.correr(["scripts/aplicar_param.sh", "wheel_radius", "0.0331", "tras corridas 1-3, con coma"], entrada="SI\n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (lab.mock / "param_wheel_radius").read_text().strip() == "0.0331"
    filas = (lab.repo / "bitacora_params.csv").read_text().splitlines()
    assert filas[0] == "timestamp,parametro,antes,despues,nota" and filas[1].endswith("wheel_radius,0.0325,0.0331,tras corridas 1-3; con coma")


@pytest.mark.parametrize("args,texto", [
    (["wheel_radius", "0,0331"], "coma decimal"),
    (["wheel_radius", "3.25"], "fuera del rango"),          # cm en vez de m
    (["wheel_separation", "24"], "fuera del rango"),
    (["wheel_radius", "abc"], "no es un número"),
    (["firmware_wheel_radius", "0.03"], "NO se toca"),
    (["velocidad", "1"], "no permitido"),
])
def test_aplicar_param_rechaza_con_mensaje_especifico(lab, args, texto):
    r = lab.correr(["scripts/aplicar_param.sh"] + args, entrada="SI\n")
    assert r.returncode == 2 and texto in r.stderr
    assert not (lab.mock / "param_wheel_radius").exists()


def test_aplicar_param_cancelar_y_rechazo_del_nodo(lab):
    r = lab.correr(["scripts/aplicar_param.sh", "wheel_radius", "0.0331"], entrada="no\n")
    assert r.returncode == 5 and not (lab.mock / "param_wheel_radius").exists()
    r = lab.correr(["scripts/aplicar_param.sh", "wheel_radius", "0.0331"], entrada="SI\n", extra_env={"MOCK_SET_FAIL": 1})
    assert r.returncode == 2 and "rechazó el cambio" in r.stderr


# ---------------------------------------------------------------- corrida
def _env_corrida(lab, secuencia="fake_ok"):
    return {"RC0_SECUENCIA_CMD": lab.bin / secuencia, "RC0_ANALIZAR_CMD": lab.bin / "fake_analizar",
            "RC0_CALIB_CMD": lab.bin / "fake_ok"}


def test_corrida_recta_a1_flujo_completo(lab):
    r = lab.correr(["scripts/corrida.sh", "recta", "A1", "1", "--rapido"], entrada="SI\n0.985\n0.012\nizq\ns\nprimera\n",
                   extra_env=_env_corrida(lab))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SECUENCIA_OK" in r.stdout
    assert "--csv linea_recta --corrida 1 --r 0.0325 --desvio-m 0.012" in r.stdout
    assert "--escribir linea_recta.csv" in r.stdout
    bags = list((lab.repo / "bags").glob("rc0_recta_c1_*"))
    assert len(bags) == 1 and (bags[0] / "metadata.yaml").exists()
    filas = (lab.repo / "bitacora_corridas.csv").read_text().splitlines()
    assert filas[0].startswith("timestamp,modo,variante,n,bag") and ",recta,A1,1," in filas[1] and "fila_escrita" in filas[1]


def test_corrida_a2_recta_y_giro_usan_validacion_csv(lab):
    r = lab.correr(["scripts/corrida.sh", "recta", "A2", "2", "--rapido"], entrada="SI\n0.97\n0\nninguno\ns\n\n", extra_env=_env_corrida(lab))
    assert r.returncode == 0 and "--csv validacion --variante A2 --valor-real 0.97" in r.stdout
    assert list((lab.repo / "bags").glob("rc0_val_recta_c2_*"))
    r = lab.correr(["scripts/corrida.sh", "giro", "A2", "1", "--rapido"], entrada="SI\n355.5\npasó\ns\n\n", extra_env=_env_corrida(lab))
    assert r.returncode == 0 and "--prueba giro --csv validacion --variante A2 --valor-real 355.5" in r.stdout
    assert list((lab.repo / "bags").glob("rc0_val_giro_c1_*"))


def test_corrida_pide_de_nuevo_un_valor_en_cm(lab):
    r = lab.correr(["scripts/corrida.sh", "recta", "A1", "1", "--rapido"], entrada="SI\n98\n0.98\n0.01\nder\nn\n\n", extra_env=_env_corrida(lab))
    assert r.returncode == 0
    assert "valor inválido '98'" in r.stderr and "98 cm = 0.98" in r.stderr
    assert "--escribir" not in r.stdout and "fila_no_escrita" in (lab.repo / "bitacora_corridas.csv").read_text()


def test_corrida_calibrar_b_usa_el_b_eff_vivo_del_corrector(lab):
    (lab.mock / "param_wheel_separation").write_text("0.2512\n")
    r = lab.correr(["scripts/corrida.sh", "calibrar_b", "A1", "3", "--rapido"], entrada="SI\n\n", extra_env=_env_corrida(lab))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "iteracion = 1" in r.stdout and "aplicar_param.sh wheel_separation" in r.stdout
    assert list((lab.repo / "bags").glob("rc0_giro_i3_*")) and ",0.2512," in (lab.repo / "bitacora_corridas.csv").read_text()


def test_corrida_si_la_secuencia_falla_pregunta_y_descarta(lab):
    r = lab.correr(["scripts/corrida.sh", "recta", "A1", "1", "--rapido"], entrada="SI\nn\n", extra_env=_env_corrida(lab, "fake_fail7"))
    assert r.returncode == 6
    assert "código 7" in r.stderr and "FALLAS" in r.stderr and "no se borra" in r.stdout
    assert not (lab.repo / "bitacora_corridas.csv").exists()


def test_corrida_cancelada_no_graba_nada(lab):
    r = lab.correr(["scripts/corrida.sh", "recta", "A1", "1", "--rapido"], entrada="no\n", extra_env=_env_corrida(lab))
    assert r.returncode == 5 and not (lab.repo / "bags").exists()


@pytest.mark.parametrize("args,texto", [
    (["giro", "A1", "1"], "calibrar_b"),
    (["calibrar_b", "A2", "1"], "NO se recalibra"),
    (["recta", "A1", "x"], "no es un número entero"),
    (["recta", "B7", "1"], "no válida"),
])
def test_corrida_rechaza_combinaciones_invalidas(lab, args, texto):
    r = lab.correr(["scripts/corrida.sh"] + args, extra_env=_env_corrida(lab))
    assert r.returncode == 2 and texto in r.stderr


def test_corrida_con_preflight_y_falla_no_graba(lab):
    (lab.mock / "nodes").write_text("/YB_Car_Node\n/odom_corrector\n/teleop_key\n")
    r = lab.correr(["scripts/corrida.sh", "recta", "A1", "1"], extra_env=_env_corrida(lab))
    assert r.returncode == 1 and "preflight tiene FALLAS" in r.stderr and not (lab.repo / "bags").exists()
