---
name: google-ads-mcp
description: Audita cuentas de Google Ads leyendo datos reales por MCP y cruzándolos con GA4 y Search Console. Saca las cuatro métricas que la interfaz no da - CPA marginal por tramo de presupuesto, cuota de impresiones perdida traducida a dinero y separada por presupuesto vs ranking, curva de maduración de conversiones y coste real del clic incremental - y cierra con un veredicto de una línea (escalar, arreglar antes de escalar, mantener o apagar) más acciones ordenadas por dinero al mes. Incluye el recetario GAQL y el barrido de cartera por MCC. SOLO LECTURA - los tres MCP leen, ninguno escribe; la skill entrega el plan y aplicarlo lo decide Dirección. Trae también el montaje de la conexión (proyecto de Google Cloud, OAuth, nivel de acceso de la API y los tres `claude mcp add`) en references/instalacion.md. Es el PASO SIGUIENTE a `reportes-cliente`: aquel da la contabilidad diaria en la hoja del cliente, esta la interpreta. Puede correr por MCP o, si la conexión no está montada, leyendo la pestaña `datos-google` de esa misma hoja. Usar cuando Dirección diga "audita la cuenta de Google Ads de <cliente>", "cómo va Google en <cliente>", "monta el MCP de Google Ads/GA4/Search Console", o pida cruzar Google Ads con Analytics o con Search Console. NO usar para Meta (eso es gestion-cuenta-meta) ni para planificar keywords desde el brief (eso es keywords-google-ads).
---

# Google Ads + GA4 + Search Console por MCP

Origen: vídeo de Fede (https://youtu.be/NDhMuxq9Tcg), indexado en el notebook de NotebookLM
**«NotebookLM MCP — integración y automatización»** (`33f8544e-4a7e-4b82-95dc-cbabf4cc0df3`).
Los comandos **no** salen del vídeo: están verificados contra los repos oficiales y la documentación
de Google. Auditada por consejo el 21-09-2026.

**Glosario** (una vez, para no repetirlo): **MCP** = el protocolo por el que Claude habla con una
herramienta externa · **MCC** = cuenta administradora de Google Ads, la que cuelga de la agencia ·
**GAQL** = el lenguaje de consulta de la API de Google Ads · **ADC** = credenciales por defecto de
aplicación, el fichero que deja `gcloud` tras el login · **IS** = *impression share*, cuota de
impresiones · **QS** = Quality Score, nivel de calidad de una keyword · **PMax** = Performance Max,
el tipo de campaña automática · **micros** = millonésimas: todo importe de la API va así.

> ## ⛔ El MCP no escribe — la skill propone
> Los tres servidores son de lectura. El oficial de Google Ads expone `customers_list_accessible_customers`,
> `search_search` (GAQL) y `metadata_get_resource_metadata`: ninguna modifica nada. No pausa campañas,
> no cambia pujas, no añade negativas. El vídeo insinúa que Claude aplica los cambios «aprobando uno a
> uno»: **con el MCP oficial eso no ocurre**. La skill entrega el plan cuantificado y, si Dirección lo pide,
> un Google Ads Script con vista previa para que **él** lo ejecute. Misma regla que `gestion-cuenta-meta`.

> ## 📐 Los números no se inventan
> Cada cifra del informe sale de una consulta ejecutada en esta sesión y queda registrada en el anexo
> con su id. Si algo no se puede calcular —faltan datos, la cuenta no tiene volumen, PMax no da IS, el
> MCP devolvió error— se escribe **«no calculable»** y por qué. Un hueco nunca se rellena de memoria
> ni con otra consulta parecida.

---

## De dónde salen los datos: dos vías

Esta skill es el **paso siguiente a `reportes-cliente`**. Aquella deja cada mañana, a las 6:00, la
contabilidad de Google en la hoja del cliente; esta dice si esos números son buenos y qué hacer.
Por eso puede trabajar de dos maneras:

| | **Vía MCP** (completa) | **Vía hoja** (sin montar nada) |
|---|---|---|
| Fuente | los tres conectores | pestaña `datos-google` de la hoja del cliente |
| Qué alcanza | las 10 secciones del informe | secciones 1, 2, 4 y parte de la 3 |
| Cuándo usarla | conexión montada y verificada | **hoy mismo**, en Cliente 01, Cliente 13 y Cliente 03 |

**Lo que `datos-google` ya trae** (lo escribe el Ads Script, una fila por día y campaña):
fecha · campaña · coste · impresiones · clics · CTR · CPC medio · conversiones · valor de conversión
· **cuota de impresiones**. Eso es exactamente la consulta **A3** y buena parte de **B1**: con ella
salen el **CPA marginal**, el **coste del clic incremental** y la foto del periodo, con 200+ filas
de histórico real por cliente.

**Lo que le falta**: el desglose de la IS por causa. El Ads Script trae
`metrics.search_impression_share` pero no `search_budget_lost_impression_share` ni
`search_rank_lost_impression_share`, así que por la vía hoja **no se puede separar la pérdida
comprable de la que no lo es** y la sección 3 sale a medias. Se arregla añadiendo esos dos campos a
la consulta de `~/Desktop/SCRIPTS-GOOGLE-ADS/<cliente>.js` y dos columnas a la hoja (tocando las
**tres** listas, como avisa `reportes-cliente`).

**El CPA máximo rentable y el valor por lead no se preguntan: se leen de la hoja.**
Pestaña `Reporte Google`, columnas **«Cierres (a mano)»** y **«Facturado (a mano)»** — el ticket
medio sale de dividir una por otra en las semanas que tienen las dos. Y el CPA máximo se mide
contra el **coste total** (inversión + la parte del fee, `'Reporte Meta'!$J$6`), igual que el ROAS
de esa hoja, nunca contra la inversión sola. Si las columnas están vacías, eso **es** un hallazgo
del informe: la cuenta no sabe qué vale un lead.

## Antes de auditar (puerta, 30 segundos)

1. `claude mcp list` → los tres en `✓ Connected`. Si no, `references/instalacion.md`.
2. Lanzar **A1** (identidad de la cuenta) y **parar si `customer.descriptive_name` no coincide con el
   cliente que pidió Dirección**. Un dígito mal en el `customer_id` y se audita la cuenta de otro cliente.
3. Anotar `customer.currency_code`. Si no es EUR, todo el informe va en esa moneda, con su código.

El montaje completo (proyecto de Cloud, OAuth, nivel de acceso, los `claude mcp add`) está en
`references/instalacion.md` y se lee **una vez en la vida**, no en cada auditoría.
Desde el **09-09-2026 no hay developer token**: el nivel de acceso lo da el proyecto de Google Cloud
y **Explorer**, que basta para leer cuentas de producción, se concede prácticamente al solicitarlo.
Ya no hay ningún paso que bloquee tres días.

---

## Auditar una cuenta

### Paso 0 · Contexto
Del fichero `~/Desktop/CLIENTES/<Cliente>/contexto-google-ads.md` (plantilla en `references/analisis.md`).
Lo que hace falta sí o sí:
- `customer_id` de 10 dígitos **sin el prefijo** `customers/` y sin guiones · `login_customer_id` del MCC.
- Propiedad de GA4 y propiedad de Search Console.
- Objetivo real: lead cualificado, venta o llamada.
- **CPA máximo rentable**, calculado desde las columnas a mano de `Reporte Google` (ver arriba), no
  preguntado. Sin este número el CPA marginal es un dato huérfano y **no hay veredicto de escalado**.
- Periodo: **mes natural cerrado anterior** para la foto. La **serie diaria (A3) se pide siempre a 90
  días**, porque el CPA marginal y el CPC incremental necesitan 60 como mínimo.
- Search Console va **2-3 días retrasado** y reporta en hora del Pacífico: no auditar GSC antes del día 4.

### Paso 1 · Batería de consultas
Todo el GAQL está en `references/gaql.md`, en este orden:
**A** cuenta y campañas → **K** estado real de entrega y cambios recientes → **B** cuota de impresiones
→ **J** pujas y presupuestos → **C** keywords, QS y términos → **D** conversiones y maduración →
**I** anuncios y activos → **H** PMax → **E** dispositivo, hora, geografía y landings → **F** GA4 → **G** GSC.

**K va antes que el diagnóstico**: auditar una cuenta sin saber qué se tocó es atribuirle a la subasta
lo que hizo una persona.

**Reparto en subagentes** cuando hay más de una fuente. Contrato fijo, no «ya se apañarán»:
- **Entrada**: `{customer_id, login_customer_id, periodo, moneda, lista de consultas por id}`.
- **Salida**: ruta a un `.md` en el scratchpad con **tablas ya agregadas** (máximo 40 filas), 10 líneas
  de resumen, y las filas crudas en `datos/`. Nunca devuelven el volcado entero: la sesión se queda sin
  contexto antes del informe.
- Uno por fuente (Ads / GA4 / GSC). En modo cartera, uno por cuenta.

### Paso 2 · Las cuatro métricas
Fórmulas, unidades y trampas en `references/analisis.md`. Resumen:
1. **CPA marginal por tramo de presupuesto** — cuánto cuesta *la siguiente* conversión, no la media.
2. **IS perdida traducida a dinero, separada por causa** — presupuesto se compra, ranking se gana.
   Los euros de «recuperarlo» solo se calculan sobre la parte de **presupuesto**.
3. **Curva de maduración** — cuántos días tarda un clic en convertir, y por tanto cuándo se puede leer
   la cuenta.
4. **Coste real del clic incremental** — si dobla al CPC medio, el problema es Ad Rank, no presupuesto.

### Paso 3 · Los cruces
- **Ads × GSC**: canibalización (pagas lo que ya rankeas en top 3), huecos (posición 4-20 sin cubrir),
  términos que convierten y no tienen contenido → encargo a `ai-seo` / `programmatic-seo`.
- **Ads × GA4**: conversiones infladas (acciones principales que no son negocio), discrepancia de
  atribución, calidad del tráfico de pago, landings caras que rebotan → encargo a `informe-landing-clarity`.
- **Términos basura**: familias completas a negativizar, no palabra a palabra → entrada de `keywords-google-ads`.
- **Activos con `performance_label = LOW`** → encargo a `fundamentos-copy` para reescribir titulares.
- **Valor por lead**: sale de la pestaña `Reporte Google` de la hoja del cliente (`reportes-cliente`),
  donde ya están los cierres y el facturado. No se pregunta si no hace falta.

### Paso 4 · Informe
Formato en `references/analisis.md`. Abre con el **veredicto en una línea** —escalar, arreglar antes de
escalar, mantener o apagar— y las diez secciones son la prueba de esa línea, no su sustituto. Cierra con
acciones ordenadas por dinero al mes, cada una con su `n` y su nivel de confianza: una recomendación
sacada de 4 conversiones y otra de 400 no pueden parecer iguales.
Se guarda en `~/Desktop/CLIENTES/<Cliente>/Auditoria-Google-Ads-<AAAA-MM>.md`.

### Paso 5 · Aplicar
No se aplica desde aquí. Cuando Dirección decida ejecutar:
- **Una palanca cada vez.** Dos cambios a la vez y no se sabe cuál funcionó.
- **Piloto primero** en una campaña, no en toda la cuenta.
- **Foto del estado previo** guardada (la consulta que lo prueba, con fecha) para poder deshacer.
- **Ventana de evaluación ≥ la curva de maduración** antes de juzgar el resultado.
- Con Smart Bidding, los **7 días siguientes al cambio no cuentan**: el sistema reaprende.

---

## Modo cartera (varias cuentas del MCC)
Con `customer_client` (consulta K3) se listan las cuentas hijas. Por cada una: gasto del mes en curso
vs mes anterior, CPA vs CPA máximo del contexto, e IS perdida por presupuesto. Un subagente por cuenta,
una sola tabla de salida, semáforo por cuenta.
**Nunca se mezclan monedas distintas en la misma suma**, y cada subagente recibe **solo** el
`customer_id` de su cuenta: nada de un cliente entra en el informe de otro.

## Cuando la cuenta es pequeña o nueva
Con menos de ~30 conversiones en el periodo no hay señal para el CPA marginal: se dice y se pasa al
carril de bajo volumen (IS perdida por presupuesto, CTR, cobertura de keywords frente a términos reales,
Ad Strength, QS, velocidad de gasto). Por debajo de ese umbral **no se toca Smart Bidding ni se sube
presupuesto**: se arreglan señal de conversión y relevancia.

## Si algo falla
Error del MCP, cuota agotada, cuenta vacía o campo desconocido: el error **literal** va a la sección
«No calculable» del informe y la sección que dependía de él se marca «sin datos». No se sustituye por
otra consulta ni por una estimación. Si el error es `UNRECOGNIZED_FIELD`, comprobar el campo con
`metadata_get_resource_metadata` antes de reescribir nada: la API versiona y rompe campos cada año.

---

## Errores que ya se han cometido
- **Escribir esta skill con la doctrina del developer token** (21-09-2026). Google lo retiró el
  **09-09-2026** y el nivel de acceso pasó al proyecto de Cloud; la primera versión mandaba esperar
  2-3 días por un token que ya no existe. Lo que dicta un vídeo de hace meses se verifica contra la
  documentación **con fecha**, siempre.
- **Dar por buenos los comandos que dicta una IA sobre un vídeo.** NotebookLM reconstruyó paquetes npm
  inexistentes. Y el README de `mcp-server-gsc` documenta parámetros que su propio código no acepta:
  manda el código, no el README.
- **Leer IS en Performance Max**: no existe. Para PMax van las consultas de la sección H.
- **Comparar CPA de Ads con key events de GA4** como si midieran lo mismo. Tendencias, no valores.
- **Proponer negativas que ya existen**: hay que mirar también las listas compartidas (C4).
- **Usar `ad_group_criterion.quality_info` para un periodo pasado**: eso es el QS de hoy. Para la serie
  histórica van las métricas `metrics.historical_*`.
