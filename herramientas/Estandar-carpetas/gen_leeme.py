#!/usr/bin/env python3
"""Genera un LEEME.md por skill: lo que hay que tener en cuenta ANTES de tocarla.

Pensado para quien recibe solo el paquete de su área y no ha estado en las conversaciones
donde se fijaron estas reglas. Se regenera; no se edita a mano.
"""
import os, re, json, subprocess

RAIZ = os.path.expanduser("~/.claude/skills")

AREA = {"fundamentos-copy":"fundamentos",
 "brief-desde-onboarding":"onboarding","radar-competencia":"onboarding",
 "estaticos-meta":"creatividades","copy-anuncios-meta":"creatividades",
 "guiones-egc":"guiones","guion-vsl":"guiones","auditar-guiones-egc":"guiones",
 "editar-vsl-cliente":"video","editar-ad-meta-9x16":"video",
 "armar-campana-meta":"meta-ads","gestion-cuenta-meta":"meta-ads",
 "keywords-google-ads":"meta-ads","reportes-cliente":"meta-ads",
 "contenido-organico":"organico","funnel":"direccion","montar-crm-cliente":"direccion","informe-landing-clarity":"direccion"}
for s in ["landing-b2b-alto-ticket","landing-b2b-copy-html","landing-b2b-index-html","landing-conversion",
 "landing-conversion-copy-html","landing-inmueble-copy-html","landing-vsl-directa",
 "landing-vsl-directa-copy-html","landing-vsl-directa-index-html","copy-b2b-alto-ticket",
 "copy-vsl-directa","publicar-landing","pagina-gracias","impeccable"]: AREA[s]="landing"

# Lo que NO se deduce del código: sale de las decisiones de Dirección. Formato: (necesita, prohibido, ojo)
NOTAS = {
"contenido-organico": dict(
 necesita=["El **brief real** del cliente. Es lo único que la skill pide; sin brief no arranca.",
   "**NotebookLM operativo** (`notebooklm login`): monta una libreta de intereses por cliente. Si no hay acceso, sigue con búsqueda directa y lo anota.",
   "Saber **qué cuentas tiene abiertas** el cliente y **quién puede salir en cámara**."],
 prohibido=["⛔ **LinkedIn.** Decisión de Dirección (21-09-2026): las plataformas son Instagram, TikTok y Facebook.",
   "⛔ **Cebo de interacción** («comenta SÍ», «escribe GUÍA y te lo mando»): lo penalizan las tres plataformas.",
   "⛔ **«Enlace en la bio»** como CTA: muerto desde abril de 2026.",
   "⛔ Republicar contenido ajeno o subir vídeo con marca de agua de otra red: saca la cuenta de las recomendaciones."],
 ojo=["**El vídeo nace en TikTok.** A las 48 h, lo que pasa el listón se adapta a Reel de Instagram y después a Reel de Facebook de 90 s. Nunca a la vez en dos redes.",
   "**Los Trial Reels prueban el gancho**, una sola variable por prueba, y se comparan solo entre ellos.",
   "**La base de investigación caduca a los 3 meses**: en 2026 los algoritmos cambiaron casi cada mes. La fecha está en la cabecera de `references/base-investigacion.md`.",
   "**Capacidad por defecto: 4 piezas únicas por semana.** Las adaptaciones a otra red no cuentan como pieza."]),
"estaticos-meta": dict(
 necesita=["El **brief real** del cliente (`0. Onboarding/Brief_<Cliente>.pdf`) **convertido a TXT** con `brief_a_texto.py` — el PDF a veces no sube al GPT y falla en silencio.",
   "**Branding de Drive** (`1. Branding`): logo oficial, paleta y tipografías del MANUAL, no de un anuncio viejo. Si falta, se pide; no se inventa la marca.",
   "Sesión de ChatGPT en el workspace de **Flowboost empresa**."],
 prohibido=["⛔ **Entrar con `<correo-direccion>`.** El GPT se usa SIEMPRE con `<correo-cuenta-de-trabajo>`. Verificar el perfil de Chrome ANTES de pegar nada.",
   "⛔ **Adjuntar estáticos de otros clientes** al GPT: se confunde. El registro visual se le describe con palabras.",
   "⛔ Publicar una pieza con **testimonios generados** si la marca `[REEMPLAZAR]` no está **dentro del PNG**."],
 ojo=["**Primero los estáticos, después los guiones.** Es el orden que fijó Dirección para lanzar en 48 h.",
   "En **advertorial no va el logo**: va un masthead de periódico, y el logo baja a firma de pie.",
   "**El hook SEGMENTA**: cada pieza habla a un avatar distinto, variando el eje (identidad / situación / dolor / creencia).",
   "**El 9:16 rehace el ENCUADRE y solo el encuadre.** Botón, halo, pesos de letra, dónde vive el color y los props de la foto: idénticos al 1:1. Ver `references/refs/FlowboostDubai_LEEME.md` §DERIVA.",
   "Safe zones de Stories: **270 px arriba, 384 px abajo**; margen lateral de la casa **107 px** (65 es el mínimo técnico, no el objetivo)."]),
"armar-campana-meta": dict(
 necesita=["**El presupuesto diario. Es PUERTA 0.** Sin él no se emite ninguna configuración: se busca en el contrato → ESTADO.md → lo que gasta la cuenta, y si no aparece, se PARA y se pregunta.",
   "Identificadores reales: cuenta, página, píxel y URL de destino."],
 prohibido=["⛔ **ACTIVAR una campaña.** La activación es SIEMPRE de Dirección, con OK explícito. Todo se crea `PAUSED`.",
   "⛔ **Copiar parámetros de las cuentas de clientes existentes.** De ahí venían los errores. Todo sale de `../gestion-cuenta-meta/references/parametros-campana.md`.",
   "⛔ Montar conjuntos por debajo de **30 €/día**: antes se monta un conjunto menos."],
 ojo=["La estructura no se improvisa: se ejecuta `scripts/plan_campana.py <€/día>` y se copia el bloque del tramo en `references/matriz-campanas.md`.",
   "Objetivo **Ventas** con evento `Engaged Lead`, nunca 'Clientes potenciales'.",
   "**Categoría especial** (vivienda, crédito, empleo, temas sociales): declararla mal puede costar la cuenta. Se avisa a Dirección con `avisar.py --nivel urgente` ANTES de crear."]),
"gestion-cuenta-meta": dict(
 necesita=["Acceso de **solo lectura** a la cuenta y el TCPL (coste objetivo por lead cualificado) del cliente."],
 prohibido=["⛔ **Ejecutar cambios.** Esta skill PROPONE. Mover presupuesto, pausar, escalar o matar lo decide Dirección."],
 ojo=["`references/parametros-campana.md` es **la fuente única de los números** de toda la casa: lo lee también `armar-campana-meta`. Si un número de otra skill no coincide con este fichero, manda este fichero.",
   "Nada se toca en las primeras **72 h** de un conjunto nuevo: reinicia el aprendizaje."]),
"funnel": dict(
 necesita=["El nombre del cliente y su `ESTADO.md`."],
 prohibido=["⛔ Marcar una etapa como hecha si el mensaje al cliente **no ha salido de verdad**. Preparado ≠ enviado."],
 ojo=["Corre **tres carriles a la vez**: A-lanzamiento (48 h, estáticos + landing sin VSL), B-vídeo (guiones → grabación → el VSL entra en la landing ya publicada) y C-operación.",
   "**El formulario y la página de gracias los hace Dirección**, no el agente.",
   "Si una etapa no tiene canal para llegar al cliente, se avisa **en el momento** con `avisar.py --nivel urgente`, no al final en el resumen."]),
"publicar-landing": dict(
 necesita=["La landing **aprobada**, y el **DNS del cliente** — es el DNS quien decide el hosting, no hay uno fijo."],
 prohibido=["⛔ Teclear credenciales de hosting, DNS o WordPress. Las pone Dirección."],
 ojo=["Incluye página de gracias, medición, aviso de cookies conforme al RGPD y base de datos de leads.",
   "Al terminar encadena con `montar-crm-cliente`."]),
"pagina-gracias": dict(
 necesita=["La URL de la landing publicada y los campos reales del formulario de Tally."],
 prohibido=["⛔ Quemar el número de WhatsApp: **el lead INICIA la conversación**, nunca al revés."],
 ojo=["**El formulario y esta página son trabajo de Dirección** (los hace con su GPT). Esta skill define la estructura y la lógica, no sustituye ese trabajo.",
   "Va con `noindex`."]),
"montar-crm-cliente": dict(
 necesita=["Acceso al VPS y el subdominio del cliente."],
 prohibido=["⛔ **Generar o teclear la clave de API.** La genera Dirección, y él invita al cliente. El agente solo avisa después con la URL."],
 ojo=["La columna **«Ganado» alimenta la hoja de reportes**: es lo que convierte el ROAS de estimación en dato real.",
   "Lo primero que hace el comercial tras cerrar una venta es actualizar el CRM."]),
"informe-landing-clarity": dict(
 necesita=["Token de Clarity del cliente y acceso a la landing."],
 prohibido=["⛔ **Enviarlo al cliente.** Es INTERNO: llega solo a `<correo-direccion>`, los viernes.",
   "⛔ Meter métricas de Meta (gasto, leads, CPL). Eso es el reporte del cliente, no éste."],
 ojo=["Habla de la landing: comportamiento, fricción, roturas. Cero euros."]),
"reportes-cliente": dict(
 necesita=["El **`ad_account_id`** del cliente y el **`sheet_id`** de su hoja, en la pestaña `clientes` de la maestra `Flowboost · Datos Meta`. Sin esos dos campos el flujo diario se salta al cliente.",
   "El **`META_TOKEN`** en el VPS (usuario del sistema, `ads_read` + «Ver rendimiento»). Sin él no se actualiza nada."],
 prohibido=["⛔ **Mandar el reporte por correo.** El envío está RETIRADO (Dirección, 10-09-2026): no se manda a nadie, ni de prueba. El cliente entra a su hoja.",
   "⛔ **Enseñar cifras sin comprobar antes que la cuenta es la de ESE cliente.** Las cuentas no se identifican por las iniciales: se mira que las campañas encajen con su negocio.",
   "⛔ **Regenerar una hoja que ya está en uso.** Borra los cierres, el ticket, el margen y las pestañas de Google. `montar_hoja_reportes.py` se planta; no forzarlo con `--rehacer` sin rescatar antes lo escrito.",
   "⛔ **Escribir en Meta.** Solo lectura de insights: a Dirección le restringieron una cuenta por enlazar herramientas."],
 ojo=["**Una semana a medias YA enseña sus datos.** No hay que esperar a que se cierren los 7 días: la fila en curso se rellena cada mañana. Pero una fila incompleta no sirve para decidir.",
   "**A mano van tres cosas una vez** —ticket medio, margen y **fee de agencia al mes** (viene con 1.100 € puesto)— **y el NÚMERO de cierres cada semana**, en la columna «Cierres (a mano)». Lo demás se calcula. Todo lo manual lleva «(a mano)» en el rótulo.",
   "**El ROAS se mide contra el COSTE TOTAL** (inversión + la parte del fee que toca a esa semana), no contra la inversión sola: el cliente paga las dos cosas. Ojo: el fee entero se carga a los DOS reportes, así que sumar las dos columnas «Coste total» lo cuenta dos veces.",
   "**El coste por lead que ve el cliente es BRUTO.** El real es del orden de 2,5×. Internamente nunca se decide con el bruto.",
   "**Ya no hay correo que empuje a mirar los números.** La hoja se actualiza en silencio: si nadie la abre, nadie se entera. Quien la mira es `gestion-cuenta-meta` en la revisión semanal.",
   "Un ratio del mes se calcula **sobre las sumas del mes**, nunca promediando los ratios de las semanas: las semanas que no han pasado valen cero y hunden la media."]),
"brief-desde-onboarding": dict(
 necesita=["La **transcripción literal** de la llamada de onboarding."],
 prohibido=["⛔ **Inventar datos.** Fuente única = la transcripción. Lo deducible va marcado `[Inferencia]`; lo que falta va al fichero interno, nunca al brief visible."],
 ojo=["El brief resultante es la fuente de TODO lo que viene después: estáticos, copy, guiones y landing lo leen tal cual."]),
"radar-competencia": dict(
 necesita=["Los competidores del brief."],
 prohibido=["⛔ Nombrar competidores en el copy de los anuncios (regla legal)."],
 ojo=["Se dispara al terminar el brief. Los 'ganadores' son los anuncios que llevan más tiempo corriendo."]),
"guiones-egc": dict(
 necesita=["El brief real del Drive."],
 prohibido=["⛔ Voseo. Español de España.", "⛔ Entregar alternativas A/B/C de gancho: se elige uno y se entrega final."],
 ojo=["**5 guiones = 5 ángulos = 5 avatares distintos**, y el hook de cada uno segmenta a su avatar.",
   "Máximo 40 s ≈ 136 palabras. Pasa por `auditar-guiones-egc` en pasada separada."]),
"guion-vsl": dict(
 necesita=["El brief real del Drive."],
 prohibido=["⛔ Voseo. Español de España.", "⛔ Pasar de **8 minutos** (tope 1.150 palabras). El ideal son 5-6 min / 700-865 palabras; entre 865 y 1.150 se puede, pero hay que justificarlo. *(Dirección subió el tope de 6 a 8 min el 12-09-2026.)*"],
 ojo=["Estructura de la casa en 5 pasos: Hook → Retorcer el cuchillo → Solución → Imagina esto → CTA."]),
"auditar-guiones-egc": dict(
 necesita=["Los ficheros `Script N - PARA GRABAR.md` ya escritos."],
 prohibido=["⛔ Reescribir el guion. Esta skill audita y devuelve correcciones; el que reescribe es `guiones-egc`."],
 ojo=["Rechazado por defecto. Se audita **sin ver el razonamiento** de quien lo escribió."]),
"editar-vsl-cliente": dict(
 necesita=["**Colores y tipografías del cliente** (se preguntan, no se inventan), logo PNG con alpha, y el vídeo (crudo + guion, o ya cortado)."],
 prohibido=["⛔ **Recrear el logo con HTML o texto.** Se usa el PNG real. Ya pasó dos veces.",
   "⛔ Emojis: iconos SVG recoloreados a la marca."],
 ojo=["Regla de oro: la animación entra **exacta con la palabra dicha**, nunca antes (reveal-on-mention, DELAY 0.38 s). Nada estático más de 3 s.",
   "**Leer `references/aprendizajes-y-feedback.md` ENTERO antes de editar** y añadir una entrada cada vez que Dirección corrige algo.",
   "El VSL también lleva su título; render CRF16 y mux `-c:v copy`."]),
"editar-ad-meta-9x16": dict(
 necesita=["Colores, tipografías y logo del cliente. El motor se copia de `editar-vsl-cliente`, no se reconstruye."],
 prohibido=["⛔ Recrear el logo a mano.", "⛔ Pasar de 1:30 (ideal 20-45 s)."],
 ojo=["Aquí los **subtítulos SÍ van quemados** (karaoke), al revés que en el VSL: el anuncio se ve sin sonido.",
   "Hook en los primeros 3 s y respeto de la UI de Meta arriba, abajo y a la derecha."]),
"copy-anuncios-meta": dict(
 necesita=["El estático ya producido y el guion del vídeo de ese anuncio."],
 prohibido=["⛔ Inventar cifras o testimonios: lo que falte se marca `[FALTA]`."],
 ojo=["Da 2-3 variantes por campo para testear. Alimenta a `armar-campana-meta`."]),
"keywords-google-ads": dict(
 necesita=["Confirmación de que **el cliente quiere Google Ads**."],
 prohibido=[],
 ojo=["**Es condicional: NO forma parte del funnel estándar de Meta.** Solo se ejecuta si Dirección lo pide."]),
"impeccable": dict(necesita=[],prohibido=[],
 ojo=["Es una skill de criterio de diseño: la invocan las de landing bloque a bloque, no produce entregables por sí sola."]),
"fundamentos-copy": dict(
 necesita=[],
 prohibido=["⛔ Duplicar estos ficheros dentro de otra skill. Hasta el 10-09-2026 había cuatro copias divergentes de `ogilvy-principios.md`; si aparece otra, se borra y se apunta aquí.",
   "⛔ Leer los PDFs enteros: son 18,5 MB. Se abren con `pages` para la cita exacta."],
 ojo=["**No se invoca sola**: la leen las skills de estáticos, copy, guiones, VSL y landings.",
   "Resumen para REDACTAR, `ogilvy-reglas-reales.md` para AUDITAR. Si chocan, ganan las reglas reales."]),
}
DEF_LANDING = dict(
 necesita=["El copy aprobado (o el brief, si la skill también redacta) y los tokens de marca del cliente."],
 prohibido=["⛔ Inventar testimonios, cifras, fechas o garantías."],
 ojo=["Cada bloque pasa por `impeccable`, `design-taste-frontend` y `emil-design-eng` antes de darse por bueno.",
   "En cada corrección se devuelve el **HTML completo de la sección**, nunca fragmentos sueltos."])

TRANSVERSAL = """## Reglas de la casa (valen para todas las skills)

- **Todo el texto para clientes en español de España** (tú/vosotros). Nunca voseo ni LATAM.
- **No se inventa nada**: cifras, testimonios, fechas, garantías o casos. Lo que falte se marca `[FALTA]` y se pide.
- **Las fechas salen del reloj del sistema** (`date +%d/%m/%Y`), nunca de memoria.
- **Los ficheros de un cliente van a `~/Desktop/CLIENTES/<cliente>/`**, nunca sueltos en Descargas.
- **El Drive del cliente es de SOLO LECTURA**, salvo los entregables en su subcarpeta correcta. No se mueve, borra ni renombra nada.
- **Nunca se sube un `.md` crudo al Drive del cliente**: se convierte a Google Doc.
- **Nunca se teclean contraseñas, claves de API ni tokens**, aunque te los den. Los pone Dirección.
- **Para avisar a Dirección se usa `avisar.py`** (`--nivel urgente|aviso|info`), no un mensaje suelto que nadie lee."""

def frontmatter(d, campo):
    p = os.path.join(RAIZ, d, "SKILL.md")
    dentro = False; buf = []
    for ln in open(p, encoding="utf-8"):
        if ln.strip() == "---":
            if dentro: break
            dentro = True; continue
        if not dentro: continue
        if ln.startswith(campo + ":"): buf = [ln.split(":", 1)[1].strip()]
        elif buf and ln.startswith((" ", "\t")): buf.append(ln.strip())
        elif buf: break
    return " ".join(buf)

def primera_frase(t, n=2):
    fr = re.split(r'(?<=[.!?])\s+', t)
    return " ".join(fr[:n]).strip()

def genera(d, info):
    area = AREA.get(d, "?")
    desc = frontmatter(d, "description")
    nota = NOTAS.get(d) or (DEF_LANDING if area == "landing" else dict(necesita=[], prohibido=[], ojo=[]))
    L = [f"# LEEME — `{d}`", "",
         f"> Paquete **{area}**. Esto es lo que hay que tener en cuenta **antes** de usar la skill.",
         "> Las instrucciones de trabajo están en `SKILL.md`; esto son las condiciones y los límites.", ""]
    L += ["## Qué hace", "", primera_frase(desc, 2), ""]
    no = re.findall(r'(?:NO |No )(?:maqueta|redacta|genera|produce|escribe|hace|usar)[^.]*\.', desc)
    if no: L += ["**Qué NO hace:** " + " ".join(no[:2]), ""]

    L += ["## Antes de empezar necesitás", ""]
    if info["deps"]:
        otros = [x for x in info["deps"] if x != "fundamentos-copy"]
        if "fundamentos-copy" in info["deps"]:
            L.append("- **El paquete `fundamentos` instalado al lado** (`npx skills add <owner>/flowboost-skills-fundamentos --copy`). "
                     "Esta skill lee Ogilvy, Schwartz y el compliance de Meta desde `../fundamentos-copy/`. "
                     "**Si no está, la skill funciona a medias y NO avisa.**")
        for o in otros:
            L.append(f"- La skill **`{o}`** (paquete *{AREA.get(o,'?')}*): lee ficheros suyos.")
    for x in nota["necesita"]: L.append("- " + x)
    if not info["deps"] and not nota["necesita"]:
        L.append("- Nada externo: es autónoma.")
    L.append("")

    if nota["prohibido"]:
        L += ["## Lo que NO se puede hacer", ""] + ["- " + x for x in nota["prohibido"]] + [""]
    if nota["ojo"]:
        L += ["## Ojo con esto", ""] + ["- " + x for x in nota["ojo"]] + [""]

    if info["aprendizajes"]:
        L += ["## Lectura obligatoria antes de trabajar", "",
              "Esta skill **aprende de los errores**. Leer y, cuando Dirección corrija algo, **añadir la entrada en la misma sesión**:", ""]
        L += [f"- `{a}`" for a in info["aprendizajes"]] + [""]
    if info["scripts"]:
        L += ["## Scripts que trae", ""] + [f"- `{s}`" for s in info["scripts"]] + [""]

    # Quién toca de verdad la cuenta de Meta (lista explícita: detectarlo por "píxel" daba falsos positivos)
    META = {"armar-campana-meta":"cuenta de Meta Ads — **crea entidades, siempre EN PAUSA; activar es de Dirección**",
            "gestion-cuenta-meta":"cuenta de Meta Ads — **solo lectura**, propone y no ejecuta",
            "radar-competencia":"Biblioteca de Anuncios de Meta (pública, solo lectura)",
            "reportes-cliente":"cuenta de Meta Ads — **solo lectura** (insights) · Google Ads (script dentro de la cuenta, solo escribe en la hoja)",
            "informe-landing-clarity":"cuenta de Meta Ads — **solo lectura** (gasto y leads por campaña) + Microsoft Clarity",
            "estaticos-meta":"cuenta de Meta Ads — **solo lectura** (para mirar los ganadores reales)"}
    accesos = []
    if info["drive"]: accesos.append("Google Drive del cliente (solo lectura salvo entregables)")
    if d in META: accesos.append(META[d])
    accesos += [t for k, t in [("chrome","Chrome con sesión de ChatGPT"),("vps","VPS por SSH"),
                               ("n8n","n8n"),("tally","Tally (formulario)")] if info[k]]
    if accesos:
        L += ["## Accesos que toca", "", ", ".join(accesos) + ".", ""]

    L += [TRANSVERSAL, "", "---", "",
          "*Generado el 10-09-2026 desde el sistema de Flowboost. Se regenera con `gen_leeme.py`; no editar a mano.*"]
    return "\n".join(L) + "\n"

def analizar():
    """Recorre las skills y saca dependencias, scripts, aprendizajes y accesos.

    Antes esto vivía en un script aparte que dejaba un JSON en /tmp, y bastaba con que ese
    JSON estuviera viejo para regenerar los LEEME con datos caducados (pasó al renombrar
    `reportes-cliente`). Ahora se calcula aquí cada vez.
    """
    import re
    cwd = os.getcwd(); os.chdir(RAIZ)
    propias = [d for d in sorted(os.listdir(".")) if os.path.isdir(d) and not os.path.islink(d)]
    out = {}
    for d in propias:
        i = {"deps": set(), "scripts": [], "aprendizajes": [], "drive": False, "meta": False,
             "chrome": False, "vps": False, "n8n": False, "tally": False}
        for root, _, fs in os.walk(d):
            for f in fs:
                pp = os.path.join(root, f)
                if f.endswith((".py", ".sh")): i["scripts"].append(os.path.relpath(pp, d))
                if re.search(r"(errores|aprendizaje|feedback|registro)", f, re.I) and f.endswith(".md"):
                    i["aprendizajes"].append(os.path.relpath(pp, d))
                if not f.endswith(".md"): continue
                t = open(pp, encoding="utf-8", errors="ignore").read()
                for m in re.findall(r"\.\./+([a-z0-9][a-z0-9-]{3,})/", t):
                    if m in propias and m != d: i["deps"].add(m)
                low = t.lower()
                if re.search(r"\bdrive\b", low): i["drive"] = True
                if re.search(r"meta ads|\bads_|campañas? de meta|píxel", low): i["meta"] = True
                if re.search(r"claude-in-chrome|chatgpt", low): i["chrome"] = True
                if re.search(r"\bvps\b|ssh -i", low): i["vps"] = True
                if re.search(r"\bn8n\b", low): i["n8n"] = True
                if re.search(r"\btally\b", low): i["tally"] = True
        i["deps"] = sorted(i["deps"]); i["scripts"] = sorted(set(i["scripts"]))[:6]
        i["aprendizajes"] = sorted(set(i["aprendizajes"]))[:4]
        out[d] = i
    os.chdir(cwd)
    return out


if __name__ == "__main__":
    info = analizar()
    n = 0
    for d in sorted(info):
        open(os.path.join(RAIZ, d, "LEEME.md"), "w", encoding="utf-8").write(genera(d, info[d]))
        n += 1
    print(f"{n} LEEME.md generados")
