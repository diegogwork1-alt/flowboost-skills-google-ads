#!/usr/bin/env python3
"""Sube un entregable al Drive del cliente COMO DOCUMENTO DE GOOGLE (nunca .md pelado).

Regla de Dirección (06-09-2026): al Drive del cliente no sube ni un .md. Todo documento
va como **Documento de Google** nativo (editable y legible por el cliente).

Cadena: .md → HTML → Drive API con conversión a application/vnd.google-apps.document.
Convierte de verdad TABLAS, enlaces, citas y listas anidadas (antes salían como texto crudo
y el documento parecía un .md pegado). Ya NO pasa por textutil: no conserva las tablas.
El token sale del remoto `gdrive` de rclone (mismo permiso que ya usa el agente).

IDEMPOTENTE (arreglado 07-09-2026 — bug de los duplicados):
  Si el documento ya existe en esa carpeta, se **actualiza en su sitio** (mismo ID,
  misma URL, Drive guarda la versión anterior en su historial). No se borra nada.
  El bug anterior hacía `rclone deletefile "<carpeta>/<nombre>"`, pero rclone lista
  los Documentos de Google con la extensión de exportación (`<nombre>.docx`), así que
  ese borrado NUNCA acertaba y cada resubida dejaba una copia más. Perseguir el nombre
  con `.docx` tampoco vale: borrar y recrear cambia el ID y rompe los enlaces ya
  compartidos con el cliente. Por eso se busca por API y se hace update.

Uso:
  python3 subir_a_drive.py "<fichero.md|.docx|.pdf|.png>" "<carpeta destino en gdrive:>" ["Nombre en Drive"]

Ejemplos:
  python3 subir_a_drive.py "Guiones EGC.md" "gdrive:i_Cliente 01/c_Cliente 01/2. Ads/EGC/Guiones" "Guiones EGC - Cliente 01 - Tanda 1"
  python3 subir_a_drive.py foto.png "gdrive:i_Cliente 01/c_Cliente 01/2. Ads/Estáticos/GPT/Tanda 1"

.md y .docx → Documento de Google. .pdf/.png/otros → se suben tal cual (rclone).
"""
import json, os, random, re, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, uuid, pathlib

DOC = "application/vnd.google-apps.document"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# 403 de Google que NO son de permisos: son cuota/ritmo y se reintentan.
RITMO = {"rateLimitExceeded", "userRateLimitExceeded", "sharingRateLimitExceeded",
         "quotaExceeded", "backendError", "internalError"}


def token(refrescar=False):
    if refrescar:  # fuerza a rclone a renovar el access_token antes de releerlo
        subprocess.run(["rclone", "lsd", "gdrive:", "--max-depth", "1"], capture_output=True)
    cfg = json.loads(subprocess.run(["rclone", "config", "dump"], capture_output=True, text=True).stdout)["gdrive"]
    return json.loads(cfg["token"])["access_token"]


def _motivo(cuerpo):
    try:
        e = json.loads(cuerpo)["error"]
        return (e.get("errors") or [{}])[0].get("reason", "") or e.get("status", "")
    except Exception:
        return ""


def api(url, data=None, headers=None, metodo=None, intentos=6):
    """Petición a la API de Drive con reintentos. Distingue límite de peticiones de permisos."""
    for i in range(intentos):
        h = {"Authorization": "Bearer " + token(refrescar=(i > 0)), **(headers or {})}
        try:
            return json.loads(urllib.request.urlopen(
                urllib.request.Request(url, data=data, headers=h, method=metodo)).read() or b"{}")
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "replace")
            motivo = _motivo(cuerpo)
            reintentable = e.code in (429, 500, 502, 503, 504) or (e.code == 403 and motivo in RITMO)
            if e.code == 401 and i == 0:
                continue  # token caducado: el siguiente intento lo refresca
            if reintentable and i < intentos - 1:
                espera = min(2 ** i + random.random(), 32)
                print(f"  ⏳ {e.code} {motivo or 'límite de peticiones'} — reintento {i+1}/{intentos-1} en {espera:.1f}s",
                      file=sys.stderr)
                time.sleep(espera)
                continue
            if e.code == 403 and motivo not in RITMO:
                raise SystemExit(f"✋ Drive rechazó por PERMISOS ({motivo}), no por ritmo: {cuerpo[:300]}")
            raise SystemExit(f"✋ Drive falló {e.code} ({motivo or 'sin motivo'}): {cuerpo[:300]}")
    raise SystemExit("✋ Drive: agotados los reintentos por límite de peticiones.")


def folder_id(remoto):
    """remoto = 'gdrive:ruta/carpeta' → id de esa carpeta."""
    padre, _, nombre = remoto.rstrip("/").rpartition("/")
    if not padre.endswith(":") and ":" not in padre: padre = "gdrive:" + padre
    out = subprocess.run(["rclone", "lsjson", "--dirs-only", padre], capture_output=True, text=True).stdout
    for d in json.loads(out):
        if d["Name"] == nombre: return d["ID"]
    # crear si no existe
    subprocess.run(["rclone", "mkdir", remoto], check=True)
    out = subprocess.run(["rclone", "lsjson", "--dirs-only", padre], capture_output=True, text=True).stdout
    return [d["ID"] for d in json.loads(out) if d["Name"] == nombre][0]


def _inline(t):
    """Formato de dentro de la linea. Escapa HTML ANTES de meter etiquetas."""
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\*\w])\*(?!\s)([^*]+?)\*(?![\*\w])", r"<i>\1</i>", t)
    return t


def _fila(l):
    l = l.strip()
    if l.startswith("|"): l = l[1:]
    if l.endswith("|"): l = l[:-1]
    return [c.strip() for c in l.split("|")]


def md_a_html(md):
    """Markdown -> HTML con TABLAS, enlaces, citas y listas anidadas de verdad.

    El conversor anterior era una tanda de regex sueltas: no entendia tablas, enlaces
    ni citas, y volcaba `| a | b |` y `[t](url)` como texto crudo -> el documento en
    Drive parecia un .md copiado y pegado (Dirección, 07-09-2026). Ademas no escapaba HTML,
    asi que un "A&C" rompia el marcado.
    """
    out, lineas, i = [], md.split("\n"), 0
    pila = []  # listas abiertas: (tag, sangria)

    def cerrar(hasta=-1):
        while pila and (hasta == -1 or pila[-1][1] > hasta):
            out.append(f"</{pila.pop()[0]}>")

    while i < len(lineas):
        l = lineas[i]; strip = l.strip()

        # --- tabla: linea de | seguida de separador |---| ---
        if strip.startswith("|") and i + 1 < len(lineas) and re.match(r"^\|[\s:|-]+\|?$", lineas[i + 1].strip()):
            cerrar()
            cab = _fila(strip); i += 2
            out.append('<table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;width:100%">')
            out.append("<tr>" + "".join(f'<th style="background:#f0f0f0;text-align:left">{_inline(c)}</th>' for c in cab) + "</tr>")
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                cel = _fila(lineas[i])
                cel += [""] * (len(cab) - len(cel))
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cel[:len(cab)]) + "</tr>")
                i += 1
            out.append("</table>")
            continue

        # --- encabezados ---
        m = re.match(r"^(#{1,4})\s+(.*)$", strip)
        if m:
            cerrar(); out.append(f"<h{len(m.group(1))}>{_inline(m.group(2))}</h{len(m.group(1))}>"); i += 1; continue

        # --- separador ---
        if re.match(r"^-{3,}$|^\*{3,}$", strip):
            cerrar(); out.append("<hr>"); i += 1; continue

        # --- cita (bloque de > seguidas) ---
        if strip.startswith(">"):
            cerrar(); trozo = []
            while i < len(lineas) and lineas[i].strip().startswith(">"):
                trozo.append(_inline(re.sub(r"^\s*>\s?", "", lineas[i]))); i += 1
            out.append('<div style="border-left:3px solid #999;padding-left:12px;margin:8px 0;color:#333">'
                       + "<br>".join(trozo) + "</div>")
            continue

        # --- listas (con anidado por sangria) ---
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", l)
        if m:
            sang, marca, txt = len(m.group(1)), m.group(2), m.group(3)
            tag = "ul" if marca in ("-", "*") else "ol"
            while pila and pila[-1][1] > sang: cerrar(sang)
            if not pila or pila[-1][1] < sang or pila[-1][0] != tag:
                if pila and pila[-1][1] == sang and pila[-1][0] != tag: cerrar(sang - 1)
                out.append(f"<{tag}>"); pila.append((tag, sang))
            out.append(f"<li>{_inline(txt)}</li>"); i += 1; continue

        # --- vacio / parrafo ---
        if not strip: cerrar(); i += 1; continue
        cerrar(); out.append(f"<p>{_inline(strip)}</p>"); i += 1

    cerrar()
    return "\n".join(out)


def md_a_html_file(ruta_md):
    """Escribe el HTML completo y devuelve (ruta, mime).

    Se manda HTML a Drive, no .docx: `textutil` NO conserva las tablas (comprobado
    07-09-2026, el docx salia con 0 <w:tbl>), y el importador de HTML de Google Docs
    si las respeta, junto con enlaces y listas. Un eslabon menos en la cadena.
    """
    cuerpo = md_a_html(pathlib.Path(ruta_md).read_text(encoding="utf-8"))
    html = os.path.join(tempfile.mkdtemp(), "d.html")
    open(html, "w", encoding="utf-8").write(
        "<html><head><meta charset='utf-8'><style>"
        "body{font-family:Helvetica,Arial;font-size:11pt;line-height:1.45}"
        "h1{font-size:20pt}h2{font-size:15pt}h3{font-size:12.5pt}h4{font-size:11.5pt}"
        "li{margin-left:6pt}table{font-size:9.5pt}th,td{vertical-align:top}"
        "code{font-family:Menlo,monospace;font-size:10pt;background:#f2f2f2}"
        "</style></head>"
        f"<body>{cuerpo}</body></html>")
    return html, "text/html"


def buscar_docs(nombre, fid):
    """Documentos de Google ya existentes con ese nombre exacto en esa carpeta.

    Se busca por API (nombre REAL en Drive, sin extensión). rclone los lista como
    '<nombre>.docx' —extensión de exportación, no parte del nombre—; por eso cualquier
    comparación hecha sobre el listado de rclone falla y acaba duplicando.
    """
    n = nombre.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name = '{n}' and '{fid}' in parents and trashed = false"
    url = ("https://www.googleapis.com/drive/v3/files?"
           + urllib.parse.urlencode({"q": q, "fields": "files(id,name,mimeType,modifiedTime)",
                                     "orderBy": "modifiedTime desc", "pageSize": "50",
                                     "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}))
    return api(url).get("files", [])


def _multipart(meta, fichero, mime):
    b = uuid.uuid4().hex
    body = b"".join([
        f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode(), json.dumps(meta).encode(), b"\r\n",
        f"--{b}\r\nContent-Type: {mime}\r\n\r\n".encode(),
        open(fichero, "rb").read(), f"\r\n--{b}--\r\n".encode()])
    return body, {"Content-Type": f"multipart/related; boundary={b}"}


def subir_como_google_doc(fichero, fid, nombre, mime=DOCX):
    """Crea el Documento de Google, o ACTUALIZA el que ya existe con ese nombre.

    Nunca borra: actualizar conserva el ID, la URL ya compartida y el historial de
    versiones de Drive. Es lo que impide que se acumulen copias al resubir.
    """
    previos = buscar_docs(nombre, fid)
    if previos:
        destino = previos[0]
        body, h = _multipart({"name": nombre, "mimeType": DOC}, fichero, mime)
        r = api(f"https://www.googleapis.com/upload/drive/v3/files/{destino['id']}"
                "?uploadType=multipart&supportsAllDrives=true", data=body, headers=h, metodo="PATCH")
        r["_accion"] = "actualizado"
        if len(previos) > 1:  # duplicados de antes del arreglo: se avisan, NO se tocan
            r["_duplicados"] = [p["id"] for p in previos[1:]]
        return r
    body, h = _multipart({"name": nombre, "parents": [fid], "mimeType": DOC}, fichero, mime)
    r = api("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true",
            data=body, headers=h)
    r["_accion"] = "creado"
    return r


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    src, dest = sys.argv[1], sys.argv[2]
    nombre = sys.argv[3] if len(sys.argv) > 3 else pathlib.Path(src).stem
    ext = pathlib.Path(src).suffix.lower()
    if ext in (".md", ".docx", ".txt"):
        if ext in (".md", ".txt"):
            fuente, mime = md_a_html_file(src)
        else:
            fuente, mime = src, DOCX
        fid = folder_id(dest)
        r = subir_como_google_doc(fuente, fid, nombre, mime)
        print(f"Documento de Google {r['_accion']}: {r['name']}  ({r['mimeType']})")
        print(f"https://docs.google.com/document/d/{r['id']}/edit")
        for d in r.get("_duplicados", []):
            print(f"  ⚠️  copia duplicada previa (NO borrada, decide Dirección): "
                  f"https://docs.google.com/document/d/{d}/edit", file=sys.stderr)
    else:
        subprocess.run(["rclone", "copyto", src, f"{dest.rstrip('/')}/{nombre}{ext}"], check=True)
        print(f"Subido tal cual: {nombre}{ext}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
