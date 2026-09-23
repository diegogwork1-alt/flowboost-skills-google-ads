# Google Trends: qué añade, cómo se consulta y cómo se lee sin engañarse

Comprobado el 23-09-2026 contra una cuenta real, y corregido el mismo día por un consejo de auditoría.

## Para qué sirve, exactamente

La cuenta dice qué convierte **de lo que ya se puja**. Trends dice tres cosas que la cuenta no puede:

1. **Si cada concepto crece o se hunde**, con cinco años de historia, frente a los meses que lleve
   la cuenta.
2. **Si la estacionalidad que muestra la cuenta existe en el mercado** o la fabricó la gestión.
3. **Qué se busca junto a cada concepto y qué está subiendo ahora**: demanda que la cuenta no recibe.

## Cómo se consulta (sin navegador)

`scripts/trends.py` y `scripts/descubrir.py` usan la API interna de Trends. Contesta `429` a la
primera; abrir antes la portada deja la cookie `NID`, y con ella responde. Entre llamadas se espera,
y si falla tres veces el script **lo dice y se para**: nunca imprime una conclusión con datos vacíos.

No usa `pytrends` (archivado en 2025) ni ninguna API de pago.

## Cómo mide la tendencia, y por qué así

**Cada término se consulta SOLO**, en su propia escala 0-100, y se compara la media de las últimas 52
semanas con la de las primeras 52. Con `today 5-y` la serie son 262 semanas: el primer año tiene 15 y
el último 38, así que comparar «2021 frente a 2026» mezcla temporada con tendencia. La última semana,
marcada `isPartial`, se descarta.

**Nunca se mide desde un lote con ancla.** Trends escala cada consulta para que el mayor de los
términos llegue a 100; los pequeños quedan en 1-3 y el porcentaje anual sale del ruido. Medido: el
mismo término daba +69 % en un lote y +309 % en otro; otro daba −46 % o +411 % según la compañía. La
primera versión de la skill lo hacía así y todas sus cifras estaban infladas.

**El lote con ancla solo sirve para `vol`**, el tamaño relativo: el único dato comparable entre
términos. Un `vol` por debajo de ~10 no es fiable.

## Leer el resultado

- Un término que **cae un 25 % o más** en cinco años está perdiendo mercado aunque hoy convierta.
  Uno que sube es hacia donde se mueve la demanda. El script marca ⚠ a partir del 25 %.
- Buscar el **patrón de lenguaje**, no términos sueltos.
- En el índice mensual, **±15 % no es una temporada**.
- Los términos **largos** salen a ceros: Trends solo publica lo que tiene volumen. Conceptos de 1-3
  palabras, en el lenguaje de la landing.
- `descubrir.py` mezcla intenciones: «terapia de pareja» sale junto a «terapia online». **Todo se
  revisa a mano** y se filtra con `excluir` y `--ruido`.
- `--geo ES` por defecto; regional como `ES-MD` cuando el servicio es local.

## Lo que salió en la prueba real (23-09-2026, cifras corregidas)

Servicio online de adicciones, sin ingreso. España, 5 años, cada término solo.

| término | cambio | vol | ¿lo cumple el servicio? |
|---|---|---|---|
| terapia online | **+70 %** | 15 | sí |
| dejar el alcohol | +31 % | 18 | sí |
| dejar de beber | +21 % | 21 | sí |
| psicólogo online | +20 % | 12 | sí |
| adicción | −20 % | 100 | sí, pero se hunde |
| alcoholismo | −21 % | 47 | sí, pero se hunde |
| alcohólicos anónimos | **−43 %** | 19 | sí, pero se hunde |
| ~~centro de adicciones~~ | (descartado) | — | **no: pide un sitio físico** |

Dos lecciones:
1. **El lenguaje se mueve**: baja lo que obliga a ponerse una etiqueta, sube lo que describe una
   acción o un formato. Iba a favor del cliente, posicionado para «quien no se reconoce como
   adicto», y su cuenta pujaba justo lo que se hundía.
2. **El término que más crecía en la primera versión («centro de adicciones» +199 %) era el único
   que no podía vender.** Sin `excluir`, habría sido la acción número uno.

Estacionalidad del mercado: casi nula (±15 % en verano), mientras la cuenta oscilaba de 30 a 215
entre su peor y su mejor mes. Los picos eran de gestión.

## Lo que no se puede hacer

- **Keyword Planner** da volumen mensual absoluto (12 meses por defecto; hasta 4 años con
  `year_month_range`) y sería mejor fuente, pero el MCP oficial de Google Ads solo hace consultas
  GAQL y no llega a ese servicio. Haría falta la librería de Python de Google Ads con el mismo OAuth.
- **La API oficial de Trends** existe desde julio de 2025, pero sigue en alpha por solicitud.
