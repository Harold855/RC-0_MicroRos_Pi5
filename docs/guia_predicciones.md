# Guía para escribir las predicciones (método, no respuestas)

> Esta guía **no contiene las predicciones del grupo**. Las predicciones oficiales se escriben en
> `informe/predicciones.md`, con las palabras y los números de ustedes, **antes** de medir con cinta.
> Aquí hay un método y un ejemplo resuelto de OTRO escenario para que lo repliquen. El docente permite IA
> para código y depuración; el razonamiento de las predicciones y su defensa son suyos.

## Cómo se construye una buena predicción (3 pasos)
1. **Línea base ideal.** ¿Qué dice el modelo si todo fuera perfecto? (una cuenta de una línea).
2. **Qué se aparta de lo ideal y de qué lado.** Lista las causas físicas posibles y, para cada una, responde:
   - ¿afecta a **lo que mide la cinta**, a **lo que dice la odometría**, o a **ambas por igual**?
   - ¿empuja el valor hacia arriba o hacia abajo?
3. **Decide y comprométete.** Un número (o "más/menos"), una justificación de 2–3 líneas, y qué dato real te
   haría cambiar de idea. Una predicción vaga ("más o menos igual") sirve menos que una concreta que luego falle.

## Preguntas para razonar cada predicción del reto
**P1 (dos números en cm: cinta y odometría).**
- ¿Cuántos cm da velocidad × tiempo? Esa es la línea base.
- `ros2 topic pub` tarda en arrancar y el motor tarda en acelerar y en frenar: ¿eso cambia la distancia real
  respecto de v·t? ¿Cambia **también** lo que registra la odometría, o solo la cinta? (Piensa en qué mide cada una.)
- ¿Qué podría hacer que la cinta y la odometría **no** coincidan entre sí aunque midan el mismo movimiento?
  (¿qué valor del robot usa la odometría para convertir giros de rueda en metros? ¿y qué pasa con el patinaje?)
- Con eso, ¿cuál esperas mayor, y en cuántos cm aproximadamente?

**P2 (`b_eff` = W y giro de 360° por odometría: ¿más o menos de 360° reales?).**
- Repasa `v_L = v − ω·b/2`, `v_R = v + ω·b/2`: ¿para qué sirve `b_eff` en el modelo?
- Un robot de 4 ruedas sin dirección gira arrastrando las ruedas de lado. ¿El ancho **efectivo** del giro es
  igual, mayor o menor que el medido con regla? ¿Qué diría eso de la odometría frente al giro real?
- Cierra en una frase: "girará más / menos de 360° porque…".

**P3 (dos grupos con el mismo `ROS_DOMAIN_ID`).**
- ¿Qué separa a los participantes de ROS 2: el dominio, la red, o ambos? ¿Qué hace cada uno?
- Cada RosCar tiene **su propio** Wi-Fi: ¿pueden verse dos robots así? ¿Y si estuvieran en la misma LAN con el mismo dominio?
- Distingue aislamiento **lógico** de **físico**.

## Ejemplo resuelto de OTRO escenario (no es el de ustedes)
*Escenario ilustrativo:* "Se publica `linear.x = 0.15 m/s` durante 6 s. ¿Cuánto avanzará según la cinta y según la odometría?"
1. Base ideal: 0.15 × 6 = 0.90 m = 90 cm.
2. Desvíos: (a) arranque de `topic pub` y rampa del motor: se mueve menos tiempo "efectivo" → la **distancia real** es
   menor que v·t, y la odometría, que mide el movimiento real, lo ve **igual que la cinta**. (b) Escala de la
   odometría (radio de rueda que usa vs. el real): afecta **solo a la odometría**, en un sentido que no se conoce
   de antemano. (c) Patinaje en una superficie lisa: la rueda gira más de lo que avanza el robot; la odometría
   cuenta el giro de la rueda y la cinta el avance real → odometría ≥ cinta.
3. Decisión de ejemplo: "cinta ≈ 86 cm, odometría ≈ 88 cm. Resto 4 cm a v·t por arranque/rampa (afecta a ambas) y
   sumo ~2 cm a la odometría por posible patinaje. Cambiaría de idea si veo que la odometría marca MENOS que la
   cinta: entonces el radio que usa estaría subestimado."
   *(Números inventados para el ejemplo; los de ustedes salen de su propio razonamiento y deben poder defenderlos.)*

## Cómo registrarlas
1. Escribe en `informe/predicciones.md`: fecha y hora, autor(es), las 3 respuestas con justificación.
2. `git add informe/predicciones.md && git commit -m "Predicciones RC-0 escritas antes de medir"` **antes** de la
   primera medición con cinta. La fecha del commit prueba que son anteriores. El `push` puede hacerse después.
3. No se editan después. Si te equivocas, añade una nota debajo; no borres la original.
4. Cada integrante debería poder explicar las tres sin mirar el archivo (pregunta 1 y 2 del banco de defensa
   están relacionadas con la 5, 6 y 7).
