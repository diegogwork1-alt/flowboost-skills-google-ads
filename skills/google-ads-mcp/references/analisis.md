# Las cuatro métricas, los cruces y el informe

Las métricas 1, 2 y 4 salen de la serie diaria (**A3**, 90 días) y de la cuota de impresiones (**B1**);
la 3 sale de **D3**. Ninguna de las cuatro está en la interfaz de Google Ads: la interfaz da medias, y
la media esconde justo lo que hace falta para decidir si se escala.

---

## 1 · CPA marginal por tramo de presupuesto

**Qué responde**: si mañana subo el presupuesto, ¿a cuánto sale *la siguiente* conversión? El CPA medio
mezcla las conversiones baratas del principio con las caras del margen, y por eso escalar siempre
parece buena idea.

**Método**
1. Serie diaria de la campaña (A3), 90 días. Mínimo aceptable: 60. Con 30 o menos, «no calculable».
2. Descartar días con ruido conocido (web caída, festivo, cambio de puja o presupuesto ese día — K2 dice
   cuáles fueron).
3. Ordenar los días por gasto y partirlos en **tramos** (terciles o cuartiles), o usar los tramos
   naturales si hubo cambios de presupuesto.
4. Por tramo: **gasto medio por día** y **conversiones medias por día**.
5. **CPA marginal entre tramos** = (Coste medio/día del tramo alto − Coste medio/día del tramo bajo) /
   (Conversiones medias/día del tramo alto − Conversiones medias/día del tramo bajo).
   Las dos magnitudes van **por día**: restar totales de tramos con distinto número de días da basura.

**Trampa que hay que decir en el informe**: ordenar los días por gasto mezcla «más presupuesto» con
«días de más demanda» (lunes, campañas puntuales, estacionalidad). Es una **aproximación observacional,
no un experimento**. Cuando el tramo alto coincide con una temporada fuerte, se dice y se baja la
confianza de esa recomendación.

**Lectura**
- Marginal ≈ medio → escala linealmente: hay sitio.
- Marginal 30-50 % por encima del medio → rendimientos decrecientes; escalar solo si el margen aguanta.
- Marginal > 2× el medio, o conversiones planas con más gasto → **saturado**: más dinero no compra más
  negocio; el crecimiento sale de ranking, creatividad u otra campaña.

**Con Smart Bidding**, los 7 días posteriores a cada cambio de presupuesto no cuentan: el sistema
reaprende.

---

## 2 · Cuota de impresiones perdida, traducida a dinero y separada por causa

**Qué responde**: cuánto negocio se queda en la mesa y **por qué** — dinero o relevancia.

```
si search_impression_share viene vacío → «no calculable» para esa campaña (no se asume 0)

impresiones_disponibles = impressions / search_impression_share
perdidas_presupuesto    = impresiones_disponibles × search_budget_lost_impression_share
perdidas_ranking        = impresiones_disponibles × search_rank_lost_impression_share

CTR = clicks / impressions           (de B1, en FRACCIÓN: 0,043, no 4,3 %)
CVR = conversions / clicks           (de B1, en fracción; «tasa de conversión» y CVR son lo mismo)

leads_perdidos(causa)   = perdidas(causa) × CTR × CVR

euros_para_recuperarlos = leads_perdidos(PRESUPUESTO) × CPA_marginal
                          ← SOLO la parte de presupuesto. Ver abajo.
valor_perdido           = leads_perdidos × valor_por_lead
```

**Por qué los euros solo se calculan sobre la pérdida por presupuesto**: las impresiones perdidas por
ranking **no se compran a ningún precio**. Poner «X € para recuperarlas» al lado sería una cifra que el
cliente refuta en diez segundos. La pérdida por ranking se expresa en **leads perdidos y su causa**, y
la palanca es Quality Score, relevancia del anuncio (I1, I2) y landing — no presupuesto.

**Con porcentajes en vez de fracciones el resultado sale 10.000 veces mayor.** Comprobar siempre que
CTR y CVR están entre 0 y 1.

La proyección usa el CTR y la CVR actuales, y las impresiones nuevas suelen convertir algo peor: se
presenta como **rango** (por ejemplo −20 %/+0 %), nunca como cifra exacta.

---

## 3 · Curva de maduración de conversiones

**Qué responde**: cuántos días tarda un clic en convertirse en lead o venta, y por tanto cuándo se
puede juzgar un periodo. Sale de D3, acumulando los buckets a 1, 3, 7, 14 y 30 días.

- Fija la **ventana mínima de evaluación**: si el 40 % entra después del día 7, leer los últimos 7 días
  es leer una cuenta falsamente mala.
- Corrige el mes en curso: las conversiones del último tramo **todavía están entrando**.
- Ciclo largo (alto ticket, B2B) → Smart Bidding con la conversión final va ciego; tiene sentido
  optimizar a una conversión intermedia bien definida.

---

## 4 · Coste real del clic incremental

**ΔCoste medio/día / ΔClics medios/día** entre tramos, igual que la métrica 1. Si el CPC incremental
dobla al CPC medio, la subasta cobra caro cada clic extra: el problema es **Ad Rank**, no presupuesto, y
la palanca es Quality Score.

---

## Los cruces

### Ads × Search Console
1. Consultas en **top 3 orgánico** que además se pagan → probar bajada de puja y medir el total
   (orgánico + pago), no solo el de pago.
2. Consultas con impresiones y **posición 4-20** (quick wins, sección G) que **no** están en Ads → o
   contenido, o cubrirlas con Ads mientras el SEO madura.
3. Términos de Ads que **convierten** y no tienen página propia → encargo a `ai-seo` / `programmatic-seo`.
4. Recordar el desfase: GSC va 2-3 días por detrás y en hora del Pacífico.

### Ads × GA4
1. **Conversiones infladas**: acciones `primary_for_goal` que no son negocio (D1), contrastadas con los
   key events reales. Hasta que eso se arregle, el CPA de la cuenta es ficción.
2. **Discrepancia de atribución**: se mira la proporción, no el número.
3. **Calidad del tráfico de pago** frente a orgánico y directo: `engagementRate`, páginas por sesión,
   tasa de key event por canal. Tráfico caro que rebota = landing o promesa, no puja.
4. **Landings**: E4 (coste por landing) × GA4 (`landingPage`, `bounceRate`, key events) → la URL concreta
   que más dinero quema va como encargo a `informe-landing-clarity`.

### De dónde sale el dinero de verdad
De la hoja del cliente que mantiene `reportes-cliente`, no de una pregunta:

| Dato | Dónde está |
|---|---|
| Cierres de la semana | `Reporte Google`, columna **«Cierres (a mano)»** |
| Importe facturado | `Reporte Google`, columna **«Facturado (a mano)»** |
| Ticket medio | facturado ÷ cierres, **solo en las semanas que tienen los dos** (si no, una semana con cierres y sin importe hunde el ticket) |
| Fee de agencia | `'Reporte Meta'!$J$6` — 1.100 €, igual para todos |
| Coste total | inversión de la semana **+ la parte del fee**. El CPA máximo se mide contra esto, no contra la inversión sola |

`CPA máximo ≈ ticket medio × margen ÷ leads por cierre`. Si las dos columnas a mano están vacías, no
se inventa el ticket: se escribe en el informe que **la cuenta no sabe qué vale un lead**, y esa es la
primera acción del plan.

---

## El informe

```markdown
# Auditoría Google Ads — <Cliente> · <periodo> · <CÓDIGO DE MONEDA>
Cuenta: <customer_id> (<descriptive_name>) · MCC: <id> · GA4: <id> · GSC: <site>
Consultado el <fecha> · API v<versión> · Datos de GSC hasta <fecha real>

## 0. Veredicto
Una línea, una de estas cuatro:
**ESCALAR** (CPA marginal por debajo del CPA máximo y hay IS de presupuesto que comprar) ·
**ARREGLAR ANTES DE ESCALAR** (la fuga es ranking, o la señal de conversión está sucia) ·
**MANTENER** (saturada: más dinero no compra más negocio) ·
**APAGAR O REHACER** (CPA marginal por encima del máximo con IS alta).
Las nueve secciones siguientes son la prueba de esta línea, no su sustituto.

## 1. Foto del periodo
Gasto · clics · conversiones · CPA medio · valor/ROAS. Contra el periodo anterior.

## 2. ¿Esta cuenta escala? (CPA marginal)
Tabla de tramos → gasto/día, conv/día, CPA medio, CPA marginal. Y el CPA máximo rentable al lado.

## 3. Lo que se está dejando en la mesa (IS perdida)
Campaña · IS · perdida por presupuesto → leads → dinero para recuperarlos ·
perdida por ranking → leads (no comprables: palanca QS/relevancia).

## 4. Cuándo se puede leer esta cuenta (maduración)
% acumulado a 1/3/7/14/30 días → ventana mínima de evaluación.

## 5. Qué se está contando como conversión
Acciones principales, infladores a sacar, y si falta importación offline.

## 6. Relevancia y dinero quemado
Keywords con QS histórico ≤ 4 y gasto, con el componente culpable. Anuncios y activos LOW.

## 7. Términos basura
Familias a negativizar con su coste, comprobadas contra C3 **y C4** (listas compartidas).

## 8. Cruce con GA4 y con Search Console
Canibalización, huecos, calidad del tráfico, landings.

## 9. Acciones ordenadas por dinero al mes
| # | Acción | Por qué (métrica y cifra) | Impacto/mes | n | Confianza | Riesgo | Quién |
`n` = número de conversiones o clics en que se basa. Una recomendación con n=4 y otra con n=400
no pueden presentarse igual.

## 10. No calculable
Lo que no se pudo medir, el error literal que devolvió la herramienta, y qué haría falta.

## Anexo · Consultas
| id | herramienta | GAQL / parámetros literales | customer_id | rango | hora | filas |
Cada tabla del informe cita el id de la consulta que la produjo. Las filas crudas quedan en `datos/`.
Sin esto nadie puede reauditar una cifra ni defenderla delante del cliente.
```

Se guarda en `~/Desktop/CLIENTES/<Cliente>/Auditoria-Google-Ads-<AAAA-MM>.md`.

---

## Qué ve el cliente

La auditoría completa es **interna**. Al cliente le llega:
1. Las cifras que correspondan en su pestaña `Reporte Google` de la hoja de Drive (`reportes-cliente`).
2. Un resumen de **cinco líneas en español llano**: sin GAQL, sin «CPA marginal», sin siglas. Se dice
   «por cada euro extra que metamos este mes, el lead nos sale a X» y qué se va a hacer.
3. Lo que se le pide (presupuesto, decisión, material) en una sola frase.
Si Dirección quiere enseñarle el informe entero, se decide explícitamente; no se manda por defecto.

---

## Cuenta pequeña o nueva

Con menos de ~30 conversiones en el periodo, el CPA marginal no tiene señal. Carril alternativo, con lo
que sí se puede medir con poco dato:
- IS perdida por presupuesto (no necesita conversiones).
- CTR frente al histórico de la propia cuenta.
- Cobertura: keywords activas frente a términos reales que llegan (C2).
- Ad Strength y estado de aprobación (I1), QS histórico (C1).
- Velocidad de gasto: `campaign_budget.amount_micros` × días frente al `cost_micros` real.
- `primary_status_reasons` (K1): a veces la campaña simplemente no entrega.

Regla: por debajo de ese umbral **no se toca Smart Bidding ni se sube presupuesto**. Se arregla la señal
de conversión y la relevancia, y se vuelve a mirar cuando haya volumen.

---

## Cómo se trabaja

- **En paralelo**: un subagente por fuente (Ads / GA4 / GSC), con el contrato de entrada y salida que
  fija `SKILL.md` (tablas agregadas, máximo 40 filas, crudo en `datos/`). Nunca devuelven el volcado
  entero: la sesión se queda sin contexto antes del informe.
- **Aislamiento**: cada subagente recibe **solo** el `customer_id` de su cuenta. En modo cartera, ni una
  cifra de un cliente entra en el informe de otro, y no se suman monedas distintas.
- **Comparar contra la auditoría anterior**: qué se propuso, si se aplicó y qué pasó. Una auditoría sin
  seguimiento es un PDF bonito.

### `~/Desktop/CLIENTES/<Cliente>/contexto-google-ads.md`
Se crea en la primera auditoría y se actualiza en cada una:
```markdown
customer_id: 1234567890          # sin prefijo customers/ ni guiones
login_customer_id: 9876543210    # el MCC
moneda: EUR
propiedad_ga4: 123456789
propiedad_gsc: sc-domain:ejemplo.com
objetivo: lead cualificado (cierre por teléfono)
cpa_maximo: 85 EUR               # ticket medio × tasa de cierre × margen
valor_por_lead: 140 EUR          # de la hoja de reportes
conversiones_que_cuentan: [Formulario web, Llamada > 60s]
estrategia_puja: Maximizar conversiones con CPA objetivo
presupuestos_compartidos: no
ultima_auditoria: 2026-08
acciones_propuestas:
  - negativizar familia "gratis" → aplicada 2026-09-05 → CPA -12 %
```

## Prompt de arranque
> Audita <Cliente>. customer_id <10 dígitos>, MCC <id>, propiedad GA4 <id>, propiedad GSC <sc-domain:…>,
> periodo <AAAA-MM>, objetivo <lead/venta/llamada>, CPA máximo <importe y moneda>.
> Comprueba primero que la cuenta es la correcta. Saca las cuatro métricas (CPA marginal por tramo, IS
> perdida en dinero separada por causa, curva de maduración y coste del clic incremental), mira qué se
> tocó en la cuenta este mes, cruza con GA4 y Search Console, y cierra con el veredicto en una línea y
> las acciones ordenadas por dinero al mes.
