---
name: reportes-cliente
description: Los REPORTES DE RESULTADOS que ve el cliente, en su hoja de cálculo del Drive: **Meta Ads y Google Ads**, cada uno en su pestaña del MISMO archivo (`Reporte Meta` y `Reporte Google`), por semana y por mes, con coste por lead y ROAS. Se actualizan solas cada mañana —Meta a las 8:00 desde n8n, Google a las 6:00 desde un script de Google Ads—. **NO se manda ningún correo**: el envío por email está RETIRADO por decisión de Dirección (10-09-2026); el cliente entra a su hoja cuando quiere. El ROAS sale de las DOS casillas que se rellenan a mano cada semana —**cuántos cerraron** y **cuánto facturaron**, de donde se deduce solo el ticket medio— y se mide contra el **coste total** (la inversión más la parte del fee de agencia que toca a esa semana), no contra la inversión sola; en los clientes que tengan CRM conectado (hoy casi ninguno) el facturado puede venir de la pestaña `ventas` con importes reales, que comparten los dos reportes. Cubre también la hoja maestra que alimenta Looker Studio y el alta de un cliente en el sistema de reportes. El paso SIGUIENTE a esta skill es `google-ads-mcp`, que lee `datos-google` y las columnas a mano de esta misma hoja para decir si la cuenta merece más dinero. Usar cuando Dirección pida "el reporte de <cliente>", quiera dar de alta un cliente en las hojas, añadir Google Ads a un cliente, cambiar columnas, fórmulas o colores, montar Looker Studio, o revisar por qué una hoja no se actualizó.
---

# Los reportes del cliente: Meta Ads y Google Ads en su hoja del Drive

> ## ⛔ EL CORREO ESTÁ RETIRADO — decisión de Dirección, 10-09-2026
> **No se manda ningún email de reporte a nadie.** Ni al cliente, ni a Dirección, ni de prueba.
> El flujo `reporteSemanalMeta01` se queda **desactivado para siempre**; no se activa "para probar".
> Lo único vivo es el **volcado diario a las 8:00** que actualiza las hojas de cálculo.
>
> La plantilla del correo (`templates/reporte.html`) y su generador (`scripts/generar_reporte.py`)
> se conservan **solo para mirar los números en local**. Nunca para enviarlos.

**Lo que hay, entonces, es esto:** cada cliente tiene su hoja de cálculo en su carpeta de reportes del
Drive, y esa hoja se actualiza sola **todas las mañanas a las 8:00 (Europe/Madrid)**. El cliente entra
cuando quiere y ve sus números. No hay envío, no hay disparador semanal, no hay nadie a quien avisar.

## La semana a medias YA enseña sus datos (Dirección, 10-09-2026)
No hay que esperar a que se cierren los 7 días de una fila. **La fila de la semana en curso se va
rellenando cada mañana** con los días que ya hay.

Funciona así por cómo están escritas las fórmulas, y **no hay que "arreglarlo"**:
- Cada fila de semana es un `SUMPRODUCT` sobre la pestaña `datos` que suma **las filas cuya fecha cae
  dentro del rango**. Si del 8 al 14 solo existen el 8, el 9 y el 10, suma esos tres y ya está: no
  espera, no bloquea, no deja la fila en blanco.
- El volcado diario reescribe **los últimos 7 días**, no solo el de ayer, porque Meta sigue atribuyendo
  conversiones días después del clic. La clave `id` (`fecha|campaña`) hace que los días ya escritos se
  **corrijan**, no se dupliquen. Es decir: la semana en curso no solo crece, también **se corrige sola**.
- Los días que todavía no han pasado sencillamente no existen en `datos` y no suman nada.

⚠️ **Ojo con leerla a media semana:** una fila incompleta es una fila incompleta. El coste por lead de
un martes no es el coste por lead de la semana. Para decidir, se mira la semana cerrada o el TOTAL del
mes; la fila en curso es para ver por dónde va, no para sacar conclusiones.

## Qué enseñan las hojas
**Dos pestañas que mira el cliente**, una por fuente, con una fila por semana y un total por mes:

| Pestaña | Columnas |
|---|---|
| **`Reporte Meta`** | Inversión · Impresiones · CTR · Clics en el enlace · Clientes potenciales · Coste por lead · Coste por clic · **Cierres (a mano)** · **% de cierre** · **Facturado (a mano)** · **Coste total** · ROAS · ROAS mínimo |
| **`Reporte Google`** | **no son las mismas, a propósito**: Google no da alcance, ni frecuencia, ni vistas de landing (eso es el píxel). A cambio da la **cuota de impresiones** |

- El coste por lead se muestra **—** cuando no hubo leads (nunca "€0,00" ni "∞"). Igual el resto de
  columnas sin dato.
- **Las campañas con gasto 0 no molestan**: no suman nada y no ocupan fila propia, porque la hoja va
  por semana, no por campaña.

## Dónde está cada cosa
| Pieza | Dónde |
|---|---|
| **Flujo del volcado diario (LO ÚNICO VIVO)** | VPS, `reporteDiarioMetaSheets01` (8:00 Europe/Madrid) · copia en `n8n/datos-diarios-meta.json` |
| ~~Flujo del correo semanal~~ | **RETIRADO** (10-09-2026). `reporteSemanalMeta01` queda desactivado; la copia en `n8n/reporte-semanal-meta.json` se guarda solo como histórico |
| **Plantilla HTML** | `templates/reporte.html` — **solo para mirar en local**, no se envía |
| **Generador local** | `scripts/generar_reporte.py datos.json salida.html` — abre el HTML y lo miras tú |
| ~~Credencial de correo~~ | ya no se usa: no hay envío |
| **Credencial de hojas** | `Google Sheets account` (`jeOsaDPqbHEhZNw4`) |
| **Alta de un cliente (todo de una vez)** | `Estandar-carpetas/alta_reportes.py` |
| **Solo la hoja del cliente** | `Estandar-carpetas/crear_hoja_cliente.py` |
| **Añadir Google Ads a un cliente** | `Estandar-carpetas/anadir_hoja_google.py "<Cliente>"` |
| **Recolorear una hoja ya creada** | `Estandar-carpetas/recolorear_reportes.py --todos` |
| **Hoja maestra** | `Flowboost · Datos Meta` → `<ID_DRIVE>` |

## ⛔ QUÉ FALTA PARA QUE FUNCIONE (está INACTIVO a propósito)
**Falta el token de Meta.** Es el bloqueo que el funnel arrastra desde hace tiempo (etapa 16).
1. Crear un **token de sistema de larga duración** con permiso `ads_read` sobre el Business Manager.
2. Meterlo en el VPS como variable de entorno del contenedor: `META_TOKEN` — el flujo ya lo lee con
   `{{ $env.META_TOKEN }}`, así que **no queda escrito dentro del flujo**.
   ```bash
   # en /root/stack/docker-compose.yml, servicio n8n:  environment: - META_TOKEN=EAAG...
   docker compose up -d n8n
   ```
3. **Dar de alta a los clientes** en la pestaña `clientes` de la hoja maestra (`alta_reportes.py`):
   basta con `ad_account_id` y `sheet_id`. El correo de destino y el diccionario `objetivos` ya **no
   hacen falta**: eran del email, y el email está retirado.
4. **Importar en n8n** la copia de `n8n/datos-diarios-meta.json`, que ya lleva dentro el ID de la
   maestra en sus tres nodos de Sheets. *(Ese JSON no tiene `versionId`, lo que apunta a que el flujo
   todavía no está importado en el VPS: mirar si `reporteDiarioMetaSheets01` aparece en n8n; si no,
   hay que importarlo, no solo activarlo.)*
5. Ejecutarlo a mano una vez, mirar que la hoja del cliente se rellena, y **recién ahí activarlo**.
   Se activa SOLO el diario.
6. **La API de Sheets está deshabilitada** en el proyecto del token de rclone (403 `SERVICE_DISABLED`,
   proyecto `202264815644`, que es el client_id compartido de rclone). Por eso **`alta_reportes.py` no
   funciona de punta a punta**: todo lo que escribe con `sheets.googleapis.com` falla.

   **Se esquiva** montando el libro con openpyxl y subiéndolo a Drive **con conversión** — lo mismo que
   ya hace `montar_hoja_reportes.py`. Así se creó la maestra el 10-09-2026:
   `Flowboost · Datos Meta` → `<ID_DRIVE>`, con sus cuatro pestañas
   y compartida con la cuenta de servicio de n8n. **Ya no es un bloqueo**; lo sigue siendo solo para
   `alta_reportes.py` tal cual está escrito. Arreglarlo de raíz pide un **client_id propio de Google**
   para el remoto `gdrive`, con Drive **y** Sheets habilitadas (y de paso quita el aviso de que el
   client_id compartido de rclone se retira durante 2026).

## Añadir o quitar un cliente
Se edita **solo la pestaña `clientes` de la hoja maestra** — no se abre n8n. Para quitarlo, `activo` a
`no`: el flujo diario lo salta y su hoja se queda como estaba.

## Lo que este reporte NO dice, y hay que tenerlo presente
Es un reporte **descriptivo**: cuánto se gastó y cuántos leads entraron. **No** lleva diagnóstico ni
decisiones. Y ahora, además, **nadie recibe un aviso**: si nadie abre la hoja, nadie se entera. Tres avisos:
- **El coste por lead que muestra es BRUTO.** Con un 40 % de leads cualificados, el coste real es
  **2,5×** (`../gestion-cuenta-meta/references/parametros-campana.md` §1). Al cliente se le enseña el bruto
  porque es lo que él entiende; **internamente nunca se decide con ese número**.
- **Una campaña con gasto y cero leads sale igual en el reporte.** El reporte informa, no actúa: quien
  decide pausarla es `gestion-cuenta-meta` con la regla del §11-ter. *(En el ejemplo real de Cliente 06
  había dos campañas con 104 € gastados y cero leads.)*
- **Ya no hay correo que empuje a mirar los números.** Antes el viernes llegaba un email y eso obligaba
  a mirar. Ahora la hoja se actualiza en silencio: quien tiene que mirarla es `gestion-cuenta-meta` en
  la revisión semanal. Si esa revisión no se hace, una campaña puede quemar presupuesto sin que salte
  nada. **Esto es consecuencia de retirar el correo, y hay que tenerlo presente.**

## Volcado DIARIO a la hoja de cada cliente — ES TODO EL SISTEMA
Decisión de Dirección (07-09-2026, y desde el 10-09-2026 es lo único que queda): **cada cliente tiene su
propia hoja de cálculo**, actualizada **todas las mañanas a las 8:00 hora de España**.

Sigue siendo su propio flujo (`datos-diarios-meta`, copia en `n8n/datos-diarios-meta.json`). Nació
separado del semanal porque eran cadencias distintas; ahora, retirado el correo, **es el único que se
activa**.

| Qué | Cómo |
|---|---|
| Cuándo | Disparador diario 08:00, zona horaria `Europe/Madrid` |
| Qué pide a Meta | `time_increment=1`, nivel campaña → **una fila por día y campaña** |
| Ventana | Los **últimos 7 días**, no solo ayer |
| Dónde escribe | La hoja del cliente **y** la hoja maestra, en paralelo |

**Por qué reescribe 7 días y no añade solo el de ayer:** Meta sigue atribuyendo conversiones días después
del clic, así que el dato de ayer no es definitivo. Cada fila lleva una columna `id` (`fecha|campaña`) y el
nodo usa `appendOrUpdate` contra esa columna: los días ya escritos se **corrigen**, no se duplican.

### El número de la carpeta NO es fijo
Puede ser `5.`, `6.` o `7.` según el cliente, porque las carpetas anteriores no son iguales en todos
(Cliente 02 real tiene `5. Closer` + `6. Reportes`; el de test tiene `5. Reportes／Informes`). Se
resuelve **por nombre** con `Estandar-carpetas/carpeta_reportes.py`, que ignora el número, las tildes
y las variantes (`Reporting`, `Reportes／Informes`). **Nunca se escribe «6. Reportes» a pelo.**

## Las DOS hojas de cada cliente
| Hoja | Qué lleva | Quién la escribe | ¿Se puede regenerar? |
|---|---|---|---|
| **Reporte Ads — \<Cliente\> — \<año\>** | los números de Meta y de Google, por semana y mes | n8n cada mañana + lo que se escribe **a mano** (cierres, ticket, margen) | **NO a la ligera**: regenerar borra lo escrito a mano. `montar_hoja_reportes.py` se niega y hay que forzarlo con `--rehacer` |
| **Estado de cuenta — \<Cliente\>** ⚠️ **solo en clientes NUEVOS** | en qué punto del proceso está, con desplegable por etapa | el agente al cerrar cada etapa | **NO**: regenerarla borra lo marcado. `montar_hoja_estado.py` no la toca si ya existe (`--rehacer` para forzarlo) |

> ### La hoja de estado NO va en cuentas que ya están en marcha (Dirección, 10-09-2026)
> El «Estado de cuenta» sirve para **montar** un cliente: dice en qué punto del proceso va.
> En una cuenta que ya lleva meses funcionando no aporta nada y estorba — Dirección borró la de
> Cliente 03 por eso: *«no es un set-up, esto ya es cliente y hay que mejorar cosas»*.
> **Se crea solo cuando el cliente entra nuevo.** Para los que ya están: solo la hoja de reportes.>
> **Cómo se evita:** `alta_reportes.py "<Cliente>" --en-marcha`. Con ese flag no se crea.
> Para los que entran nuevos, sin flag, se crea como siempre.

## El fee de agencia entra en el ROAS (Dirección, 10-09-2026)

**El ROAS NO se calcula sobre la inversión publicitaria, sino sobre el COSTE TOTAL**: lo que el
cliente paga de anuncios **más lo que paga a Flowboost**. Si no, el número miente: un cliente que
gasta 400 € en Meta no está invirtiendo 400 €, está invirtiendo 1.500 €.

| Celda / columna | Qué es |
|---|---|
| **Fee de agencia al mes** (`J6` de `Reporte Meta`) | **1.100 €** por defecto, a mano. Se escribe UNA vez y vale para los dos reportes |
| **Coste total** (columna, en los dos reportes) | inversión de esa semana **+ la parte del fee que le toca** |
| **ROAS** | Facturado ÷ **Coste total** |

**El fee se reparte por DÍAS, no a partes iguales entre semanas.** Una semana de 7 días carga
`1.100 × 7/30`; la última del mes, que suele tener 2 o 3 días, carga solo esos. Si se repartiera
en partes iguales, la última semana saldría con un ROAS artificialmente hundido.

**El ROAS mínimo no cambia de fórmula** (`1 ÷ margen`) y sigue valiendo: compara facturado contra
coste, y ahora el coste es el de verdad. Lo que cambia es que **ahora es mucho más difícil
superarlo**, que es justo el punto.

⚠️ **Ojo al sumar Meta y Google de un cliente que lleva los dos:** cada reporte carga el fee
completo, así que **el fee aparece dos veces**. Cada pestaña responde a *«¿es rentable este canal
contando lo que cuesta la agencia?»*, y para eso está bien; pero los dos «Coste total» **no se
suman** para sacar el coste real del cliente.

## Meses cerrados en su propia pestaña: `--corte-mes` (Dirección, 10-09-2026)

Con cuatro meses en la misma tabla no se leía ninguno. `--corte-mes 9` parte la hoja en dos
pestañas del **mismo archivo**:

| Pestaña | Qué lleva |
|---|---|
| **`Reporte Meta`** | del mes de corte en adelante — lo vivo, y donde viven ticket, margen y fee |
| **`Histórico hasta <mes>`** | los meses anteriores, ya cerrados |

- **El corte es de PRESENTACIÓN, no de facturación.** El fee se sigue cargando en todos los
  meses que lleve la cuenta, histórico incluido (Dirección: *«desde junio»*). No confundir «lo
  aparto para que se lea» con «esto no lo gestionábamos».
- **Una sola fuente de verdad:** en el histórico, `B6`, `D6` y `J6` son **fórmulas**
  (`='Reporte Meta'!$B$6`), no celdas a mano. Si se dejaran a mano, alguien cambiaría el
  ticket en una pestaña y no en la otra y los dos ROAS dejarían de comparar lo mismo. Los
  cierres y el «% que cierra» sí son de cada pestaña, como en `Reporte Google`.
- **Las dos leen del mismo `datos`**, así que la suma de las dos = la cuenta entera. Comprobado
  en Cliente 02: 239,82 € (septiembre) + 2.808,08 € (junio-agosto) = **3.047,90 €**, el gasto
  exacto de Meta.
- ⚠️ **`datos_a_mano()` ahora mira TODAS las pestañas de reporte, no solo la primera.** Antes
  buscaba la primera que empezara por «reporte»: con el histórico al lado, los cierres escritos
  ahí no estaban protegidos y regenerar los habría borrado sin avisar.

## DOS funnels en la MISMA cuenta (Dirección, 10-09-2026)

Un cliente puede correr **dos negocios distintos con un solo `act_`**. Cliente 02 es el caso:
**inversión inmobiliaria** y **gestión de pisos**. Sumarlos en la misma fila esconde cuál de
los dos paga: en septiembre, inversión iba a 114,50 € con 1 lead y gestión a 125,32 € con
**cero**, y juntos parecían una sola cuenta mediocre.

**Se resuelve con `--funnel`, repetible**, en `montar_hoja_reportes.py`. La tabla gana una
columna **«Funnel»** y cada semana pasa a tener **una fila por funnel**:

```bash
python3 ~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/montar_hoja_reportes.py \
  --cliente Cliente 02 --cuenta <ID_META> --anio 2026 --desde-mes 6 \
  --carpeta-id <ID de «6. Reportes»> --datos datos.json \
  --funnel "Inversión=LANDING INVERSION;FUNNEL INVERSION;INVERSORES" \
  --funnel "Gestión de pisos=LANDING GESTION;FUNNEL GESTION;FORM INTERNO;| INT |"
```

| | |
|---|---|
| Formato | `Nombre=MARCA;MARCA` — una **marca** es un TROZO del nombre de la campaña |
| Con qué separa | `datos` trae una fila por día y **campaña**: el nombre es lo ÚNICO con lo que se puede separar |
| Filas del mes | una por funnel + **«Sin clasificar»** + **TOTAL DEL MES (con fee)** |
| Sin `--funnel` | la hoja sale **exactamente igual que antes** (comprobado celda a celda) |

### La fila «Sin clasificar» no es decorativa
Lo que no case con **ningún** funnel cae ahí, y se calcula contra `datos` con el filtro al
revés — **no restando**. Si alguien crea una campaña sin la marca de su funnel en el nombre,
su gasto **aparece en rojo** en vez de esfumarse del reporte sin que salte nada. El TOTAL DEL
MES la incluye, así que **el total siempre cuadra con la cuenta de Meta** aunque haya campañas
mal nombradas. En Cliente 02 sale **0 €**: no se pierde ni un euro.

### El funnel se decide MIRANDO, no por el nombre de la campaña
El nombre de la campaña **no siempre lo dice**. En Cliente 02 dos campañas no llevaban marca:
- `... | FORM INTERNO | ABO` → su **conjunto** se llama `Cliente 02:: FUNNEL GESTION | LEAD |
  LAL 1% 2%`. Los adsets sí llevan `FUNNEL GESTION`/`FUNNEL INVERSION`: **mirar ahí primero**.
- `... | INT | ING | CBO` → ni el conjunto lo decía. Se resolvió **abriendo los creativos**
  (`ads_get_ad_preview`): «un conflicto entre inquilinos» y «3 errores en el alquiler por
  habitaciones» hablan al propietario → gestión.

⛔ **Nunca repartir a ojo.** Si no se sabe, se deja en «Sin clasificar», que para eso está.

> **Lo que hay que arreglar de raíz:** las campañas deberían llevar `FUNNEL GESTION` /
> `FUNNEL INVERSION` en el nombre, como ya hacen los conjuntos. Mientras no lo lleven, el
> reparto depende de marcas frágiles como `FORM INTERNO`: el día que exista un form nativo
> de inversión, se irá a gestión sin avisar.

### ⛔ El fee NO se trocea entre funnels (Dirección, 10-09-2026)
> *«El fee es por los funnels, no es un fee por funnel.»*

Es **un pago mensual por la cuenta entera**, así que entra **una sola vez, en la fila TOTAL DEL
MES**. Las filas de funnel enseñan **solo su inversión** —igual que las filas de semana— y su
ROAS se mide contra eso.

Se probó a repartirlo en proporción al gasto de cada funnel (993,13 € a inversión + 106,87 € a
gestión en julio) y **se descartó**: sumaba bien, pero repartir un pago único inventa un coste
de agencia por funnel que nadie factura así. Si hace falta saber si un funnel se sostiene con
el fee encima, se mira el TOTAL DEL MES, que lo lleva entero.

### `ventas` NO se puede repartir por funnel
El CRM no dice de qué campaña vino la venta. Si cada funnel mirase `ventas`, **los dos se
apuntarían la misma factura** y el mes sumaría el doble. Por eso las filas de funnel van por
**cierres a mano o estimación**, y el dato real del CRM entra **una sola vez, en el TOTAL DEL
MES**.

### El fallo que apareció montándolo (no repetirlo)
La fila TOTAL suma `SUM(C10:C19)+C22` (las semanas **más** «Sin clasificar»). Sin paréntesis,
`B/H` se convertía en `SUM(...)+C22/SUM(...)+G22`: la división afectaba **a un solo sumando** y
el coste por lead salía mal **sin dar ningún error**. Ahora cada trozo va entre paréntesis en
`celdas_total()`. Es el mismo tipo de fallo que las letras de columna a mano: números válidos
en el sitio equivocado.

## `results` vs `lead`: el número de leads que engaña
⛔ **Para la carga inicial NUNCA se usa el campo `lead` a secas.** En Cliente 02 daba **5 leads
para 3.047,90 €** (609 €/lead). Los de verdad son **20**:

| Campaña | Indicador de `results` | Leads |
|---|---|---|
| `LANDING INVERSION` | `offsite_conversion.fb_pixel_complete_registration` | 15 (175,90 €) |
| `FORM INTERNO` | `leadgen.other` | 5 (20,90 €) |
| `LANDING GESTION` | `fb_pixel_complete_registration` | 0 |
| `INT \| ING \| CBO` | `profile_visit_view` | **0 — son visitas de perfil, NO leads** |

Las campañas a landing optimizan a **registro completado** (píxel), no a `lead`, así que `lead`
las da a cero. Se usa **`results`**, pero **solo cuando su `indicator` es de tipo lead**
(`offsite_conversion.fb_pixel_complete_registration`, `leadgen.other`, `lead`). Las visitas de
perfil y las vistas de landing **no se suman**: sumarlas habría metido 671 leads que no existen.
Misma regla de siempre — *lo que no es aditivo, no se suma*.

## Colores: cada fuente con los suyos (Dirección, 10-09-2026)
Con los dos reportes en el mismo archivo hacía falta distinguirlos de un vistazo. Ya no se usa
la paleta de Flowboost (morado y rosa) dentro de las hojas de cliente:

| | Cabecera de mes | Cabecera de columnas | Totales |
|---|---|---|---|
| **Reporte Meta** | azul de Meta `#0866FF` | negro `#0B0B0F` | azul claro `#5AA9FF` |
| **Reporte Google** | azul de Google `#1A73E8` | gris de Google `#202124` | verde `#188038` |

Lo que **no** cambia entre pestañas es el fondo de las celdas que se escriben a mano:
`A_MANO_BG = #BBD6FF` en las dos. Hasta el 10-09-2026 `Reporte Google` usaba `#E8F0FE`,
casi blanco — el hueco se veía en Meta y no en Google. Un mismo hueco tiene que verse
igual en las dos pestañas.

Para cambiarle los colores a una hoja **ya creada**, sin tocar datos ni fórmulas:

```bash
python3 ~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/recolorear_reportes.py --todos
```

Solo sustituye rellenos y color de letra de las celdas que llevan un color de la paleta vieja.

## Cinco fallos reales, con su causa (no repetirlos)

### 1. Los ratios del TOTAL DEL MES NO se promedian. NUNCA.
El total de Google promediaba las cinco filas de semana, y **las semanas que aún no han pasado
valen cero y hunden la media**. El cliente vio, en septiembre:

| | Mostraba | Real |
|---|---|---|
| CTR | 3,85 % | **9,17 %** |
| CPC medio | 0,41 € | **1,04 €** |
| Coste por lead | 15,01 € | **24,06 €** |
| Cuota de impresiones | 15 % | **~40 %** |

Las sumas estaban bien; solo fallaban los ratios. **Es exactamente el error del que avisa esta
misma skill para Looker** —nunca promediar el CPL—, cometido dentro de la hoja.

**La regla:** un ratio del mes se calcula **sobre las sumas del mes**, no sobre los ratios de
las semanas. CPL del mes = gasto total ÷ leads totales. Y la cuota de impresiones se recalcula
desde `datos-google`, no promediando una columna que ya es un promedio.

### 2. Una hoja ya creada NO se actualiza sola al cambiar la plantilla
`montar_hoja_reportes.py` **rehace el libro entero desde cero**. Sobre una hoja que ya existe
eso **borraría `Reporte Google` y las filas de `datos-google`**, que solo se recuperan
reejecutando el script en la cuenta de Google Ads.

**Cuando cambie la plantilla:** trabajar en local sobre el `.xlsx` exportado y **subir una sola
vez al MISMO ID**. Nunca regenerar encima.

### 3. El archivo se llama «Reporte Ads — \<Cliente\> — \<año\>»
Perdió el «Meta» al meter Google dentro, y era correcto: ya no es solo de Meta. Pero el buscador
iba por la cadena `'Reporte Meta Ads'` y dejó de encontrarlo, con lo que habría creado un
duplicado. **Ahora busca por `Reporte` + el nombre del cliente y descarta las de «Estado de
cuenta»** — que es el otro error del que ya nos habíamos tropezado.

**Al día 10-09-2026:** los tres archivos que existen ya llevan el nombre nuevo (Cliente 11,
Cliente 13 y Cliente 03). Renombrar en Drive **no cambia el ID**, así que n8n (que va por
`sheet_id`) y los scripts de Google (que van por URL con el ID) siguieron funcionando sin tocar
nada. Y `montar_hoja_reportes.py` crea ya con el nombre nuevo, pero **sigue buscando también el
viejo**: si aparece un archivo antiguo sin renombrar, lo actualiza en vez de duplicarlo.

### 4. Lo que NO es aditivo no se suma: el alcance y la frecuencia

`Reporte Meta` sumaba la columna `alcance` de `datos` como si fuera el gasto. **No lo es.**
`datos` tiene una fila por día **y por campaña**, y una misma persona alcanzada el lunes y el
martes, o por dos campañas a la vez, aparece en varias filas. Sumarlas la cuenta varias veces.

Medido en Cliente 13 (1 de junio → 10 de septiembre de 2026):

| | La hoja mostraba | Lo real de la cuenta |
|---|---|---|
| Alcance | 373.176 | **123.540** — ×3 |
| Frecuencia | 1,33 | **4,03** |

Y lo peor no es el alcance, es la **frecuencia**, que es `impresiones ÷ alcance` y hereda el
error al revés: **decía 1,33 —«queda público de sobra»— cuando la de verdad era 4,03, o sea que
se estaba saturando a la audiencia**. Justo la métrica que tenía que haber avisado mientras el
coste por lead pasaba de 10 € en julio a 51 € en septiembre.

**No tiene arreglo sumando:** el alcance deduplicado solo lo sabe Meta, no se puede deducir de
`datos`. Ni siquiera sumar el total de las tres campañas vale (daba 145.836, y el real es
123.540: también se solapan entre ellas).

**Decisión: fuera de la vista**, con el mismo criterio que «Llegan a la landing» — un número
que miente es peor que no enseñar nada. `alcance` y `frecuencia` **se siguen guardando en
`datos`** (n8n las escribe y el orden de columnas no se toca): solo se ha dejado de mostrarlas.

> **La regla, para cualquier columna nueva:** antes de sumarla por semana, preguntarse si
> sumar dos filas de `datos` tiene sentido. Gasto, impresiones, clics y leads **sí** son
> aditivos. Alcance, frecuencia, CTR, CPM, CPC, cuota de impresiones y cualquier % o media
> **no**: se recalculan desde las sumas (`CTR = Σclics ÷ Σimpresiones`), o no se muestran.
> Es el mismo error del fallo 1 y el mismo del que avisa esta skill para Looker.

### 5. Añadir una columna son TRES listas, no una (15-09-2026)

Al meter «Facturado (a mano)» se tocaron `COLS` y las filas de semana… y se olvidó
**`celdas_total`**, que es la fila de TOTAL DEL MES. Esa fila siguió escribiendo en el orden
viejo, o sea **cada cifra una columna a la izquierda**, y al convertir el `.xlsx` a Google la
hoja salió llena de **`#REF!`**. En local el fichero parecía correcto: el error solo aparece al
convertir, que es donde nadie mira. Es el mismo tipo de fallo que las letras a mano —números
válidos en el sitio equivocado—, pero por duplicado.

**Y hubo daño real:** en la vuelta rota se perdieron dos importes que Equipo había escrito en
Cliente 05. Se pudieron reponer porque el migrador los había impreso al rescatarlos; si no, no
habría forma de saber qué había.

**Ya no puede repetirse:** `_comprobar_columnas()` compara ahora **las tres listas**
—`COLS`, las filas de semana y la fila de TOTAL— y se planta antes de generar nada.

> **La regla:** una columna nueva se toca en `COLS`, en `bloque_formulas` **y** en
> `celdas_total`. Y después se comprueba la hoja **ya subida**, no el `.xlsx` local: los
> `#REF!` nacen en la conversión.

### Y la causa de fondo: las letras de columna estaban escritas a mano

El error de arriba no dio ni un aviso, y hay una razón más general: las letras iban a pelo por
todo `montar_hoja_reportes.py` (`CIERRES_COL = "K"`, `L{r}/M{r}`, `col_sum('K')`,
`leads_tot = N(H{f})`...). Con eso, **mover o quitar una columna deja fórmulas apuntando a la
de al lado sin romper nada**: el reporte sigue saliendo, con los números de otra columna.

Pasó al quitar Alcance y Frecuencia: `leads_tot` seguía fijado a `H`, que era «Clientes
potenciales» y pasó a ser «Coste por clic». El «% que cierra» habría dividido los cierres entre
el CPC y nadie se habría enterado.

**Ya no se escribe ninguna letra a mano.** Se deducen de `COLS`:

```python
X = {n: get_column_letter(i + 1) for i, (n, _, _) in enumerate(COLS)}
CIERRES_COL = X["Cierres (a mano)"];  FACTURADO_COL = X["Facturado (a mano)"]
# y en las fórmulas:  f'=IFERROR({X["Facturado"]}{r}/{X["Coste total"]}{r},0)'
```

⛔ **Si añades o quitas una columna, toca `COLS` y nada más.** Cualquier `"K"`, `"H"` o
`col_sum('L')` suelto que aparezca en el fichero es un fallo esperando a pasar.

## ⛔ Campañas que NO gestionamos: `marca_campanas` (Dirección, 22-09-2026)

En la cuenta de un cliente puede haber campañas que **paga y lanza él por su cuenta**. En
**Cliente 05** eran cinco «Publicación de Instagram: …» que sumaban **166,08 € con 0 leads**, y
estaban dentro de su reporte: enseñaba 650,48 € de inversión cuando lo nuestro eran 484,40 €, y
el coste por lead subía de 2,17 € a 2,92 €. Le estábamos midiendo el ROAS contra gasto ajeno.

Se arregla con `marca_campanas` en `clientes_reportes.json`: un trozo del nombre de **nuestras**
campañas. Solo entran las que lo lleven.

```json
{"cliente": "Cliente 05", "marca_campanas": "Cliente 05::", ...}
```

| | |
|---|---|
| Lo aplica | `armar_datos.py` (4.º argumento) — y `actualizar_todos.py` se lo pasa solo desde la lista |
| Qué hace con lo excluido | lo cuenta y lo IMPRIME con su gasto, no lo esconde |
| Vacío | entran todas, como siempre |

⚠️ **Si se limpia una hoja a mano sin poner la marca, la rutina vuelve a meterlas al día
siguiente** y deshace el arreglo sin que nadie se entere. Van juntos.

**Cómo se detecta:** las nuestras llevan el prefijo del cliente (`Cliente 05::`, `Cliente 11::`,
`Cliente 02::`). Si al mirar `datos` aparecen campañas con otro patrón —«Publicación de
Instagram», nombres sueltos sin `::`— casi seguro son del cliente.

## ⛔ El mes de arranque NO es enero: es el mes en que entró el cliente

Cada hoja empieza en su mes y `--desde-mes` **es obligatorio** en `redisenar_hoja.py`. Ponerlo
por defecto a enero le añadió a cuatro clientes bloques de meses vacíos que nunca tuvieron
(Dirección lo vio enseguida: *«porque metiste enero de 2026 en todos»*).

| Cliente | Arranca en |
|---|---|
| Cliente 14 | enero |
| Cliente 13 · Cliente 03 | junio |
| Cliente 11 | julio |
| Cliente 05 | septiembre |
| Cliente 02 | junio, con corte en septiembre (histórico aparte) |

**Si no se sabe, NO se inventa:** el mes real está en las **revisiones de Drive** de la propia
hoja (`files/<id>/revisions` → `exportLinks` de la revisión anterior). Así se recuperaron estos.

## Cambiar el diseño de una hoja YA EN USO: `redisenar_hoja.py`

`montar_hoja_reportes.py --rehacer` borra los cierres, el ticket, el margen, el fee y `ventas`.
Para pasar una hoja viva al diseño actual **sin perder nada**:

```bash
python3 ~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/redisenar_hoja.py \
  <sheet_id> "<Cliente>" <ad_account_id> [--dry]
```

Rescata lo escrito, reconstruye con la plantilla nueva y lo devuelve buscando **por mes +
etiqueta de semana**, nunca por número de fila (las filas se mueven al cambiar columnas o meses).
**Si algún cierre no encuentra su sitio, NO sube nada** y lo dice.

⛔ **Se niega solo en tres casos**, y hay que respetarlo:

| Caso | Por qué | Qué hacer |
|---|---|---|
| La hoja tiene `Reporte Google` / `datos-google` | la plantilla no monta esas pestañas: se perderían, y el histórico solo vuelve reejecutando el script en Google Ads | `--pierdo-google` **solo** si se asume, y después rehacerlas con `anadir_hoja_google.py` |
| La hoja usa **funnels** (columna «Funnel») | se fusionarían las filas y se perdería qué negocio paga | rehacerla a mano con los mismos `--funnel` |
| La hoja tiene pestaña **«Histórico hasta \<mes\>»** | se montó con `--corte-mes` y desaparecería | rehacerla a mano con el mismo `--corte-mes` |

**Al día 22-09-2026:** rediseñadas **Cliente 14, Cliente 11 y Cliente 05** (cierres rescatados y
verificados en su semana). Pendientes: **Cliente 13** y **Cliente 03** (llevan Google),
**Cliente 02** (funnels + histórico) y **Cliente 01** (Google, y además fuera de la rutina).

## El reporte se rehízo de raíz: dos casillas y nada más (Dirección, 22-09-2026)

Durante el día se intentó arreglar a parches —quitar una columna, renombrar otra— hasta que
Dirección paró: *«me parece poner parches lo que decís, no sirve»*. Tenía razón: el problema no era
dónde iba cada columna.

**El problema era que «Facturado» intentaba ser tres cosas a la vez** —dato del CRM, dato
escrito a mano y estimación—, y por eso necesitaba una columna que la alimentara
(`Facturado (a mano)`), otra que la calculara (`Facturado`) y una tercera que explicara cuál de
las tres había salido (`Origen`). Tres columnas para un dato.

### Cómo queda

`Semana · Inversión · Impresiones · CTR · Clics en el enlace · Clientes potenciales · Coste por
lead · Coste por clic · **Cierres (a mano)** · **% de cierre** · **Facturado (a mano)** · Coste
total · ROAS · ROAS mínimo`

| | |
|---|---|
| **Lo que rellena Equipo** | **DOS casillas azules por semana**: cuántos cerró y cuánto facturó |
| **Lo que rellena Dirección** | el **margen**, una sola vez. El fee ya viene puesto (1.100 €) |
| Ticket medio | **se calcula**: suma de facturado ÷ suma de cierres de las semanas |
| % de cierre (por fila) | cierres ÷ leads **de esa fila** |
| % que cierra (`H6`) | cierres del año ÷ leads del año |
| ROAS | facturado ÷ coste total. **Vacío si no hay facturado** |

⛔ **Fuera la estimación y fuera «Origen».** Un ROAS estimado es un ROAS inventado, y la regla de
la casa es no inventar cifras. Con una sola fuente por fila no hay nada que explicar.

⛔ **El ticket medio NO se escribe.** Sale de lo que apunta Equipo. No hay referencia circular
porque «Facturado» ya no depende del ticket. En Cliente 05 da **193,85 €** sin que nadie lo teclee.

### El fallo que costó caro, y que no se puede repetir
Al quitar la columna se borraron **3.295,53 € que Equipo tenía escritos** en Cliente 05
(121,00 € · 1.748,53 € · 1.426,00 €). Se recuperaron de las **revisiones de Drive**
(`files/<id>/revisions`, campo `exportLinks`), pero la lección es doble:

1. **Antes de quitar una columna, mirar si alguien la está usando.** No era teórica: Equipo metía
   ahí el importe REAL, que no coincide con la estimación — en una semana puso 121 € donde el
   ticket medio habría dado 193,85 €, porque cada cierre factura distinto.
2. **`redisenar_hoja.py` rescata cierres E IMPORTES.** Rescatar solo los cierres fue el error.


## Qué se rellena a mano y qué se calcula solo

**Arriba se rellena UNA sola cosa, una sola vez: el MARGEN (`D6`).** Qué parte del ticket es
beneficio, antes de publicidad. Lo dice el cliente y no hay forma de deducirlo de la
publicidad. Sin él, el «ROAS mínimo» sale «—».

**El fee (`J6`) ya viene puesto: 1.100 €, y no se toca.** Todos los clientes pagan lo mismo
(Dirección, 15-09-2026); no hay tarifas distintas que consultar.

**Y cada semana, DOS cosas**, en las dos columnas azules:

| Columna | Qué se pone |
|---|---|
| **Cierres (a mano)** | el NÚMERO de cierres de esa semana. Si cerraste 3, pones `3` |
| **Facturado (a mano)** | el IMPORTE que se facturó esa semana, en euros |

El margen y el fee se escriben en **`Reporte Meta`**; `Reporte Google` los lee de ahí (el fee,
literalmente, como `'Reporte Meta'!$J$6`), así que **no se rellenan dos veces**. Los cierres y
los importes sí son de cada pestaña.

### El TICKET MEDIO se calcula solo desde el 15-09-2026

Era una casilla a mano y ya no lo es (Dirección, 15-09-2026): sale de
**lo facturado a mano ÷ los cierres de esas mismas semanas**. Mismo criterio que el
«% que cierra»: si el dato se puede deducir de lo que ya se escribe, no se pregunta.

Dos cosas que hubo que resolver para que funcionara, y que explican por qué existe la columna
«Facturado (a mano)»:
- **Equipo escribía el importe ENCIMA de la fórmula de «Facturado».** Eso se perdía en cuanto
  se regeneraba la hoja, y además impedía calcular el ticket: si el ticket saliera de una
  columna que a su vez depende del ticket, Sheets da **referencia circular**. Con columna
  propia, lo escrito a mano no depende de nada.
- **Solo cuentan los cierres de semanas que además llevan importe.** Si no, una semana con
  2 cierres y sin importe rebajaría el ticket como si esos dos cierres hubieran facturado 0 €.
  La fórmula va mes a mes (`SUMPRODUCT((J10:J14>0)*N(I10:I14))`) y **nunca por la columna
  entera**, que incluiría las filas de TOTAL y contaría cada semana dos veces.

Ejemplo real (Cliente 05, 15-09-2026): 121 € + 385,48 € facturados y 3 cierres → ticket
**168,83 €**, y con él la semana en curso ya estima sin que nadie escriba nada.

> **El rótulo manda, no el color.** Todo lo que se rellena a mano lleva **«(a mano)»**
> en el rótulo, y además va sobre fondo azul (`A_MANO_BG = BBD6FF` en
> `montar_hoja_reportes.py`). El rótulo es lo que vale: una versión anterior decía
> «rellenad las celdas lilas» y ni eran lilas ni se distinguían del blanco.

**Todo lo demás sale solo**, incluidas las dos celdas de arriba a la derecha:

| Celda | Qué es | Cómo se calcula |
|---|---|---|
| **Cierres totales** (`F6`) | los cierres del año | suma de las filas «TOTAL DEL MES» |
| **% que cierra** (`H6`) | de cada 100 leads, cuántos compran | cierres totales ÷ leads totales |

⛔ **El «% que cierra» NO se escribe a mano.** Hasta el 10-09-2026 era una casilla manual y era
pedirle al usuario que hiciera una división: *«es un dato completo para ponerlo a mano, que eso
se calcule solo»* (Dirección). Ahora se deduce de los cierres que se van escribiendo, y el reporte
aprende solo a medida que se rellena.

**Cada pestaña tiene los suyos:** los cierres y el % de `Reporte Google` salen de la columna de
esa pestaña, no de los de Meta. Ticket y margen sí son comunes.

**«Facturado» se escribe a mano, y punto (Dirección, 22-09-2026).** Es una casilla azul más,
al lado de los cierres. No hay cascada, no hay estimación y no hay columna «Origen»:

- si hay dato, se ve;
- si no, está vacío — y el ROAS de esa fila, también.

⛔ **Se quitó la ESTIMACIÓN a propósito.** Un ROAS estimado es un ROAS inventado, y la regla de
la casa es no inventar cifras (por eso el resto del reporte pone «—» cuando no hay dato). Antes
«Facturado» intentaba ser tres cosas —dato del CRM, dato a mano y estimación— y por eso
necesitaba una columna que la alimentara, otra que la calculara y una tercera que explicara cuál
de las tres había salido.

### El ROAS va sobre el COSTE TOTAL, no sobre la inversión (Dirección, 10-09-2026)
Entre «Facturado» y «ROAS» hay una columna **«Coste total»**:

```
Coste total = inversión de esa semana + la parte del fee que le toca
ROAS        = Facturado ÷ Coste total
```

**El fee se reparte por DÍAS, no por semanas.** Si no, la última fila del mes —que suele tener 2
o 3 días— cargaría un mes entero de fee y su ROAS saldría por los suelos sin motivo.

Se hace así porque **el cliente paga las dos cosas**: la publicidad y a nosotros. Un ROAS medido
solo contra la inversión le dice que gana dinero cuando puede estar perdiéndolo.

⚠️ **El fee entero se carga a los DOS reportes.** El «Coste total» de `Reporte Meta` lleva todo el
fee prorrateado, y el de `Reporte Google` también. Es a propósito —cada canal se mide como si
tuviera que sostener él solo la agencia—, pero significa que **sumar las dos columnas de «Coste
total» cuenta el fee dos veces**. Para el coste real del mes: inversión de Meta + inversión de
Google + un solo fee.

**Si el ticket y el margen están a cero, el ROAS sale «—»** en vez de una cifra inventada. Es
deliberado.

**El ROAS mínimo** (breakeven) sigue siendo `1 ÷ margen`, y ahora dice más: por debajo de ese
número, esa semana **no paga ni la publicidad ni el fee**. Por eso va justo al lado del ROAS.

## La plantilla de la hoja del cliente
`Estandar-carpetas/montar_hoja_reportes.py` es **la plantilla de la casa**. Aprobada por Dirección
(07-09-2026). Todo cliente lleva esta y no otra.

| | |
|---|---|
| **Filas** | una por **SEMANA**. **Desde septiembre de 2026, de LUNES A DOMINGO** (Equipo, 15-09-2026): los informes se leen por semana natural. Septiembre queda 1-6, 7-13, 14-20, 21-27, 28-30. Hasta agosto de 2026 se quedan los bloques fijos de 7 días (1-7, 8-14…), porque esos meses ya se enseñaron así. El corte está en `LUNES_DESDE` de `montar_hoja_reportes.py`. ⚠️ **Un mes puede necesitar 6 filas y no siempre 5** (en 2026: marzo, agosto y noviembre): nada puede dar por hecho que un bloque de mes ocupa 5 filas. **Nunca por día**: el detalle diario marea al cliente y no dice nada |
| **Bloques** | uno por **mes**, con dos filas de aire entre medias. Se monta **el año entero de una vez**: cuando llegue octubre su bloque ya está esperando |
| **Columnas** | Inversión · Impresiones · CTR · Clics en el enlace · Clientes potenciales · Coste por lead · Coste por clic · **Cierres (a mano)** · **% de cierre** · **Facturado (a mano)** · **Coste total** · ROAS · ROAS mínimo |
| **Fuera desde el 10-09-2026** | «Alcance» y «Frecuencia» (ver fallo 4: no son sumables, daban ×3 y 1,33 en vez de 4,03), y «Llegan a la landing» y «% que llega». Las quitó Dirección. El dato de Meta no es fiable: en las campañas de formulario nativo no hay landing que visitar, y aun así devuelve cifras sueltas; en las de landing salían días con más visitas que clics. Un porcentaje que pasa del 100 % en la hoja del cliente es peor que no enseñar nada. **`vistas_landing` se sigue guardando en `datos`** (n8n lo escribe y el orden de columnas no se toca): solo se ha dejado de mostrar |
| **ROAS** | Meta **no sabe** lo que factura el cliente por un lead. Sale de lo que se escriba a mano (ver abajo), y se mide contra el **Coste total** (inversión + fee), no contra la inversión. Sin nada escrito, sale «—»: no se inventa |
| **ROAS mínimo** | el punto de equilibrio, `1 ÷ margen`. Por debajo, esa semana no paga ni la publicidad ni el fee |
| **Sin datos** | «—», nunca «€0,00», ni «0 %», ni infinito |

### Cambiar la plantilla de hojas YA EN USO: `migrar_semanas.py`

Regenerar con `--rehacer` se lleva por delante `datos`, `ventas`, `datos-google` y lo escrito a
mano. Para un cambio de diseño en hojas vivas está `migrar_semanas.py` + `migrar_cliente.py`
(Estandar-carpetas), que hace tres cosas: **rescata**, **rehace** y **devuelve**, y sube al MISMO
archivo (mismo ID, mismo enlace, n8n ni se entera). Se estrenó el 15-09-2026 con el cambio a
semanas de lunes a domingo, en los siete clientes con reportes.

Tres trampas que costaron y que el script ya tiene resueltas:
- **Lo escrito a mano puede ser una FÓRMULA.** Equipo escribió `=264,48+121` en un «Facturado».
  Descartar todo lo que empiece por `=` lo habría borrado. Se rescata lo que NO lee de `datos`,
  `ventas` ni `datos-google`, que son las de la plantilla.
- **En `datos-google` la fecha es una FECHA, no texto** (la escribe el script de Google Ads y
  Sheets la convierte). Filtrando solo texto ISO se perdían las 209 filas de Cliente 03.
- **Las pestañas de motor llevan NOTAS** en las primeras filas. Copiarlas como si fueran datos
  las duplica: se reconocen las filas de verdad porque su segunda columna es una fecha.

Los cierres se devuelven a la semana nueva que **contiene el primer día de la semana vieja**
(Dirección, 15-09-2026), y el script imprime uno a uno los que ha movido y los que no ha podido colocar.

### ⛔ Regenerar la hoja BORRA lo que escriba Equipo
`construir()` rehace el libro entero. Por eso `montar_hoja_reportes.py` ahora **se niega a pisar**
una hoja que tenga ticket, margen, cierres o ventas apuntadas, y dice qué encontró. Para forzarlo hay
que pasarle `--rehacer`, y entonces se pierde. Mismo criterio que `montar_hoja_estado.py`.

Si hay que cambiar el diseño de una hoja que ya está en uso, **hay que rescatar y devolver lo
escrito a mano**: leer los cierres y las tres celdas, regenerar con `--rehacer`, y volver a
escribirlos buscando **por mes + etiqueta de semana**, no por número de fila (las filas se mueven
si cambia el número de columnas o de meses). Se hizo así con Cliente 11 el 10-09-2026.

**Por qué normalmente no hace falta regenerar:** la pestaña `datos` es la única que toca n8n; las
semanas son **fórmulas** que leen de ahí. Se monta una vez y se actualiza sola. Regenerar es solo
para cambiar el diseño.

Dos cosas que costaron y no hay que volver a romper:
- **`SUMIFS` no vale** para filtrar por rango de fechas: con un criterio como `">=2026-09-01"`
  Sheets lo interpreta como FECHA, la columna es TEXTO y no casa ni una fila — todas las semanas
  salen vacías. Se usa `SUMPRODUCT` con comparación de texto (en ISO, el orden alfabético es el
  cronológico). Por eso `fecha` se escribe **como texto** desde n8n.
- **El formato de número** es `positivo;negativo;CERO;texto`. El guion va en la **tercera**
  sección; ponerlo en la cuarta deja la celda en blanco.
- **El orden de columnas de `datos`** está duplicado en dos sitios: `DATOS` en
  `montar_hoja_reportes.py` y el nodo *Armar filas* del flujo diario. Si cambia uno, cambia el otro.

**La API de Sheets no está disponible** con el token de rclone (403 `PERMISSION_DENIED`: el
proyecto no la tiene habilitada). Por eso la hoja se compone con openpyxl y se sube a Drive **con
conversión**: lo que queda en Drive es un **Sheet nativo**, no un `.xlsx`. n8n sí usa la API de
Sheets, con su propia credencial, así que a él no le afecta.

**Ejemplo montado y revisado:** **Cliente 11** (10-09-2026) — `<ID_DRIVE>`,
en `6. Reportes` de `c_Cliente 11`, con 118 filas reales del 1 de julio al 9 de septiembre. Los tres
meses cuadran al céntimo con los totales de Meta (julio 944,99 €/41 leads · agosto 1.323,43 €/25 ·
septiembre 350,93 €/6). Renombrado a la convención nueva el 10-09-2026.

### ⚠️ Cliente 06 se quedó con el sistema viejo (15-09-2026)

`montar_hoja_reportes_funnels.py` —la plantilla de Cliente 06, con Resumen y una pestaña por
funnel— **no tiene «Facturado (a mano)» ni el ticket calculado**: ahí el ticket sigue siendo
una casilla a mano por funnel. Sí tiene ya las semanas de lunes a domingo, porque importa
`semanas()` de la plantilla de la casa. Si hay que igualarla, es el mismo cambio: columna
nueva en sus COLS, en sus filas de semana y en su fila de total, más la fórmula del ticket.

### ⛔ ÚLTIMO PASO SIEMPRE: sumarlo a la rutina diaria (Dirección, 22-09-2026)

**Crear la hoja de un cliente NO lo deja actualizándose.** La hoja queda con su carga inicial y
ahí se queda para siempre si nadie la suma a la rutina. Es un paso que se olvida porque la hoja
ya se ve bonita y parece terminada.

Así que, **en cuanto exista la hoja del cliente**, un comando más:

```bash
python3 ~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/actualizar_todos.py \
  --alta "<Cliente>" <ad_account_id> <sheet_id> [indicador_leads]
```

Es idempotente: repetirlo actualiza, no duplica. Y con eso ya entra en la pasada de cada mañana,
sin tocar nada más.

| | |
|---|---|
| Dónde vive la lista | `Estandar-carpetas/clientes_reportes.json` |
| Quién la lee | `actualizar_todos.py` **y** la tarea programada, que la pide con `--listar` |
| Por qué una sola | Estuvo escrita en los dos sitios y se separaban en cuanto entraba un cliente |
| Ver quién está dentro | `actualizar_todos.py --listar` |
| Sacar a uno | `activo: false` en el JSON. Su hoja se queda como está |

**`indicador_leads` es el cuarto argumento, y solo hace falta cuando la cuenta mide los leads con
una conversión personalizada.** Cliente 14 usa
`offsite_conversion.fb_pixel_custom.TypeformSubmit`, el envío de su Typeform. Si se deja vacío se
usan los de siempre (`leadgen.other`, `fb_pixel_complete_registration`, `lead`). **Cómo saber si
hace falta:** si el cliente tiene gasto y sale con **cero leads**, es esto: se mira qué
`indicator` trae su `results` y se le pasa. La rutina lo avisa sola en su resumen.

### ⛔ El `indicator: "mixed"` NO se arregla. Está estudiado y descartado (22-09-2026)

Cuando una campaña tiene **conjuntos optimizando a cosas distintas** (uno a
`fb_pixel_complete_registration`, otro a una conversión personalizada), Meta **se niega a dar
el número a nivel de campaña**: devuelve `indicator: "mixed"` y `"Not available"`. Esos leads no
se cuentan, y el coste por lead de esa cuenta sale алgo inflado.

**Pasó en Cliente 11** (septiembre 2026): su campaña de landing gastó 326,71 € y trajo **1 lead**
que no se contaba. La hoja decía 9 leads a 95,52 €; lo real eran 10 a 85,97 €.

**Se miraron las dos salidas y las dos se descartaron:**

| Vía | Por qué NO |
|---|---|
| Pedir los datos **por conjunto** en vez de por campaña | La clave de `datos` es `fecha|campaña`. Al cambiar de nivel deja de casar con lo ya escrito, las filas viejas conviven con las nuevas y **las sumas se doblan**. Rompe el reporte |
| Leer el campo **`actions`**, que trae el desglose completo | **No existe en este MCP** (`unknown_field`). `conversions` sí existe, pero agrupa contactos, donaciones y suscripciones — no incluye los registros |

**La estructura del reporte la fijó el Project Manager del cliente y no se toca por esto.** El
agujero es de un lead sobre diez. Lo que SÍ hay es un aviso: la rutina escribe en su resumen
`indicador NO contado como lead: mixed ×N` siempre que ocurre. **Si ese número deja de ser
anecdótico, entonces sí habrá que replantearlo** — pero con ese dato en la mano, no antes.

⚠️ Y ojo con confundirlo con el fallo de los leads de verdad: ahí faltaba un indicador en la
lista (el `TypeformSubmit` de Cliente 14) y se arregla con `--alta`. Esto es distinto: el
indicador ya está en la lista, es Meta quien no da el número.

### La rutina diaria, en dos líneas
Corre a las **3:00 de Argentina, que son las 8:00 de Madrid** (la máquina de Dirección está en
UTC−3, y el cron va en hora local). Pide los datos al **MCP de Meta** —no hace falta
`META_TOKEN`— y escribe **solo la pestaña `datos`** de cada hoja con `actualizar_todos.py`.
⛔ Nunca con `montar_hoja_reportes.py`, que rehace el libro y borra los cierres a mano y
`datos-google`. Y ojo: **corre con la app de Claude abierta**; si está cerrada, se ejecuta al
abrirla.

### Dar de alta un cliente — UN comando, una sola vez
```bash
python3 ~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/alta_reportes.py \
  "<Cliente>" --cuenta act_123456789 \
  --carpeta "gdrive:i_<C>/c_<C>/6. Reportes" --landing https://... \
  --n8n <correo de la credencial de n8n> --maestra <ID de la maestra>
```
`--correo` y `--objetivos` **ya no se pasan**: eran del correo semanal, que está retirado. Los
argumentos siguen existiendo en el script, pero no se usan.
Deja hecho: la hoja maestra con sus cuatro pestañas (`datos`, `clientes`, `landing`, `ventas`), **la hoja del
cliente con la plantilla de arriba** y la fila del cliente en `clientes`. Es idempotente: repetirlo
actualiza, no duplica. **Después de esto no se vuelve a abrir n8n.**

Con `--cliente-raiz "gdrive:i_X/c_X"` en vez de `--carpeta`, **busca la carpeta de reportes por
nombre**: el número cambia según el cliente (`5. Reportes／Informes`, `6. Reportes`, `6. Reporting`)
porque las carpetas de antes no son iguales en todos. Nunca se escribe el número a pelo.

**`--n8n` no es opcional en la práctica:** las hojas las crea la identidad de rclone, pero quien escribe
cada mañana es la credencial `Google Sheets account` de n8n, que es otra cuenta. Sin ese permiso da 403.

**Clarity está FUERA de este flujo** (Dirección, 10-09-2026). Se quitaron los cuatro nodos que lo traían
(`Clarity: ayer`, `Armar fila de landing`, `¿Hubo Clarity?`, `Hoja landing`) y el flujo pasó de 13 a 9
nodos. Ya no hace falta `CLARITY_TOKENS` para nada de esta skill.

⚠️ **Lo que había que arreglar al quitarlo, y que no es obvio:** la rama de Clarity era **el camino de
vuelta al bucle**. `Hoja landing` y `¿Hubo Clarity?` eran los que devolvían el flujo a *Uno por uno*.
Borrarlos sin más deja el bucle sin retorno y **el flujo procesa solo al primer cliente** — sin error,
sin aviso, simplemente los demás se quedan sin datos. Ahora vuelven al bucle *Hoja maestra (Looker)*
(rama con datos) y *¿Hay datos?* por su salida 1 (rama sin datos).

La pestaña `landing` de la maestra se queda ahí, vacía y sin que nadie la escriba. No molesta; si
alguna vez vuelve Clarity, ya está montada. `alta_reportes.py` la sigue creando.

## Looker Studio
Looker lee **la hoja maestra**, no las de los clientes: un solo origen para ver todas las cuentas juntas
(`documentId` del nodo *Hoja maestra*, ya puesto en la copia de `n8n/`). Las hojas individuales son para que el
cliente vea lo suyo sin ver lo de nadie más. Guía de montaje en
`../../Documentos-Flowboost/Investigacion/looker-studio-montaje.md` — con los dos avisos de siempre:
**nunca promediar el CPL** (`SUM(gasto)/SUM(leads)`) y **nunca compartir el panel interno con un filtro
puesto**, que el filtro se quita y se ve todo.

## Los flujos, y a qué hora
| Hora (Madrid) | Qué corre | Dónde vive | Qué escribe |
|---|---|---|---|
| **06:00** | script de Google Ads | dentro de cada cuenta de Ads | `datos-google` |
| **07:30** | ventas cerradas del CRM | n8n | `ventas` *(solo en los clientes que tengan CRM conectado — hoy casi ninguno)* |
| **08:00** | `reporteDiarioMetaSheets01` | n8n, VPS | `datos` |
| ~~Viernes 9:00~~ | ~~`reporteSemanalMeta01`~~ | — | **RETIRADO** (Dirección, 10-09-2026): no se manda correo a nadie |

El orden importa: Google a las 6:00 porque consolida sus cifras hasta 3 h después de medianoche, y
Meta a las 8:00, después de que el CRM haya dejado las ventas. Ninguna de las tres escribe en las
pestañas que mira el cliente: esas son fórmulas.

Queda en pie `informeInternoViernes01` (viernes 8:30, estado de las landings para Dirección), pero **ése no
es de esta skill**: es de `informe-landing-clarity`. Si Dirección también lo quiere sin correo, se cambia
allí, no aquí. Y ojo: su motivo de existir era avisar antes de que al cliente le llegara el reporte del
viernes; sin ese reporte, hay que decidir para qué se quiere.

## Google Ads en el MISMO archivo (Cliente 01, Cliente 13 y Cliente 03)

Tres clientes llevan también Google Ads. Su reporte vive en **dos pestañas más del mismo
archivo**, no en uno aparte — y eso no es comodidad: la pestaña `ventas` trae los cerrados del
CRM, así que **compartiendo archivo el ROAS de Meta y el de Google se miden contra el MISMO
dinero real**. En archivos separados habría que duplicar las ventas y acabarían divergiendo.

| Pestaña | Qué es | Quién la escribe | Cuándo |
|---|---|---|---|
| **`Reporte Meta`** | lo que se mira: semanas y meses de Meta | fórmulas | — |
| **`Reporte Google`** | lo mismo, de Google Ads | fórmulas | — |
| `datos` | Meta en crudo, una fila por día y campaña | n8n (`reporteDiarioMetaSheets01`) | 8:00 |
| `ventas` | las ventas cerradas, con su importe real | el CRM del cliente, **si lo tiene conectado** (hoy casi ninguno) | 7:30 |
| `datos-google` | Google en crudo, una fila por día y campaña | el script de Google Ads | 6:00 |

**Las tres de abajo son el motor: no se miran ni se tocan a mano.** Los dos reportes leen de
ellas. `ventas` la usan **las dos**, y por eso el ROAS de Meta y el de Google salen contra el
mismo dinero real.

⚠️ **Los nombres son exactamente `Reporte Meta` y `Reporte Google`** (Dirección, 10-09-2026). Antes la
de Meta se llamaba solo `Reporte` y con la de Google al lado no se distinguían.

**Por qué un script de Ads y no la API vía n8n** (razón revisada el 21-09-2026): la razón vieja
—«la API exige un *developer token* que Google aprueba a mano y tarda semanas»— **ya no vale**:
Google **retiró los developer tokens el 09-09-2026** y el nivel de acceso lo da ahora el proyecto
de Google Cloud, con el nivel *Explorer* concedido casi al instante.

La decisión **se mantiene igual**, pero por los motivos buenos, que son otros tres:
- El Ads Script **corre dentro de la cuenta**: no hay credencial externa que caducar ni renovar.
  La vía API depende de un OAuth que, mal configurado, caduca **cada 7 días** y tumbaría la hoja
  del cliente un martes cualquiera.
- **No consume cuota** de la API ni depende de que el VPS o n8n estén vivos.
- Ya funciona y tiene 200+ filas de histórico por cliente. Rehacerlo no compra nada.

⛔ **Si alguien propone pasar los reportes a la API «ahora que ya se puede»: no.** Lo que sí se
hace con la API es el **paso siguiente** (ver abajo), que es otra cosa.

## El paso siguiente: de los números al criterio (`google-ads-mcp`)

El reporte dice **cuánto** se gastó y **cuántos** leads salieron. No dice si eso está bien, ni qué
hacer. Ese es el trabajo de la skill **`google-ads-mcp`**, que se ejecuta **después** y **encima**
de esta:

| | Esta skill (`reportes-cliente`) | La siguiente (`google-ads-mcp`) |
|---|---|---|
| Qué produce | contabilidad: gasto, leads, coste por lead, ROAS | criterio: escalar, arreglar, mantener o apagar |
| Cada cuándo | sola, cada mañana | a demanda, una vez al mes |
| Quién lo ve | el cliente, en su hoja | Dirección (interno) |
| De dónde lee | la cuenta de Ads (Ads Script) | el MCP de Google Ads **y esta hoja** |

**Lo que la auditoría toma de aquí** —y por eso esta skill es su requisito, no al revés:
- **`datos-google`**: la serie diaria por día y campaña. Es exactamente la materia prima del
  **CPA marginal** y del **coste del clic incremental**. Con 200+ filas ya hay serie suficiente.
- **`Reporte Google`, columnas «Cierres (a mano)» y «Facturado (a mano)»**: de ahí salen el
  **valor por lead** y el **ticket medio** reales. Sin esos dos números la auditoría no puede
  dar veredicto de escalado, porque no sabe cuál es el CPA máximo rentable.
- **El fee** (`'Reporte Meta'!$J$6`, 1.100 €) y el margen: el CPA máximo se calcula contra el
  **coste total**, igual que el ROAS de esta hoja, no contra la inversión sola.

**Lo que le falta a `datos-google` para que la auditoría corra entera sin MCP**: el Ads Script trae
`metrics.search_impression_share`, pero **no el desglose por causa**. Añadiendo dos campos a la
consulta del script —`metrics.search_budget_lost_impression_share` y
`metrics.search_rank_lost_impression_share`— la auditoría podría separar la pérdida comprable de
la que no lo es **sin depender del MCP**. Es un cambio de una línea en
`~/Desktop/SCRIPTS-GOOGLE-ADS/<cliente>.js` y dos columnas nuevas, que se tocan en las **tres**
listas (ver «Añadir una columna son TRES listas»).

**Lo que NO se hace**: meter la auditoría dentro del volcado de las 6:00. El reporte es
infraestructura que ya funciona; la auditoría depende de credenciales que pueden caducar. No se
cuelga lo frágil de lo que va bien.

### Montarlo en un cliente

**1. Las pestañas** (esto lo hace el agente):

```bash
python3 ~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/anadir_hoja_google.py "<Cliente>"
```

⚠️ **NO usa `marcar_etapa.buscar_por_nombre`**: esa devuelve la primera hoja del cliente que
encuentra y gana la de «Estado de cuenta»: así se metieron estas pestañas en el archivo equivocado
la primera vez. Busca por **`Reporte` + el nombre del cliente**, descartando las de «Estado de
cuenta», para que valga tanto «Reporte Ads — …» como el «Reporte Meta Ads — …» de los antiguos.

**2. El script, ya relleno por cliente** (esto lo hace Dirección, una vez por cuenta). Se le generan
los ficheros con `SHEET_URL` y `CLIENTE` puestos, para que no tenga que editar nada:

**No hay ningún comando que los genere** — `anadir_hoja_google.py` solo acepta `--sheet-id`,
`--anio`, `--desde-mes`, `--rehacer` y `--salida`, y al terminar se limita a decir «pegá
`google-ads-script-a-sheets.js` en la cuenta». Los `.js` por cliente ya hechos están en
`~/Desktop/SCRIPTS-GOOGLE-ADS/` (`Cliente 13.js`, `Cliente 03.js`, `Cliente 01.js`).

**Para un cliente nuevo:** copiar `Estandar-carpetas/google-ads-script-a-sheets.js` y rellenar sus
dos primeras variables, que vienen con un hueco explícito:

```js
var SHEET_URL = 'PEGAR_AQUI_LA_URL_DE_LA_HOJA';   // la hoja de reportes del cliente
var CLIENTE   = 'PEGAR_AQUI_EL_NOMBRE';           // igual que en la pestaña `datos` de Meta
```

⚠️ **`CLIENTE` tiene que escribirse EXACTAMENTE igual que en la pestaña `datos` de Meta**, o las
dos fuentes no casan en la maestra ni en Looker.

Y los pasos **en la interfaz real de Google Ads**, que no se llama como dice su documentación:

| Paso | Dónde está de verdad |
|---|---|
| 1 | **Herramientas** (llave inglesa, barra izquierda) |
| 2 | **Acciones en bloque** ← *no* «Acciones masivas» |
| 3 | **Secuencias de comandos** ← *no* «Scripts» |
| 4 | Botón **`+`** azul, pegar el `.js` entero |
| 5 | **Guardar** → sale un diálogo → **Vista previa** |
| 6 | La primera vez sale un aviso amarillo abajo con **Autorizar**. Darle y **repetir Vista previa** |
| 7 | **Frecuencia → Diariamente → 06:00** |

**«Sin cambios» en la pestaña Cambios es lo correcto**, no un error: esa pestaña lista cambios en
la *cuenta de Google Ads*, y el script no hace ninguno. Lo que importa está en **Registros**
(«Escritas N filas») y en la propia hoja.

**No antes de las 06:00:** Google consolida las cifras hasta 3 h después de medianoche.

⚠️ **La hoja tiene que estar compartida con EDICIÓN** con el Google que autoriza el script. Si
Dirección es el propietario de la hoja y entra a Ads con ese mismo correo, no hay que hacer nada.

### El fallo de la fecha (resuelto el 10-09-2026 — no repetirlo)

El script escribe la fecha y **Google Sheets la convierte a FECHA REAL**. Las fórmulas del
`Reporte Google` comparaban contra el texto `"2026-09-01"`, así que **todo el reporte salía a
cero** aunque `datos-google` tuviera 209 filas correctas. Es el mismo tropiezo que el `SUMIFS`
de Meta.

**Cómo está resuelto:** las fórmulas envuelven la fecha en `TEXT(...,"yyyy-mm-dd")`, que deja
igual lo que ya es texto y formatea lo que es fecha. Funciona en los dos casos, sin depender de
cómo lo escriba quien rellene la pestaña. Si alguna vez un reporte sale a cero con datos
debajo, **mirar primero el tipo de la celda de fecha**.

⛔ **`datos-google` SÍ se pierde al regenerar.** `construir()` no monta esas pestañas: rehace el
libro con `Reporte Meta`, `datos` y `ventas`, y `Reporte Google` y `datos-google` desaparecen. Ese
histórico solo se recupera volviendo a ejecutar el script en la cuenta de Google Ads.

**Lo que lo evita:** desde el 10-09-2026 `datos_a_mano()` también mira esas dos pestañas, así que
`montar_hoja_reportes.py` se planta antes de tocarlas. Comprobado: en Cliente 03 detecta las
**209 filas** de `datos-google` y no deja regenerar sin `--rehacer`.

### Prueba real (Cliente 03, 10-09-2026)

209 filas desde el 12-06, **4.029,35 € · 3.262 clics · 164 conversiones**. El reporte por
semanas cuadró: 298,83 € y 15 leads del 1 al 7; 110,25 € y 2 leads del 8 al 14.

**Las columnas NO son las de Meta**, y es a propósito: Google no da alcance, ni frecuencia, ni
vistas de landing (eso es el píxel). A cambio da la **cuota de impresiones**, que en Búsqueda es
lo que dice cuánto mercado te estás dejando sin cubrir.
