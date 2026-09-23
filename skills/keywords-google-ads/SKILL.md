---
name: keywords-google-ads
description: Genera un .md de investigación de keywords bien curradas para Google Ads (campañas de Búsqueda) a partir del brief del cliente. SOLO se ejecuta si el cliente quiere publicitar en Google Ads (condicional, no es parte del funnel estándar de Meta). Produce grupos de anuncios temáticos, keywords por tipo de concordancia, lista de negativas, e intención de búsqueda. Guarda en la carpeta interna del cliente en Drive. Usar cuando Dirección diga "el cliente quiere Google Ads", "armá las keywords", "keyword research para <cliente>".
---

# Keyword research para Google Ads (condicional)

Armás la investigación de keywords para campañas de **Búsqueda** de Google Ads, sacada del **brief** del cliente. Es un paso **opcional del funnel**: solo corre si el cliente decidió pautar en Google (el funnel estándar de Flowboost es Meta).

> **Alcance honesto:** esto genera el **plan de keywords** (el .md). NO crea las campañas en Google Ads: el MCP de Google Ads es de **solo lectura**, así que armar campañas sigue siendo manual — Dirección carga el plan o se lo pasamos al cliente/gestor.
>
> Lo que sí cambió (21-09-2026): **los datos reales de la cuenta ya se pueden leer** con la skill `google-ads-mcp` (términos de búsqueda que llegan de verdad, keywords con Quality Score, negativas que ya existen). Si el cliente ya tiene cuenta activa, el plan se contrasta con esos datos en vez de salir solo del brief.

## Fuente
- **El brief** (`0. Onboarding/Brief.md`): oferta, avatares, dolores, servicio, zona/país, competencia. De ahí sale todo.
- País/idioma del brief (por defecto España / español).
- Si el brief no alcanza para un dato clave (ej. servicios exactos o zonas), pedirlo; no inventar volúmenes ni datos de mercado.

## Qué produce el .md
1. **Intención de búsqueda por avatar:** qué escribiría en Google cada buyer persona cuando está listo para comprar (no "curioso").
2. **Grupos de anuncios temáticos** (ad groups): agrupar keywords por intención/servicio, no todo junto. Cada grupo = un tema con su propio anuncio.
3. **Keywords por tipo de concordancia:**
   - **Exacta** `[keyword]` — la intención más precisa y rentable.
   - **De frase** `"keyword"` — variaciones controladas.
   - **Amplia** solo si se justifica, y siempre con negativas fuertes.
   - Priorizar **intención transaccional/comercial** ("presupuesto reformas madrid", "abogado laboralista barcelona") sobre informacional ("qué es una reforma").
4. **Keywords negativas** (crítico para no quemar presupuesto): genéricos, "gratis", "curso", "empleo", "cómo hacer", DIY, marcas propias mal ubicadas, etc. Lista amplia adaptada al rubro.
5. **Long-tail de alta intención** (menos volumen, más barato, más cierra).
6. **Notas de estructura:** sugerencia de campañas/ad groups, y qué mandar como destino (la landing del cliente).

## Formato de salida
```
# Keywords Google Ads — <Cliente> · <fecha> · <país>

## Intención por avatar
- <avatar> → cómo busca cuando quiere comprar

## Estructura sugerida (campañas > grupos)
- Campaña Búsqueda — <servicio>
  - Grupo: <tema> → keywords + concordancias

## Keywords por grupo
### Grupo <tema>
| Keyword | Concordancia | Intención |

## Negativas (lista para pegar)
palabra1, palabra2, ...

## Long-tail de alta intención
- ...

## Notas
- destino (landing), presupuesto sugerido si el brief lo permite, qué falta.
```

## Entrega
- Guardar en `i_<Cliente>/2. Ads/keywords-google-ads-<fecha>.md`.
- Actualizar `ESTADO.md` ("Keywords Google Ads: hecho <fecha>").
- Avisar a Dirección (en el resumen si hay sesión; si no, `python3 ~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/avisar.py … --nivel info`) y listar lo que falte del brief para afinar.

## Qué NO hace
- No crea campañas en Google Ads (sin API todavía).
- No inventa volúmenes de búsqueda ni CPCs (si hiciera falta dato real de volumen, se valida con Keyword Planner del cliente; marcarlo, no inventar).
