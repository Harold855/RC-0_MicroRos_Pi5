# RC-0 — Predicciones previas a las pruebas

**Proyecto:** CapyTown — Primer arranque y calibración del robot  
**Equipo:** 8
**Sección:** [S-003]  
**Fecha de registro:** [30/10/2026 18:18:50]

> **Importante:** Estas son nuestras predicciones, no las mediciones reales. Donde, se registran antes de iniciar las pruebas y no se modifican después de conocer los resultados.

## 1. Movimiento recto a 0.10 m/s durante 10 s

**Pregunta:** Si publicamos `linear.x = 0.10 m/s` durante `10 s`, ¿cuánto llegará a avanzar el robot y cuánto según `/odom`?

**Predecimos:**
- **Distancia real (cinta métrica): 98 cm.**
- **Distancia estimada por `/odom`: 100 cm.**

**Motivo:** El desplazamiento teórico es `d = v × t = 0.10 m/s × 10 s = 1.00 m = 100 cm`. Sin embargo, estimamos que el avance físico puede ser ligeramente menor debido al deslizamiento de las ruedas, la respuesta de los motores o el inicio y la detención del movimiento. Entonces, suponemos que, antes de calibrar, la odometría podría indicar aproximadamente el desplazamiento nominal de 100 cm. Son valores estimados: los datos reales se verificarán con la cinta y el registro de `/odom`.

## 2. Giro de 360° usando `b_eff = W`

**Pregunta:** Si configuramos el ancho de vía efectivo (`b_eff`) igual al ancho físico entre ruedas (`W`) y solicitamos un giro de 360° según la odometría, ¿el robot tendrá un giroo más o menos de 360°?

**Predicimos:** **Giró físicamente de menos de 360°**.

**Motivo:** Al tratarse de un robot de cuatro ruedas sin dirección, los giros pueden producir deslizamiento lateral. Esperamos que el ancho de vía efectivo real sea mayor que la separación física `W`. Si se usa `b_eff = W`, la odometría podría sobreestimar el ángulo de giro; por ello, cuando `/odom` marque 360°, el giro físico todavía podría ser inferior a una vuelta completa. Esta hipótesis se comprobará midiendo el giro real y ajustando `b_eff`.

## 3. Dos grupos con el mismo `ROS_DOMAIN_ID`

**Pregunta:** ¿Qué observaríamos si dos grupos utilizan el mismo `ROS_DOMAIN_ID`?

**Predecimos:** **Podrían aparecer nodos y tópicos de ambos robots y producirse interferencias en la comunicación.**

**Motivo:** Si los dos equipos están en la misma red ROS 2, comparten dominio y no tienen otro aislamiento, sus nodos pueden descubrirse mutuamente. Si publican y escuchan los mismos nombres de tópicos, como `/cmd_vel` y `/odom`, podrían mezclarse los datos e incluso recibirse comandos dirigidos al otro robot. Por eso, cada grupo debe usar el dominio asignado y configurarlo de manera consistente en la Raspberry Pi 5 y en la placa.

---

## Verificación posterior (se registran por separado)

Los resultados obtenidos durante las pruebas y la explicación de las diferencias entre predicción y medición se documentarán en `informe.pdf` y en los archivos `linea_recta.csv`, `calibration_log.csv` y `validacion.csv`. **No se modificarán las predicciones originales de este archivo.**

