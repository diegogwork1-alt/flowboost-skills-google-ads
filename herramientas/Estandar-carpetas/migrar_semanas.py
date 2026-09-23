#!/usr/bin/env python3
"""Rehace la hoja de un cliente con las semanas NUEVAS sin perder nada de lo que ya tiene.

Por qué no vale con `montar_hoja_reportes.py --rehacer`: ese comando rehace el libro desde
cero y se lleva por delante `datos` (lo que escribe n8n), `ventas`, `datos-google` (que solo
se recupera reejecutando el script de Google Ads) y TODO lo escrito a mano.

Aquí se hace en tres tiempos: se rescata, se rehace, se devuelve.

Los cierres se devuelven a la semana NUEVA que contiene el primer día de la semana vieja
(«Del 1 al 7» → «Del 1 al 6»), que es lo que decidió Dirección el 15-09-2026.
"""
import datetime, json, os, re, sys, tempfile, urllib.parse
import openpyxl


def a_mano(v):
    """¿Esto lo escribió una persona, o es de la plantilla?

    Un número suelto, siempre. Y también una FÓRMULA que no lee de `datos` ni de `ventas`:
    Equipo escribió «=264,48+121» en un facturado para sumar dos importes, y darla por
    generada la habría borrado sin avisar. Las de la plantilla siempre miran esas pestañas.
    """
    if v is None or v == "":
        return False
    t = getattr(v, "text", v)
    if not isinstance(t, str):
        return True
    if not t.startswith("="):
        return True
    return "datos!" not in t and "ventas!" not in t and "datos-google" not in t

EST = os.path.expanduser("~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas")
sys.path.insert(0, EST)
import montar_hoja_reportes as M
import anadir_hoja_google as G
from subir_a_drive import api, _multipart

HOJA = "application/vnd.google-apps.spreadsheet"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MOTOR = ("datos", "ventas", "datos-google", "funnels")
MES_N = {m.upper(): i for i, m in enumerate(M.MESES) if m}


def _filas(ws, ancho):
    """Las filas de DATOS de una pestaña de motor.

    Se reconocen porque la segunda columna es una `fecha` en ISO. No vale con «tiene algo
    escrito»: las tres pestañas llevan notas sueltas en las primeras filas («OPCIONAL. Solo
    hace falta si queréis…»), y arrastrarlas las duplicaría en la hoja nueva, que ya trae
    las suyas.
    """
    out = []
    for r in range(2, ws.max_row + 1):
        f = ws.cell(r, 2).value
        # En `datos` la fecha es TEXTO (la escribe n8n en ISO), pero en `datos-google` el
        # script de Google Ads la deja como FECHA de verdad y Sheets la convierte. Si aquí
        # solo se aceptara el texto, las 209 filas de Cliente 03 se perderían enteras.
        es_fecha = (isinstance(f, (datetime.date, datetime.datetime))
                    or (isinstance(f, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", f.strip())))
        if es_fecha:
            out.append([ws.cell(r, c).value for c in range(1, ancho + 1)])
    return out


def rescatar(ruta):
    """Todo lo que NO se puede volver a generar: datos, ventas, y lo escrito a mano."""
    wb = openpyxl.load_workbook(ruta)
    r = {"motor": {}, "tabs": {}}
    for n in MOTOR:
        if n in wb.sheetnames:
            r["motor"][n] = _filas(wb[n], wb[n].max_column)
    for n in wb.sheetnames:
        if n in MOTOR:
            continue
        ws = wb[n]
        # B6 (ticket medio) YA NO se rescata: desde el 15-09-2026 es una fórmula que sale de
        # lo facturado a mano. Rescatarla y devolverla la congelaba, y si la hoja de origen
        # venía con la fórmula mal, se arrastraba el error a la hoja nueva.
        t = {"D6": ws["D6"].value, "J6": ws["J6"].value, "manual": []}
        mes, cab = None, {}
        for row in range(1, ws.max_row + 1):
            a = ws.cell(row, 1).value
            if not isinstance(a, str):
                continue
            s = a.strip()
            if s.upper() in MES_N and False:
                pass
            m = re.match(r"^([A-ZÁÉÍÓÚÑ]+)\s+(\d{4})$", s.upper())
            if m and m.group(1) in MES_N:
                mes = MES_N[m.group(1)]
            elif s == "Semana":
                cab = {ws.cell(row, c).value: c for c in range(1, ws.max_column + 1)
                       if ws.cell(row, c).value}
            elif s.startswith("Del ") and mes:
                d = int(re.match(r"Del (\d+)", s).group(1))
                for et in ("Cierres (a mano)", "Facturado"):
                    c = cab.get(et)
                    if not c:
                        continue
                    v = ws.cell(row, c).value
                    if a_mano(v):
                        v = getattr(v, "text", v)
                        fn = ws.cell(row, cab["Funnel"]).value if "Funnel" in cab else None
                        t["manual"].append({"mes": mes, "dia": d, "col": et,
                                            "valor": v, "funnel": fn})
        r["tabs"][n] = t
    return r


def devolver(wb, resc):
    """Vuelve a escribir lo rescatado sobre el libro NUEVO, buscando por mes + día."""
    puestos, perdidos = [], []
    for n, t in resc["tabs"].items():
        if n not in wb.sheetnames:
            perdidos += [f"pestaña «{n}» ya no existe: {len(t['manual'])} valor(es)"]
            continue
        ws = wb[n]
        # Las celdas de arriba solo si llevaban un valor, no una fórmula (el histórico las
        # lee de «Reporte Meta» y ahí NO se pisa nada).
        for cel in ("D6", "J6"):
            v = t[cel]
            if a_mano(v):
                ws[cel] = v
        mes, cab, semanas = None, {}, {}
        for row in range(1, ws.max_row + 1):
            a = ws.cell(row, 1).value
            if not isinstance(a, str):
                continue
            s = a.strip()
            m = re.match(r"^([A-ZÁÉÍÓÚÑ]+)\s+(\d{4})$", s.upper())
            if m and m.group(1) in MES_N:
                mes = MES_N[m.group(1)]
            elif s == "Semana":
                cab = {ws.cell(row, c).value: c for c in range(1, ws.max_column + 1)
                       if ws.cell(row, c).value}
            elif s.startswith("Del ") and mes:
                a_, b_ = map(int, re.match(r"Del (\d+) al (\d+)", s).groups())
                fn = ws.cell(row, cab["Funnel"]).value if "Funnel" in cab else None
                semanas.setdefault((mes, fn), []).append((a_, b_, row, cab))
        for x in t["manual"]:
            cand = semanas.get((x["mes"], x["funnel"])) or []
            fila = next((c for c in cand if c[0] <= x["dia"] <= c[1]), None)
            if not fila:
                perdidos.append(f"{n} · mes {x['mes']} día {x['dia']} · {x['col']}={x['valor']}")
                continue
            _, _, row, cab = fila
            # Lo que estaba escrito ENCIMA de la fórmula de «Facturado» va ahora a su propia
            # columna, «Facturado (a mano)»: si se devolviera a «Facturado» volvería a tapar
            # la fórmula y el ticket medio no podría calcularse (referencia circular).
            col = x["col"]
            if col == "Facturado" and "Facturado (a mano)" in cab:
                col = "Facturado (a mano)"
            ws.cell(row, cab[col]).value = x["valor"]
            puestos.append(f"{n} · {M.MESES[x['mes']]} · día {x['dia']} → fila «{ws.cell(row,1).value}»"
                           f" · {col}={x['valor']}")
    return puestos, perdidos


def subir(ruta_xlsx, sid):
    cuerpo, cab = _multipart({"mimeType": HOJA}, ruta_xlsx, XLSX)
    api(f"https://www.googleapis.com/upload/drive/v3/files/{sid}"
        f"?uploadType=multipart&supportsAllDrives=true", data=cuerpo, headers=cab,
        metodo="PATCH")
