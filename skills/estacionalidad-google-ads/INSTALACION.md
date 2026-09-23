# Estacionalidad de Google Ads, paso a paso

Esta guía deja lista la estacionalidad de un cliente: **en qué meses del año la gente busca lo que
vende, y cuánto presupuesto tiene que haber en cada mes.**

Se hace **una vez por cliente**. Lo único técnico es copiar y pegar un script en Google Ads; el resto
es mirar que salgan las cosas.

> Si usas Claude Code, puedes decirle: *«prepárame la estacionalidad de <cliente> siguiendo
> INSTALACION.md»*. Va paso a paso y comprueba cada uno.

**Tiempo:** 15 minutos tuyos + esperar a la mañana siguiente (o previsualizar y verlo al momento).

---

## Qué es cada cosa

| Pieza | Qué hace | Quién la toca |
|---|---|---|
| **El Ads Script** | Vive dentro de la cuenta de Google Ads del cliente. Cada mañana a las 6:00 escribe los datos en la hoja de Drive. | Se pega una vez y se olvida |
| **`datos-google`** | La pestaña de siempre: día × campaña. Alimenta el reporte que ve el cliente. | **No se toca nunca** |
| **`datos-google-terminos`** | NUEVA. Lo que la gente escribió de verdad en Google, mes a mes, 24 meses. | La crea el script sola |
| **`datos-google-is`** | NUEVA. Cuánto se perdió cada mes y **por qué**: por falta de presupuesto o por ranking. | La crea el script sola |
| **La skill** | Lee esas dos pestañas y saca el calendario de presupuesto. | Tú, pidiéndoselo a Claude |

## La cadena de uso

```
   El Ads Script                 La hoja del cliente              Las skills
   (en Google Ads)                  (en Drive)                  (en Claude Code)

   cada mañana 6:00  ──────►  datos-google          ──────►  reportes-cliente
                                (el reporte del cliente)        el cliente lo mira

                     ──────►  datos-google-terminos ──────►  estacionalidad-google-ads
                              datos-google-is                 ¿en qué meses hay que estar?

                                                      └────►  google-ads-mcp
                                                              ¿esta cuenta merece más dinero?
```

Las tres skills leen de la misma hoja. **Primero tiene que haber datos**: por eso el script va antes
que todo lo demás.

---

## 0 · Instalar las skills (una vez por ordenador)

```bash
git clone https://github.com/<usuario-github>/flowboost-skills-google-ads.git
cd flowboost-skills-google-ads
python3 instalar.py
```

Tiene que salir `✅ Claude Code: …/.claude/skills`.

## 1 · Abrir el script de la cuenta

En **Google Ads**, con la cuenta del cliente seleccionada:

**Herramientas** → **Acciones masivas** → **Scripts**

- Si ya hay un script (se llamará algo como «reporte» o «datos»), **ábrelo**: hay que sustituirlo.
- Si no hay ninguno, dale al **«+»** para crear uno.

## 2 · Pegar el script nuevo

Abre `scripts/ads-script-estacionalidad.js` (está dentro de esta misma skill), **cópialo entero** y
pégalo encima de lo que hubiera, borrando lo anterior.

Ahora cambia **solo estas dos líneas**, arriba del todo:

```javascript
var SHEET_URL = 'PEGA_AQUI_LA_URL_DE_LA_HOJA_DEL_CLIENTE';
var CLIENTE   = 'NOMBRE_DEL_CLIENTE';
```

- **`SHEET_URL`**: abre la hoja del cliente en Drive (se llama `Reporte Ads — <Cliente> — <año>`) y
  copia la URL entera de la barra del navegador.
- **`CLIENTE`**: el nombre tal y como aparece en el resto de la hoja. Si en `datos-google` pone
  `Cliente 13`, aquí va `Cliente 13` — con las mismas mayúsculas.

**No toques nada más.**

## 3 · Autorizar y previsualizar

1. Botón **«Autorizar»** (solo la primera vez). Entra con el Google que tiene **permiso de edición**
   sobre la hoja. Si no lo tiene, el script no podrá escribir.
2. Botón **«Previsualizar»**. Tarda entre 30 segundos y 2 minutos.
3. Mira el registro de abajo. Tiene que salir algo así:

```
Escritas 412 filas en datos-google
Escritas 1.284 filas en datos-google-terminos
Escritas 96 filas en datos-google-is
```

**Si sale «FALLÓ»** en alguna de las dos últimas, no pasa nada grave: el reporte del cliente se ha
escrito igual. Mira la tabla de abajo.

## 4 · Comprobar la hoja

Abre la hoja del cliente. Tienen que estar las dos pestañas nuevas:

- **`datos-google-terminos`** → una fila por término y mes. Mira la columna `mes`: tiene que haber
  varios meses distintos, no solo el actual.
- **`datos-google-is`** → una fila por campaña y mes, con `is_perdida_presupuesto` e
  `is_perdida_ranking`.

En las dos, la columna `actualizado` tiene que tener la fecha de hoy.

## 5 · Programarlo (si el script era nuevo)

**Frecuencia diaria, a las 06:00.** No antes: Google tarda hasta 3 horas después de medianoche en
cerrar las cifras del día.

Si sustituiste un script que ya estaba programado, la programación se mantiene: no hay que hacer nada.

## 6 · Pedir la estacionalidad

En Claude Code:

```
Hazme la estacionalidad de <Cliente>
```

Sale un documento en `~/Desktop/CLIENTES/<Cliente>/` con:

- **Temporada alta y baja** en tres líneas
- **El índice mes a mes** por familia de términos, calculado tres veces: cuándo *buscan*, cuándo
  *hacen clic* y cuándo *compran*. Cuando los tres no coinciden, ahí está lo interesante.
- **Dónde se está dejando dinero**: meses con mucha demanda y presupuesto corto
- **El calendario de presupuesto** de 12 meses, con la fecha en que hay que hacer cada cambio
- **Lo que no se puede saber con estos datos**, dicho claramente

---

## Si algo falla

| Lo que ves | Qué pasa | Qué hacer |
|---|---|---|
| `No existe la pestaña "datos-google"` | La hoja del cliente no está dada de alta para Google | Pedir que se ejecute `anadir_hoja_google.py` antes |
| `Términos por mes FALLÓ` | Casi siempre: el Google que autorizó no tiene permiso de edición en la hoja | Compartir la hoja con ese correo, con permiso de **Editor** |
| Las pestañas nuevas están vacías | La cuenta no tuvo clics en esos términos, o es muy nueva | Normal en cuentas recién abiertas. Esperar |
| Solo hay 2 o 3 meses distintos | La cuenta es nueva | La skill lo dirá y dará una **hipótesis**, no un plan. Es lo correcto |
| Se escribió en la pestaña equivocada | `CLIENTE` no coincide con el resto de la hoja | Corregir esa línea y previsualizar otra vez |

## Dos cosas que conviene saber

**Hacen falta 2 años para hablar de estacionalidad.** Con menos, no se puede distinguir «este mes es
bueno todos los años» de «la cuenta viene creciendo». Con 12 meses o menos, lo que sale es una
hipótesis y la skill lo dice así. Sirve igual, pero no se mueve el presupuesto del año entero con eso.

**Google Trends no se automatiza.** La skill lo usa solo al final y a mano, para 5 o 10 términos
dudosos. El motivo está en `references/trends.md`: Trends solo deja comparar 5 términos por consulta y
sus números son relativos a esa consulta, así que juntar muchas consultas produce cifras que parecen
datos y no lo son. La parte pesada —recoger los términos mes a mes— es justo lo que hace el script
solo, cada mañana.
