---
name: keywords-google-ads
description: Las keywords de Google Ads de un cliente, con criterio - qué pujar, qué negativizar y hacia dónde se mueve la demanda. Con cuenta activa, cruza tres fuentes - los términos de búsqueda REALES de la cuenta mes a mes (archivo «Estacionalidad - <Cliente>», interno, que escribe solo el Ads Script), la tendencia de 5 años de Google Trends en España (automatizada, cada término en su propia escala) y lo que el servicio ofrece DE VERDAD según su landing actual. Sin cuenta todavía, arma el plan desde el brief. Saca qué términos crecen y cuáles se hunden, si hay estacionalidad real o la fabricó la gestión, qué demanda del sector no se recibe, qué queman dinero y cuánto se va en lo que el servicio no puede cumplir; y cierra con el plan - grupos por intención, concordancias, negativas para pegar y alertas de medición. Filtra siempre la marca y todo lo que el servicio no ofrece (un servicio online no compra «centro de…»). Entrega un solo documento en 6. Reportes del Drive del cliente. Usar cuando alguien diga "keywords de <cliente>", "estacionalidad de <cliente>", "tendencias de <cliente>", "qué keywords crecen", "en qué meses invertimos más", "por qué bajó/subió este mes", "negativas de <cliente>" o "el cliente quiere Google Ads". NO usar para decidir si la cuenta escala en general (eso es google-ads-mcp) ni para nada de Meta.
---

# Keywords de Google Ads: qué pujar, qué no, y hacia dónde va la demanda

Para Equipo, o para quien lo use: **una frase lo dispara todo**:

> *«Haz las keywords de \<Cliente\>. Landing: \<URL\>. No ofrece: \<lo que no vende\>.»*

Claude te preguntará lo que falte. Si el cliente **no tiene cuenta todavía**, salta al final: «Sin cuenta: el plan desde el brief».

**Glosario de una línea, para no repetirlo:** *keyword* = la palabra por la que se puja · *término de búsqueda* = lo que la gente escribió de verdad · *negativa* = palabra que le dice a Google «no enseñes el anuncio si buscan esto» · *concordancia* = cuánto se parece la búsqueda a la keyword para que salga el anuncio: `[exacta]`, `"de frase"`, amplia · *CPA* = lo que cuesta cada contacto conseguido · *cuota de impresiones* = de las veces que podía salir el anuncio, cuántas salió; lo que falta se pierde por **presupuesto** (se acabó el dinero) o por **ranking** (no ganó la subasta) · *Ads Script* = un programa que corre dentro de Google Ads y escribe en una hoja · *rclone* = la herramienta con la que Claude baja archivos de Drive · *Trends* = Google Trends, lo que busca el país entero.

> ## ⛔ Solo lectura
> Lee la cuenta, la hoja y Trends, y propone. No toca Google Ads: subir una keyword, pausar
> o negativizar lo hace una persona después de aprobarlo.

> ## 📐 El servicio manda sobre los datos
> Un término que crece un 70 % no vale nada si el cliente no puede cumplir lo que pide. Antes de
> recomendar una keyword se comprueba contra lo que el servicio ofrece **hoy** (paso 0). Y antes
> de fiarse de un CPA, se mira si la medición es de fiar (paso 3).

---

## Las tres fuentes y lo que aporta cada una

| Fuente | Qué dice | Lo que NO puede decir |
|---|---|---|
| **La cuenta** (Ads Script → «Estacionalidad - Cliente») | Qué convierte y a qué coste, qué quema dinero, cuándo compra quien llega, qué se pierde y por qué | Lo que nunca se pujó; lo que pasó antes de la cuenta |
| **Google Trends** (`trends.py`, `descubrir.py`) | Si cada concepto crece o se hunde en 5 años; qué se busca junto a él y qué sube ahora | La cola larga (queda bajo su umbral); si el cliente puede cumplirlo |
| **El servicio** (landing actual + Dirección) | Qué se ofrece de verdad y qué no | Nada de volumen: es el filtro |

Ninguna basta sola. La cuenta sin Trends confunde gestión con temporada. Trends sin el servicio
recomienda lo que no se vende. El servicio sin datos es intuición.

---

## Paso 0 · Qué ofrece el servicio HOY, y dónde está todo

**No se salta.** De aquí salen las listas que usan todos los scripts.

1. **La landing que recibe el tráfico de Google** (no la home). Se saca de la cuenta: campañas →
   URL final; o se le pregunta a Dirección. Es la fuente más fiel de lo que se vende hoy.
2. **El brief** del Drive (`Clientes → <Cliente> → 0. Onboarding`), solo para contrastar. Puede
   tener meses y describir líneas que ya no van en Google. **Si brief y landing no coinciden, se
   pregunta a Dirección antes de seguir**: él sabe qué se vende; el brief, qué se pensaba vender.
3. Claude escribe **`~/Desktop/CLIENTES/<Cliente>/google-ads/contexto.json`** y te lo enseña:
   ```json
   {"landing": "https://…",
    "estacional": "https://docs.google.com/spreadsheets/d/…",
    "marca": "nombre del cliente, variantes, nombre del fundador",
    "excluir": "centro, clinica, ingreso, internamiento, residencial, hospital, cerca de mi",
    "conceptos": "dejar de beber, terapia online, adiccion"}
   ```
   - **`marca`**: cómo escribe la gente el nombre del cliente. También el del fundador si la
     gente lo busca. Se apartan siempre: quien busca por el nombre ya conocía al cliente.
   - **`excluir`**: lo que el servicio **no** ofrece. Online sin ingreso → `centro, clinica,
     ingreso, internamiento, residencial, hospital, cerca de mi`. Local en una ciudad → las otras
     ciudades. Solo empresas → `particular, gratis, casero`.
   - **`conceptos`**: 6-10 conceptos cortos del servicio en el lenguaje de la landing. Son las
     semillas de Trends. Cola larga no: Trends no la publica.
   - **`estacional`**: la URL del archivo «Estacionalidad - \<Cliente\>». Está en la línea
     `SHEET_URL_ESTACIONAL` del Ads Script de la cuenta, o buscando ese nombre en el Drive del
     Google que autorizó el script. Si no existe, la cuenta no tiene el script: `INSTALACION.md`.
4. Y **`familias.json`** en la misma carpeta, con los conceptos agrupados. Lo escribe Claude a
   partir de la landing y te lo enseña; tú no lo escribes:
   ```json
   {"dejar de beber": ["dejar de beber", "dejar el alcohol"], "online": ["online", "terapia", "psicolog"]}
   ```
   Un término cae en **una** familia: la primera del JSON que encaje. Lo que no encaja va a «resto».

**El caso que originó este paso** (23-09-2026): el análisis recomendó «centro de adicciones» porque
crecía. El cliente es 100 % online: quien busca «centro» quiere un sitio adonde ir. Con `excluir`
desaparece, y lo que queda («terapia online» +70 %) sí es lo que vende.

## Paso 1 · La cuenta: qué convierte, qué quema, qué se pierde

```bash
S=~/.claude/skills/keywords-google-ads/scripts; C=~/Desktop/CLIENTES/<Cliente>/google-ads
python3 $S/terminos.py "<estacional>" --marca "<marca>" --excluir "<excluir>" --familias $C/familias.json
python3 $S/estacionalidad.py "<estacional>" --marca "<marca>" --excluir "<excluir>" --familias $C/familias.json
```

`terminos.py` saca: los que **convierten** con su CPA · los que **queman dinero** sin una conversión ·
cuánto se va en **lo que el servicio no cumple** y a qué CPA frente al resto (convierten peor, no
cero) · gasto y CPA **por familia** · las **alertas de medición**.

`estacionalidad.py` saca: la cuenta **por año** (¿crece o cae?) · el índice mensual de impresiones,
clics y conversiones sobre los años completos, con el mes en curso aparte · **gasto y CPA por mes** ·
la **cuota perdida** por presupuesto y por ranking, ponderada por impresiones elegibles · familias.

- Menos de **24 meses completos** = hipótesis, no patrón. Los scripts lo avisan.
- Las impresiones son de términos que tuvieron al menos un clic: no es toda la demanda.

## Paso 2 · Trends: ¿cada concepto crece o se hunde, y tiene temporada?

```bash
python3 $S/trends.py --terminos "<conceptos>" --excluir "<excluir>"
```

Dos tablas. **La que importa es la tendencia**: últimas 52 semanas frente a las primeras 52, **cada
término consultado solo, en su propia escala**. No se mide nunca desde un lote con ancla: ahí los
términos pequeños quedan en valores de 1-3 y el porcentaje sale del ruido (el mismo término dio
+69 % o +309 % según con quién fuera). El lote con ancla solo sirve para `vol`, el tamaño relativo.

Cómo leerla:
- **Cae un 25 % o más en cinco años** → está perdiendo mercado aunque hoy convierta.
- **Sube** → hacia ahí va la demanda.
- **Buscar el patrón de lenguaje**, no términos sueltos. En la prueba real: caía todo lo que obliga
  a ponerse una etiqueta («alcohólicos anónimos» −43 %, «alcoholismo» −21 %) y subía lo que describe
  una acción o un formato («terapia online» +70 %, «dejar el alcohol» +31 %). El patrón es el
  hallazgo; los números, la prueba.
- `vol` por debajo de 10: no fiable. ±15 % en el índice mensual no es una temporada.
- Si Trends no responde (429), el script lo dice y se para. Esperar 10-15 minutos.

## Paso 3 · Lo que se busca en el sector y la cuenta no recibe

```bash
python3 $S/descubrir.py --semillas "<conceptos>" --excluir "<excluir>" --hoja "<estacional>" --marca "<marca>"
```

Por cada concepto, las búsquedas relacionadas y las que suben ahora, cruzadas con lo que la cuenta ya
recibe. Filtra series, canciones y «qué es…»; con `--ruido` se añaden famosos o títulos del sector.

**Todo lo que salga se revisa a mano.** El cruce es aproximado, y Trends mezcla intenciones: «terapia
de pareja» sale junto a «terapia online» y no es el servicio.

## Paso 4 · El cruce: ¿temporada del mercado o de la gestión?

| La cuenta | Trends | Qué significa | Qué se hace |
|---|---|---|---|
| picos marcados | mismos picos | estacionalidad real | presupuesto 2-3 semanas antes del pico |
| picos marcados | **plano** | **los picos los hizo la gestión** | **estabilizar y arreglar la cuenta, no el calendario** |
| plana | picos | se está perdiendo la temporada | entrar antes, ampliar términos |
| plana | plana | nada estacional | tendencia y relevancia |

Señal fuerte de la segunda fila: el mejor mes de la cuenta coincide con uno flojo del mercado. En la
prueba real, septiembre era el mejor de la cuenta (índice 215) y de los flojos del mercado (91).

Y mirar siempre la **cuota perdida por ranking**. Por encima del 40 % todo el año, es la bolsa más
grande y no la arregla ningún calendario: relevancia del anuncio, keyword y landing.

## Paso 5 · El plan de keywords

Con las salidas de los pasos 1-3 se arma el plan. Formato fijo:

- **Grupos por intención**, cada uno con su tabla `Keyword | Concordancia | Por qué`. El «por qué»
  lleva siempre un número: conversiones y CPA de la cuenta, o el cambio en Trends.
- `[exacta]` para lo que ya convierte o lo que más crece; `"de frase"` para variaciones controladas;
  amplia casi nunca.
- **Un grupo por cada concepto que crece** en Trends, aunque la cuenta lo trabaje poco.
- **Un grupo «mantener, no crecer»** para lo que convierte pero cuyo mercado se hunde: solo exactas.
- **Negativas en una línea, para pegar**: todo `excluir` + las familias que queman dinero + lo que
  no es el servicio (otras patologías, empleo, curso, «qué es»…). Nunca una que comparta raíz con un
  término que convierte.
- **«Pendiente de confirmar con Dirección»**: lo que tiene datos buenos pero no está claro si se ofrece.
- **Destino**: la landing del paso 0.

**Antes de fiarse de un CPA, las alertas de medición.** Un término con más conversiones que clics
cuenta de más. En la prueba real, uno solo hacía parecer la familia «tratamiento» la más barata de la
cuenta (12 €); sin él, era **1 conversión por 300 €**.

## Paso 6 · El documento, uno solo

`Google Ads - <Cliente> - mercado, estacionalidad y keywords - <mes año>`. En este orden:

1. **Lo que hay que saber** — tres párrafos y el veredicto en una línea.
2. **Hacia dónde va el mercado** — la tabla de tendencia y el patrón de lenguaje explicado; por
   qué va a favor o en contra de cómo está posicionado el cliente.
3. **Estacionalidad** — la tabla mensual del mercado, en su tamaño real.
4. **La cuenta** — por año, por mes, gasto y CPA.
5. **La cuota perdida** — presupuesto frente a ranking.
6. **Dónde se va el dinero** — quema, lo que no se cumple, familias, alerta de medición.
7. **Términos sugeridos** — el plan del paso 5.
8. **Qué haría, por orden** — primero lo que falsea los datos, luego lo que pierde dinero, luego lo
   que lo gana. Solo acciones que el servicio puede cumplir, y un apartado de lo que NO se haría.
9. **Lo que no se puede calcular** — con el motivo.

### Entrega
Al Drive de trabajo, carpeta `Clientes → <Cliente> → 6. Reportes` (en rclone,
`gdrive:i_<Cliente>/c_<Cliente>/6. Reportes/`; `i_` es la carpeta interna, `c_` la que ve el cliente).

```bash
# el .docx se genera con python-docx desde el markdown del informe; luego:
rclone copy "<informe>.docx" "gdrive:i_<Cliente>/c_<Cliente>/6. Reportes/"
```

**rclone sube el `.docx` pero no lo convierte a Google Doc**, y el conector de Drive convierte pero
no puede escribir en esa carpeta. Así que, al entregar, **se avisa a Dirección** de que le quedan dos
clics: botón derecho → Abrir con → Documentos de Google → Guardar como Documento de Google. Para
avisarle: `python3 ~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/avisar.py --nivel info "…"`.
**Nunca un `.md`**: no lo abre nadie.

---

## Sin cuenta: el plan desde el brief

Cliente nuevo que quiere Google Ads y aún no tiene cuenta con histórico. No hay pasos 1-4: solo
el brief, Trends (pasos 2 y 3 sirven igual, con los conceptos del brief) y el paso 5. El método
del plan desde el brief está en `references/keywords-desde-brief.md`. El documento se llama
`Keywords Google Ads - <Cliente> - <mes año>` y va a la misma carpeta. En cuanto la cuenta tenga
tres meses de datos, se instala el Ads Script y se pasa al método completo.

---

## Errores que ya se cometieron (y cuestan dinero)

- **Recomendar lo que el servicio no ofrece.** «Centro de adicciones» a un servicio online. → Paso 0.
- **Fiarse de un brief viejo.** Describía una línea que la cuenta no trabaja; hubo que tirar medio
  informe. → La landing actual manda; ante la duda, Dirección.
- **Medir la tendencia desde un lote con ancla.** Los términos pequeños salían con +309 % o −46 %
  según el lote. → Cada término solo, ventanas de 52 semanas. Las cifras de la primera versión de
  este documento (+109 %, +75 %) estaban infladas por eso.
- **Comparar años parciales.** «2021→2026» eran 15 semanas contra 38. → Ventanas de 52.
- **Fiarse de un CPA sin mirar la medición.** 17 conversiones con 11 clics. → `terminos.py`, sección 5.
- **Confirmar lo obvio.** «El mercado del alcohol es plano» no le sirve a nadie. El valor está en la
  tendencia, el lenguaje que cambia y lo que no se recibe.
- **Consultar la cola larga en Trends.** Da ceros. → Conceptos cortos.
- **Comparar sin quitar tildes.** «clinica» no cazaba «clínica». → `comun.norm()` en todo.
- **Dejar la marca dentro.** Cambia la temporada alta entera. El fundador también es marca.
- **Meter los datos en la hoja del cliente.** Son internos y regenerar esa hoja los borraría.
- **Entregar en `.md`.**

---

## Archivos

| Archivo | Para qué |
|---|---|
| `INSTALACION.md` | Montar el Ads Script en una cuenta, paso a paso. Una vez por cliente. |
| `scripts/comun.py` | Lo compartido: normalizar, bajar el archivo, leer pestañas, familias. |
| `scripts/generar_script_cliente.py` | El Ads Script de un cliente, relleno, sin otros clientes y en caracteres seguros. |
| `scripts/ads-script-estacionalidad.js` | La plantilla del Ads Script. No se pega cruda: se genera. |
| `scripts/terminos.py` | Paso 1: convierte, quema, no se cumple, familias, medición. |
| `scripts/estacionalidad.py` | Paso 1: por año, por mes, gasto, CPA, cuota perdida. |
| `scripts/trends.py` | Paso 2: tendencia y estacionalidad del mercado. |
| `scripts/descubrir.py` | Paso 3: lo que se busca y no se recibe. |
| `references/trends.md` | Cómo funciona la consulta a Trends y cómo leerla sin engañarse. |
| `references/keywords-desde-brief.md` | El plan cuando aún no hay cuenta. |
