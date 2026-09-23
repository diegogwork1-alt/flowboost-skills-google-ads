#!/usr/bin/env python3
"""Cambia SOLO los colores de la pestaña `Reporte` (Meta) de una hoja ya creada.

Sustituye la paleta vieja de Flowboost (morado/rosa) por la de META (azul + negro + blanco),
para que no se confunda con el reporte de Google al abrir el archivo (Dirección, 10-09-2026).

NO toca valores, fórmulas, datos ni el resto de pestañas: solo el relleno y el color de letra
de las celdas que llevan un color de la paleta vieja. Es reversible ejecutándolo al revés.

  python3 recolorear_reportes.py "Cliente 03"
  python3 recolorear_reportes.py --todos
"""
import argparse, os, sys, tempfile
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

# viejo → nuevo
MAPA = {
    "7C5CFF": "0866FF",   # morado Flowboost → azul Meta (cabeceras de mes)
    "FF2E7E": "5AA9FF",   # rosa Flowboost   → azul claro (acento de totales)
    "F1EDFF": "E7F0FF",   # lila suave       → azul suave (celdas editables)
    "FAF9FC": "F5F8FF",   # gris suave       → gris azulado (franja alterna)
}


def _hex(color):
    """El RGB de un color de openpyxl, sin el alfa, o None."""
    if color is None or color.type != "rgb" or not color.rgb:
        return None
    v = str(color.rgb)
    return v[-6:].upper() if len(v) >= 6 else None


def recolorear(ws):
    n = 0
    for fila in ws.iter_rows():
        for c in fila:
            f = _hex(c.fill.fgColor) if c.fill and c.fill.fill_type == "solid" else None
            if f in MAPA:
                c.fill = PatternFill("solid", fgColor=MAPA[f]); n += 1
            t = _hex(c.font.color) if c.font else None
            if t in MAPA:
                c.font = Font(name=c.font.name, size=c.font.size, bold=c.font.bold,
                              italic=c.font.italic, color=MAPA[t]); n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente", nargs="?", default="")
    ap.add_argument("--sheet-id", default="")
    ap.add_argument("--todos", action="store_true", help="todas las hojas «Reporte Meta Ads — …»")
    a = ap.parse_args()

    import marcar_etapa as me
    from subir_a_drive import api, _multipart
    import urllib.parse

    if a.todos:
        q = ("name contains 'Reporte Meta Ads' and trashed=false and "
             "mimeType='application/vnd.google-apps.spreadsheet'")
        hojas = [(f["name"], f["id"]) for f in api(
            "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(
                {"q": q, "fields": "files(id,name)", "pageSize": 100,
                 "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"})
        ).get("files", [])]
    elif a.sheet_id:
        hojas = [(a.cliente or a.sheet_id, a.sheet_id)]
    else:
        sys.path.insert(0, AQUI)
        from anadir_hoja_google import _buscar_hoja_reportes
        sid = _buscar_hoja_reportes(a.cliente)
        if not sid:
            sys.exit(f"⛔ No encontré la hoja de reportes de {a.cliente!r}.")
        hojas = [(a.cliente, sid)]

    for nombre, sid in hojas:
        tmp = os.path.join(tempfile.mkdtemp(), "h.xlsx")
        me._descargar_xlsx(sid, tmp)
        wb = load_workbook(tmp)
        nom = "Reporte Meta" if "Reporte Meta" in wb.sheetnames else "Reporte"
        if nom not in wb.sheetnames:
            print(f"  · {nombre}: sin pestaña «Reporte», se salta"); continue
        n = recolorear(wb[nom])
        if not n:
            print(f"  · {nombre}: ya estaba con los colores nuevos"); continue
        wb.save(tmp)
        cuerpo, cabs = _multipart({"mimeType": me.HOJA}, tmp, me.XLSX)
        api(f"https://www.googleapis.com/upload/drive/v3/files/{sid}"
            f"?uploadType=multipart&supportsAllDrives=true",
            data=cuerpo, headers=cabs, metodo="PATCH")
        print(f"  ✓ {nombre}: {n} celdas recoloreadas a la paleta de Meta")


if __name__ == "__main__":
    main()
