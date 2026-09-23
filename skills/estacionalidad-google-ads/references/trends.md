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
python3 scripts/trends.py "<URL del archivo de estacionalidad>" --marca "cliente" --top 9
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

Cuenta de servicios de adicciones, España, 9 términos, 5 años:

| término | vol | forma |
|---|---|---|
| dejar de beber alcohol | 492 | **plana**: 79-119 todo el año |
| como dejar el alcohol | 100 | variable, pero con poco volumen absoluto |
| los otros 7 | 3-6 | sin volumen publicable |

**El mercado no tiene estacionalidad.** Y esa misma cuenta mostraba en sus propios datos septiembre
a 177 y marzo a 28. Conclusión: **esos picos no son del mercado, son de la cuenta** — de cuánto se
invirtió cada mes y de cómo estaban las campañas. Sin Trends, el informe habría propuesto un
calendario estacional para un mercado que es plano.

Esa es exactamente la comprobación que justifica este paso.

## Lo que no se puede hacer

- **Keyword Planner** da volumen mensual absoluto de los últimos 12 meses y sería mejor fuente, pero
  el MCP oficial de Google Ads solo hace consultas GAQL y no llega a ese servicio. Haría falta la
  librería de Python de Google Ads con el mismo OAuth.
- **La API oficial de Trends** existe desde julio de 2025, pero sigue en alpha por solicitud.
