# El plan de keywords cuando el cliente aún no tiene cuenta

Es el método original de la skill `keywords-google-ads` (antes de fusionarla con la estacionalidad),
para el único caso en que no hay datos propios: un cliente que quiere Google Ads y todavía no ha
pujado nunca. Se usa junto con los pasos 0, 2 y 3 del `SKILL.md`: el servicio, Trends y lo que se
busca en el sector sirven igual sin cuenta.

## Fuente

- **El brief** (`0. Onboarding` del Drive del cliente): oferta, avatares, dolores, servicio, zona,
  competencia. Y **la landing**, si ya existe, que manda sobre el brief.
- País e idioma del brief (por defecto España, español).
- Si falta un dato clave (servicios exactos, zonas), se pide; **no se inventan volúmenes ni datos
  de mercado**.

## Qué se produce

1. **Intención de búsqueda por avatar**: qué escribiría en Google cada perfil cuando está listo para
   contratar, no cuando curiosea. Intención transaccional («presupuesto reforma cocina madrid») antes
   que informacional («qué es una reforma»).
2. **Grupos de anuncios por intención**: cada grupo, un tema con su propio anuncio. No todo junto.
3. **Keywords por concordancia**: `[exacta]` para la intención más precisa; `"de frase"` para
   variaciones controladas; amplia solo si se justifica y con negativas fuertes.
4. **Negativas, lista para pegar**: genéricos, «gratis», «curso», «empleo», «cómo hacer», DIY, marcas
   ajenas, y todo lo que el servicio **no** ofrece (paso 0 del `SKILL.md`).
5. **Cola larga de alta intención**: menos volumen, más barata, cierra más.
6. **Tendencia de cada concepto** (`trends.py`) y **lo que se busca en el sector** (`descubrir.py`):
   con esto se decide qué grupo lleva más presupuesto de salida.
7. **Notas de estructura**: campañas, grupos, destino (la landing) y lo que falta del brief.

## Formato del documento

```
# Keywords Google Ads - <Cliente> - <mes año>

## Lo que hay que saber (tres líneas y el destino)
## Intención por avatar
## Hacia dónde va el mercado (tabla de trends.py)
## Estructura sugerida (campañas > grupos)
## Keywords por grupo
   | Keyword | Concordancia | Por qué |
## Negativas (una línea para pegar)
## Cola larga de alta intención
## Pendiente de confirmar con Dirección
## Lo que falta del brief
```

Se entrega en `6. Reportes` del Drive del cliente, como todo (ver «Entrega» en `SKILL.md`).

## Cuándo pasar al método completo

En cuanto la cuenta lleve **tres meses** con datos, se monta el Ads Script (`INSTALACION.md`) y las
siguientes revisiones se hacen con los términos reales. El plan desde el brief es una hipótesis
razonada; la cuenta es el dato.
