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

```bash
rclone config
```

Y se le va diciendo, una a una, qué teclear:

1. `n` (nuevo remoto)
2. Nombre: **`gdrive`** ← exacto, en minúsculas. Las skills lo buscan con ese nombre.
3. Tipo: escribir **`drive`**
4. `client_id` y `client_secret`: **Enter** (en blanco)
5. Ámbito: **`1`** (acceso completo)
6. `root_folder_id`: **Enter**
7. Service account: **Enter**
8. Configuración avanzada: **`n`**
9. Usar navegador: **`y`** → se abre Chrome → **entrar con la cuenta de Flowboost** que le haya
   dado Dirección, y aceptar
10. Shared drive: **`n`** · Confirmar: **`y`** · Salir: **`q`**

**Comprobarlo de verdad** (no vale con que diga que terminó):

```bash
rclone lsd gdrive: | head -5
```

Tiene que salir una lista de carpetas de clientes (`i_…`, `c_…`). Si sale vacío o da error, **no
está conectado**: se repite el paso 2.

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

Si sale un número mayor que cero, está listo. Entonces se le dice **qué puede pedir ya**, con
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
