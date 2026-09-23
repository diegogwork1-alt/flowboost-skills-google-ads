---
name: estacionalidad-google-ads
description: Averigua en qué meses del año la gente busca de verdad lo que vende el cliente, y convierte eso en un calendario de presupuesto para Google Ads. Parte de los términos de búsqueda REALES de la cuenta mes a mes (pestaña `datos-google-terminos` de la hoja del cliente, que escribe sola el Ads Script cada mañana), calcula el índice de estacionalidad por familia de términos, lo cruza con la cuota de impresiones perdida por falta de presupuesto (`datos-google-is`) para encontrar los meses en los que se está dejando dinero sobre la mesa, y solo al final usa Google Trends para confirmar si un patrón es de verdad estacional o fue un año raro. Entrega un calendario de 12 meses con qué subir, cuándo y cuánto, más los términos que se adelantan o se retrasan respecto al resto. Usar cuando alguien diga "estacionalidad de <cliente>", "en qué meses invertimos más", "cuándo sube la demanda", "calendario de presupuesto", "por qué bajó/subió este mes", o pregunte si conviene adelantar campañas antes de temporada. NO usar para decidir si la cuenta escala en general (eso es google-ads-mcp) ni para planificar keywords nuevas desde el brief (eso es keywords-google-ads).
---

# Estacionalidad de Google Ads: en qué meses hay que estar

La pregunta que responde: **¿en qué meses del año la gente busca esto, y estamos poniendo el dinero
cuando toca?**

La mayoría de las cuentas reparten el presupuesto plano todo el año. Si la demanda no es plana —y casi
nunca lo es— eso significa dos errores a la vez: se pierde volumen en los meses buenos y se quema
dinero en los flojos.

> ## 📐 El dato propio manda sobre Google Trends
> Trends dice cuándo busca **el mercado entero**. La cuenta dice cuándo busca **quien acaba
> comprándole a este cliente**, en su zona y con su oferta. Cuando los dos se contradicen, gana la
> cuenta. Trends entra al final, y solo para una cosa: saber si el patrón se repite años atrás o fue
> una casualidad de este año.

> ## ⛔ Solo lectura
> Esta skill lee hojas y propone un calendario. **No toca la cuenta de Google Ads**: subir o bajar un
> presupuesto lo hace una persona, a mano, después de aprobarlo.

---

## Lo que hace falta antes de empezar

Un archivo **aparte del reporte del cliente**, llamado «Estacionalidad — <Cliente>», con dos pestañas:

| Pestaña | Qué trae | Quién la escribe |
|---|---|---|
| `terminos-mes` | término de búsqueda × mes: impresiones, clics, coste, conversiones | el Ads Script, cada mañana |
| `is-mes` | campaña × mes: cuota de impresiones y **por qué** se pierde | el Ads Script, cada mañana |

**Por qué en otro archivo y no en el del reporte**: el de reportes lo abre el cliente, y miles de
filas de términos ahí son ruido; además, regenerar esa hoja borra las pestañas que no son de la
plantilla. Este archivo es **interno**: no se comparte con el cliente.

El Ads Script lo crea solo la primera vez y escribe su URL en el registro. Si no está:
- Mira la columna `actualizado`: si tiene fecha de hoy, el script corrió bien.
- Si la pestaña no existe, el script de esa cuenta todavía es el viejo. Hay que actualizarlo
  (está en `~/Desktop/SCRIPTS-GOOGLE-ADS/<cliente>.js`) y darle a *Previsualizar* en Google Ads.

**Cuánto histórico hace falta**: el script guarda **24 meses**. Con menos de **2 años** no se puede
separar *estacionalidad* de *tendencia* — una cuenta que crece todos los meses parece tener «temporada
alta» en diciembre solo porque es el mes más reciente. Con 12 meses o menos se dice claramente:
**«esto es una foto, no un patrón»**, y se usa como hipótesis, no como plan.

---

## Paso 0.5 · Bajar los datos y lanzar el cálculo

No se abre la hoja a mano ni se copian celdas. Un comando lo hace todo:

```bash
python3 ~/.claude/skills/estacionalidad-google-ads/scripts/estacionalidad.py \
  "<URL o id de la hoja del cliente>" \
  --marca "nombre del cliente,variantes de su marca"
```

Baja la hoja entera con **rclone** (el conector de Drive no vale: solo exporta la primera pestaña),
lee `datos-google-terminos` y `datos-google-is`, y saca los índices, la cuota perdida por causa y las
familias. Opciones: `--familias familias.json` para agrupar con criterio propio, `--top N`,
`--remoto otro:` si el remoto de rclone no se llama `gdrive:`.

**`--marca` no es opcional en la práctica.** Ver abajo por qué.

## Paso 1 · Agrupar en familias, no términos sueltos

Un término suelto («reparar caldera urgente madrid») tiene pocos datos y mucho ruido. Se agrupa por
**familia**: el trozo común que define la intención.

- familia «urgencias» → todo lo que lleve *urgente*, *avería*, *no funciona*, *ahora*
- familia «mantenimiento» → *revisión*, *mantenimiento*, *contrato*, *anual*
- familia «instalación» → *instalar*, *cambiar*, *presupuesto*, *nueva*

Las familias salen de mirar los términos reales, no de una lista inventada. Un término puede estar en
una sola familia: si encaja en dos, manda la palabra que indica **urgencia o dinero**.

Por familia y por mes se suman: impresiones, clics, conversiones y coste.

## Paso 2 · El índice de estacionalidad

Para cada familia:

```
índice del mes = (media de ese mes en los años disponibles ÷ media de TODOS los meses) × 100
```

- **100** = un mes del montón.
- **140** = ese mes tiene un 40 % más de demanda que la media.
- **60** = un 40 % menos.

Se calcula **tres veces**, con tres magnitudes distintas, y hay que mirar las tres:

| Con qué | Qué te dice |
|---|---|
| **impresiones** | cuándo **busca** la gente (demanda pura) |
| **clics** | cuándo **hace caso** al anuncio |
| **conversiones** | cuándo **compra** — el único que manda para mover dinero |

**Cuando no coinciden, ahí está el hallazgo.** Un mes con muchas impresiones y pocas conversiones es
gente mirando, no comprando: no merece más presupuesto, merece otro mensaje. El caso contrario —pocas
búsquedas pero altísima conversión— suele ser el mes más rentable del año y casi nadie lo ve.

**Aviso que hay que escribir siempre en el informe**: las impresiones dependen del presupuesto que se
puso ese mes. Si en julio se gastó la mitad, julio parecerá flojo aunque la demanda estuviera intacta.
Por eso existe el paso 3.

## Paso 3 · Cruzar con lo que se dejó escapar

De `datos-google-is`, por mes:
- **IS perdida por presupuesto** → había demanda y **no se pagó**. Esto se compra con dinero.
- **IS perdida por ranking** → había demanda y no se ganó la subasta. Esto **no se arregla con
  presupuesto**: es relevancia, calidad del anuncio y landing.

El cruce que vale oro:

> **mes con índice de conversión alto + IS perdida por presupuesto alta = el mes donde se está
> dejando dinero sobre la mesa.** Ahí es donde sube el presupuesto, y con números para defenderlo.

Y el contrario: mes con índice bajo y IS perdida alta **por ranking** → no es un problema de
temporada, es un problema de cuenta, y subir presupuesto no lo arregla.

## Paso 4 · Google Trends, solo al final y solo para lo dudoso

Entra únicamente cuando: (a) hay menos de 2 años de datos, (b) un mes se dispara y no se sabe si fue
real o una campaña puntual, o (c) se quiere entrar en términos que **nunca** se han pujado.

Cómo hacerlo sin sacar conclusiones falsas está en `references/trends.md`. Resumen: **no se puede
automatizar en bloque de forma fiable** y hay dos trampas serias (máximo 5 términos por consulta, y
valores relativos que no son comparables entre consultas). Para 5-10 términos dudosos se hace a mano
en 10 minutos y sale mejor.

## Paso 5 · El calendario

```markdown
# Estacionalidad — <Cliente> · <meses de histórico> · <moneda>

## El resumen en tres líneas
Temporada alta: <meses>. Temporada baja: <meses>.
Lo que hay que cambiar: <la acción principal>.
Lo que esto vale: <dinero al mes o al año, con su cálculo>.

## Índice por familia y mes
| Familia | E | F | M | A | M | J | J | A | S | O | N | D |
(uno por magnitud: impresiones, clics y conversiones)

## Dónde se está dejando dinero
| Mes | Índice conv. | IS perdida presupuesto | Leads que se escapan | Dinero |

## Los que se adelantan
Familias cuyo pico llega antes que el del resto: son la señal de que la temporada arranca.
Si «presupuesto» sube en febrero y «instalación» en abril, hay que estar en febrero.

## Calendario de presupuesto
| Mes | Presupuesto actual | Propuesto | Por qué | Cuándo se cambia |
Los cambios se hacen **2-3 semanas ANTES** del mes bueno: Smart Bidding necesita aprender,
y los 7 días siguientes a tocar el presupuesto no cuentan.

## Lo que no se puede decir con estos datos
```

Se guarda en `~/Desktop/CLIENTES/<Cliente>/Estacionalidad-Google-Ads-<AAAA-MM>.md`.

---

## Errores que cuestan dinero
- **No separar la marca.** Quien busca al cliente por su nombre **ya lo conocía**: eso no es demanda
  de mercado, es notoriedad. Medido en una cuenta real (22-09-2026): 74 filas de marca sobre 5.750
  movían el pico de octubre de **120 a 394**. Sin separarla, el calendario manda el dinero al mes
  equivocado. Siempre `--marca`.
- **Confundir tendencia con temporada.** Una cuenta que creció todo el año tiene los últimos meses
  altos por crecimiento, no por estación. Con 2 años se ve; con 1 no.
- **Leer las impresiones sin mirar el presupuesto de ese mes.** Un mes sin dinero parece un mes sin
  demanda. Siempre al lado de la IS perdida.
- **Subir el presupuesto el día 1 del mes bueno.** Llega tarde: 2-3 semanas antes.
- **Decidir con una familia de 3 conversiones.** Sin un mínimo de volumen no hay patrón, hay ruido.
  Se dice y se deja fuera.
- **Tomarse Google Trends como un volumen.** No lo es: es un índice relativo de 0 a 100 dentro de esa
  consulta concreta.
- **Meter esto en la hoja del cliente.** El reporte lo abre él; los términos de búsqueda son
  material interno, y regenerar esa hoja se llevaría las pestañas por delante. Archivo aparte.
