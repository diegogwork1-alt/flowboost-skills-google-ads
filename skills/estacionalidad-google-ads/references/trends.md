# Google Trends: qué añade, y cómo se consulta en lote

Comprobado el 23-09-2026 contra una cuenta real.

## Para qué sirve, exactamente

La cuenta dice cuándo compra **quien ya llega**. Trends dice si ese patrón existe en **todo el
mercado del país** y si **se repite años atrás** — hasta 5, frente a los meses que lleve la cuenta.

La pregunta que responde no es «¿en qué mes invierto?» (eso lo dice la cuenta), sino:

> **¿La estacionalidad que veo es del mercado, o la he fabricado yo con cómo gestiono la cuenta?**

Es una diferencia que cambia el plan entero. Si el mercado es plano y la cuenta tiene picos, el
calendario no arregla nada: lo que hay que mirar es la gestión.

## Se automatiza — con dos cuidados

`scripts/trends.py` lo hace solo:

```bash
python3 scripts/trends.py --terminos "<conceptos del servicio>" --excluir "<lo que no ofrece>"
```

Lee los términos **que más convierten** de la cuenta, los consulta en lote y devuelve el índice
mensual de cada uno. Sin navegador, sin API de pago y sin `pytrends` (archivado en 2025).

**Cuidado 1 — el máximo de 5 y los valores relativos.** Trends compara 5 términos por consulta y sus
valores son relativos *a esa consulta*: dos lotes no son comparables entre sí. El script mete el
mismo **término ancla** (el de más clics) en todos los lotes y reescala por él. La columna `vol` es
el volumen de cada término respecto al ancla.

**Cuidado 2 — el 429.** La API interna responde `429` a la primera. Se abre antes la portada de
Trends: esa llamada también falla, pero deja la cookie `NID`, y con ella la API contesta. El script
espera entre lotes; pedir deprisa vuelve a bloquear.

## Leer el resultado sin engañarse

- **Un término con `vol` por debajo de ~10 no es fiable.** Trends devuelve 0 en las semanas por
  debajo de su umbral de publicación, y al promediar salen picos absurdos (631, 1150). Eso no es
  demanda: es dividir por casi cero. El script los separa en su propia lista.
- **Un 0 aislado en un mes con volumen alto** también es umbral, no ausencia de búsquedas.
- **Los términos largos casi siempre salen vacíos.** Trends solo publica lo que tiene volumen; la
  cola larga vive en la cuenta, no aquí.
- Mira **la forma**, no el número: ¿el pico cae en el mismo mes todos los años?

## Lo que salió en la prueba real (23-09-2026)

Servicio online de adicciones, sin ingreso. España, 5 años.

**Tendencia anual — lo que más importa:**

| término | 2021→2026 | ¿el servicio lo cumple? |
|---|---|---|
| terapia online | **+109 %** | sí |
| dejar el alcohol | +75 % | sí |
| psicólogo online | +69 % | sí |
| dejar de beber | +43 % | sí |
| alcoholismo | −21 % | sí, pero se hunde |
| alcohólicos anónimos | −46 % | sí, pero se hunde |
| ~~centro de adicciones~~ | ~~+199 %~~ | **NO: pide un sitio físico** |

Dos lecciones en una tabla:

1. **El lenguaje se movía**: bajaba lo que obliga a ponerse una etiqueta, subía lo que describe una
   acción o un formato. Eso iba a favor del cliente, que se posiciona para «quien no se reconoce como
   adicto» — y su cuenta pujaba justo los términos que se hundían.
2. **El término que más crecía era el único que no podía vender.** Sin `--excluir centro,clinica,
   ingreso`, el informe lo habría puesto como acción número uno.

**Estacionalidad mensual:** casi nula (±15 % en verano), mientras la cuenta oscilaba seis veces entre
su peor y su mejor mes. Los picos eran de gestión, no de demanda.

## Lo que no se puede hacer

- **Keyword Planner** da volumen mensual absoluto de los últimos 12 meses y sería mejor fuente, pero
  el MCP oficial de Google Ads solo hace consultas GAQL y no llega a ese servicio. Haría falta la
  librería de Python de Google Ads con el mismo OAuth.
- **La API oficial de Trends** existe desde julio de 2025, pero sigue en alpha por solicitud.
