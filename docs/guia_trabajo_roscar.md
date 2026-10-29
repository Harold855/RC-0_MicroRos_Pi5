# Guía de trabajo con el RosCar 8 (MicroROS-Pi5) — RC-0

Etiquetas: **[DOC]** lo dicen los documentos del reto; **[LAB]** lo informó el grupo; **[VERIFICAR]** hay que comprobarlo en el robot; **[RECOM]** recomendación técnica.
Cada comando indica dónde se ejecuta: `[PC]` (laptop o Pi 400), `[PI HOST]` (Raspberry Pi 5 del RosCar) o `[DOCKER ROS 2]` (contenedor del RosCar).

## 0. Mapa de lo que se conecta

```text
Laptop (Windows/Ubuntu)  o  Raspberry Pi 400 (Ubuntu)      ← aquí viven el repositorio y las copias de seguridad
        │  Wi-Fi "RosCar8"  ·  TigerVNC (escritorio)  ·  SSH/scp (archivos)
        ▼
Raspberry Pi 5 del RosCar  (HOST, 10.42.0.1)
        │  docker  (sh ros2_humble.sh)
        ▼
Contenedor ROS 2 Humble  ← ros2, rosbag2, capytown_esan
        │  micro-ROS Agent
        ▼
ESP32-S3 → motores, encoders, IMU, LiDAR
```

- **"Escritorio remoto" aquí es TigerVNC, no el Escritorio remoto de Microsoft (RDP).** El RosCar ofrece VNC en `10.42.0.1:5900` [LAB]; `mstsc.exe` no conectará salvo que alguien haya instalado `xrdp` en el robot [VERIFICAR, poco probable].
- `10.42.0.1` identifica **el robot cuyo Wi-Fi tienes conectado**. Conéctate solo a `RosCar8`.
- La contraseña del Wi-Fi y del robot las da el docente. **No las escribas en el repositorio, en scripts ni en esta guía.**

## 1. Conectarse por escritorio remoto (TigerVNC)

### Ubuntu (Pi 400 o laptop con Linux) [LAB]
```bash
# [PC] una sola vez
sudo apt update
sudo apt install tigervnc-viewer
# [PC] cada sesión, con el Wi-Fi RosCar8 conectado
xtigervncviewer 10.42.0.1::5900
```

### Windows
1. Instala **TigerVNC Viewer** (ejecutable `vncviewer64-*.exe`, desde la página de releases del proyecto TigerVNC en GitHub).
2. Conéctate al Wi-Fi `RosCar8`, abre el viewer y en *VNC server* escribe `10.42.0.1::5900` (los dos puntos fuerzan el puerto 5900).
3. Pide la contraseña VNC al docente.

### Uso del escritorio remoto
- **Varias personas conectadas al mismo VNC ven y controlan el mismo escritorio a la vez** [RECOM, comprobar al probarlo]. Que opere **una** persona; las demás miran. Dos personas escribiendo en la misma terminal es la forma más rápida de mandar un comando equivocado.
- El portapapeles suele funcionar entre tu equipo y la sesión: sirve para pegar comandos largos.
- **TigerVNC no transfiere archivos.** Para copiar código y bags usa `scp` (sección 4).
- `F8` abre el menú del viewer (pantalla completa, portapapeles, desconectar).
- Si la sesión se congela: cierra y vuelve a abrir el viewer antes de tocar el robot.

## 2. Dentro del robot: host y contenedor

```bash
# [PI HOST] abre una terminal en el escritorio remoto
whoami; hostname
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
ls -l ~/ros2_humble.sh ~/start_agent_rpi5.sh          # scripts del fabricante [VERIFICAR que existan]
```
```bash
# [PI HOST] entrar al contenedor ROS 2 (según las diapositivas del fabricante; leer el script antes)
sh ros2_humble.sh
```
```bash
# [DOCKER ROS 2] ya dentro del contenedor
source config/entorno_rc0.sh      # exporta ROS_DOMAIN_ID=20 (el del Agent del robot) solo en esta terminal
echo "$ROS_DISTRO $ROS_DOMAIN_ID"
```

Reglas de la Parte A:
- **No dupliques el micro-ROS Agent.** El reto dice que `ros2 launch capytown_esan bringup.launch.py` ya lo incluye; las diapositivas del fabricante mandan `start_agent_rpi5.sh`. Antes de lanzar nada, mira si ya corre (`bash scripts/parteA_host.sh` lo comprueba) [VERIFICAR cuál aplica].
- El dominio **8** debe coincidir en la Pi y en la placa. Cómo configurarlo en la placa lo debe explicar el docente: **no flashees por tu cuenta**.
- Diagnóstico de solo lectura, que añade al `setup_log.txt`:
  ```bash
  bash scripts/parteA_host.sh                 # [PI HOST]
  bash scripts/parteA_contenedor.sh           # [DOCKER ROS 2]
  ```
- La captura de `rqt_graph` se hace a mano (es una ventana): por eso conviene el escritorio remoto.
- La odometría suele ser `/odom_raw`, no `/odom` [DOC: presentación del fabricante]. Comprueba con `ros2 topic list -t | grep odom`.

## 3. Varias terminales, cada una con un trabajo

Abre terminales separadas dentro del contenedor (o `docker exec -it <contenedor> bash` desde otras terminales del host):

| Terminal | Para qué |
|---|---|
| 1 | Bringup / Agent (déjalo corriendo) |
| 2 | `ros2 bag record` (se inicia **antes** de mover) |
| 3 | La prueba: `secuencia_rc0.py` o `calibrate_beff` |
| 4 | **Parada lista:** escribe el comando de frenado pero **no pulses ENTER**: `ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"` |

Nombres de bag con fecha y corrida, **nunca repetidos** (`ros2 bag record` falla si la carpeta existe):
```bash
# [DOCKER ROS 2] ejemplo; sustituir el topic por el real
ros2 bag record /odom_raw /cmd_vel /tf -o rc0_recta_c1_$(date +%H%M%S)
```
Los nombres exigidos por el reto (`rc0_recta`, `rc0_giro`, `rc0_val_recta`, `rc0_val_giro`) se obtienen **copiando** la corrida final, sin renombrar ni borrar las demás.

## 4. Llevar código al robot y sacar los datos (lo más importante)

**Nada se guarda solo dentro del RosCar** [LAB]: el robot se reinicia, su software se cierra y el contenedor puede recrearse (`docker rm`) y perder todo lo que tenía dentro. El RosCar es solo lugar de paso.

El Wi-Fi `RosCar8` probablemente **no tiene internet** [VERIFICAR]. Entonces `git` se usa en casa o desde la laptop con otra red; en el laboratorio se copia con `scp`.

### Hacia el robot (código)
```bash
# [PC] desde la carpeta del repositorio, con el Wi-Fi RosCar8   (<usuario> lo confirma el docente)
scp -r capytown_esan config scripts <usuario>@10.42.0.1:~/rc0/
```
```bash
# [PI HOST] del host al contenedor (cambio operativo: pide aprobación; <contenedor> sale de docker ps)
docker cp ~/rc0/. <contenedor>:/root/rc0/
```
[VERIFICAR] si `ros2_humble.sh` ya monta una carpeta compartida entre host y contenedor: en ese caso `docker cp` no hace falta.

### Desde el robot (bags y CSV), después de CADA corrida
```bash
# [PI HOST] del contenedor al host
docker cp <contenedor>:/root/rc0/bags ~/rc0_respaldo/
```
```bash
# [PC] del host a la laptop o al Pi 400
scp -r <usuario>@10.42.0.1:~/rc0_respaldo/bags ./bags_respaldo/
```
Comprueba la copia: cada carpeta de bag debe tener `metadata.yaml` y su archivo de datos (`.db3` o `.mcap`):
```bash
# [PC con ROS 2]
ros2 bag info bags_respaldo/bags/rc0_recta_c1_123456
```
- Windows: `scp` y `ssh` vienen con Windows 10/11 (PowerShell); si no responde, activa *Cliente de OpenSSH* en Características opcionales.
- Si `scp` no funciona (SSH desactivado o usuario distinto) [VERIFICAR], la alternativa es un pendrive USB conectado a la Pi 5.

## 5. Antes de mover el robot (siempre)

- [ ] Robot identificado: el 8, y el Wi-Fi conectado es `RosCar8`.
- [ ] Área despejada, **una persona junto al robot** con la mano libre y una terminal con el comando de frenado preparado.
- [ ] Batería suficiente. El robot suena cuando necesita carga y la autonomía ronda los 30 min [LAB]. No calibres con el aviso sonando: la velocidad puede cambiar con la carga [RECOM]. Anota el nivel de batería de cada corrida.
- [ ] `ros2 topic list -t | grep odom` muestra la odometría y **`ros2 topic hz` la ve llegando**.
- [ ] El bag está grabando **antes** de la orden de movimiento.
- [ ] Orientación inicial y línea de inicio comprobadas. En A1 la recta va oeste→este y el giro es antihorario; en A2, este→oeste y horario.
- [ ] Probaste `secuencia_rc0.py` en **dry-run** (no mueve) y el plan impreso es el que quieres.
- [ ] Sabes qué hace el botón de reinicio con los motores [VERIFICAR con el docente]; no lo trates como parada de emergencia hasta saberlo.

## 6. Si algo se reinicia o falla

| Síntoma | Qué comprobar |
|---|---|
| `ros2: command not found` | Estás en el host, no en el contenedor: `sh ros2_humble.sh` y `source` del entorno |
| `ros2 node list` vacío | Dominio distinto entre Pi y placa, Agent caído, o terminal sin `source config/entorno_rc0.sh` |
| No aparece `/odom` | Probablemente se llama `/odom_raw` |
| La odometría vuelve a cero | Se reinició el bringup o el robot: no mezcles ese tramo; mide con poses relativas y graba una corrida nueva |
| El software del robot se cerró en pleno bag | Descarta la corrida o conserva el bag como "interrumpido"; no lo uses para calibrar |
| `docker ps` sin permisos | Pide acceso al docente; no uses `sudo` a ciegas |
| El escritorio remoto no conecta | ¿Wi-Fi correcto? `ping 10.42.0.1`; reinicia el viewer |
| Los datos desaparecieron del contenedor | Estaban solo dentro del RosCar: por eso se copian después de cada corrida |

## 7. Qué no sé todavía [VERIFICAR]

Usuario y contraseña de SSH, si SSH está habilitado, nombre del contenedor, si `ros2_humble.sh` monta una carpeta compartida, si el bringup ya incluye el Agent, topic de odometría real, ubicación y claves de `wheel_params.yaml`, y si el Wi-Fi `RosCar8` tiene internet. Anótalos aquí cuando los confirmes.
