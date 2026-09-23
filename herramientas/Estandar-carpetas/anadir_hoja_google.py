#!/usr/bin/env python3
"""Añade a la hoja de reportes de un cliente las DOS pestañas de Google Ads.

  `Reporte Google`  — mismo diseño que el de Meta: una fila por semana, un bloque por mes,
                      el año entero y ROAS. Son fórmulas; no las toca nadie.
  `datos-google`    — lo crudo, una fila por día y campaña. Lo escribe el SCRIPT DE GOOGLE ADS
                      (ver `google-ads-script-a-sheets.js`), no n8n.

NO toca las pestañas que ya existen (`Reporte`, `datos`, `ventas`): el reporte de Meta está
aprobado por Dirección y se queda exactamente como está. Si las pestañas de Google ya existen,
no hace nada salvo que se pase --rehacer.

Por qué en el MISMO archivo y no en uno aparte: la pestaña `ventas` trae los cerrados del CRM.
Compartiendo archivo, el ROAS se calcula contra las MISMAS ventas reales, y se puede mirar
Meta y Google contra una sola fuente de facturación.

Uso:
  python3 anadir_hoja_google.py "Cliente 01"
  python3 anadir_hoja_google.py "Cliente 01" --anio 2026 --desde-mes 9 --rehacer
"""
import argparse, calendar, io, os, subprocess, sys, tempfile
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
# Se reutiliza TODO del generador de Meta: colores, formatos, el helper de celda y las semanas.
# Así los dos reportes no pueden divergir de estilo.
from montar_hoja_reportes import (F, semanas, MESES, EUR, ENT, PCT, DEC2,
                                  EURG, ENTG, PCTG, PCT0G, DEC2G, ROASG,
                                  NEGRO, GRIS, BLANCO, FIN as FILA_FIN, HOJA, XLSX)

# Paleta de GOOGLE, para que no se confunda con la de Meta al abrir la hoja (Dirección, 10-09-2026).
# Meta va en azul #0866FF + negro; Google en sus propios colores de marca.
G_AZUL   = "1A73E8"   # cabecera de mes
G_GRIS   = "202124"   # cabecera de columnas (el gris oscuro de Google)
G_VERDE  = "188038"   # fila de totales
G_SUAVE  = "F8F9FA"   # franja alterna
# El fondo de las celdas que se escriben a mano es EL MISMO que en «Reporte Meta»: si cada
# pestaña usa un azul distinto, en una se ve el hueco y en la otra no. El E8F0FE que había
# aquí era casi blanco — el mismo problema que ya se corrigió en Meta (Dirección, 10-09-2026).
from montar_hoja_reportes import A_MANO_BG
MORADO, ROSA, SUAVE = G_AZUL, G_VERDE, G_SUAVE

# Columnas de Google Ads. NO son las de Meta: Google no da alcance, ni frecuencia, ni vistas
# de landing (eso es el píxel). En cambio sí da la cuota de impresiones, que en Búsqueda es
# el dato que dice cuánto mercado te estás dejando.
COLS_G = [("Semana", 22, "left"), ("Inversión", 13, "right"), ("Impresiones", 13, "right"),
          ("Clics", 11, "right"), ("CTR", 10, "right"), ("CPC medio", 12, "right"),
          ("Cuota de impresiones", 20, "right"), ("Clientes potenciales", 20, "right"),
          ("Coste por lead", 15, "right"), ("Cierres (a mano)", 17, "right"),
          ("Facturado (a mano)", 18, "right"), ("Facturado", 15, "right"), ("Coste total", 14, "right"), ("ROAS", 11, "right"), ("ROAS mínimo", 14, "right"),
          ("Origen", 12, "center")]
# Las DOS columnas que se escriben a mano, igual que en el reporte de Meta: el NÚMERO de
# cierres de esa semana y el IMPORTE facturado. Sus letras se DEDUCEN de COLS_G: estaban
# escritas a pelo («CIERRES_COL_G = "J"») y al meter una columna nueva delante habrían
# seguido apuntando a la de al lado sin dar ningún error.
X_G = {n: get_column_letter(i + 1) for i, (n, _, _) in enumerate(COLS_G)}
CIERRES_COL_G = X_G["Cierres (a mano)"]
MANUAL_COL_G = X_G["Facturado (a mano)"]

DATOS_G = ["id", "fecha", "cliente", "campana", "coste", "impresiones", "clics", "ctr",
           "cpc", "conversiones", "valor_conversion", "cuota_impresiones", "actualizado"]
VENTAS = ["id", "fecha", "cliente", "oportunidad", "importe", "actualizado"]
G = {n: get_column_letter(i + 1) for i, n in enumerate(DATOS_G)}
V = {n: get_column_letter(i + 1) for i, n in enumerate(VENTAS)}
# El ticket, el margen y el % de cierre se escriben UNA sola vez, en «Reporte Meta», y desde
# aquí se apunta allí. Duplicados en las dos pestañas obligaban a escribirlos dos veces y, si
# divergían, el ROAS de Meta y el de Google salían con supuestos distintos — justo lo contrario
# de por qué los dos reportes viven en el mismo archivo.
META = "'Reporte Meta'"
# Ticket y margen SÍ son espejo de «Reporte Meta»: se escriben una vez y valen para los dos.
# El % que cierra NO: el de Google es el suyo, calculado en H6 de ESTA pestaña con sus propios
# cierres y sus propios leads. (Apuntaba a META!$F$6, que desde el 10-09-2026 son los CIERRES
# TOTALES de Meta y no un porcentaje: multiplicaba por un número de cierres, no por un %.)
TICKET, MARGEN = f"{META}!$B$6", f"{META}!$D$6"
CIERRE = "$H$6"
# El fee de agencia se escribe UNA vez, en «Reporte Meta»: es el mismo para los dos reportes.
FEE = "'Reporte Meta'!$J$6"


def cuota_prom(ini, fin, col=None):
    """Media de la cuota de impresiones de los DÍAS con dato entre `ini` y `fin`.

    Vale para una semana y para un mes entero: se recalcula siempre desde `datos-google`,
    nunca promediando la columna ya calculada de la hoja (ver el aviso del TOTAL DEL MES).
    """
    col = col or G["cuota_impresiones"]
    rng = f"'datos-google'!${col}$2:${col}${FILA_FIN}"
    fch = f'TEXT(\'datos-google\'!${G["fecha"]}$2:${G["fecha"]}${FILA_FIN},"yyyy-mm-dd")'
    cond = f'({fch}>="{ini}")*({fch}<="{fin}")'
    return f'IFERROR(SUMPRODUCT({cond}*{rng})/SUMPRODUCT({cond}*({rng}<>"")),0)'


def formulas_g(ini, fin, fila):
    """Fila de semana del reporte de Google: SUMPRODUCT por rango de fechas sobre `datos-google`.

    SUMPRODUCT y no SUMIFS: la columna de fecha es TEXTO, y SUMIFS con un criterio ">=2026-09-01"
    lo interpreta como fecha y devuelve vacío. Ya pasó en el reporte de Meta.
    """
    import calendar as _cal
    _a, _m, _d1 = (int(x) for x in ini.split("-"))
    _dias = int(fin.split("-")[2]) - _d1 + 1
    # Parte del fee mensual que toca a esta semana, por DÍAS: la última semana del mes suele
    # tener 2-3 días y no puede cargar un mes entero de fee.
    _fee = "0"     # pago único mensual: no se trocea entre semanas (ver montar_hoja_reportes)
    rng = lambda col: f"'datos-google'!${col}$2:${col}${FILA_FIN}"
    # TEXT() alrededor de la fecha: el script de Google Ads escribe la columna y Sheets la
    # convierte a FECHA REAL, con lo que comparar contra el texto "2026-09-01" daba 0 en todo.
    # TEXT() deja igual lo que ya es texto y formatea lo que es fecha, así funciona en los dos
    # casos y no depende de cómo lo escriba quien rellene la pestaña.
    fch = f'TEXT({rng(G["fecha"])},"yyyy-mm-dd")'
    cond = f'({fch}>="{ini}")*({fch}<="{fin}")'
    s = lambda col: f'SUMPRODUCT({cond}*{rng(col)})'
    prom = lambda col: cuota_prom(ini, fin)
    gs, im, cl = s(G["coste"]), s(G["impresiones"]), s(G["clics"])
    conv = s(G["conversiones"])
    vr = f'{rng(V["fecha"])}'
    fv = f'TEXT(\'ventas\'!${V["fecha"]}$2:${V["fecha"]}${FILA_FIN},"yyyy-mm-dd")'
    cv = f'({fv}>="{ini}")*({fv}<="{fin}")'
    vent = f'SUMPRODUCT({cv}*\'ventas\'!${V["importe"]}$2:${V["importe"]}${FILA_FIN})'
    nvent = f'SUMPRODUCT({cv}*1)'
    # De dónde sale el facturado, por orden de mando (idéntico al reporte de Meta):
    #   1. el CRM, si trajo ventas de esa semana  → dato real
    #   2. los cierres escritos a mano            → cierres × ticket medio
    #   3. la estimación                          → leads × % de cierre × ticket medio
    # Nunca se suman: manda uno y punto, y la columna «Origen» dice cuál.
    cie = f"${CIERRES_COL_G}{fila}"
    man = f"${MANUAL_COL_G}{fila}"
    fac = (f'IF({nvent}>0,{vent},'
           f'IF(N({man})>0,N({man}),'
           f'IF(N({cie})>0,N({cie})*{TICKET},'
           f'IF(OR({TICKET}=0,{CIERRE}=0),0,{conv}*{CIERRE}*{TICKET}))))')
    origen = (f'IF(B{fila}=0,"—",IF({nvent}>0,"ventas",'
              f'IF(OR(N({man})>0,N({cie})>0),"a mano","estimado")))')
    return [
        (f"={gs}", EURG), (f"={im}", ENTG), (f"={cl}", ENTG),
        (f"=IFERROR({cl}/{im},0)", PCTG),
        (f"=IFERROR({gs}/{cl},0)", EURG),
        (f"={prom(G['cuota_impresiones'])}", PCT0G),
        (f"={conv}", ENTG),
        (f"=IFERROR({gs}/{conv},0)", EURG),
        ("__A_MANO__", ENTG),                 # «Cierres (a mano)»: hueco, no fórmula
        ("__A_MANO__", EURG),                 # «Facturado (a mano)»: el otro hueco
        (f"={fac}", EURG),
        (f"=B{fila}", EURG),                        # Coste total de la SEMANA = su inversión
        (f"=IFERROR(K{fila}/L{fila},0)", ROASG),    # ROAS sobre el COSTE TOTAL, no la inversión
        (f"=IFERROR(1/{MARGEN},0)", ROASG),
        (f"={origen}", None),
    ]


def _comprobar_columnas():
    """Lo mismo que en el reporte de Meta: COLS_G y formulas_g se cambian A LA VEZ."""
    f = formulas_g("2026-01-01", "2026-01-07", 10)
    if len(f) != len(COLS_G) - 1:
        raise SystemExit(
            f"⛔ El script está a medio editar: {len(COLS_G)} columnas en COLS_G "
            f"({len(COLS_G)-1} sin «Semana») y {len(f)} fórmulas por fila.\n"
            f"   COLS_G: {[c[0] for c in COLS_G]}\n"
            f"   Cuadra las dos listas antes de generar nada.")


def pestana_reporte(wb, cliente, anio, desde_mes):
    _comprobar_columnas()
    ws = wb.create_sheet("Reporte Google", 1)      # justo detrás del de Meta
    ws.sheet_properties.tabColor = G_AZUL          # el azul de Google
    ws.sheet_view.showGridLines = False
    for j, (_, an, _) in enumerate(COLS_G, start=1):
        ws.column_dimensions[get_column_letter(j)].width = an

    F(ws, "A1", f"{cliente} — Google Ads", tam=18, bold=True, color=NEGRO)
    F(ws, "A2", "Búsqueda y Display. Las ventas y la facturación salen de la pestaña "
                "`ventas`, la misma que el reporte de Meta: el ROAS de los dos se mide "
                "contra el MISMO dinero real.", tam=9, color=GRIS, italic=True)
    F(ws, "A4", "PARA CALCULAR EL ROAS — nada de esto se rellena aquí",
      tam=9, bold=True, color=GRIS)
    for ref, et in (("A5", "Ticket medio"), ("C5", "Margen"),
                    ("E5", "Cierres totales de Google"), ("G5", "% que cierra en Google")):
        F(ws, ref, et, tam=8, bold=True, color=GRIS)
    # Ticket y margen son ESPEJO de «Reporte Meta»: se rellenan una sola vez y valen para los
    # dos reportes. Por eso no llevan el fondo de «(a mano)», que aquí sería mentira.
    for ref, fmt in (("B6", EURG), ("D6", PCT0G)):
        F(ws, ref, f"={META}!{ref}", tam=13, bold=True, color=NEGRO, fmt=fmt,
          fondo=G_SUAVE, hor="right")
    # Los cierres y el % SÍ son propios: los de Google no son los de Meta. Se escriben abajo,
    # cuando ya se sabe en qué filas quedaron los totales de cada mes.
    F(ws, "I5", "El ticket y el margen se rellenan en «Reporte Meta» y valen para los dos. "
                "Los cierres totales y el % que cierra son de GOOGLE: salen solos de la columna "
                "«Cierres (a mano)» de esta pestaña. Mientras el ticket esté a cero, el ROAS "
                "sale «—».",
      tam=8, color=GRIS, italic=True)

    fila = 9
    filas_total = []                # filas «TOTAL DEL MES», para sumar el año
    for mes in range(desde_mes, 13):
        F(ws, f"A{fila}", f"{MESES[mes]} {anio}", tam=13, bold=True, color=BLANCO, fondo=MORADO)
        for j in range(2, len(COLS_G) + 1):
            F(ws, f"{get_column_letter(j)}{fila}", "", fondo=MORADO)
        fila += 1
        for j, (c, _, hor) in enumerate(COLS_G, start=1):
            F(ws, f"{get_column_letter(j)}{fila}", c, tam=9, bold=True,
              color=BLANCO, fondo=G_GRIS, hor="center" if j > 1 else "left")
        fila += 1
        primera = fila
        sems = semanas(anio, mes)
        mes_ini, mes_fin = sems[0][1], sems[-1][2]
        for et, ini, fin in sems:
            F(ws, f"A{fila}", et, tam=10, hor="left",
              fondo=SUAVE if (fila - primera) % 2 else None)
            for j, (v, fmt) in enumerate(formulas_g(ini, fin, fila), start=2):
                # «Cierres (a mano)» es un HUECO para escribir, no una fórmula. Va con fondo
                # azul claro para que se vea que hay que rellenarlo.
                a_mano = (v == "__A_MANO__")
                F(ws, f"{get_column_letter(j)}{fila}", "" if a_mano else v, tam=10, fmt=fmt,
                  hor="right",
                  fondo=A_MANO_BG if a_mano else (SUAVE if (fila - primera) % 2 else None))
            fila += 1
        # Total del mes.
        # ⛔ NUNCA promediar los ratios de las filas de semana. Es el mismo error que el
        # aviso de Looker: un AVERAGE() sobre CTR/CPC/CPL cuenta como CERO las semanas que
        # todavía no han pasado y hunde el número. En Cliente 03 llegó a enseñar un coste
        # por lead de 15,01 € cuando el real era 24,06 € (10-09-2026). Cada ratio se calcula
        # sobre las SUMAS del mes, igual que en el reporte de Meta.
        F(ws, f"A{fila}", "TOTAL DEL MES", tam=10, bold=True, color=BLANCO, fondo=ROSA)
        filas_total.append(fila)
        ult = fila - 1
        # Por NOMBRE de columna, nunca por letra fija: el 21-09-2026 se añadió «Facturado
        # (a mano)» a COLS_G y, con las letras a pelo, la fila de TOTAL quedó corrida — el
        # ROAS acabó escrito en la casilla de «Coste total», que salía 0.
        L = {c[0]: get_column_letter(i + 1) for i, c in enumerate(COLS_G)}
        S = lambda nombre: f"SUM({L[nombre]}{primera}:{L[nombre]}{ult})"
        inv, imp, cli = S("Inversión"), S("Impresiones"), S("Clics")
        leads, fact = S("Clientes potenciales"), S("Facturado")
        totales = [
            (f"={inv}", EURG), (f"={imp}", ENTG), (f"={cli}", ENTG),
            (f"=IFERROR({cli}/{imp},0)", PCTG),          # CTR
            (f"=IFERROR({inv}/{cli},0)", EURG),          # CPC medio
            (f"={cuota_prom(mes_ini, mes_fin)}", PCT0G),  # cuota: media de los días del mes
            (f"={leads}", ENTG),
            (f"=IFERROR({inv}/{leads},0)", EURG),        # coste por lead
            (f"={S('Cierres (a mano)')}", ENTG),
            (f"={S('Facturado (a mano)')}", EURG),
            (f"={fact}", EURG),
            # Coste total del mes = inversión del mes + el fee ENTERO, una sola vez (es un
            # pago único mensual). Sin inversión en todo el mes no hubo servicio: tampoco fee.
            (f"=IF({inv}=0,0,{inv}+{FEE})", EURG),
            (f"=IFERROR({fact}/IF({inv}=0,0,{inv}+{FEE}),0)", ROASG),   # ROAS sobre el coste total
            (f"=IFERROR(1/{MARGEN},0)", ROASG),
            ("", None),                                  # «Origen»: no aplica al total
        ]
        if len(totales) != len(COLS_G) - 1:
            raise SystemExit(
                f"⛔ La fila de TOTAL no cuadra con COLS_G: {len(totales)} valores para "
                f"{len(COLS_G)-1} columnas. Así se escribe cada fórmula en la casilla de al "
                f"lado (el 21-09-2026 el ROAS acabó en «Coste total»). Cuadra las dos listas.")
        for j, (v, fmt) in enumerate(totales, start=2):
            F(ws, f"{get_column_letter(j)}{fila}", v, tam=10, bold=True, color=BLANCO,
              fondo=ROSA, fmt=fmt, hor="right")
        fila += 3
    ct = "+".join(f"N({CIERRES_COL_G}{f})" for f in filas_total) or "0"
    lt = "+".join(f"N(H{f})" for f in filas_total) or "0"
    F(ws, "F6", f"={ct}", tam=13, bold=True, color=NEGRO, fmt=ENTG, hor="right", fondo=G_SUAVE)
    F(ws, "H6", f"=IFERROR(({ct})/({lt}),0)", tam=13, bold=True, color=NEGRO, fmt=PCT0G,
      hor="right", fondo=G_SUAVE)
    ws.freeze_panes = "A9"
    return ws


def pestana_datos(wb):
    ws = wb.create_sheet("datos-google")
    ws.sheet_properties.tabColor = G_VERDE
    ws.freeze_panes = "B2"
    anchos = [26, 12, 16, 42, 12, 13, 11, 10, 11, 14, 16, 18, 15]
    for j, (c, an) in enumerate(zip(DATOS_G, anchos), start=1):
        ws.column_dimensions[get_column_letter(j)].width = an
        F(ws, f"{get_column_letter(j)}1", c, tam=8, bold=True, color=BLANCO, fondo=NEGRO,
          hor="center" if j > 4 else "left")
    F(ws, "A3", "Esta pestaña la escribe el SCRIPT DE GOOGLE ADS de la cuenta del cliente "
                "(google-ads-script-a-sheets.js), programado a diario. No la toca n8n ni "
                "nadie a mano: lo que se escriba aquí se pierde en el siguiente volcado.",
      tam=9, color=GRIS, italic=True)
    return ws


def primer_mes_con_datos(ws, anio):
    """El mes más antiguo de `datos-google` en ese año, o None si no hay nada.

    El reporte tiene que empezar donde empiezan los datos, no en el mes en que se ejecuta el
    script. Arrancando en `hoy.month` se dejaba fuera todo lo anterior: Cliente 03 llegó a
    enseñar 409 € de una cuenta que llevaba gastados 4.029 € (10-09-2026).
    """
    meses = []
    for f in range(2, ws.max_row + 1):
        v = ws.cell(f, 2).value            # columna `fecha`
        if not v:
            continue
        if hasattr(v, "year"):             # Sheets la convierte a fecha real
            a, m = v.year, v.month
        else:
            try:
                a, m = int(str(v)[:4]), int(str(v)[5:7])
            except ValueError:
                continue
        if a == anio:
            meses.append(m)
    return min(meses) if meses else None


def _buscar_hoja_reportes(cliente):
    """El ID de la hoja «Reporte Meta Ads — <cliente> — <año>», y solo de esa."""
    import urllib.parse
    from subir_a_drive import api
    # «Reporte Ads — …» y «Reporte Meta Ads — …»: el archivo se renombró al meter Google
    # dentro, y buscar la cadena larga dejaba de encontrarlo. Se busca por «Reporte» + el
    # cliente, y se descartan las hojas de «Estado de cuenta».
    q = (f"name contains 'Reporte' and name contains '{cliente}' "
         f"and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false")
    r = api("https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(
        {"q": q, "fields": "files(id,name)", "pageSize": 10,
         "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}))
    fs = [f for f in r.get("files", []) if "estado" not in f["name"].lower()]
    if len(fs) > 1:                      # varios años: el más reciente por nombre
        fs.sort(key=lambda x: x["name"], reverse=True)
    return fs[0]["id"] if fs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente")
    ap.add_argument("--sheet-id", default="")
    ap.add_argument("--anio", type=int, default=0)
    ap.add_argument("--desde-mes", type=int, default=0)
    ap.add_argument("--rehacer", action="store_true",
                    help="borra las pestañas de Google si ya existen y las vuelve a crear")
    ap.add_argument("--salida", default="", help="guardar en un .xlsx local en vez de subir")
    a = ap.parse_args()

    from datetime import date
    hoy = date.today()
    anio = a.anio or hoy.year
    desde = a.desde_mes or hoy.month

    if a.salida:                      # modo prueba: no toca Drive
        from openpyxl import Workbook
        wb = Workbook(); wb.active.title = "Reporte"; wb.create_sheet("datos")
        wb.create_sheet("ventas")
        pestana_reporte(wb, a.cliente, anio, desde); pestana_datos(wb)
        wb.save(a.salida); print(f"✓ {a.salida} ({', '.join(wb.sheetnames)})")
        return

    import marcar_etapa as me
    # OJO: NO vale me.buscar_por_nombre(cliente). Devuelve la primera hoja del cliente que
    # encuentra, y la de «Estado de cuenta» gana: así se metieron estas pestañas en el archivo
    # equivocado la primera vez. Hay que buscar la de REPORTES por su nombre exacto.
    sid = a.sheet_id or _buscar_hoja_reportes(a.cliente)
    if not sid:
        sys.exit(f"⛔ No encontré la hoja «Reporte Meta Ads — {a.cliente} — …» en el Drive. "
                 f"¿Está dada de alta con alta_reportes.py?")

    # api() solo devuelve JSON; el .xlsx es binario y lo baja el descargador de marcar_etapa.
    tmp = os.path.join(tempfile.mkdtemp(), "hoja.xlsx")
    me._descargar_xlsx(sid, tmp)
    wb = load_workbook(tmp)

    # Sin --desde-mes, el reporte arranca donde arrancan los datos, no en el mes de hoy.
    if not a.desde_mes and "datos-google" in wb.sheetnames:
        m = primer_mes_con_datos(wb["datos-google"], anio)
        if m and m < desde:
            print(f"  · datos-google empieza en el mes {m}: el reporte arranca ahí")
            desde = m

    ya = [n for n in ("Reporte Google", "datos-google") if n in wb.sheetnames]
    if ya and not a.rehacer:
        print(f"✓ {a.cliente}: ya tiene {', '.join(ya)}. Nada que hacer "
              f"(--rehacer para recrearlas).")
        return
    for n in ya:
        # Nunca se tira `datos-google` si el script de Google Ads ya escribió: son datos
        # históricos que solo se recuperan volviendo a ejecutar el script en la cuenta.
        if n == "datos-google" and wb[n].max_row > 3:
            print(f"  · «datos-google» tiene {wb[n].max_row - 1} filas: NO se toca")
            continue
        del wb[n]

    pestana_reporte(wb, a.cliente, anio, desde)
    # Solo se crea si no sobrevivió a la limpieza de arriba. Sin esta comprobación, conservar
    # la original y crearla otra vez dejaba una «datos-google1» duplicada y vacía.
    if "datos-google" not in wb.sheetnames:
        pestana_datos(wb)
    wb.save(tmp)

    cuerpo, cabs = me._multipart({"mimeType": HOJA}, tmp, XLSX)
    me.api(f"https://www.googleapis.com/upload/drive/v3/files/{sid}"
           f"?uploadType=multipart&supportsAllDrives=true",
           data=cuerpo, headers=cabs, metodo="PATCH")
    print(f"✓ {a.cliente}: añadidas «Reporte Google» y «datos-google»")
    print(f"  https://docs.google.com/spreadsheets/d/{sid}/edit")
    print(f"  Siguiente paso: pegar google-ads-script-a-sheets.js en la cuenta de Google Ads")
    print(f"  y darle permiso de EDICIÓN sobre esta hoja.")


if __name__ == "__main__":
    main()
