#!/usr/bin/env python3
"""FASE 0 en una llamada: deja los insumos de la tanda en `Insumos/` con nombres fijos, los valida
y escribe el manifiesto. Sustituye el ir y venir a Drive del principio.

Por qué (consejo, 13-09-2026). La Fase 0 era buscar a mano en Drive el brief, el logo final, el
manual y las fotos, y cada tanda repetía el recorrido. Si Dirección pasa el material al empezar, no hace
falta entrar a Drive hasta el final (a subir). Pero el material pasado a mano quita un control —un
logo en JPG, un brief viejo, reseñas olvidadas—, así que este script **para con error** si falta lo
imprescindible y **avisa** de lo que degrada la tanda, antes de gastar una sola generación.

Tres formas de darle el material (se pueden mezclar):
  --desde <ficheros o carpetas>     lo clasifica solo por nombre (brief, logo, manual/guía, reseñas…)
  --brief --logo --guia --fotos --personas --resenas --variar   explícito, gana a --desde
  --drive                            lo baja del Drive del cliente (la Fase 0 de siempre, automática)
Si no se pasa nada, valida lo que ya haya en `Insumos/`.

Uso:
  python3 preparar_tanda.py "Cliente 04" --desde ~/Downloads/brief.pdf ~/Downloads/logo.png ~/Downloads/manual.pdf
  python3 preparar_tanda.py "Cliente 13" --modo variaciones --variar pieza1.png pieza2.png --logo logo.png
  python3 preparar_tanda.py "Cliente 11" --drive
  python3 preparar_tanda.py "Cliente 07" --skill estaticos-inmobiliario-meta --desde ~/Downloads/insumos/
    (inmobiliario: clasifica renders/ y permisos/, nunca sube el QR al GPT, no admite --drive ni lanza casting)

Sale con 0 (todo listo), 2 (listo con avisos: se produce y los avisos van al specs/resumen)
o 1 (falta algo imprescindible: no se abre Chrome).
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tanda_lib as L

IMG = (".png", ".jpg", ".jpeg", ".webp")
TOPE_SUBIDA = 9_500_000  # ChatGPT corta a 10 MB por llamada de file_upload (chrome-rapido.md §1)
INMO = "estaticos-inmobiliario-meta"  # opt-in: sin --skill todo se comporta como antes


def clasificar(ruta, skill="estaticos-meta"):
    n = os.path.basename(ruta).lower()
    ext = os.path.splitext(n)[1]
    if re.search(r"brief|onboarding", n) and ext in (".txt", ".md", ".pdf", ".docx"):
        return "brief"
    if skill == INMO and re.search(r"qr|madmoun|trakheesi|permit|permiso", n):
        return "permisos"  # QR antes que logo: un `logo_qr.png` nunca se sube al GPT
    if "logo" in n or "isotipo" in n or "logotipo" in n:
        return "logo"
    if skill == INMO:
        if re.search(r"qr|madmoun|trakheesi|permit|permiso|escrow|(^|[^a-z])(noc|nma)([^a-z]|$)|form[\s_-]?a([^a-z]|$)", n):
            return "permisos"
        # En inmobiliario toda imagen que no sea logo, persona, reseña o guía es foto/render del inmueble.
        if ext in IMG and not re.search(r"persona|avatar|rese[nñ]a|review|testimon|interview|entrevista|manual|gu[ií]a|paleta|colou?r|branding|identidad", n):
            return "renders"
    if re.search(r"manual|gu[ií]a|branding|identidad|brand|paleta|colou?r", n):
        return "guia"
    if re.search(r"rese[nñ]a|review|opinion|testimon", n):
        return "resenas"
    if re.search(r"persona|avatar", n):
        return "personas"
    if re.search(r"variar|original|referencia|ref_|^var\d", n) and ext in IMG:
        return "variar"
    if ext in IMG:
        return "fotos"
    return None


PIEZAS_INMO = ["01", "02", "03", "04", "05", "06", "07", "08"]


def validar_permisos(ruta_csv, carpeta):
    """Lee `Insumos/permisos/permisos.csv` (estaticos-inmobiliario-meta) y devuelve los avisos por pieza.
    Columnas: pieza,permiso_trakheesi,caducidad,qr,tipo,noc,escrow,form_a,agentes,empresa,datos_permiso,nma,nma_caducidad
    Todo aviso significa `_PEND` administrativo (no cuenta para el freno). Formato en mercados/dubai-eau.md §1."""
    import csv as _csv
    hoy = dt.date.today()
    out = []

    def fecha(valor, pz, que):
        if not valor:
            out.append(f"permisos.csv pieza {pz}: falta la caducidad de {que} → _PEND")
            return
        try:
            if dt.date.fromisoformat(valor) < hoy:
                out.append(f"permisos.csv pieza {pz}: {que} caducado el {valor} → _PEND")
        except ValueError:
            out.append(f"permisos.csv pieza {pz}: caducidad de {que} «{valor}» no es AAAA-MM-DD → _PEND")

    filas = list(_csv.DictReader(open(ruta_csv, encoding="utf-8")))
    vistas = set()
    for f in filas:
        g = {k: (v or "").strip() for k, v in f.items() if k}
        pz = g.get("pieza", "?").zfill(2)
        vistas.add(pz)
        tipo = g.get("tipo", "").lower()
        per = g.get("permiso_trakheesi", "")
        if not per:
            out.append(f"permisos.csv pieza {pz}: sin permiso Trakheesi" + (" (anuncio de marca: falta confirmar si lo necesita)" if tipo == "marca" else "") + " → _PEND")
        else:
            if not (per.isdigit() and len(per) == 10):
                out.append(f"permisos.csv pieza {pz}: el permiso «{per}» no tiene 10 dígitos → _PEND")
            fecha(g.get("caducidad", ""), pz, "el permiso Trakheesi")
            qr = g.get("qr", "")
            if not qr or not os.path.exists(os.path.join(carpeta, qr)):
                out.append(f"permisos.csv pieza {pz}: el QR «{qr or '—'}» no está en Insumos/permisos/ → _PEND")
            if not g.get("empresa"):
                out.append(f"permisos.csv pieza {pz}: falta la empresa titular del permiso (tiene que ser la anunciante) → _PEND")
            if not g.get("datos_permiso"):
                out.append(f"permisos.csv pieza {pz}: faltan los datos aprobados en el permiso (precio, proyecto, unidad) para cotejar la pieza → _PEND")
        si = lambda k: g.get(k, "").lower() in ("si", "sí", "yes", "true", "1", "x")
        if tipo == "off-plan" and not (si("noc") and si("escrow")):
            out.append(f"permisos.csv pieza {pz}: off-plan sin NOC y escrow confirmados → _PEND")
        elif tipo == "reventa":
            if not si("form_a"):
                out.append(f"permisos.csv pieza {pz}: reventa sin Form A confirmado → _PEND")
            ag = g.get("agentes", "")
            if not ag.isdigit() or int(ag) > 3:
                out.append(f"permisos.csv pieza {pz}: reventa sin confirmar que la anuncian 3 agentes o menos (columna agentes) → _PEND")
        elif tipo not in ("off-plan", "reventa", "marca"):
            out.append(f"permisos.csv pieza {pz}: tipo «{tipo or '—'}» no es off-plan, reventa ni marca → _PEND")
        if not g.get("nma"):
            out.append(f"permisos.csv pieza {pz}: sin nº de permiso de anunciante NMA → _PEND")
        else:
            fecha(g.get("nma_caducidad", ""), pz, "el permiso NMA")
    faltan = [x for x in PIEZAS_INMO if x not in vistas]
    if faltan:
        out.append("permisos.csv no tiene fila para las piezas " + ", ".join(faltan) + " → esas piezas _PEND")
    return out


def expandir(rutas):
    out = []
    for r in rutas or []:
        r = os.path.expanduser(r)
        if os.path.isdir(r):
            out += sorted(p for p in glob.glob(os.path.join(r, "**", "*"), recursive=True)
                          if os.path.isfile(p) and not os.path.basename(p).startswith("."))
        elif os.path.isfile(r):
            out.append(r)
        else:
            print(f"✗ No existe: {r}")
    return out


def copiar(src, carpeta, nombre=None):
    os.makedirs(carpeta, exist_ok=True)
    dst = os.path.join(carpeta, nombre or os.path.basename(src))
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)
    return dst


def brief_a_txt(src, cli, ins):
    """Deja `Brief_<C>_para_GPT.txt`. El PDF no se sube al GPT: ya se inventó el cliente una vez."""
    dst = os.path.join(ins, f"Brief_{cli.replace(' ', '')}_para_GPT.txt")
    ext = os.path.splitext(src)[1].lower()
    if ext in (".txt", ".md"):
        texto = open(src, encoding="utf-8", errors="replace").read()
    elif ext == ".pdf":
        import fitz
        texto = "\n".join(p.get_text() for p in fitz.open(src))
    elif ext == ".docx":
        if shutil.which("textutil"):   # Mac
            r = subprocess.run(["textutil", "-convert", "txt", "-stdout", src], capture_output=True, text=True)
            texto = r.stdout
        else:                          # Windows/Linux: no hay textutil → se lee el XML del .docx con Python puro
            import zipfile, html as _h
            xml = zipfile.ZipFile(src).read("word/document.xml").decode("utf-8", "replace")
            xml = re.sub(r"</w:p>", "\n", xml)
            xml = re.sub(r"<w:tab/>", "\t", xml)
            texto = _h.unescape(re.sub(r"<[^>]+>", "", xml))
    else:
        return None, 0
    texto = re.sub(r"\n{3,}", "\n\n", texto.replace("\x0c", "\n")).strip() + "\n"
    open(dst, "w", encoding="utf-8").write(texto)
    return dst, len(texto)


def bajar_drive(cli, ins):
    """La Fase 0 de siempre, en una sola pasada de rclone. Nunca `Logos Antiguos`."""
    base = L.drive_base(cli)
    if not base:
        print(f"✗ {cli} no existe en Drive (la carpeta la crea Operaciones). Se sigue solo con lo local.")
        return
    pasos = [
        (base + "0. Onboarding/", os.path.join(ins, "_drive", "brief"), ["--include", "Brief*"]),
        (base + "0. Onboarding/Reseñas/", os.path.join(ins, "resenas"), []),
        (base + "1. Branding/", os.path.join(ins, "logo"),
         ["--include", "**Archivos_Finales*/RGB/02_PNG/*.png", "--exclude", "**Logos Antiguos**"]),
        (base + "1. Branding/", os.path.join(ins, "guia"),
         ["--include", "**[Mm]anual*.pdf", "--include", "**[Gg]u[ií]a*", "--exclude", "**Logos Antiguos**"]),
    ]
    for origen, destino, filtro in pasos:
        os.makedirs(destino, exist_ok=True)
        subprocess.run(["rclone", "copy", origen, destino, "--max-depth", "6", *filtro],
                       capture_output=True, timeout=600)
    # rclone respeta el árbol: se aplanan los PNG del logo para que queden a mano.
    for p in glob.glob(os.path.join(ins, "logo", "**", "*.png"), recursive=True):
        if os.path.dirname(p) != os.path.join(ins, "logo"):
            shutil.move(p, os.path.join(ins, "logo", os.path.basename(p)))
    briefs = sorted(glob.glob(os.path.join(ins, "_drive", "brief", "**", "Brief*"), recursive=True),
                    key=lambda p: (not p.endswith(".md"), not p.endswith(".txt"), -os.path.getmtime(p)))
    return briefs[0] if briefs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente")
    ap.add_argument("--modo", choices=["tanda", "variaciones"], default="tanda")
    ap.add_argument("--skill", default="estaticos-meta")
    ap.add_argument("--tanda", type=int)
    ap.add_argument("--desde", nargs="+")
    for k in ("brief", "logo", "guia", "fotos", "personas", "resenas", "variar", "renders", "permisos"):
        ap.add_argument(f"--{k}", nargs="+")
    ap.add_argument("--drive", action="store_true")
    a = ap.parse_args()

    cli = a.cliente
    if not os.path.isdir(L.dir_cliente(cli)):
        sys.exit(f"✗ No existe ~/Desktop/CLIENTES/{cli}. Revisa el nombre (se usa el de la carpeta).")
    inmo = a.skill == INMO
    if inmo and a.drive:
        sys.exit("✗ estaticos-inmobiliario-meta no usa --drive: lo que falte se le pide a Dirección (SKILL Parte 1 §3).")
    ins = L.dir_insumos(cli)
    os.makedirs(ins, exist_ok=True)
    n = a.tanda or L.tanda_local_siguiente(cli)
    L.marcar(cli, n, "fase0_ini", nota=a.modo)

    errores, avisos = [], []
    brief_src = None

    if a.drive:
        brief_src = bajar_drive(cli, ins)

    # 1. Lo que llega por --desde se clasifica por nombre; lo explícito gana.
    lotes = {k: [] for k in ("brief", "logo", "guia", "fotos", "personas", "resenas", "variar", "renders", "permisos")}
    sin_clasificar = []
    for f in expandir(a.desde):
        k = clasificar(f, a.skill)
        (lotes[k] if k else sin_clasificar).append(f)
    for k in lotes:
        explicito = expandir(getattr(a, k))
        if explicito:
            lotes[k] = explicito
    if a.modo == "variaciones" and not lotes["variar"] and lotes["fotos"] and a.desde and not a.fotos:
        # En variaciones, las imágenes sueltas sin palabra clave son las piezas a variar, en su orden.
        lotes["variar"], lotes["fotos"] = lotes["fotos"], []
    if sin_clasificar:
        avisos.append("sin clasificar (no se han usado): " + ", ".join(map(os.path.basename, sin_clasificar)))

    for k in ("logo", "guia", "fotos", "personas", "resenas", "renders", "permisos"):
        for f in lotes[k]:
            copiar(f, os.path.join(ins, k))
    for i, f in enumerate(lotes["variar"], 1):
        copiar(f, os.path.join(ins, "variar"), f"{i:02d}_{os.path.basename(f)}")
    if lotes["brief"]:
        brief_src = lotes["brief"][0]

    # 2. BRIEF — imprescindible.
    if brief_src:
        brief, chars = brief_a_txt(brief_src, cli, ins)
    else:
        previos = sorted(glob.glob(os.path.join(ins, "Brief_*_para_GPT.txt")), key=os.path.getmtime)
        brief = previos[-1] if previos else None
        chars = len(open(brief, encoding="utf-8").read()) if brief else 0
    if not brief:
        errores.append("FALTA EL BRIEF. Pásalo con --brief, o corre `brief-desde-onboarding`. No se produce con brief inventado.")
    elif chars < 400:
        errores.append(f"El brief tiene {chars} caracteres: PDF escaneado o vacío. No se adjunta.")
    elif brief_src is None:
        dias = (dt.datetime.now().timestamp() - os.path.getmtime(brief)) / 86400
        if dias > 45:
            avisos.append(f"el brief local tiene {int(dias)} días: comprobar que es el vigente")

    # 3. LOGO — imprescindible y en PNG.
    logos = [p for p in glob.glob(os.path.join(ins, "logo", "*")) if "antig" not in p.lower()]
    logos_png = [p for p in logos if p.lower().endswith(".png")]
    if not logos:
        errores.append("FALTA EL LOGO. Pásalo con --logo (PNG final de `1. Branding/.../02_PNG/`)" + ("" if inmo else " o usa --drive") + ".")
    elif not logos_png:
        avisos.append("el logo no está en PNG (" + ", ".join(map(os.path.basename, logos)) +
                      "): el GPT lo deforma más; buscar el PNG final")

    # 4. GUÍA / PALETA — si falta se saca de la web (produccion-render.md §5) y la pieza va _PEND.
    guia = glob.glob(os.path.join(ins, "guia", "*")) + glob.glob(os.path.join(ins, "guia-visual*")) + \
        glob.glob(os.path.join(ins, "BRANDING.md")) + glob.glob(os.path.join(ins, "paleta*"))
    if not guia:
        avisos.append("sin guía visual/manual: la preproducción saca paleta y tipos de la web → branding sustituido, piezas _PEND")

    # 5. PRUEBAS Y PERSONAS
    resenas = glob.glob(os.path.join(ins, "resenas", "*"))
    if not resenas and not inmo:
        avisos.append("sin reseñas reales: Review+Claim y Prueba social salen con cita PROVISIONAL [REEMPLAZAR] (_PEND)")
    personas = [p for p in glob.glob(os.path.join(ins, "personas", "*")) if p.lower().endswith(IMG)]
    fotos = [p for p in glob.glob(os.path.join(ins, "fotos", "**", "*"), recursive=True) if p.lower().endswith(IMG)]
    necesita_casting = a.modo == "tanda" and len(personas) < 2 and not inmo
    if necesita_casting:
        avisos.append(f"{len(personas)} persona(s) en Insumos/personas: se lanza el agente de casting (hacen falta 2-3)")
    renders = [p for p in glob.glob(os.path.join(ins, "renders", "*")) if p.lower().endswith(IMG)]
    # Aunque un QR llegue por --renders a mano, nunca se sube al GPT.
    renders_subida = [p for p in renders if not re.search(r"qr|madmoun|trakheesi|permit|permiso", os.path.basename(p).lower())]
    permisos = sorted(glob.glob(os.path.join(ins, "permisos", "*")))
    if inmo:
        if not personas:
            avisos.append("sin fotos reales de personas: las piezas van sin persona (casting de stock solo si Dirección lo pide)")
        if not renders:
            avisos.append("sin renders del proyecto: se omiten los formatos 1, 2, 3, 5, 7 y 8")
        csvs = [x for x in permisos if x.lower().endswith(".csv")]
        if not csvs:
            avisos.append("sin Insumos/permisos/permisos.csv (permiso Trakheesi, caducidad, QR y NMA por pieza): piezas _PEND")
        else:
            avisos += validar_permisos(csvs[0], os.path.join(ins, "permisos"))

    # 6. VARIACIONES — la pieza a variar es imprescindible.
    variar = sorted(glob.glob(os.path.join(ins, "variar", "*")))
    if a.modo == "variaciones" and not variar:
        errores.append("FALTA la pieza a variar. Pásala con --variar (en orden).")
    if a.modo == "variaciones" and a.variar:
        variar = sorted(glob.glob(os.path.join(ins, "variar", "*")))[-len(a.variar):]

    # 7. Lo que se sube en el Mensaje 2, partido para no pasar de 10 MB por llamada.
    subida, lote, peso = [], [], 0
    for p in [brief] + [l for l in logos_png if not (inmo and re.search(r"qr|madmoun|trakheesi|permit", os.path.basename(l).lower()))][:2] + ((renders_subida[:3] if inmo else fotos[:3]) if a.modo == "tanda" else []):
        if not p:
            continue
        s = os.path.getsize(p)
        if lote and peso + s > TOPE_SUBIDA:
            subida.append(lote); lote, peso = [], 0
        lote.append(p); peso += s
    if lote:
        subida.append(lote)

    manifiesto = {
        "cliente": cli, "modo": a.modo, "tanda_provisional": n,
        "fecha": dt.date.today().isoformat(), "fecha_texto": dt.date.today().strftime("%d/%m/%Y"),
        "brief": brief, "brief_caracteres": chars, "logos": logos_png or logos,
        "guia": guia, "resenas": resenas, "personas": personas, "fotos": fotos, "variar": variar,
        "necesita_casting": necesita_casting,
        "subida_mensaje2": subida,
        "salida": L.dir_salida(cli),
        "progreso": os.path.join(L.dir_salida(cli), f"PROGRESO-Tanda{n}.md"),
        "auditoria": os.path.join(L.dir_salida(cli), "_auditoria", f"Tanda{n}"),
        "errores": errores, "avisos": avisos,
    }
    if inmo:
        manifiesto.update({"skill": INMO, "renders": renders, "permisos": permisos})
    mpath = os.path.join(ins, f"manifiesto_Tanda{n}.json")
    json.dump(manifiesto, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not errores:
        os.makedirs(manifiesto["auditoria"], exist_ok=True)
    if not errores and not os.path.exists(manifiesto["progreso"]):
        open(manifiesto["progreso"], "w", encoding="utf-8").write(
            f"# PROGRESO — {cli} · Tanda {n} ({a.modo})\n\n| Pieza | Ratio | Estado | Chat GPT |\n|---|---|---|---|\n")
    L.marcar(cli, n, "fase0_fin", nota=f"errores={len(errores)} avisos={len(avisos)}")

    print(f"{'✗' if errores else '✓'} {cli} · Tanda {n} (provisional) · modo {a.modo}")
    print(f"  brief: {os.path.basename(brief) if brief else '—'} ({chars} car.) · logos: {len(logos)} · guía: {len(guia)}"
          f" · reseñas: {len(resenas)} · personas: {len(personas)} · fotos: {len(fotos)}"
          + (f" · a variar: {len(variar)}" if a.modo == "variaciones" else ""))
    if inmo:
        print(f"  renders: {len(renders)} · permisos: {len(permisos)} (el QR nunca se sube al GPT)")
    for e in errores:
        print(f"  ✗ {e}")
    for w in avisos:
        print(f"  ⚠ {w}")
    print(f"  manifiesto: {mpath}")
    sys.exit(1 if errores else 2 if avisos else 0)


if __name__ == "__main__":
    main()
