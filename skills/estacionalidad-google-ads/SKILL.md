---
name: estacionalidad-google-ads
description: Dice hacia dónde se mueve la demanda de lo que vende el cliente y qué hacer con su cuenta de Google Ads. Cruza tres fuentes - los términos de búsqueda REALES de la cuenta mes a mes (archivo «Estacionalidad — <Cliente>», interno, que escribe solo el Ads Script), la tendencia de 5 años de Google Trends en España (automatizada, sin navegador) y lo que el servicio ofrece DE VERDAD según su landing actual. Saca qué términos crecen y cuáles se hunden año a año, si hay estacionalidad real o la ha fabricado la gestión de la cuenta, qué demanda no se está capturando, en qué meses se deja dinero sobre la mesa, y cierra con los TÉRMINOS SUGERIDOS: plan de keywords por grupos y concordancias, lista de negativas lista para pegar y alertas de medición, todo en el mismo documento. Filtra siempre la marca y todo lo que el servicio no puede cumplir (un servicio online no compra «centro de…»). Entrega un Google Doc con veredicto y acciones ordenadas. Usar cuando alguien diga "estacionalidad de <cliente>", "tendencias de <cliente>", "en qué meses invertimos más", "qué keywords crecen", "hacia dónde va el mercado", "por qué bajó/subió este mes", o pregunte si conviene adelantar campañas. NO usar para decidir si la cuenta escala en general (eso es google-ads-mcp) ni para planificar keywords de un cliente SIN cuenta todavía (eso es keywords-google-ads, que parte solo del brief).
---

# Estacionalidad y tendencia de Google Ads

La pregunta de partida era **«¿en qué meses hay que invertir más?»**. Probada contra una cuenta real,
la respuesta útil resultó ser otra: **¿hacia dónde se está moviendo la demanda, y la cuenta va con
ella o contra ella?** La estacionalidad mensual es una parte pequeña de eso; la tendencia de varios
años y el encaje con el servicio pesan mucho más.

> ## ⛔ Solo lectura
> Lee hojas y Trends y propone. No toca la cuenta de Google Ads: mover presupuestos o keywords lo hace
> una persona después de aprobarlo.

> ## 📐 El servicio manda sobre los datos
> Un término que crece un 200 % no vale nada si el cliente no puede cumplir lo que pide. Antes de
> recomendar cualquier keyword, se comprueba contra lo que el servicio ofrece **hoy** (paso 0).

---

## Las tres fuentes y lo que aporta cada una

| Fuente | Qué dice | Lo que NO puede decir |
|---|---|---|
| **La cuenta** (Ads Script → «Estacionalidad — Cliente») | Cuándo compra quien ya llega, a qué coste, qué se pierde y por qué | Lo que nunca se ha pujado; lo que pasó antes de que existiera la cuenta |
| **Google Trends** (`trends.py`, `descubrir.py`) | Si el mercado entero crece o se hunde, término a término, 5 años; qué búsquedas suben | Los términos de cola larga (quedan bajo su umbral); si el cliente puede cumplirlos |
| **El servicio** (landing actual + Dirección) | Qué se ofrece de verdad y qué no | Nada de volumen: es el filtro, no el dato |

Ninguna basta sola. La cuenta sin Trends confunde gestión con temporada. Trends sin el servicio
recomienda lo que no se vende. El servicio sin datos es intuición.

---

## Paso 0 · Qué ofrece el servicio HOY — y qué no

**Esto va primero y no se salta.** De aquí salen dos listas que se pasan a todos los scripts:

1. **Leer la landing actual** (la que recibe el tráfico de Google, no la home). Es la fuente más fiel
   de lo que se vende hoy.
2. **Contrastar con el brief** del Drive (`0. Onboarding`). Cuidado: el brief puede ser de hace meses
   y describir líneas que ya no se trabajan en Google. **Si el brief y la landing no coinciden, se
   pregunta a Dirección antes de seguir.** Él sabe qué se está vendiendo; el brief sabe qué se pensaba vender.
3. Anotar:
   - **`--marca`**: el nombre del cliente y cómo lo escribe la gente.
   - **`--excluir`**: las palabras de lo que el servicio **no** ofrece. Ejemplos:
     - servicio online sin ingreso → `centro,clinica,ingreso,internamiento,residencial,hospital,cerca de mi`
     - servicio local en una ciudad → los nombres de las demás ciudades
     - solo empresas → `particular,gratis,casero`
   - **Los conceptos del servicio**, en el lenguaje de la landing: son las semillas de Trends.

**Caso real que originó este paso** (23-09-2026): el análisis recomendó pujar «centro de adicciones»
porque crecía un 199 % en cinco años. El cliente es 100 % online, sin ingreso: quien busca «centro»
quiere un sitio adonde ir. Habría sido tráfico caro que no convierte nunca. Con `--excluir`, desaparece;
y lo que queda (terapia online +109 %, psicólogo online +69 %) sí es lo que el cliente vende.

## Paso 1 · Los datos de la cuenta

Hace falta el archivo **«Estacionalidad — \<Cliente\>»**, interno, con las pestañas `terminos-mes` e
`is-mes`. Lo escribe el Ads Script cada mañana; se monta con `INSTALACION.md` (15 minutos por cliente).

```bash
python3 ~/.claude/skills/estacionalidad-google-ads/scripts/estacionalidad.py \
  "<URL del archivo de estacionalidad>" --marca "<marca>"
```

Saca, por mes: el índice de búsquedas, de clics y de conversiones; el gasto y el coste por lead; y la
cuota de impresiones perdida **separada por presupuesto y por ranking**.

- **La marca, siempre fuera.** Quien busca al cliente por su nombre ya lo conocía: mide notoriedad,
  no demanda. En la cuenta de prueba, 74 filas de marca sobre 5.750 movían la temporada alta de mes.
- **Menos de 24 meses = hipótesis.** Con un año no se distingue temporada de crecimiento.

## Paso 2 · La tendencia de varios años — lo que más pesa

```bash
python3 ~/.claude/skills/estacionalidad-google-ads/scripts/trends.py \
  --terminos "<conceptos del servicio, 6-10>" --excluir "<lo que no se ofrece>"
```

Devuelve dos tablas. **La que importa es la segunda: el volumen medio de cada año.** Responde a
«¿qué ha pasado en otros años?», que es la pregunta real. El índice mensual (la primera) promedia los
años y **aplana justo lo que interesa**: un término que se hunde y otro que crece pueden dar el mismo
índice mensual.

Lectura:
- **Un término que cae un 25 % o más en cinco años** está perdiendo mercado aunque hoy convierta.
- **Uno que sube** es hacia donde se mueve la demanda.
- Buscar **el patrón de lenguaje**, no términos sueltos. En la prueba real: se hundía todo lo que
  obliga a ponerse una etiqueta («alcohólicos anónimos» −46 %, «alcoholismo» −21 %) y crecía todo lo
  que describe una acción o un formato («dejar de beber» +43 %, «terapia online» +109 %). Ese patrón
  es el hallazgo; los números son la prueba.

**Semillas buenas y malas.** Trends solo publica conceptos con volumen: «tratamiento alcoholismo
madrid» devuelve ceros. `trends.py` recorta ciudades y arranques de frase si lee de la cuenta, pero lo
mejor es darle **conceptos de 1-3 palabras en el lenguaje de la landing**. Un término con `vol` por
debajo de ~10 no es fiable: sus picos (631, 1.150) son divisiones por casi cero.

## Paso 3 · La demanda que no se está capturando

```bash
python3 ~/.claude/skills/estacionalidad-google-ads/scripts/descubrir.py \
  --semillas "<conceptos>" --excluir "<lo que no se ofrece>" \
  --hoja "<URL del archivo de estacionalidad>" --marca "<marca>"
```

Por cada concepto, Trends da las búsquedas **relacionadas** y las que están **en aumento**. Cruzadas
con lo que la cuenta ya recibe, queda lo que nadie trabaja. Filtra ruido (famosos, series, «qué es…»)
y, con `--excluir`, lo que el servicio no puede cumplir.

**Todo lo que sale se revisa a mano antes de proponerlo.** El filtro de «ya se puja» es laxo: una
cuenta con concordancia amplia recibe miles de términos distintos y casi todo acaba pareciendo
cubierto. Que un término haya aparecido en la cuenta no significa que se trabaje.

## Paso 4 · El cruce: ¿temporada del mercado o de la gestión?

| La cuenta | Trends | Qué significa | Qué se hace |
|---|---|---|---|
| picos marcados | mismos picos | estacionalidad real | calendario de presupuesto, 2-3 semanas antes del pico |
| picos marcados | **plano** | **los picos los hizo la gestión** | **estabilizar y arreglar la cuenta, no el calendario** |
| plana | picos | se está perdiendo la temporada | entrar antes, ampliar términos |
| plana | plana | no hay nada estacional | otras palancas: tendencia, relevancia |

Señal fuerte de la segunda fila: **el mejor mes de la cuenta coincide con uno flojo del mercado**. En
la prueba real, septiembre era el mejor de la cuenta (índice 177) y de los peores del mercado (90).

Y siempre mirar la **cuota perdida por ranking**. Si pasa del 40 % todo el año, esa es la bolsa más
grande de la cuenta y no la arregla ningún calendario: es relevancia de anuncio, keyword y landing.

## Paso 5 · Los términos sugeridos — el plan de keywords

Aquí entra la lógica de `keywords-google-ads` (grupos por intención, concordancias, negativas), pero
**con los datos reales de la cuenta en lugar del brief**. Primero:

```bash
python3 ~/.claude/skills/estacionalidad-google-ads/scripts/terminos.py \
  "<URL del archivo de estacionalidad>" --marca "<marca,fundador>" \
  --excluir "<lo que no se ofrece>" --familias familias.json
```

Saca cinco cosas: los términos que **convierten** con su coste por lead, los que **queman dinero**
sin una conversión, cuánto se va en lo que el servicio **no puede cumplir** (y a qué CPA frente al
resto), el gasto y CPA **por familia**, y las **alertas de medición**.

`familias.json` se escribe para cada cliente con los conceptos de su landing:
`{"dejar de beber": ["dejar de beber", "dejar el alcohol"], "online": ["online", "psicolog", "terapia"]}`.

Con eso y la tendencia del paso 2 se arma el plan:

- **Grupos por intención**, cada uno con su tabla `Keyword | Concordancia | Por qué`. El «por qué»
  lleva siempre un número: conversiones y CPA de la cuenta, o crecimiento en Trends.
- **Exacta** `[ ]` para lo que ya convierte o lo que más crece; **frase** `" "` para variaciones
  controladas; **amplia** casi nunca.
- **Un grupo para cada línea que crece** en Trends, aunque la cuenta la trabaje poco.
- **Un grupo «mantener, no crecer»** para lo que convierte pero cuyo mercado se hunde: solo sus exactas.
- **Negativas en una línea, listas para pegar**: todo `--excluir` + los términos de la sección
  «queman dinero» que se repiten como familia + lo que no es el servicio (otras patologías, empleo, curso…).
- **«Pendiente de confirmar»**: lo que tiene datos buenos pero no está claro si se ofrece. No se
  decide solo: se le pregunta a Dirección.
- **Destino**: la URL de la landing que se leyó en el paso 0.

**Antes de fiarse de un CPA, mirar las alertas de medición.** Un término con más conversiones que
clics significa que la conversión cuenta varias veces por persona. En la prueba real, uno solo
(«tratamiento alcoholismo madrid», 17 conversiones con 11 clics) hacía parecer la familia
«tratamiento» la más barata de la cuenta (17 €). Sin él, era la peor: **1 conversión por 304 €**.

## Paso 6 · El informe — un solo documento

Estructura, en este orden:

1. **Lo que hay que saber** — tres párrafos: hacia dónde va el mercado, si hay temporada o no, y el
   problema de fondo. Con el veredicto en una línea.
2. **Qué sube y qué baja en cinco años** — la tabla anual, y el patrón de lenguaje explicado.
   Por qué eso va a favor o en contra de cómo está posicionado el cliente.
3. **La estacionalidad** — la tabla mensual del mercado, dicha en su tamaño real (un ±15 % no es una temporada).
4. **Lo que hace la cuenta** — índices, gasto y coste por lead por mes.
5. **La cuota perdida** — presupuesto frente a ranking.
6. **Dónde se va el dinero** — términos sin conversión, lo que no se puede cumplir, familias, y la
   alerta de medición si la hay.
7. **Términos sugeridos** — el plan del paso 5: grupos con sus tablas, negativas para pegar,
   pendientes de confirmar y destino.
8. **Qué haría, por orden** — acción, por qué (con el número), confianza. **Solo acciones que el
   servicio puede cumplir.** Primero lo que falsea los datos (medición), luego lo que pierde dinero
   (negativas), luego lo que lo gana (grupos nuevos). Y un apartado de lo que NO se haría y por qué.
9. **Lo que no se puede calcular** — con el motivo.

Todo en el **mismo documento**: mercado, cuenta y keywords se leen juntos porque se explican entre sí.
Nombre: `Google Ads - <Cliente> - mercado, estacionalidad y keywords - <mes año>`.

**Dónde se entrega:** Google Doc en `6. Reportes` del Drive del cliente. **Nunca un `.md`.** Ver
«Entrega» abajo.

---

## Errores que ya se cometieron (y cuestan dinero)

- **Recomendar lo que el servicio no ofrece.** «Centro de adicciones» +199 % a un servicio online.
  → Paso 0, `--excluir`.
- **Fiarse de un brief viejo.** El de junio describía una línea de alimentación que la cuenta no
  trabaja; el informe la analizó entera y hubo que tirarla. → La landing actual manda; ante la duda, Dirección.
- **Confirmar lo obvio.** «El mercado del alcohol es plano» no le sirve a nadie. El valor está en lo
  que no se ve: la tendencia de años, el lenguaje que cambia, la demanda sin capturar.
- **Promediar los años.** El índice mensual esconde que un término se está hundiendo. → Paso 2, la
  tabla anual primero.
- **Consultar la cola larga en Trends.** Da ceros. → Conceptos cortos, en el lenguaje de la landing.
- **Fiarse de un CPA sin mirar la medición.** Un término con 17 conversiones y 11 clics convirtió la
  peor familia de la cuenta en la mejor. → `terminos.py`, sección 5, antes de recomendar nada.
- **Dejar la marca dentro.** Cambia la temporada alta entera. Y el nombre del fundador también es marca.
- **Leer las impresiones sin el presupuesto de ese mes.** Un mes sin dinero parece un mes sin demanda.
- **Subir presupuesto el día 1 del mes bueno.** Llega tarde: 2-3 semanas antes.
- **Meter los datos en la hoja del cliente.** Son internos y regenerar esa hoja los borraría. Archivo aparte.
- **Entregar en `.md`.** No lo abre nadie.

---

## Entrega

El informe va como **Google Doc** a `i_<Cliente>/c_<Cliente>/6. Reportes/`.

Límites comprobados de las dos vías de escritura:
- **rclone** escribe en esa carpeta pero **no convierte a Google Doc** (sube `.docx` aunque se le pase
  `--drive-import-formats docx`).
- **El conector de Drive** sí crea Google Docs nativos (HTML en base64 + `mimeType:
  application/vnd.google-apps.document`), pero va con la cuenta personal de Dirección y **no puede escribir
  en las carpetas del Drive de trabajo**.

Así que: `.docx` con `python-docx` → rclone a `6. Reportes` → **avisar a Dirección** de que falta
convertirlo (botón derecho → Abrir con → Documentos de Google). No dejar ese paso sin decir.

---

## Archivos

| Archivo | Para qué |
|---|---|
| `INSTALACION.md` | Montar el Ads Script en una cuenta, paso a paso. Una vez por cliente. |
| `scripts/generar_script_cliente.py` | Genera el Ads Script de un cliente, relleno y sin mencionar a otros. |
| `scripts/estacionalidad.py` | Paso 1: la cuenta, mes a mes. |
| `scripts/trends.py` | Paso 2: tendencia anual y estacionalidad del mercado, en lote. |
| `scripts/descubrir.py` | Paso 3: búsquedas relacionadas y en aumento que no se capturan. |
| `scripts/terminos.py` | Paso 5: lo que convierte, lo que quema dinero, lo que no se cumple, familias y alertas de medición. |
| `references/trends.md` | Cómo funciona la consulta a Trends y cómo leerla sin engañarse. |
