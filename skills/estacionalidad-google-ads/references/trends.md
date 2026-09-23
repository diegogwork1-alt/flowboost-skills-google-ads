# Google Trends: cómo usarlo sin sacar conclusiones falsas

Comprobado el 22-09-2026.

## Las dos trampas

**1. Máximo 5 términos por consulta, y los valores son RELATIVOS a esa consulta.**
El 100 no significa «100.000 búsquedas»: significa «el punto más alto de estos términos, en este
periodo, en esta zona». Dos consultas distintas **no se pueden comparar entre sí**. Si en una
consulta «caldera» marca 80 y en otra «aire acondicionado» marca 80, eso **no** quiere decir que se
busquen igual.

**La solución es un término ancla**: se elige uno (el más estable y con volumen), se mete en **todas**
las consultas, y después se reescala todo dividiendo por el valor del ancla en cada una. Sin ancla,
comparar lotes es inventarse los datos.

**2. No hay forma fiable de automatizarlo en bloque.**

| Vía | Estado hoy |
|---|---|
| **API oficial de Google Trends** | Existe desde julio de 2025, pero sigue en **alpha por solicitud**. Hay gente esperando respuesta meses. Cuando entra, resuelve el problema: da datos «consistentemente escalados» y 5 años de histórico. Merece la pena solicitarla. |
| **`pytrends`** | **Archivado en abril de 2025**, sin mantenimiento. Se rompe con cada cambio interno de Google y devuelve `429 Too Many Requests` en cuanto se le pide volumen. No usar en nada que tenga que funcionar solo. |
| **Forks** (`pytrends-modern`, `trendspyg`) | Vivos, pero siguen siendo scraping de un endpoint que Google no se compromete a mantener. |
| **APIs de pago** (SerpApi, Glimpse y similares) | Funcionan y se pagan por consulta. Tienen sentido si esto se convierte en rutina para toda la cartera. |

**Conclusión práctica**: para 5-10 términos dudosos, se hace **a mano** en `trends.google.com` en diez
minutos y se acabó. Montar automatización frágil para eso es perder el tiempo, y peor: produce
números que parecen datos.

## Cómo hacerlo a mano, bien

1. `trends.google.com` → escribe el término.
2. **País: España** (o el del cliente). Sin esto estás mirando otro mercado.
3. **Periodo: «Últimos 5 años»**. Es lo que responde la pregunta de verdad: ¿se repite todos los años?
4. Añade hasta 4 términos más para comparar, **siempre con el mismo término ancla**.
5. Mira **la forma**, no el número: ¿el pico cae siempre en el mismo mes? ¿es un pico o una meseta?
6. Baja a «Consultas relacionadas → En aumento»: ahí salen términos nuevos que aún no están en la
   cuenta, y a veces es lo más valioso de toda la visita.

Lo que se apunta en el informe por cada término: **en qué mes pica, si se repite los 5 años, y si la
tendencia general sube o baja**. Nada más. Los números de Trends no entran en el cálculo del índice:
ese sale de los datos de la cuenta.

## La alternativa mejor, si algún día hace falta automatizar

**Keyword Planner de Google Ads**, método `GenerateKeywordHistoricalMetrics` de la API. Le pasas una
lista de keywords de golpe, con país e idioma, y devuelve el **volumen de búsqueda mensual absoluto
de los últimos 12 meses** por keyword. Sin límite de 5, sin valores relativos, sin scraping.

Dos avisos:
- Solo llega a **12 meses**. Para «¿qué pasó hace 3 años?» sigue haciendo falta Trends.
- **El MCP de Google Ads no llega ahí**: ese solo hace consultas GAQL, y el Keyword Planner es otro
  servicio. Haría falta la librería de Python de Google Ads con el mismo OAuth.
