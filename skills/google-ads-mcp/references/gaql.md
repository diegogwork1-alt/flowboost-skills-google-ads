# Recetario — GAQL (Ads), run_report (GA4), search_analytics (GSC)

> **Versión**: escrito contra la API de Google Ads **v25 (09-2026)**. La API rompe campos cada año: si
> una consulta devuelve `UNRECOGNIZED_FIELD`, comprobar el campo con `metadata_get_resource_metadata`
> **antes** de reescribirla a ojo.
> **Micros**: todo importe viene en millonésimas. `cost_micros / 1.000.000 = unidad monetaria`.
> **Moneda**: la de A1, no «euros» por defecto.
> **PMax**: no da cuota de impresiones ni términos de búsqueda. Para PMax, sección **H**.

Se pegan en la herramienta `search_search` del MCP de Ads. Sustituir `AAAA-MM-DD` por el periodo;
alternativa: `DURING LAST_30_DAYS`.

---

## A · Cuenta y campañas

**A1. Identidad, moneda y huso** — obligatoria, y es la puerta: si `descriptive_name` no es el cliente
que pidió Dirección, se para aquí.
```sql
SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone
FROM customer
```

**A2. Campañas del periodo, ordenadas por gasto**
```sql
SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type,
       campaign_budget.amount_micros,
       metrics.impressions, metrics.clicks, metrics.ctr, metrics.average_cpc,
       metrics.cost_micros, metrics.conversions, metrics.conversions_value
FROM campaign
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND metrics.impressions > 0
ORDER BY metrics.cost_micros DESC
```
Para la **comparación con el periodo anterior** que exige el informe, se lanza **dos veces** (mes
cerrado y mes anterior) y se construye la tabla de deltas. No hay atajo.

**A3. Serie diaria — siempre a 90 días** (materia prima del CPA marginal y del CPC incremental)
```sql
SELECT segments.date, campaign.name,
       metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.conversions
FROM campaign
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
ORDER BY segments.date
```
**Sin `LIMIT`**: recortarla descarta días y falsea el tramo alto de gasto. Si el volumen es grande, se
vuelca a fichero en el scratchpad y se agrega con un script, no se trunca.

---

## B · Cuota de impresiones (solo Búsqueda y Shopping)

**B1. IS y sus dos fugas**
```sql
SELECT campaign.name,
       metrics.search_impression_share,
       metrics.search_budget_lost_impression_share,
       metrics.search_rank_lost_impression_share,
       metrics.search_absolute_top_impression_share,
       metrics.impressions, metrics.clicks, metrics.ctr,
       metrics.conversions, metrics.cost_micros
FROM campaign
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND campaign.advertising_channel_type = 'SEARCH'
```
Las tres cuotas suman ~1. Si `search_impression_share` **no viene** (la API lo omite cuando no hay
volumen suficiente, no devuelve 0), esa campaña se marca «no calculable»: dividir por un campo vacío
revienta el cálculo de la sección 3 del informe.

**B2. IS a nivel de grupo** — para saber *dónde* duele el ranking
```sql
SELECT campaign.name, ad_group.name,
       metrics.search_impression_share, metrics.search_rank_lost_impression_share,
       metrics.impressions, metrics.cost_micros, metrics.conversions
FROM ad_group
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND metrics.impressions > 0
```

---

## C · Keywords, Quality Score y términos de búsqueda

**C1. Keywords con QS histórico y actual**
```sql
SELECT campaign.name, ad_group.name,
       ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
       metrics.historical_quality_score,
       metrics.historical_creative_quality_score,
       metrics.historical_landing_page_quality_score,
       metrics.historical_search_predicted_ctr,
       ad_group_criterion.quality_info.quality_score,
       metrics.impressions, metrics.clicks, metrics.ctr,
       metrics.cost_micros, metrics.conversions
FROM keyword_view
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND metrics.impressions > 0
ORDER BY metrics.cost_micros DESC
LIMIT 300
```
Las `metrics.historical_*` son **la serie del periodo**: son las que valen para decir «esta keyword
quemó dinero el mes pasado». `ad_group_criterion.quality_info.*` (`quality_score`,
`creative_quality_score`, `post_click_quality_score`, `search_predicted_ctr`) es el **estado de hoy**:
sirve para decidir qué arreglar ahora, no para auditar un mes cerrado.
Los componentes dicen **qué** arreglar: creativo bajo → el anuncio no habla de la keyword; landing page
bajo → la página; CTR previsto bajo → la keyword no es relevante para esa búsqueda.

**C2. Términos de búsqueda reales** — de aquí salen las familias a negativizar
```sql
SELECT search_term_view.search_term, search_term_view.status,
       campaign.name, ad_group.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM search_term_view
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND metrics.clicks > 0
ORDER BY metrics.cost_micros DESC
LIMIT 500
```
Se agrupa por **familia** (token común: «gratis», «curso», «empleo», «cómo», marcas ajenas), se suma el
coste de la familia y se negativiza entera. Palabra a palabra no se acaba nunca.

**C3. Negativas propias de campaña**
```sql
SELECT campaign.name, campaign_criterion.keyword.text, campaign_criterion.keyword.match_type
FROM campaign_criterion
WHERE campaign_criterion.negative = TRUE
  AND campaign_criterion.type = 'KEYWORD'
```

**C4. Negativas en listas compartidas** — sin esto se proponen negativas que ya existen
```sql
SELECT shared_set.id, shared_set.name, shared_set.type, shared_criterion.keyword.text,
       shared_criterion.keyword.match_type
FROM shared_criterion
```
```sql
SELECT campaign.name, campaign_shared_set.shared_set, campaign_shared_set.status
FROM campaign_shared_set
```

---

## D · Conversiones: qué se cuenta y cuándo entra

**D1. Inventario de acciones de conversión y su configuración**
```sql
SELECT conversion_action.id, conversion_action.name, conversion_action.category,
       conversion_action.type, conversion_action.status,
       conversion_action.primary_for_goal, conversion_action.counting_type,
       conversion_action.click_through_lookback_window_days,
       conversion_action.view_through_lookback_window_days,
       conversion_action.include_in_conversions_metric
FROM conversion_action
```
`primary_for_goal = TRUE` es lo que entra en la columna «Conversiones» y lo que optimiza Smart Bidding.
Aquí aparecen los **infladores** (suscripciones, clics a teléfono sin llamada, vistas de página): si el
objetivo es lead cualificado y hay tres acciones principales, el CPA de la cuenta es ficción.
**El problema contrario, en lead-gen telefónico**: si no hay ninguna acción de tipo `UPLOAD_CLICKS` /
`UPLOAD_CALLS` y el negocio cierra por teléfono, la cuenta **no sabe qué lead vale**: está optimizando
a «rellenó formulario». La acción es montar la importación offline, que es justo lo que ya recoge el
CRM de `montar-crm-cliente`.

**D2. Conversiones por acción**
```sql
SELECT segments.conversion_action_name, campaign.name,
       metrics.all_conversions, metrics.all_conversions_value, metrics.conversions
FROM campaign
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
ORDER BY metrics.all_conversions DESC
```

**D3. Curva de maduración (lag)**
```sql
SELECT segments.conversion_lag_bucket, metrics.conversions
FROM campaign
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
```
`segments.conversion_lag_bucket` **solo combina con métricas de conversión**: si se le añade
`metrics.clicks`, `metrics.impressions` o `metrics.cost_micros`, falla o vuelve vacía. El resultado son
buckets (`LESS_THAN_ONE_DAY`, `ONE_TO_TWO_DAYS`, …) que se acumulan para saber qué porcentaje del
periodo ya está cerrado.

**D4. Llamadas** (si el cliente cierra por teléfono)
```sql
SELECT campaign.name, metrics.phone_calls, metrics.phone_impressions,
       metrics.phone_through_rate, metrics.cost_micros
FROM campaign
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
```

---

## E · Dónde, cuándo y a quién

**E1. Dispositivo**
```sql
SELECT campaign.name, segments.device,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM campaign
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
```

**E2. Día de la semana y hora**
```sql
SELECT campaign.name, segments.day_of_week, segments.hour,
       metrics.clicks, metrics.cost_micros, metrics.conversions
FROM campaign
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
```

**E3. Geografía** — devuelve **IDs numéricos**, no nombres
```sql
SELECT campaign.name, geographic_view.country_criterion_id,
       metrics.clicks, metrics.cost_micros, metrics.conversions
FROM geographic_view
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
```
Para traducirlos (2724 = España):
```sql
SELECT geo_target_constant.id, geo_target_constant.name, geo_target_constant.country_code
FROM geo_target_constant
WHERE geo_target_constant.id IN (2724, 2840)
```

**E4. Landings que se llevan el dinero**
```sql
SELECT landing_page_view.unexpanded_final_url,
       metrics.clicks, metrics.cost_micros, metrics.conversions
FROM landing_page_view
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
ORDER BY metrics.cost_micros DESC
```

**E5. Audiencias y demográficos** — donde están los ajustes de puja fáciles en lead-gen
```sql
SELECT campaign.name, ad_group.name, ad_group_criterion.type,
       ad_group_criterion.user_list.user_list, ad_group_criterion.bid_modifier,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM ad_group_audience_view
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND metrics.impressions > 0
```
Lo mismo con `age_range_view` y `gender_view`. Regla: ajustar puja donde el CPA del segmento se desvía
más de un 30 % de la media **y** hay al menos 15 conversiones en ese segmento.

---

## H · Performance Max

**H1. Grupos de activos**
```sql
SELECT campaign.id, campaign.name, asset_group.id, asset_group.name,
       asset_group.status, asset_group.ad_strength,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM asset_group
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
ORDER BY metrics.cost_micros DESC
```

**H2. Categorías de búsqueda** — el sustituto de los términos de búsqueda en PMax
```sql
SELECT campaign_search_term_insight.id, campaign_search_term_insight.category_label,
       metrics.impressions, metrics.clicks, metrics.conversions
FROM campaign_search_term_insight
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND campaign_search_term_insight.campaign_id = 'ID_DE_LA_CAMPAÑA'
ORDER BY metrics.impressions DESC
```
Este recurso **no admite campos de `campaign`**: la campaña se filtra por `campaign_id` en el `WHERE`,
una consulta por campaña.

---

## I · Anuncios y activos

**I1. Anuncios, fuerza y estado de aprobación** — un RSA con Ad Strength pobre es causa nº1 de IS
perdida por ranking
```sql
SELECT campaign.name, ad_group.name, ad_group_ad.ad.id, ad_group_ad.ad.type,
       ad_group_ad.status, ad_group_ad.ad_strength,
       ad_group_ad.policy_summary.approval_status,
       metrics.impressions, metrics.clicks, metrics.ctr,
       metrics.cost_micros, metrics.conversions
FROM ad_group_ad
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND metrics.impressions > 0
ORDER BY metrics.cost_micros DESC
```

**I2. Qué titular concreto rinde y cuál no**
```sql
SELECT campaign.name, ad_group.name, asset.id, asset.text_asset.text,
       ad_group_ad_asset_view.field_type, ad_group_ad_asset_view.performance_label,
       metrics.impressions, metrics.clicks, metrics.conversions
FROM ad_group_ad_asset_view
WHERE segments.date BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'
  AND metrics.impressions > 0
```
Los activos con `performance_label = LOW` **se reescriben** (encargo a `fundamentos-copy`), no se miran.

---

## J · Pujas y presupuestos — antes de recomendar «sube el presupuesto»

```sql
SELECT campaign.name, campaign.status, campaign.bidding_strategy_type,
       campaign.maximize_conversions.target_cpa_micros,
       campaign.maximize_conversion_value.target_roas,
       campaign_budget.id, campaign_budget.name, campaign_budget.amount_micros,
       campaign_budget.explicitly_shared, campaign_budget.delivery_method
FROM campaign
WHERE campaign.status = 'ENABLED'
```
Si `explicitly_shared = TRUE`, la recomendación va **al presupuesto, no a la campaña**, y hay que
listar todas las campañas que cuelgan de él: subir un presupuesto compartido reparte el dinero en
campañas que no lo pedían.

---

## K · Estado real, cambios y cartera

**K1. Campañas activas que no entregan** — A2 filtra `impressions > 0` y estas serían invisibles
```sql
SELECT campaign.id, campaign.name, campaign.status,
       campaign.primary_status, campaign.primary_status_reasons,
       campaign.start_date, campaign.end_date,
       metrics.impressions, metrics.cost_micros, metrics.conversions
FROM campaign
WHERE campaign.status = 'ENABLED'
```
`primary_status_reasons` da el diagnóstico gratis: presupuesto limitado, puja demasiado baja, anuncios
rechazados.

**K2. Qué se tocó en la cuenta y quién lo tocó**
```sql
SELECT change_event.change_date_time, change_event.user_email,
       change_event.change_resource_type, change_event.client_type,
       change_event.resource_change_operation, change_event.changed_fields,
       change_event.campaign, change_event.ad_group
FROM change_event
WHERE change_event.change_date_time DURING LAST_30_DAYS
ORDER BY change_event.change_date_time DESC
LIMIT 1000
```
La API **obliga** a filtrar por fecha (máximo 30 días hacia atrás) y a poner `LIMIT` (tope 10.000).
Sin esta consulta, la regla de «los 7 días tras un cambio no cuentan» es incomprobable.

**K3. Cuentas hijas del MCC** (lanzada contra el `customer_id` del MCC)
```sql
SELECT customer_client.client_customer, customer_client.id,
       customer_client.descriptive_name, customer_client.currency_code,
       customer_client.manager, customer_client.status
FROM customer_client
WHERE customer_client.manager = FALSE
  AND customer_client.status = 'ENABLED'
```

**K4. Recomendaciones de Google** — gratis, y conviene llevarlas contestadas antes de que el cliente
las vea en la interfaz
```sql
SELECT recommendation.type, recommendation.campaign,
       recommendation.impact.base_metrics.conversions,
       recommendation.impact.potential_metrics.impressions,
       recommendation.impact.potential_metrics.clicks,
       recommendation.impact.potential_metrics.cost_micros,
       recommendation.impact.potential_metrics.conversions
FROM recommendation
```
Se listan, se traducen a dinero y **se dice cuáles se rechazan y por qué** (típicamente «aplicar
concordancia amplia» y «optimizar a maximizar clics»).

---

## F · GA4 (`run_report`)

Identificar la propiedad con `get_account_summaries` y confirmar el vínculo con Ads mediante
`list_google_ads_links`: **sin vínculo no hay cruce posible**, y eso se dice en el informe.

- **Canales de adquisición**: dimensión `sessionDefaultChannelGroup`; métricas `sessions`, `totalUsers`,
  `keyEvents`, `engagementRate`. (En propiedades antiguas, `conversions` en vez de `keyEvents`.)
- **Campañas de pago**: `sessionCampaignName` + `sessionSource` / `sessionMedium`.
- **Landings**: `landingPage` + `sessions`, `bounceRate`, `keyEvents`.
- **Embudo**: `run_funnel_report` con los pasos reales del sitio (vista → formulario → gracias). Si el
  servidor no lo acepta, se hace a mano con `run_report` paso por paso.
- **Antes de pedir un evento personalizado**: `get_custom_dimensions_and_metrics`. Si no está declarado,
  no existe.

**Conversiones de Ads ≠ key events de GA4**: distinta atribución y distinta ventana. Se comparan
**tendencias y proporciones**, nunca cifras absolutas. Y el huso de la propiedad puede no ser el de la
cuenta de Ads (A1): si difieren, se dice.

## G · Search Console

```json
{ "siteUrl": "sc-domain:ejemplo.com",
  "startDate": "AAAA-MM-DD", "endDate": "AAAA-MM-DD",
  "dimensions": "query,page", "rowLimit": 1000 }
```
- `dimensions` es una **cadena separada por comas**, nunca una lista JSON: un array rompe la validación.
- `sc-domain:ejemplo.com` para propiedad de dominio; `https://ejemplo.com/` para prefijo de URL.
- `rowLimit` por defecto 1000, máximo 25.000. Subirlo solo si hace falta de verdad.
- **Quick wins**: `enhanced_search_analytics` con `"enableQuickWins": true` (y `quickWinsThresholds`
  opcional), o la herramienta dedicada `detect_quick_wins` (`minImpressions`, `maxCtr`,
  `positionRangeMin`, `positionRangeMax`). **No** existe `detectQuickWins`, aunque el README lo diga.
- **Los datos van 2-3 días retrasados y el reporte es en hora del Pacífico**: no cruzar GSC con Ads
  antes del día 4 del mes siguiente, y decir en el informe que los periodos no son idénticos.
- Cruce con C2: consulta en top 3 orgánico **y** pagada en Ads → candidata a bajar puja y medir si el
  total (orgánico + pago) se mantiene.
