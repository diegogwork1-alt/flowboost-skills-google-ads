---
name: flowboost-empezar
description: Guía la PRIMERA configuración de alguien que acaba de instalar las skills de Flowboost. Comprueba qué hay en su ordenador (rclone, Drive, Python, ffmpeg), le conecta el Google Drive de la agencia paso a paso, verifica que funciona de verdad leyendo una carpeta real, y le explica qué puede pedir ya y qué no. Usar cuando alguien diga "guíame en la primera configuración", "acabo de instalar las skills", "conectá el Drive", "no me funciona nada", "¿qué necesito para empezar?", o cuando una skill falle porque falta un acceso.
---

# Primera configuración de un miembro del equipo

Alguien acaba de instalar un paquete de skills y **no sabe qué hace falta**. Esta skill lo lleva
de la mano hasta que pueda trabajar. Se habla **en castellano, sin jerga**, y se comprueba cada
paso **de verdad** antes de pasar al siguiente — nada de «ya debería funcionar».

## Regla que manda sobre todas

**No se avanza al paso siguiente sin comprobar el anterior con un comando.** Si un paso falla,
se para ahí y se resuelve. Alguien que instala esto no tiene por qué saber qué es un terminal:
si algo se le pide, se le da **el comando entero, listo para pegar**, y se le dice qué tiene que
salir.

## Paso 0 — Qué ha instalado

```bash
python3 instalar.py --revisar
```

Si no encuentra el fichero, es que no clonó el repo: se le da la orden de clonar otra vez.
La salida dice qué le falta. **Se resuelve de arriba abajo**, en ese orden.

## Paso 1 — Las herramientas

| Falta | Qué se le dice |
|---|---|
| **Python 3** | Ya viene en el Mac. Si falla de verdad: `brew install python` |
| **rclone** | `brew install rclone` — es lo que conecta con el Drive |
| **openpyxl** | `pip3 install openpyxl` — solo si va a tocar hojas de reportes |
| **ffmpeg** | `brew install ffmpeg` — **solo** si va a editar vídeo (y entonces, todo lo de `editar-vsl-cliente/INSTALACION.md`). Si no, se salta |

Si no tiene Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

## Paso 2 — Conectar el Drive de la agencia

Es el paso que más falla y el que más importa: **sin Drive no hay brief, ni branding, ni dónde
dejar nada**.

⚠️ **Nunca con el client_id compartido de rclone** (dejar `client_id` y `client_secret` en blanco
en `rclone config`). Google lo retira en 2026 y, el día que lo corte, dejan de funcionar a la vez
todas las subidas y bajadas de Drive de las skills. El remoto se conecta siempre con un **cliente
OAuth propio** (un «App de escritorio» de Google Cloud), cargado con el script de esta skill.

**2a · Conseguir el JSON del cliente.** Uno de estos dos caminos:

- **Lo normal (cuenta @flowboostmarketing.com):** pedirle a Dirección el JSON del cliente de la agencia
  (proyecto `rclone-flowboost`, cliente «App de escritorio»). Se lo pasa **por un canal privado**,
  nunca por el chat con el agente ni dentro de una skill o un repo. Como la app es **Interna**, solo
  la pueden autorizar cuentas de flowboostmarketing.com.
- **Si su cuenta no es de flowboostmarketing.com, o Dirección prefiere que tenga el suyo:** que lo cree
  él en https://console.cloud.google.com, con su cuenta (unos 10 minutos):
  1. Crear un proyecto (p. ej. «rclone»).
  2. *APIs y servicios → Biblioteca* → «Google Drive API» → **Habilitar**.
  3. *Google Auth Platform → Comenzar*: nombre «rclone», su correo. Público: **Interno** si sale;
     si no, **Externo** y después *Público → **Publicar aplicación*** («En producción»). En
     «Prueba», el permiso caduca a los 7 días.
  4. *Acceso a los datos → Agregar o quitar permisos*, pegar a mano
     `https://www.googleapis.com/auth/docs,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/drive.metadata.readonly`
     → *Agregar a la tabla* → *Actualizar* → **Save**.
  5. *Clientes → Crear cliente* → tipo **App de escritorio** → *Crear* → **Descargar JSON**, antes de
     cerrar el diálogo (después Google ya no deja bajar el secreto).

  Guía oficial: https://rclone.org/drive/#making-your-own-client-id

**2b · Conectar `gdrive:` con ese JSON.** Se le pide **solo la ruta** del archivo. El agente **no
abre el JSON** ni le pide que pegue el ID o el secreto: se los pasa el script a rclone directamente.

```bash
python3 ~/.claude/skills/flowboost-empezar/scripts/conectar_drive.py ~/Downloads/client_secret_XXXX.json
```

(En Windows: `py -3.11 $HOME\.claude\skills\flowboost-empezar\scripts\conectar_drive.py <ruta del JSON>`.)

El script guarda el JSON junto a `rclone.conf` y crea el remoto **`gdrive`** (exacto, en
minúsculas: las skills lo buscan con ese nombre), o lo actualiza si ya existía. Luego abre el
navegador, donde hay que **entrar con la cuenta de Flowboost** que le haya dado Dirección y aceptar. Si
la app es Externa, saldrá «Google no ha verificado esta aplicación»: *Configuración avanzada → Ir a
rclone*, porque la app es suya. Al terminar escribe la cuenta y cuántas carpetas ve.

**Comprobarlo de verdad** (no vale con que diga que terminó):

```bash
rclone lsd gdrive: | head -5
```

Tiene que salir una lista de carpetas de clientes (`i_…`, `c_…`) **y no puede salir** el aviso
`This remote uses rclone's shared Google Drive client_id`. Si sale vacío, da error o sale el aviso,
**no está bien conectado**: se repite el 2b.

¿Con qué Google está conectado su rclone? Sin enseñar el token:

```bash
python3 ~/.claude/skills/flowboost-empezar/scripts/conectar_drive.py --cuenta
```

## Paso 3 — Su carpeta de trabajo

```bash
mkdir -p ~/Desktop/CLIENTES && echo OK
```

Todo lo que se descarga o se crea de un cliente vive en `~/Desktop/CLIENTES/<cliente>/`. Nunca
suelto en Descargas.

## Paso 4 — Lo que hace falta SOLO en algunas áreas

Preguntarle **de qué se va a encargar** y montar solo lo suyo. No se le pide nada que no vaya a usar.

| Si lleva… | Necesita | Quién se lo da |
|---|---|---|
| **Campañas o reportes** | acceso de lectura a Meta Ads | Dirección lo añade al Business Manager |
| **Reportes** | nada más: las hojas ya están en el Drive | — |
| **Estáticos** | la cuenta de ChatGPT de la agencia | Dirección. ⚠️ **Nunca la cuenta `<correo-direccion>`** |
| **Vídeo** | bastante más que `ffmpeg`: librerías de Python, modelo de transcripción, herramientas de QC, MoneyPrinterTurbo con **su** clave de Pexels y ~8 GB de disco. **Se sigue `editar-vsl-cliente/INSTALACION.md` paso a paso** y se comprueba con `python3 ~/.claude/skills/editar-vsl-cliente/scripts/comprobar_entorno_edicion.py` | él mismo (la clave de Pexels la pone él, nunca por chat) |
| **Landings** | acceso al hosting del cliente | Dirección, cuando toque publicar |

⚠️ **Nunca se le piden contraseñas ni claves por chat, ni se las teclea el agente.** Si algo
necesita una clave, la pone él en su ordenador y se le explica dónde.

## Paso 5 — La prueba real

No se da por terminado hasta que esto funcione:

```bash
rclone lsd gdrive: | wc -l
```

Si sale un número mayor que cero, y sin el aviso del client_id compartido, está listo. Entonces se le dice **qué puede pedir ya**, con
ejemplos de su área:

- Reportes: *«dame el reporte de \<cliente\>»*, *«da de alta a \<cliente\> en los reportes»*
- Campañas: *«armá la campaña de \<cliente\>»* (se crea en pausa; activar es siempre de Dirección)
- Estáticos: *«armá los estáticos de \<cliente\>»*
- Landings: *«escribí el copy de la landing de \<cliente\>»*

## Y lo que tiene que saber desde el minuto uno

- **Todo el texto para clientes va en español de España.** Nunca voseo.
- **No se inventa nada**: cifras, testimonios, fechas ni garantías. Lo que falte se marca `[FALTA]`.
- **El Drive del cliente es de solo lectura**, salvo los entregables en su carpeta.
- **Activar una campaña es siempre de Dirección.** El agente las deja en pausa.
- **Si falta un acceso, se avisa y se para.** No se sigue a medias.

## Si algo se rompe

| Síntoma | Casi siempre es |
|---|---|
| «no encuentro la carpeta del cliente» | el Drive no está conectado → paso 2 |
| «no existe el fichero …» | falta el paquete **fundamentos** → instalarlo también |
| el copy sale sin criterio | lo mismo: falta **fundamentos**, y no avisa solo |
| «command not found: rclone» | paso 1 |
| sale `This remote uses rclone's shared Google Drive client_id` | el remoto está sin cliente propio → paso 2 (2a y 2b) |
