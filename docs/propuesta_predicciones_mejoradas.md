# Propuesta de mejora de las predicciones (NO es el archivo oficial)

> Esto es una **propuesta de redacción** sobre el texto del grupo. Los números y las conclusiones son los de ustedes y no se han tocado.
> Lo marcado como **SUGERENCIA** es opcional: acepten, reescriban con sus palabras o descarten.
> El archivo oficial sigue siendo `informe/predicciones.md`, que el grupo copia, revisa y commitea.
> Antes de copiar: quiten las líneas de SUGERENCIA y cualquier texto que no puedan defender sin mirar el archivo.

---

# RC-0 — Predicciones previas a las pruebas

**Proyecto:** CapyTown — Primer arranque y calibración del robot
**Equipo:** 8 · **Sección:** S-003 · **Robot:** RosCar 8
**Fecha y hora de registro (hora local):** 30/10/2026, 18:18:50

> Estas son nuestras predicciones, no mediciones. Se registran antes de iniciar las pruebas de calibración y no se modifican después de conocer los resultados.

## 1. Movimiento recto a 0.10 m/s durante 10 s

**Pregunta:** Si publicamos `linear.x = 0.10 m/s` durante `10 s`, ¿cuánto avanzará el robot según la cinta y cuánto según `/odom`?

**Predecimos:**
- **Distancia real (cinta métrica): 98 cm.**
- **Distancia según `/odom`: 100 cm.**

**Motivo:** El desplazamiento teórico es `d = v × t = 0.10 m/s × 10 s = 1.00 m = 100 cm`.

> **SUGERENCIA — decidan cuál de estas dos redacciones refleja lo que ustedes creen y borren la otra.**
> Antes de elegir, respondan: *¿`/odom` sale de los encoders de las ruedas o de la velocidad comandada?* (Según la presentación del docente, el firmware integra los pulsos de los encoders; `odom_corrector` solo la re-escala.)
>
> **Redacción A** (se mantienen 98 y 100):
> "Esperamos que `/odom` marque cerca del valor nominal porque el firmware controla la velocidad de cada rueda y la odometría cuenta lo que giran las ruedas, y esperamos que la cinta marque algo menos porque las ruedas pueden patinar en la cartulina: la rueda gira más de lo que avanza el robot. El arranque de `ros2 topic pub` y la rampa del motor afectan al movimiento real en general, así que los consideramos un efecto menor y común a ambas medidas."
>
> **Redacción B** (si creen que el arranque y el frenado reducen *ambas* medidas):
> "Esperamos que tanto la cinta como `/odom` queden por debajo de 100 cm por el arranque y el frenado de los motores, y que `/odom` supere a la cinta por el patinaje." *(En este caso sus dos números deberían cambiar de modo coherente; eso lo deciden ustedes antes del commit.)*

**Nota de honestidad (opcional):** Son valores estimados; los datos reales se verificarán con la cinta y con el registro de `/odom` en el bag.

## 2. Giro de 360° usando `b_eff = W`

**Pregunta:** Si configuramos el ancho de vía efectivo (`b_eff`) igual al ancho físico entre ruedas (`W`) y pedimos un giro de 360° según la odometría, ¿el robot girará más o menos de 360°?

**Predecimos:** el robot **girará físicamente menos de 360°**.

**Motivo:** Es un robot de cuatro ruedas sin dirección, por lo que al girar las ruedas se arrastran lateralmente. Esperamos que el ancho de vía efectivo real sea mayor que la separación física `W`. Con `b_eff = W`, la odometría sobreestimaría el ángulo girado: cuando `/odom` marque 360°, el giro físico seguirá siendo inferior a una vuelta completa. Lo comprobaremos midiendo el giro real con transportador.

> **SUGERENCIA (práctica, no cambia la predicción):** el valor de arranque de `wheel_separation` en el YAML del robot es 0.24 m. Midan `W` con regla y anoten si coincide, porque el reto pide empezar con `b_eff = W`.

## 3. Dos grupos con el mismo `ROS_DOMAIN_ID`

**Pregunta:** ¿Qué observaríamos si dos grupos usan el mismo `ROS_DOMAIN_ID`?

**Predecimos:** **Si ambos robots estuvieran en la misma red, aparecerían nodos y tópicos de los dos y habría interferencia en la comunicación.**

**Motivo:** Dos equipos en la misma red ROS 2 con el mismo dominio pueden descubrirse entre sí. Si ambos publican y escuchan los mismos nombres de tópicos (`/cmd_vel`, `/odom`), los datos se mezclarían e incluso un robot podría recibir comandos dirigidos al otro. Por eso cada grupo debe usar el dominio asignado y configurarlo de forma consistente en la Raspberry Pi 5 y en la placa.

> **SUGERENCIA (completa la respuesta con la distinción lógico/físico):**
> "El dominio es un aislamiento *lógico* dentro de una misma red. Como cada RosCar crea su propia red Wi-Fi, dos grupos con el mismo dominio **no se verían** mientras sus robots estén en redes distintas; solo habría interferencia si ambos compartieran la misma red (por ejemplo, conectados por cable a la misma LAN)."

---

## Verificación posterior (se registra por separado)

Los resultados y la explicación de las diferencias entre predicción y medición se documentarán en `informe.pdf` y en `linea_recta.csv`, `calibration_log.csv` y `validacion.csv`. **No se modificarán las predicciones originales de este archivo.**

---
### Lista antes de hacer commit (borrar esta sección del archivo oficial)
- [ ] Quitaron los corchetes, las líneas de SUGERENCIA y las notas de este documento.
- [ ] Elegieron una sola redacción para P1 y los números concuerdan con ella.
- [ ] Cada integrante puede explicar las tres respuestas sin mirar el archivo.
- [ ] Hicieron `git commit` **antes** de la primera medición con cinta.
