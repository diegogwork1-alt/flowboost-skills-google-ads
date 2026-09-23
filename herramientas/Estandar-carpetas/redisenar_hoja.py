#!/usr/bin/env python3
"""Pasa la hoja de un cliente al diseño ACTUAL sin perder lo escrito a mano.

POR QUÉ: `montar_hoja_reportes.py` rehace el libro entero, así que cambiar una columna
borra los cierres, el ticket, el margen, el fee y la pestaña `ventas`. Esto hace lo mismo
pero rescatando y devolviendo todo eso.

CÓMO: se exporta la hoja, se lee lo que hay, se reconstruye con la plantilla nueva y se
devuelve lo rescatado buscando **por mes + etiqueta de semana**, NUNCA por número de fila
—las filas se mueven en cuanto cambia el número de columnas o de meses—. Es el método con
el que se rescató Cliente 11 el 10-09-2026.

⛔ NO rescata `Reporte Google` ni `datos-google`: esas pestañas no las monta la plantilla.
Si la hoja las tiene, el script SE NIEGA salvo que se le pase --pierdo-google.

Uso:  redisenar_hoja.py <sheet_id> "<Cliente>" <cuenta> [--anio 2026] [--dry] [--pierdo-google]
"""
import json, os, re, sys, tempfile, time, urllib.parse, urllib.request
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from subir_a_drive import api, token, _multipart
import montar_hoja_reportes as M
from openpyxl import load_workbook

HOJA = "application/vnd.google-apps.spreadsheet"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def bajar(sid, dest):
    u = (f"https://www.googleapis.com/drive/v3/files/{sid}/export?"
         + urllib.parse.urlencode({"mimeType": XLSX}))
    for i in range(6):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                u, headers={"Authorization": "Bearer " + token(refrescar=(i > 0))}))
            open(dest, "wb").write(r.read()); return
        except Exception as e:
            err = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"no se pudo exportar: {err}")


def rescatar(wb):
    """Lo que hay escrito a mano, indexado por (pestaña, mes, etiqueta de semana)."""
    out = {"params": {}, "cierres": {}, "ventas": [], "datos": []}
    for hoja in wb.sheetnames:
        if hoja in ("datos", "ventas", "datos-google"): continue
        ws = wb[hoja]
        # cabecera: donde esté
        cab = None
        for r in range(1, min(ws.max_row, 60) + 1):
            fila = {ws.cell(r, c).value: c for c in range(1, 20)
                    if isinstance(ws.cell(r, c).value, str)}
            if "Inversión" in fila and "Cierres (a mano)" in fila: cab = fila; break
        if not cab: continue
        for ref, nom in (("B6", "ticket"), ("D6", "margen"), ("J6", "fee")):
            v = ws[ref].value
            if v not in (None, "", 0) and not (isinstance(v, str) and v.startswith("=")):
                out["params"][(hoja, nom)] = v
        cf = cab.get("Funnel")
        mes = None
        for r in range(1, ws.max_row + 1):
            a = ws.cell(r, 1).value
            if isinstance(a, str):
                m = re.match(r"\s*([A-ZÁÉÍÓÚÑ]+)\s+\d{4}", a.strip())
                if m: mes = m.group(1)
                if a.strip().lower().startswith("del ") and mes:
                    fn = str(ws.cell(r, cf).value) if cf else ""
                    for etiq in ("Cierres (a mano)", "Facturado (a mano)", "Facturado"):
                        if etiq not in cab: continue
                        v = ws.cell(r, cab[etiq]).value
                        if v in (None, "", 0) or (isinstance(v, str) and v.startswith("=")):
                            continue
                        # «Facturado» y «Facturado (a mano)» son la MISMA casilla en distintas
                        # versiones del diseño: se guardan bajo la misma clave.
                        cual = "cierres" if etiq.startswith("Cierres") else "facturado"
                        out["cierres"][(hoja, mes, a.strip(), fn, cual)] = v
    if "datos" in wb.sheetnames:
        ws = wb["datos"]
        for r in range(2, ws.max_row + 1):
            if ws.cell(r, 1).value:
                out["datos"].append([ws.cell(r, c).value for c in range(1, len(M.DATOS) + 1)])
    if "ventas" in wb.sheetnames:
        ws = wb["ventas"]
        for r in range(2, ws.max_row + 1):
            if ws.cell(r, 1).value:
                out["ventas"].append([ws.cell(r, c).value for c in range(1, len(M.VENTAS) + 1)])
    return out


def devolver(wb, resc, solo_meta=False):
    """Vuelve a escribir lo rescatado en el libro NUEVO, buscando por mes + etiqueta."""
    puestos = {"params": 0, "cierres": 0, "ventas": 0}
    perdidos = []
    for hoja in wb.sheetnames:
        if hoja in ("datos", "ventas", "datos-google"): continue
        ws = wb[hoja]
        for ref, nom in (("B6", "ticket"), ("D6", "margen"), ("J6", "fee")):
            if (hoja, nom) in resc["params"]:
                ws[ref] = resc["params"][(hoja, nom)]; puestos["params"] += 1
        cab = {ws.cell(9, c).value: c for c in range(1, 20) if ws.cell(9, c).value}
        col = cab.get("Cierres (a mano)")
        mes = None
        for r in range(1, ws.max_row + 1):
            a = ws.cell(r, 1).value
            if not isinstance(a, str): continue
            m = re.match(r"\s*([A-ZÁÉÍÓÚÑ]+)\s+\d{4}", a.strip())
            if m: mes = m.group(1)
            if a.strip().lower().startswith("del ") and mes and col:
                cf2 = cab.get("Funnel")
                fn = str(ws.cell(r, cf2).value) if cf2 else ""
                for cual, c in (("cierres", col), ("facturado", cab.get("Facturado (a mano)"))):
                    k = (hoja, mes, a.strip(), fn, cual)
                    if k in resc["cierres"] and c:
                        ws.cell(r, c).value = resc["cierres"].pop(k); puestos["cierres"] += 1
    perdidos = list(resc["cierres"])          # los que no encontraron su sitio
    if resc["ventas"] and "ventas" in wb.sheetnames and not solo_meta:
        ws = wb["ventas"]
        for i, fila in enumerate(resc["ventas"], start=2):
            for j, v in enumerate(fila, start=1): ws.cell(i, j).value = v
        puestos["ventas"] = len(resc["ventas"])
    return puestos, perdidos


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sid, cliente, cuenta = args[0], args[1], args[2]
    anio = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--anio=")), 2026))
    dry = "--dry" in sys.argv
    funnels = []
    for a in sys.argv:
        if a.startswith("--funnel="):
            nom, marcas = a[len("--funnel="):].split("=", 1) if "=" in a[len("--funnel="):] \
                else (a[len("--funnel="):], "")
            funnels.append((nom.strip(), [m.strip() for m in marcas.split(";") if m.strip()]))
    corte = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--corte-mes=")), None)
    desde = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--desde-mes=")), None)
    if desde is None:
        sys.exit("✗ falta --desde-mes=N. NO se pone enero por defecto: cada hoja arranca en "
                 "el mes en que entró el cliente, y meter meses de más le inventa bloques "
                 "vacíos que nunca tuvo.")
    tmp = os.path.join(tempfile.mkdtemp(), "a.xlsx"); bajar(sid, tmp)
    viejo = load_workbook(tmp)

    # ⛔ Estructuras que la regeneración simple NO reproduce y se perderían en silencio:
    #    · la columna «Funnel» (la hoja se montó con --funnel y cada semana tiene una fila
    #      por funnel; sin ella se fusionarían y se perdería qué negocio paga)
    #    · la pestaña «Histórico hasta <mes>» (se montó con --corte-mes)
    ws0 = viejo[[h for h in viejo.sheetnames if h.startswith("Reporte")][0]]
    tiene_funnel = any(ws0.cell(9, c).value == "Funnel" for c in range(1, 20))
    historico = [h for h in viejo.sheetnames if h.lower().startswith("histórico")]
    if (tiene_funnel and not funnels) or (historico and not corte):
        sys.exit(f"✗ {cliente}: esta hoja usa "
                 + " y ".join(filter(None, ["FUNNELS" if tiene_funnel else "",
                                            f"la pestaña {historico}" if historico else ""]))
                 + ".\n  Regenerarla así la perdería. Hay que rehacerla con los mismos "
                   "--funnel / --corte-mes con que se montó, y eso se hace a mano.")

    google = [h for h in viejo.sheetnames if h.lower() in ("reporte google", "datos-google")]
    if google and not {"--pierdo-google", "--solo-meta"} & set(sys.argv):
        sys.exit(f"✗ {cliente}: esta hoja tiene {google} y la plantilla NO las monta.\n"
                 f"  Regenerar las BORRA y `datos-google` solo vuelve reejecutando el script "
                 f"en Google Ads.\n  Si aun así querés seguir: --pierdo-google")

    resc = rescatar(viejo)
    marca = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--marca=")), "")
    if marca:
        icam = M.DATOS.index("campana")
        fuera = [f for f in resc["datos"] if marca.lower() not in str(f[icam]).lower()]
        resc["datos"] = [f for f in resc["datos"] if marca.lower() in str(f[icam]).lower()]
        if fuera:
            ig = sum(float(f[M.DATOS.index("gasto")] or 0) for f in fuera)
            nom = sorted({str(f[icam]) for f in fuera})
            print(f"  ⚠ fuera del reporte por no llevar «{marca}»: {len(fuera)} fila(s), "
                  f"{ig:.2f} € en {len(nom)} campaña(s)")
            for n in nom: print(f"     · {n[:62]}")
    print(f"  rescatado: {len(resc['params'])} parámetro(s), {len(resc['cierres'])} cierre(s), "
          f"{len(resc['datos'])} fila(s) de datos, {len(resc['ventas'])} venta(s)")
    if dry:
        for k, v in resc["cierres"].items(): print(f"     · {k[0]} {k[1]} {k[2]} → {v}")
        print("  (--dry: no se toca nada)"); return

    if "--solo-meta" in sys.argv:
        # ⛔ Se sustituye ÚNICAMENTE la pestaña «Reporte Meta», dentro del MISMO libro.
        # Así `Reporte Google`, `datos-google`, `datos` y `ventas` se quedan intactas: no
        # hay que rehacerlas ni recuperar su histórico. Las referencias de `Reporte Google`
        # a 'Reporte Meta'!$B$6/$D$6/$J$6 siguen valiendo porque esas celdas no se mueven.
        nuevo = viejo
        M._configurar(); M._comprobar_columnas()
        pos = nuevo.sheetnames.index("Reporte Meta")
        del nuevo["Reporte Meta"]
        M.hoja_reporte(nuevo, "Reporte Meta", cliente, cuenta, anio, range(desde, 13))
        nuevo.move_sheet("Reporte Meta", offset=pos - nuevo.sheetnames.index("Reporte Meta"))
        intactas = [h for h in nuevo.sheetnames if h != "Reporte Meta"]
        print(f"  intactas : {intactas}")
    else:
        nuevo = M.construir(cliente, cuenta, anio, desde, resc["datos"], funnels, corte)
    puestos, perdidos = devolver(nuevo, resc, "--solo-meta" in sys.argv)
    print(f"  devuelto : {puestos['params']} parámetro(s), {puestos['cierres']} cierre(s), "
          f"{puestos['ventas']} venta(s)")
    if perdidos:
        print("  ⚠ NO se han podido recolocar (se han quedado fuera):")
        for k in perdidos: print(f"     · {k}")
        sys.exit("✗ no se sube nada: habría pérdida de datos escritos a mano")

    out = os.path.join(tempfile.mkdtemp(), "n.xlsx"); nuevo.save(out)
    cuerpo, cab = _multipart({"mimeType": HOJA}, out, XLSX)
    api(f"https://www.googleapis.com/upload/drive/v3/files/{sid}"
        f"?uploadType=multipart&supportsAllDrives=true", data=cuerpo, headers=cab, metodo="PATCH")
    print(f"  ✓ https://docs.google.com/spreadsheets/d/{sid}/edit")


if __name__ == "__main__":
    main()
