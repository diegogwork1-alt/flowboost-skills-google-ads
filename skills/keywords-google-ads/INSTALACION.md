# Montar el Ads Script en una cuenta, paso a paso

Es lo único que hay que hacer **una vez por cliente** para que la skill `keywords-google-ads` tenga
datos. Después, el script corre solo cada mañana.

> Si usas Claude Code: *«monta el script de estacionalidad de \<Cliente\>»* y te va guiando.

**Tiempo:** 15 minutos tuyos. **Necesitas:** acceso a la cuenta de Google Ads del cliente y la URL de
su hoja de reportes (`Reporte Ads — <Cliente> — <año>`, en su Drive).

## Qué es cada cosa

| Pieza | Qué es | Quién la toca |
|---|---|---|
| **El Ads Script** | Un programa dentro de Google Ads. Cada mañana a las 06:00 escribe en dos archivos de Drive. | Se pega una vez |
| **La hoja de reportes** (pestaña `datos-google`) | Lo que ve el cliente. Ya existía. | **No se toca** |
| **«Estacionalidad - \<Cliente\>»** | Archivo **aparte e interno**, con las pestañas `terminos-mes` (qué escribió la gente en Google, mes a mes, 24 meses) e `is-mes` (cuánto se perdió cada mes y por qué). | Lo crea el script solo |
| **La skill** | Lee ese archivo y Google Trends, y saca el plan de keywords. | Tú, pidiéndoselo a Claude |

```
  Google Ads --(script, 06:00)-->  hoja de reportes            -->  reportes-cliente (lo ve el cliente)
                              -->  Estacionalidad - Cliente   -->  keywords-google-ads (interno)
```

**Importante:** el archivo «Estacionalidad - \<Cliente\>» se crea en el Drive del Google que
**autoriza** el script. Ese Google tiene que ser el mismo con el que está configurado rclone en
**tu** Mac (lo ves con `rclone config show gdrive`: el correo aparece en el token), o hay que
compartirle el archivo después. Cada persona del equipo tiene su propio rclone: el archivo se
comparte con el Google de quien vaya a pedir las keywords. Si no, la skill no podrá leerlo.

## 1 · Generar el script del cliente

No se pega la plantilla cruda: lleva caracteres que el editor de Google Ads rompe y un bloque de
ejemplo con otros clientes. Se genera:

```bash
python3 ~/.claude/skills/keywords-google-ads/scripts/generar_script_cliente.py \
  "<Cliente>" "<URL de la hoja de reportes>" ~/Desktop/CLIENTES/<Cliente>/google-ads/ads-script.js
```

O a Claude: *«genera el script de \<Cliente\> con la hoja \<URL\>»*. Sale un `.js` ya relleno.

## 2 · Pegarlo en Google Ads

En Google Ads, con la cuenta del cliente seleccionada, menú de la izquierda:

**Herramientas → Acciones en bloque → Secuencias de comandos** *(en inglés: Tools → Bulk actions → Scripts)*

- Si ya hay un script (se llamará «reporte», «datos» o parecido): **ábrelo**, borra todo su contenido
  y pega el nuevo encima. El nuevo hace lo mismo que el viejo **y además** la estacionalidad.
- Si no hay ninguno: botón **«+»**.

Ponle nombre (por ejemplo «Datos + estacionalidad») y **Guardar**.

## 3 · Autorizar y previsualizar

1. **Autorizar** (solo la primera vez): entra con el Google que tiene **permiso de edición** sobre la
   hoja de reportes y que sea **el mismo de tu rclone** (o compartes el archivo después, paso 5).
2. **Vista previa** (según la versión pone «Previsualizar»). Tarda entre 30 segundos y 2 minutos.
3. Cuando ponga «Hecho», pestaña **Registros**. En la primera pasada tiene que salir esto:

```
Escritas 183 filas en datos-google
============================================================
CREADO el archivo de estacionalidad de <Cliente>.
Pega esta URL en SHEET_URL_ESTACIONAL y guarda el script:
https://docs.google.com/spreadsheets/d/XXXXXXXX/edit
============================================================
Escritas 5750 filas en terminos-mes
Escritas 95 filas en is-mes
```

La pestaña **Cambios** dirá «Sin cambios»: es correcto, el script no toca nada de la cuenta.

## 4 · Guardar la URL del archivo nuevo — no te lo saltes

Copia esa URL, súbela al principio del script donde pone `var SHEET_URL_ESTACIONAL = '';`, pégala
entre las comillas y **Guardar**. Si no lo haces, cada pasada crea un archivo nuevo.

(Si ya tienes varios archivos «Estacionalidad - \<Cliente\>» porque pasó, quédate con el más reciente
que tenga las dos pestañas, pon su URL, y borra los demás.)

Alternativa: vuelve a generar el script del paso 1 con `--estacional "<esa URL>"` y pégalo otra vez.

## 5 · Comprobar el archivo

Abre la URL. Dos pestañas:
- `terminos-mes`: una fila por término, mes y grupo. En `mes` tiene que haber varios meses.
- `is-mes`: una fila por campaña y mes, con `is_perdida_presupuesto` e `is_perdida_ranking`.
En las dos, `actualizado` con la fecha de hoy.

Si lo autorizó un Google distinto al de tu rclone, **compártelo ahora** (con ver basta) con el
Google de rclone de cada persona que vaya a pedir las keywords de este cliente.

**Este archivo es interno.** Miles de términos de búsqueda: no se comparte con el cliente. La hoja
de reportes no cambia en nada.

## 6 · Programarlo

Si el script era nuevo: **Frecuencia diaria, 06:00**. No antes: Google cierra las cifras hasta 3 h
después de medianoche. Si sustituiste uno programado, la programación se mantiene.

## 7 · Anota la URL para la skill

Claude la guardará en `~/Desktop/CLIENTES/<Cliente>/google-ads/contexto.json` en cuanto le pidas las
keywords (paso 0 de `SKILL.md`). Tenla a mano.

## Si algo falla

| Lo que ves | Qué pasa | Qué hacer |
|---|---|---|
| `No existe la pestaña "datos-google"` | La hoja del cliente no está dada de alta para Google | Pedir a Claude que corra `anadir_hoja_google.py` (skill `reportes-cliente`) |
| `Invalid or unexpected token (line 1)` | Se pegó la plantilla cruda | Generar el script (paso 1) y pegar ese |
| `Términos por mes FALLÓ` o `IS por mes FALLÓ` | Lo más común: el Google que autorizó no puede crear archivos en su Drive, o la cuenta no tiene campañas de Búsqueda | Leer el error entero en Registros; si dice permisos, autorizar con otro Google |
| Las pestañas nuevas están vacías | La cuenta es muy nueva o no tuvo clics | Normal; esperar |
| Salen pocos meses | La cuenta es nueva | La skill entregará una hipótesis, no un patrón. Es lo correcto |
| Se creó otro archivo nuevo | No se guardó la URL en `SHEET_URL_ESTACIONAL` | Paso 4 |
| La skill dice que rclone no baja el archivo | El Google que autorizó no es el de rclone | Compartir el archivo con el Google de tu rclone (con ver basta) |

## Dos cosas que conviene saber

**Hacen falta 2 años completos para hablar de estacionalidad.** Con menos no se distingue «este mes
es bueno todos los años» de «la cuenta viene creciendo». La skill lo dice sola.

**Google Trends lo consulta Claude solo**, sin navegador, con `trends.py` y `descubrir.py`. No hay
que abrir trends.google.com para nada. El detalle está en `references/trends.md`.
