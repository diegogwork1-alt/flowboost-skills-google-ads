#!/usr/bin/env python3
"""Marca una etapa en los DOS sitios a la vez: el ESTADO.md y la hoja del Drive.

Antes había que acordarse de las dos cosas y la hoja —que es la que mira Dirección— se quedaba
siempre atrás.

**Escribe la hoja DIRECTAMENTE, sin pasar por n8n.** Se probó con un webhook de n8n y el nodo
de Google Sheets no traga la cabecera en la fila 7 por importación (hay que configurarlo a
mano en su interfaz). Como el marcado es lo que sostiene el encadenado del funnel, no puede
depender de eso: se hace con el token de Drive que el agente ya tiene.

Cómo: se exporta la hoja a .xlsx, se cambia la celda, y se vuelve a subir al MISMO archivo con
conversión. Se conservan el desplegable de estados, los colores condicionales y las fórmulas
del semáforo (comprobado).

⚠️ Es lectura-modificación-escritura: si alguien está editando la hoja **en ese mismo segundo**,
su cambio se pierde. En la práctica no pasa (el agente marca de una en una y Dirección no está
dentro a la vez), pero si algún día se marcan muchas etapas seguidas, van una detrás de otra,
nunca en paralelo.

**La llama cada skill al cerrar su etapa.** Solo para las etapas que dependen del AGENTE: lo de
Dirección y lo de Operaciones se marca a mano, porque el agente no puede saber si lo hicieron.

Uso:
  python3 marcar_etapa.py "Cliente 02" "Brief" \
      [--estado Hecho|"En curso"|Bloqueado|"No aplica"] [--nota "..."] \
      [--sheet-id <ID> | --cliente-raiz "gdrive:i_X/c_X"]
"""
import argparse, io, os, subprocess, sys, tempfile, urllib.parse, urllib.request
from openpyxl import load_workbook

# La lista de etapas vive en estado_cliente.py y SOLO ahí: se lee, no se copia.
def _etapas_canonicas():
    import re as _re
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado_cliente.py")
    m = _re.search(r"ETAPAS\s*=\s*\[(.*?)\]", open(ruta, encoding="utf-8").read(), _re.S)
    return _re.findall(r'"([^"]+)"', m.group(1)) if m else []

ETAPAS_CANONICAS = _etapas_canonicas()
from subir_a_drive import api, token, _multipart

HOJA = "application/vnd.google-apps.spreadsheet"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
AQUI = os.path.dirname(os.path.abspath(__file__))
ESTADOS = ["Pendiente", "En curso", "Hecho", "Bloqueado", "No aplica"]


def buscar_por_nombre(cliente):
    """Busca «Estado de cuenta — <Cliente>» en TODO el Drive, por nombre.

    Es el camino por defecto: las skills llaman a este script sin decirle dónde está la
    hoja, porque no lo saben. Buscar por nombre no necesita ni el ID ni la ruta del cliente.
    """
    nombre = f"Estado de cuenta — {cliente}"
    n = nombre.replace("\\", "\\\\").replace("'", "\\'")
    q = (f"name = '{n}' and trashed = false "
         f"and mimeType = 'application/vnd.google-apps.spreadsheet'")
    url = ("https://www.googleapis.com/drive/v3/files?"
           + urllib.parse.urlencode({"q": q, "fields": "files(id,name)",
                                     "orderBy": "modifiedTime desc", "pageSize": "5",
                                     "supportsAllDrives": "true",
                                     "includeItemsFromAllDrives": "true"}))
    f = api(url).get("files", [])
    if len(f) > 1:
        print(f"! Hay {len(f)} hojas llamadas «{nombre}». Se usa la modificada más "
              f"recientemente; si no es la que toca, pasá --sheet-id.")
    return f[0]["id"] if f else None


def buscar_hoja_estado(cliente, raiz_cliente):
    """Igual, pero acotado a la carpeta de reportes del cliente (sea 5., 6. o 7.)."""
    sys.path.insert(0, AQUI)
    from carpeta_reportes import buscar
    from subir_a_drive import folder_id
    carpeta = buscar(raiz_cliente)
    if not carpeta:
        return None
    fid = folder_id(carpeta)
    nombre = f"Estado de cuenta — {cliente}"
    n = nombre.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name = '{n}' and '{fid}' in parents and trashed = false"
    url = ("https://www.googleapis.com/drive/v3/files?"
           + urllib.parse.urlencode({"q": q, "fields": "files(id)",
                                     "supportsAllDrives": "true",
                                     "includeItemsFromAllDrives": "true"}))
    f = api(url).get("files", [])
    return f[0]["id"] if f else None


def _descargar_xlsx(sheet_id, destino):
    u = (f"https://www.googleapis.com/drive/v3/files/{sheet_id}/export?mimeType="
         + urllib.parse.quote(XLSX))
    ultimo = None
    for i in range(5):
        try:
            r = urllib.request.Request(u, headers={"Authorization": "Bearer " + token(refrescar=i > 0)})
            with open(destino, "wb") as f:
                f.write(urllib.request.urlopen(r, timeout=60).read())
            return True
        except Exception as e:
            ultimo = e
    print(f"! No se pudo descargar la hoja: {type(ultimo).__name__}", file=sys.stderr)
    return False


def marcar_en_hoja(sheet_id, etapa, estado, nota, fecha):
    tmp = os.path.join(tempfile.mkdtemp(), "estado.xlsx")
    if not _descargar_xlsx(sheet_id, tmp):
        return False, "no se pudo descargar"

    wb = load_workbook(tmp)
    ws = wb["Estado"] if "Estado" in wb.sheetnames else wb.active

    # La cabecera está en la fila 7; se localiza por el texto, no por número fijo.
    fila_cab = next((r for r in range(1, 30)
                     if str(ws.cell(r, 1).value or "").strip().lower() == "carril"), None)
    if not fila_cab:
        return False, "la hoja no tiene la tabla de etapas"
    cab = {str(ws.cell(fila_cab, c).value or "").strip().lower(): c
           for c in range(1, ws.max_column + 1)}
    for req in ("etapa", "estado"):
        if req not in cab:
            return False, f"falta la columna «{req}»"

    objetivo = etapa.strip().lower()
    fila = None
    for r in range(fila_cab + 1, ws.max_row + 1):
        v = str(ws.cell(r, cab["etapa"]).value or "").strip().lower()
        if v == objetivo:
            fila = r; break
    if fila is None:
        return False, f"no existe la etapa «{etapa}» en la hoja"

    ws.cell(fila, cab["estado"]).value = estado
    if "fecha" in cab:
        ws.cell(fila, cab["fecha"]).value = fecha
    if nota and "notas" in cab:
        ws.cell(fila, cab["notas"]).value = nota
    wb.save(tmp)

    cuerpo, cabs = _multipart({"mimeType": HOJA}, tmp, XLSX)
    api(f"https://www.googleapis.com/upload/drive/v3/files/{sheet_id}"
        f"?uploadType=multipart&supportsAllDrives=true",
        data=cuerpo, headers=cabs, metodo="PATCH")
    return True, f"fila {fila}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente"); ap.add_argument("etapa")
    ap.add_argument("--estado", default="Hecho", choices=ESTADOS)
    ap.add_argument("--etapa-nueva", action="store_true",
                    help="solo para añadir una etapa que de verdad no existe todavía: "
                         "hay que meterla antes en ETAPAS de estado_cliente.py")
    ap.add_argument("--nota", default="")
    ap.add_argument("--sheet-id", default="")
    ap.add_argument("--cliente-raiz", default="")
    a = ap.parse_args()

    # La etapa TIENE que existir en la lista canónica. Sin esto, cualquier string entraba y
    # creaba una fila fantasma en la hoja: pasó con 10 de las 13 llamadas de las skills.
    if a.etapa not in ETAPAS_CANONICAS and not a.etapa_nueva:
        import difflib
        cerca = difflib.get_close_matches(a.etapa, ETAPAS_CANONICAS, n=3, cutoff=0.25)
        print(f"⛔ La etapa {a.etapa!r} NO existe en la lista canónica.", file=sys.stderr)
        print("   Si la escribes así, creas una fila fantasma en la hoja y nadie la ve.",
              file=sys.stderr)
        if cerca:
            print("\n   ¿Querías decir?", file=sys.stderr)
            for c in cerca: print(f"     · {c!r}", file=sys.stderr)
        print(f"\n   Lista completa ({len(ETAPAS_CANONICAS)}):", file=sys.stderr)
        for e in ETAPAS_CANONICAS: print(f"     · {e}", file=sys.stderr)
        print("\n   Si de verdad es una etapa nueva: añádela a ETAPAS en estado_cliente.py",
              file=sys.stderr)
        print("   y repite con --etapa-nueva.", file=sys.stderr)
        sys.exit(2)

    from datetime import date
    hoy = date.today().isoformat()

    # 1) ESTADO.md (local + Drive). Usa su propio vocabulario.
    equiv = {"hecho": "hecho", "en curso": "en curso", "bloqueado": "bloqueado",
             "pendiente": "pendiente", "no aplica": "hecho"}
    r = subprocess.run([sys.executable, os.path.join(AQUI, "estado_cliente.py"),
                        a.cliente, "set", a.etapa,
                        equiv.get(a.estado.lower(), "hecho"), a.nota],
                       capture_output=True, text=True)
    print("✓ ESTADO.md actualizado" if r.returncode == 0
          else f"! ESTADO.md no se actualizó:\n{r.stdout}{r.stderr}")

    # 2) La hoja del Drive, que es la que mira Dirección.
    # Orden: lo que se pasa a mano gana; si no, se busca por nombre en todo el Drive.
    sid = a.sheet_id
    if not sid and a.cliente_raiz:
        sid = buscar_hoja_estado(a.cliente, a.cliente_raiz)
    if not sid:
        sid = buscar_por_nombre(a.cliente)
    if not sid:
        print(f"! No encuentro «Estado de cuenta — {a.cliente}» en el Drive.")
        print("  ¿Se creó en la Fase 0 con montar_hoja_estado.py? El ESTADO.md sí quedó")
        print("  marcado, así que el encadenado no se frena; anotalo en el resumen.")
        return

    ok, detalle = marcar_en_hoja(sid, a.etapa, a.estado, a.nota, hoy)
    if ok:
        print(f"✓ Hoja del Drive: «{a.etapa}» → {a.estado}  ({detalle})")
    else:
        print(f"! La hoja del Drive no se marcó: {detalle}.")
        print("  El ESTADO.md SÍ quedó actualizado: el encadenado sigue. Anotarlo en el resumen.")


if __name__ == "__main__":
    main()
