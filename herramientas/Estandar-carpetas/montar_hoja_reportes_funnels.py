#!/usr/bin/env python3
"""Hoja de reportes de un cliente que corre VARIOS FUNNELS en la misma cuenta de Meta.

POR QUÉ EXISTE, aparte de `montar_hoja_reportes.py`:
  Cliente 06 corre tres ofertas distintas desde una sola cuenta publicitaria: captar
  propiedades para vender, vender UN piso concreto (Burriana) y vender casas de hormigón
  celular. En una sola tabla eso se mezcla, y la mezcla MIENTE: el coste por lead medio de
  la cuenta salía 45,90 € cuando la captación estaba a 45,90 €, el piso a 23,65 € y las
  casas a 6,93 €. Y sobre todo, el ticket medio y el margen NO son los mismos en las tres
  —una comisión de venta no es lo que deja construir una casa—, así que un ROAS único de
  la cuenta no significa nada.
  Cada funnel tiene su PESTAÑA, con su ticket, su margen y sus cierres.

QUÉ NO CAMBIA respecto de la plantilla de la casa (y no hay que volver a romper):
  · La pestaña `datos` mantiene EXACTAMENTE el orden de columnas de siempre, porque el
    nodo «Armar filas» de n8n escribe por posición.
  · Una fila por SEMANA (1-7, 8-14, 15-21, 22-28, 29-fin), un bloque por mes, el año entero.
  · `SUMPRODUCT` y no `SUMIFS`: la fecha es TEXTO y `SUMIFS` la interpretaría como fecha,
    dejando todas las semanas a cero.
  · Los ratios del TOTAL DEL MES se calculan SOBRE LAS SUMAS del mes, nunca promediando
    las semanas: las que aún no han pasado valen cero y hunden la media.
  · Alcance y frecuencia se guardan en `datos` pero NO se enseñan: no son sumables.

QUÉ SÍ CAMBIA:
  · Pestaña `funnels`: clasifica CADA fila de `datos` en un funnel, una sola vez. Las
    semanas comparan contra esa columna en vez de repetir seis SEARCH por celda; con
    5.000 filas × 60 semanas × 3 pestañas, hacerlo dentro del SUMPRODUCT colgaba la hoja.
  · Pestaña `Resumen`: los tres funnels uno al lado del otro, mes a mes.
  · El FEE DE AGENCIA se escribe UNA vez (en `Resumen`) y se reparte entre los funnels
    A PRORRATA DE LA INVERSIÓN de cada mes. Cargarle el fee entero a cada funnel —como se
    hace entre Meta y Google— aquí no vale: son el mismo canal y el mismo cliente, y a
    Burriana, con 212 € invertidos, un fee de 1.100 € le hundiría el ROAS sin motivo.
    Así, los tres «Coste total» SÍ suman el coste real del mes.
  · `ventas` lleva una columna `funnel`: sin ella, una venta del CRM no se sabe a qué
    funnel imputarla y el dato real no se podría usar en ninguna pestaña.

Uso:
  python3 montar_hoja_reportes_funnels.py --cliente "Cliente 06" --cuenta <ID_META> \
      --anio 2026 --desde-mes 4 --carpeta-id <ID> --datos datos_Cliente 06.json
"""
import argparse, json, os, sys, tempfile, urllib.parse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from montar_hoja_reportes import (
    HOJA, XLSX, NEGRO, GRIS, SUAVE, BLANCO, ROJO, A_MANO_BG,
    EUR, ENT, PCT, DEC2, EURG, ENTG, PCTG, PCT0G, ROASG,
    MESES, DATOS, C, FIN, COLS, X, DESTACADAS, CIERRES_COL, ORIGEN_COL,
    TICKET, MARGEN, CIERRE, FEE_DEF, F, semanas,
)
from subir_a_drive import api, _multipart

# `ventas` NO es la de la plantilla de la casa: lleva `funnel`. Una venta que no se sabe de
# qué funnel viene no se puede imputar a ninguna pestaña sin inventar.
VENTAS = ["id", "fecha", "cliente", "funnel", "oportunidad", "importe", "actualizado"]
V = {n: get_column_letter(i + 1) for i, n in enumerate(VENTAS)}

RESUMEN, MOTOR = "Resumen", "funnels"
FEE = f"{RESUMEN}!$D$4"          # el fee del cliente, a mano, UNA sola vez

# Cuántas filas ocupan de verdad `datos` y `ventas`, calculado en la propia hoja.
# ⛔ NO se usan rangos fijos tipo `$2:$5000`, y no es manía: al convertir el .xlsx a Sheet,
# Google crea la rejilla del TAMAÑO DE LO ESCRITO. `datos` se quedaba en 443 filas y
# `funnels` en 5.000 (porque lleva fórmulas), así que dentro del mismo SUMPRODUCT un array
# medía 442 y el otro 4.999: **#N/A**. Y como el «Coste por lead» va envuelto en IFERROR,
# lo que se veía era un tranquilísimo 0,00 € con los datos correctos debajo.
# Con INDEX los dos rangos se cortan por la MISMA cifra, así que miden igual siempre, y
# además solo se recorre lo que hay en vez de 5.000 filas vacías.
NDATOS = f"{MOTOR}!$H$1"
NVENTAS = f"{MOTOR}!$H$2"


def _r(hoja, col, n):
    return f"{hoja}!${col}$2:INDEX({hoja}!${col}:${col},{n})"


FUN = _r(MOTOR, "A", NDATOS)     # el funnel de cada fila de `datos`, ya clasificado

# Columnas del Resumen. Sin CTR ni CPC: ahí se compara rentabilidad, no creatividades.
RCOLS = [("Funnel", 26, "left"), ("Inversión", 13, "right"),
         ("Clientes potenciales", 20, "right"), ("Coste por lead", 15, "right"),
         ("Cierres", 11, "right"), ("Facturado", 15, "right"),
         ("Coste total", 14, "right"), ("ROAS", 11, "right"), ("ROAS mínimo", 14, "right")]
R = {n: get_column_letter(i + 1) for i, (n, _, _) in enumerate(RCOLS)}


def _o(kws):
    """OR de SEARCH sobre el nombre de campaña, para la pestaña `funnels`."""
    t = [f'ISNUMBER(SEARCH("{k}",datos!${C["campana"]}{{r}}))' for k in kws]
    return t[0] if len(t) == 1 else "OR(" + ",".join(t) + ")"


class Funnel:
    """Un funnel: su pestaña, su color y qué campañas caen dentro.

    El orden IMPORTA: se evalúa de arriba abajo y gana el primero que casa. Por eso los
    funnels específicos («BURRIANA», «HORMIGON») van ANTES que el genérico de captación,
    que incluye «CONVERSIONES» — si no, «CONVERSIONES - VENTA DE PISO (BURRIANA)» caería
    en captación y los dos funnels de venta se quedarían vacíos sin dar ningún error.
    """
    def __init__(self, nombre, hoja, color, suave, incluye, detalle):
        self.nombre, self.hoja = nombre, hoja
        self.color, self.suave = color, suave
        self.incluye, self.detalle = incluye, detalle


def clasificador(funnels, r):
    """Fórmula que dice a qué funnel pertenece la fila `r` de `datos`."""
    f = '"Sin clasificar"'
    for fu in reversed(funnels):
        f = f'IF({_o(fu.incluye).format(r=r)},"{fu.nombre}",{f})'
    return f'=IF(datos!${C["campana"]}{r}="","",{f})'


def _sp(col, ini, fin, funnel=None):
    """Suma de una columna de `datos` entre dos fechas, opcionalmente de un solo funnel.

    SUMIFS no sirve: con un criterio «>=2026-09-01» Sheets lo lee como FECHA y la columna
    es TEXTO, así que no casa ni una fila. En ISO, el orden alfabético es el cronológico.
    """
    fe = _r("datos", C["fecha"], NDATOS)
    f = f'({fe}>="{ini}")*({fe}<="{fin}")'
    if funnel:
        f += f'*({FUN}="{funnel}")'
    else:                                  # todos los funnels, pero NO lo sin clasificar
        f += f'*({FUN}<>"")*({FUN}<>"Sin clasificar")'
    return f'SUMPRODUCT({f}*N({_r("datos", col, NDATOS)}))'


def _sv(col, ini, fin, funnel):
    fe = _r("ventas", V["fecha"], NVENTAS)
    fu = _r("ventas", V["funnel"], NVENTAS)
    return (f'SUMPRODUCT(({fe}>="{ini}")*({fe}<="{fin}")*({fu}="{funnel}")'
            f'*N({_r("ventas", col, NVENTAS)}))')


def fila_semana(fu, ini, fin, r):
    g, im = _sp(C["gasto"], ini, fin, fu.nombre), _sp(C["impresiones"], ini, fin, fu.nombre)
    ce, ld = _sp(C["clics_enlace"], ini, fin, fu.nombre), _sp(C["leads"], ini, fin, fu.nombre)
    fact = _sv(V["importe"], ini, fin, fu.nombre)
    fev, fuv = _r("ventas", V["fecha"], NVENTAS), _r("ventas", V["funnel"], NVENTAS)
    nv = f'SUMPRODUCT(({fev}>="{ini}")*({fev}<="{fin}")*({fuv}="{fu.nombre}")*1)'
    cie = f"${CIERRES_COL}{r}"
    # De dónde sale el facturado, por orden de mando. Nunca se suman entre sí:
    #   1. el CRM, si trajo ventas de ese funnel esa semana → importes reales
    #   2. los cierres escritos a mano                      → cierres × ticket medio
    #   3. la estimación                                    → leads × % cierre × ticket
    fac = (f'IF({nv}>0,{fact},IF(N({cie})>0,N({cie})*{TICKET},'
           f'IF(OR({TICKET}=0,{CIERRE}=0),0,{ld}*{CIERRE}*{TICKET})))')
    origen = (f'IF({X["Inversión"]}{r}=0,"—",IF({nv}>0,"ventas",IF(N({cie})>0,"a mano",'
              f'IF(OR({TICKET}=0,{CIERRE}=0),"—","estimado"))))')
    return [
        (f"={g}", EURG), (f"={im}", ENTG),
        (f"=IFERROR({ce}/{im},0)", PCTG), (f"={ce}", ENTG), (f"={ld}", ENTG),
        (f"=IFERROR({g}/{ld},0)", EURG), (f"=IFERROR({g}/{ce},0)", EURG),
        (None, ENTG),                                    # Cierres: el hueco a mano
        (f"={fac}", EURG),
        (f'={X["Inversión"]}{r}', EURG),                 # la semana solo lleva su inversión
        (f'=IFERROR({X["Facturado"]}{r}/{X["Coste total"]}{r},0)', ROASG),
        (f"=IFERROR(1/{MARGEN},0)", ROASG),
        (f"={origen}", None),
    ]


def _comprobar():
    """Se planta si RCOLS/COLS y las fórmulas no encajan.

    Es el fallo del 10-09-2026: con el fichero a medio editar salió todo corrido una
    columna —el CPL en la casilla del coste por clic— y ningún número dio error, solo
    estaban en el sitio de al lado. Antes que publicar eso, no publicar nada.
    """
    fu = Funnel("X", "X", NEGRO, SUAVE, ["X"], "")
    n = len(fila_semana(fu, "2026-01-01", "2026-01-07", 10))
    if n != len(COLS) - 1:
        raise SystemExit(f"⛔ {len(COLS)} columnas en COLS y {n} fórmulas por fila.")


def _layout(anio, desde_mes):
    """(mes, cabecera, primera semana, última semana, fila de TOTAL) para cada mes."""
    out, r = [], 8
    for mes in range(desde_mes, 13):
        n = len(semanas(anio, mes))
        out.append((mes, r, r + 2, r + 1 + n, r + 2 + n))
        r += n + 6
    return out


def clasificar(funnels, campana):
    """El mismo criterio que la pestaña `funnels`, en Python: gana la primera regla que casa."""
    for fu in funnels:
        if any(k in (campana or "").upper() for k in fu.incluye):
            return fu
    return None


def arranques(funnels, filas, anio, defecto):
    """Desde qué mes tiene sentido enseñar cada funnel: el primero en el que hubo inversión.

    En Burriana no se hicieron anuncios hasta agosto, y en las casas de hormigón hasta
    septiembre. Montarles el año entero desde abril les colgaba cuatro y cinco bloques de mes
    vacíos por delante, con todo a «—». Un bloque vacío no dice «ese mes no gastamos»: dice
    «aquí no hay nada que mirar», y encima empuja hacia abajo lo que sí importa.
    Se deduce de `datos`, no se escribe a mano: así vale para cualquier cliente.
    """
    out = {}
    for fu in funnels:
        ms = [int(r["fecha"][5:7]) for r in filas
              if str(r.get("fecha", ""))[:4] == str(anio) and (r.get("gasto") or 0) > 0
              and clasificar(funnels, r.get("campana")) is fu]
        out[fu.nombre] = min(ms) if ms else defecto
    return out


def hoja_funnel(wb, fu, cliente, cuenta, anio, layout):
    ws = wb.create_sheet(fu.hoja)
    ws.sheet_properties.tabColor = fu.color
    ws.sheet_view.showGridLines = False
    for j, (_, an, _) in enumerate(COLS, start=1):
        ws.column_dimensions[get_column_letter(j)].width = an
    ncol = len(COLS); ult = get_column_letter(ncol)

    ws.merge_cells(f"A1:{ult}1"); ws.row_dimensions[1].height = 44
    F(ws, "A1", f"  {cliente.upper()}   ·   {fu.nombre.upper()}",
      tam=18, bold=True, color=BLANCO, fondo=NEGRO)
    for j in range(2, ncol + 1):
        ws[f"{get_column_letter(j)}1"].fill = PatternFill("solid", fgColor=NEGRO)
    ws.merge_cells(f"A2:{ult}2")
    F(ws, "A2", f"  Año {anio}  ·  cuenta {cuenta}  ·  {fu.detalle}  ·  "
                f"con anuncios desde {MESES[layout[0][0]].lower()}", tam=9, color=GRIS)

    F(ws, "A4", "PARA CALCULAR EL ROAS DE ESTE FUNNEL — solo las DOS primeras se rellenan a mano",
      tam=9, bold=True, color=GRIS)
    for ref_t, txt, ref_v, fmt in [("A5", "Ticket medio (a mano)", "B6", EURG),
                                   ("C5", "Margen (a mano)", "D6", PCT0G)]:
        F(ws, ref_t, txt, tam=8, bold=True, color=GRIS)
        F(ws, ref_v, 0, tam=13, bold=True, color=NEGRO, fondo=A_MANO_BG, fmt=fmt, hor="right")
    for ref_t, txt in [("E5", "Cierres totales (se calcula)"), ("G5", "% que cierra (se calcula)"),
                       ("I5", "Fee del CLIENTE al mes — los 3 funnels")]:
        F(ws, ref_t, txt, tam=8, bold=True, color=GRIS)
    # Aquí se enseña el fee ENTERO del cliente, no el trozo de este funnel, y el rótulo lo
    # dice: «Fee del CLIENTE al mes — los 3 funnels». Antes ponía «Fee del mes que le toca»
    # con los 1.100 € debajo, que se lee como que cada funnel carga un fee propio — y no:
    # es UN fee por el cliente, repartido a prorrata dentro de «Coste total».
    F(ws, "J6", f"={FEE}", tam=13, bold=True, color=GRIS, fmt=EURG, hor="right")
    F(ws, "L5", "El ticket y el margen son LOS DE ESTE FUNNEL, no los de la cuenta: vender una "
                "casa de hormigón no deja lo mismo que una comisión de captación. Después, cada "
                "semana, el NÚMERO de cierres en «Cierres (a mano)».   ·   OJO CON EL FEE: NO hay "
                "un fee por funnel. Es UN solo fee por el cliente, el de arriba, que se escribe "
                "una vez en «Resumen» y se reparte entre los tres a prorrata de lo invertido cada "
                "mes. Lo que carga este funnel en «Coste total» es solo su parte, y por eso los "
                "tres «Coste total» suman el coste real del mes sin contar el fee tres veces.",
      tam=8, color=GRIS, italic=True)
    ws.row_dimensions[6].height = 22

    filas_total = []
    for mes, fcab, prim, ultf, ftot in layout:
        ws.merge_cells(f"A{fcab}:{ult}{fcab}")
        F(ws, f"A{fcab}", f"  {MESES[mes].upper()} {anio}", tam=11, bold=True,
          color=BLANCO, fondo=fu.color)
        for j in range(2, ncol + 1):
            ws[f"{get_column_letter(j)}{fcab}"].fill = PatternFill("solid", fgColor=fu.color)
        ws.row_dimensions[fcab].height = 24
        for j, (t, _, _) in enumerate(COLS, start=1):
            F(ws, f"{get_column_letter(j)}{fcab+1}", t, tam=8, bold=True, color=BLANCO,
              fondo=NEGRO, hor="center" if j > 1 else "left")

        sem = semanas(anio, mes)
        for i, (etq, d1, d2) in enumerate(sem):
            r = prim + i
            F(ws, f"A{r}", etq, tam=9, fondo=SUAVE if i % 2 else None)
            for j, (v, fmt) in enumerate(fila_semana(fu, d1, d2, r), start=2):
                letra = get_column_letter(j)
                edit = letra == CIERRES_COL
                F(ws, f"{letra}{r}", v, tam=9, fmt=fmt,
                  hor="center" if letra == ORIGEN_COL else "right",
                  color=GRIS if letra == ORIGEN_COL else NEGRO,
                  italic=letra == ORIGEN_COL,
                  fondo=A_MANO_BG if edit else (SUAVE if i % 2 else None))

        mes_ini, mes_fin = sem[0][1], sem[-1][2]
        F(ws, f"A{ftot}", f"TOTAL {MESES[mes].upper()}", tam=9, bold=True,
          color=BLANCO, fondo=NEGRO)
        filas_total.append(ftot)

        def cs(n): return f"SUM({X[n]}{prim}:{X[n]}{ultf})"
        B, IM = cs("Inversión"), cs("Impresiones")
        CL, LD = cs("Clics en el enlace"), cs("Clientes potenciales")
        FA = cs("Facturado")
        # Coste total del mes = inversión del funnel + LA PARTE DEL FEE QUE LE TOCA.
        # El fee es un pago único mensual del cliente por los tres funnels, así que se
        # reparte a prorrata de lo invertido. Si el funnel no invirtió, no carga nada.
        inv_tot = _sp(C["gasto"], mes_ini, mes_fin)
        CT = f"IF({B}=0,0,{B}+IFERROR({FEE}*{B}/{inv_tot},0))"
        tot = [
            (f"={B}", EURG), (f"={IM}", ENTG), (f"=IFERROR({CL}/{IM},0)", PCTG),
            (f"={CL}", ENTG), (f"={LD}", ENTG),
            (f"=IFERROR({B}/{LD},0)", EURG), (f"=IFERROR({B}/{CL},0)", EURG),
            (f'={cs("Cierres (a mano)")}', ENTG), (f"={FA}", EURG), (f"={CT}", EURG),
            (f"=IFERROR({FA}/({CT}),0)", ROASG), (f"=IFERROR(1/{MARGEN},0)", ROASG), ("", None)]
        for j, (v, fmt) in enumerate(tot, start=2):
            F(ws, f"{get_column_letter(j)}{ftot}", v, tam=9, bold=True,
              color=fu.suave if get_column_letter(j) in DESTACADAS else BLANCO,
              fondo=NEGRO, fmt=fmt, hor="right")

    fin = layout[-1][4] + 3
    F(ws, f"A{fin}", "El coste por lead es BRUTO: con los leads cualificados, el real es del "
                     "orden de 2,5 veces mayor. El ROAS se mide contra el COSTE TOTAL (inversión "
                     "de este funnel + la parte del fee que le toca), no contra la inversión "
                     "sola. El ROAS mínimo es el punto de equilibrio (1 ÷ margen): por debajo, "
                     "este funnel no paga ni la publicidad ni la agencia.",
      tam=8, color=GRIS, italic=True)

    cie = "+".join(f"N({CIERRES_COL}{f})" for f in filas_total) or "0"
    lds = "+".join(f'N({X["Clientes potenciales"]}{f})' for f in filas_total) or "0"
    F(ws, "F6", f"={cie}", tam=13, bold=True, color=NEGRO, fmt=ENTG, hor="right")
    F(ws, "H6", f"=IFERROR(({cie})/({lds}),0)", tam=13, bold=True, color=NEGRO,
      fmt=PCT0G, hor="right")


def hoja_resumen(wb, funnels, cliente, cuenta, anio, desde_mes, layouts):
    ws = wb.create_sheet(RESUMEN)
    ws.sheet_properties.tabColor = NEGRO
    ws.sheet_view.showGridLines = False
    for j, (_, an, _) in enumerate(RCOLS, start=1):
        ws.column_dimensions[get_column_letter(j)].width = an
    ncol = len(RCOLS); ult = get_column_letter(ncol)

    ws.merge_cells(f"A1:{ult}1"); ws.row_dimensions[1].height = 44
    F(ws, "A1", f"  {cliente.upper()}   ·   LOS TRES FUNNELS, MES A MES",
      tam=18, bold=True, color=BLANCO, fondo=NEGRO)
    for j in range(2, ncol + 1):
        ws[f"{get_column_letter(j)}1"].fill = PatternFill("solid", fgColor=NEGRO)
    ws.merge_cells(f"A2:{ult}2")
    F(ws, "A2", f"  Año {anio}  ·  cuenta {cuenta}  ·  cada funnel tiene su pestaña, "
                f"con su ticket medio y su margen", tam=9, color=GRIS)

    F(ws, "C3", "Fee de agencia al mes — UNO por el cliente (a mano)", tam=8, bold=True, color=GRIS)
    F(ws, "D4", FEE_DEF, tam=13, bold=True, color=NEGRO, fondo=A_MANO_BG, fmt=EURG, hor="right")
    F(ws, "F3", "Se escribe UNA vez, aquí, y vale para los tres funnels: se reparte entre ellos "
                "a prorrata de lo invertido cada mes. Por eso los tres «Coste total» SÍ se pueden "
                "sumar — a diferencia de Meta y Google, que cargan el fee entero cada uno.",
      tam=8, color=GRIS, italic=True)
    ws.row_dimensions[4].height = 22

    # Para cada funnel, en qué fila de SU pestaña está el TOTAL de cada mes.
    filatot = {n: {m: f for m, _, _, _, f in l} for n, l in layouts.items()}

    r = 6
    for mes in range(desde_mes, 13):
        # Solo los funnels que YA existían ese mes. Poner «Piso Burriana — —  —  —» en abril
        # no informa de nada: en abril ese funnel no existía.
        activos = [fu for fu in funnels if mes in filatot[fu.nombre]]
        if not activos:
            continue
        ws.merge_cells(f"A{r}:{ult}{r}")
        F(ws, f"A{r}", f"  {MESES[mes].upper()} {anio}", tam=11, bold=True,
          color=BLANCO, fondo="0866FF")
        for j in range(2, ncol + 1):
            ws[f"{get_column_letter(j)}{r}"].fill = PatternFill("solid", fgColor="0866FF")
        ws.row_dimensions[r].height = 24
        r += 1
        for j, (t, _, _) in enumerate(RCOLS, start=1):
            F(ws, f"{get_column_letter(j)}{r}", t, tam=8, bold=True, color=BLANCO,
              fondo=NEGRO, hor="center" if j > 1 else "left")
        r += 1

        primera = r
        for i, fu in enumerate(activos):
            q, ftot = f"'{fu.hoja}'!", filatot[fu.nombre][mes]
            F(ws, f"A{r}", fu.nombre, tam=9, bold=True, color=fu.color,
              fondo=SUAVE if i % 2 else None)
            vals = [(f'={q}{X["Inversión"]}{ftot}', EURG),
                    (f'={q}{X["Clientes potenciales"]}{ftot}', ENTG),
                    (f'={q}{X["Coste por lead"]}{ftot}', EURG),
                    (f'={q}{X["Cierres (a mano)"]}{ftot}', ENTG),
                    (f'={q}{X["Facturado"]}{ftot}', EURG),
                    (f'={q}{X["Coste total"]}{ftot}', EURG),
                    (f'={q}{X["ROAS"]}{ftot}', ROASG),
                    (f'={q}{X["ROAS mínimo"]}{ftot}', ROASG)]
            for j, (v, fmt) in enumerate(vals, start=2):
                F(ws, f"{get_column_letter(j)}{r}", v, tam=9, fmt=fmt, hor="right",
                  fondo=SUAVE if i % 2 else None)
            r += 1
        ultima = r - 1

        # TOTAL: solo se suma lo que ES sumable. La inversión, los leads, los cierres, el
        # facturado y el coste total sí. El coste por lead se RECALCULA sobre las sumas
        # —promediar los tres CPL es el mismo error del que avisa la skill para Looker— y
        # el ROAS mínimo se deja vacío: cada funnel tiene su margen y una media no dice nada.
        F(ws, f"A{r}", "TOTAL DE LA CUENTA", tam=9, bold=True, color=BLANCO, fondo=NEGRO)
        def cs(n): return f"SUM({R[n]}{primera}:{R[n]}{ultima})"
        INV, LD = cs("Inversión"), cs("Clientes potenciales")
        FA, CT = cs("Facturado"), cs("Coste total")
        tot = [(f"={INV}", EURG), (f"={LD}", ENTG), (f"=IFERROR({INV}/{LD},0)", EURG),
               (f'={cs("Cierres")}', ENTG), (f"={FA}", EURG), (f"={CT}", EURG),
               (f"=IFERROR({FA}/{CT},0)", ROASG), ("", None)]
        for j, (v, fmt) in enumerate(tot, start=2):
            F(ws, f"{get_column_letter(j)}{r}", v, tam=9, bold=True,
              color="5AA9FF" if get_column_letter(j) == R["Coste por lead"] else BLANCO,
              fondo=NEGRO, fmt=fmt, hor="right")
        r += 3

    F(ws, f"A{r}", "El «Coste total» de cada funnel ya lleva su parte del fee, así que la fila "
                   "TOTAL es el coste real del mes: inversión de los tres + un solo fee. El "
                   "coste por lead del total se recalcula sobre las sumas, NUNCA promediando "
                   "los tres. El ROAS mínimo se deja vacío a propósito: cada funnel tiene su "
                   "margen y una media de márgenes no significa nada.",
      tam=8, color=GRIS, italic=True)


def hoja_motor(wb, funnels):
    """Clasifica cada fila de `datos` en un funnel, UNA sola vez.

    Se hace aquí y no dentro de cada SUMPRODUCT porque las semanas son 60 por pestaña y
    tres pestañas: repetir seis SEARCH sobre 5.000 filas en cada celda son decenas de
    millones de operaciones y la hoja se arrastra. Aquí son 5.000, y una sola vez.
    """
    ws = wb.create_sheet(MOTOR); ws.sheet_properties.tabColor = GRIS
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 26
    F(ws, "A1", "funnel", tam=8, bold=True, color=BLANCO, fondo=NEGRO)
    for r in range(2, FIN + 1):
        ws[f"A{r}"].value = clasificador(funnels, r)
        ws[f"A{r}"].font = Font(name="Inter", size=9, color=GRIS)

    # H1/H2: hasta qué fila llegan de verdad `datos` y `ventas`. Todos los rangos de las
    # tres pestañas se cortan por aquí, así que crecen solos según n8n va escribiendo.
    F(ws, "G1", "filas de `datos`", tam=8, bold=True, color=GRIS)
    F(ws, "H1", f'=MAX(2,COUNTA(datos!${C["fecha"]}:${C["fecha"]}))', tam=9, color=GRIS, fmt=ENT)
    F(ws, "G2", "filas de `ventas`", tam=8, bold=True, color=GRIS)
    F(ws, "H2", f'=MAX(2,COUNTA(ventas!${V["fecha"]}:${V["fecha"]}))', tam=9, color=GRIS, fmt=ENT)

    F(ws, "C1", "MOTOR — no se toca a mano", tam=11, bold=True, color=NEGRO)
    F(ws, "C2", "Esta columna dice, para cada fila de `datos`, a qué funnel pertenece. Las tres "
                "pestañas de reporte suman contra ella.", tam=9, color=GRIS, italic=True)
    F(ws, "C4", "La regla, por orden — gana la primera que casa:", tam=9, bold=True, color=NEGRO)
    r = 5
    for fu in funnels:
        F(ws, f"C{r}", fu.nombre, tam=9, bold=True, color=fu.color)
        F(ws, f"D{r}", "el nombre de la campaña contiene:  " + "  ·  ".join(fu.incluye),
          tam=9, color=GRIS)
        r += 1
    F(ws, f"C{r}", "Sin clasificar", tam=9, bold=True, color=ROJO)
    F(ws, f"D{r}", "cualquier otra cosa. Si aparece gasto aquí, es una campaña nueva que nadie "
                   "ha asignado: NO entra en ningún reporte hasta que se añada la regla.",
      tam=9, color=ROJO)
    F(ws, f"C{r+2}", "El orden importa: «Piso Burriana» y «Casas de hormigón» van ANTES que "
                     "«Captación», porque sus campañas también se llaman «CONVERSIONES ...». "
                     "Al revés, los dos funnels de venta saldrían vacíos sin dar ningún error.",
      tam=9, color=GRIS, italic=True)
    ws.column_dimensions["C"].width = 26; ws.column_dimensions["D"].width = 90


def _extender(ws, hasta=FIN):
    """Deja la pestaña con `hasta` filas de rejilla aunque estén vacías.

    NO es cosmético. Al convertir el .xlsx a Sheet, Google crea la rejilla del TAMAÑO DE LO
    ESCRITO: `datos` con 443 filas se queda en 443, y entonces `datos!$B$2:$B$5000` se
    recorta a 442 celdas mientras que `funnels!$A$2:$A$5000` sigue dando 4.999. Dos arrays
    de distinto tamaño dentro del mismo SUMPRODUCT devuelven #N/A, y como el «Coste por
    lead» va envuelto en IFERROR salía un 0,00 € tan tranquilo. Todo el reporte a cero con
    los datos correctos debajo — el mismo tropiezo que la fecha de Google Ads.
    Las filas quedan VACÍAS, así que n8n sigue añadiendo detrás de la última fila CON datos.
    """
    ws.row_dimensions[hasta].height = 15


def construir(cliente, cuenta, anio, desde_mes, funnels, filas, pestanas=None):
    _comprobar()
    wb = Workbook(); wb.remove(wb.active)

    # Cada funnel empieza en SU primer mes con inversión, así que la geometría YA NO es la
    # misma en las tres pestañas: la fila de «TOTAL AGOSTO» cae en un sitio distinto en cada
    # una. El Resumen no puede suponerla — se le pasa el layout de cada funnel.
    pestanas = pestanas or funnels
    desde = arranques(funnels, filas, anio, desde_mes)
    layouts = {fu.nombre: _layout(anio, desde[fu.nombre]) for fu in funnels}
    # ⛔ Las pestañas se crean YA en el orden en que se van a ver, y NO se reordenan luego.
    # `wb._sheets.sort()` parecía inofensivo —las fórmulas van por nombre de pestaña, no por
    # posición— pero al convertir el .xlsx a Sheet Google devolvía la hoja llena de #REF!:
    # 99 celdas, todo el «Resumen» de dos de los tres funnels y sus «Cierres totales», con
    # las referencias corridas un número exacto de bloques de mes. En local el fichero
    # estaba impecable; se rompía solo al convertir, que es donde nadie mira.
    # `pestanas` es el orden de VISTA; `funnels` es el orden de las REGLAS de clasificación
    # (los específicos antes que el genérico) y no se toca.
    hoja_resumen(wb, pestanas, cliente, cuenta, anio, desde_mes, layouts)
    for fu in pestanas:
        hoja_funnel(wb, fu, cliente, cuenta, anio, layouts[fu.nombre])
    hoja_motor(wb, funnels)

    # ---- datos: lo único que toca n8n. Orden de columnas INTOCABLE. ----
    ws = wb.create_sheet("datos"); ws.sheet_properties.tabColor = GRIS
    ws.freeze_panes = "B2"
    anchos = [30, 12, 16, 42, 12, 13, 11, 12, 10, 9, 13, 10, 15, 9, 18]
    for j, (c, an) in enumerate(zip(DATOS, anchos), start=1):
        ws.column_dimensions[get_column_letter(j)].width = an
        F(ws, f"{get_column_letter(j)}1", c, tam=8, bold=True, color=BLANCO, fondo=NEGRO,
          hor="center" if j > 4 else "left")
    fmts = [None, None, None, None, EUR, ENT, ENT, DEC2, EUR, ENT, ENT, PCT, ENT, ENT, None]
    for i, f in enumerate(filas):
        for j, (c, fmt) in enumerate(zip(DATOS, fmts), start=1):
            F(ws, f"{get_column_letter(j)}{i+2}", f.get(c), tam=9, fmt=fmt,
              hor="right" if j > 4 else "left", color=GRIS if j in (1, 3, 15) else NEGRO,
              fondo=SUAVE if i % 2 else None)
    ws.auto_filter.ref = f"A1:O{max(len(filas)+1, 2)}"
    _extender(ws)

    # ---- ventas: la rellena el CRM, no el agente ----
    ws = wb.create_sheet("ventas"); ws.sheet_properties.tabColor = "16794A"
    ws.freeze_panes = "B2"
    for j, (c, an) in enumerate(zip(VENTAS, [30, 12, 16, 26, 40, 14, 15]), start=1):
        ws.column_dimensions[get_column_letter(j)].width = an
        F(ws, f"{get_column_letter(j)}1", c, tam=8, bold=True, color=BLANCO, fondo=NEGRO,
          hor="center" if j > 3 else "left")
    F(ws, "A3", "OPCIONAL. Solo hace falta si queréis el importe REAL de cada venta en vez del "
                "ticket medio. Sin CRM conectado se puede escribir a mano o dejarla vacía: con "
                "los «Cierres (a mano)» de cada pestaña ya salen el facturado y el ROAS.",
      tam=9, color=GRIS, italic=True)
    F(ws, "A4", "La fecha, en texto y así: 2026-09-05. Si la escribís 05/09/2026 no cuenta.",
      tam=9, color=ROJO, italic=True)
    F(ws, "A5", "La columna `funnel` tiene que decir EXACTAMENTE: "
                + "  ·  ".join(f.nombre for f in funnels)
                + ". Si no casa, la venta no entra en ninguna pestaña.", tam=9, color=ROJO)
    _extender(ws)
    return wb


FUNNELS = [
    Funnel("Piso Burriana", "Meta · Piso Burriana", "E8710A", "FFC48A",
           ["BURRIANA"], "vender UN piso concreto: el de Burriana"),
    Funnel("Casas de hormigón", "Meta · Casas de hormigón", "188038", "7BC98F",
           ["HORMIG"], "vender viviendas de hormigón celular"),
    Funnel("Captación de propiedades", "Meta · Captación", "0866FF", "5AA9FF",
           ["FORM NATIVO", "CONVERSIONES", "TRAFICO", "TRÁFICO"],
           "captar propietarios que quieren vender su vivienda en la costa"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cliente", required=True); ap.add_argument("--cuenta", required=True)
    ap.add_argument("--anio", type=int, required=True)
    ap.add_argument("--desde-mes", type=int, default=1)
    ap.add_argument("--carpeta-id", required=True)
    ap.add_argument("--datos", default=None, help="JSON con las filas iniciales de `datos`")
    ap.add_argument("--nombre", default=None)
    ap.add_argument("--salida", default=None, help="guardar el .xlsx en local y no subir")
    ap.add_argument("--rehacer", action="store_true")
    a = ap.parse_args()

    filas = json.load(open(a.datos)) if a.datos else []
    # El orden de FUNNELS es el de evaluación (los específicos primero); el de las pestañas
    # se elige aparte, para que la captación —que es el grueso— quede la primera.
    orden = ["Captación de propiedades", "Piso Burriana", "Casas de hormigón"]
    pestanas = sorted(FUNNELS, key=lambda f: orden.index(f.nombre))

    wb = construir(a.cliente, a.cuenta, a.anio, a.desde_mes, FUNNELS, filas, pestanas)
    tmp = a.salida or os.path.join(tempfile.mkdtemp(), "hoja.xlsx")
    wb.save(tmp)
    if a.salida:
        print(f"✓ Guardado en local: {tmp}"); return

    nombre = a.nombre or f"Reporte Ads — {a.cliente} — {a.anio}"

    def buscar(n):
        q = f"name = '{n}' and '{a.carpeta_id}' in parents and trashed = false"
        url = ("https://www.googleapis.com/drive/v3/files?"
               + urllib.parse.urlencode({"q": q, "fields": "files(id,name)",
                                         "supportsAllDrives": "true",
                                         "includeItemsFromAllDrives": "true"}))
        return api(url).get("files", [])

    ya = buscar(nombre)
    if ya and not a.rehacer:
        sys.exit("✗ Esa hoja ya existe. Regenerarla BORRA el ticket, el margen y los cierres "
                 "escritos a mano en las tres pestañas.\n  Si de verdad querés rehacerla, "
                 "repetí el comando con --rehacer.")
    if ya:
        sid = ya[0]["id"]
        cuerpo, cab = _multipart({"mimeType": HOJA}, tmp, XLSX)
        api(f"https://www.googleapis.com/upload/drive/v3/files/{sid}"
            f"?uploadType=multipart&supportsAllDrives=true",
            data=cuerpo, headers=cab, metodo="PATCH")
        accion = "regenerada (mismo ID y misma URL)"
    else:
        cuerpo, cab = _multipart({"name": nombre, "mimeType": HOJA,
                                  "parents": [a.carpeta_id]}, tmp, XLSX)
        sid = api("https://www.googleapis.com/upload/drive/v3/files"
                  "?uploadType=multipart&supportsAllDrives=true",
                  data=cuerpo, headers=cab)["id"]
        accion = "creada"

    print(f"✓ Hoja de Google {accion}: {nombre}")
    print(f"  https://docs.google.com/spreadsheets/d/{sid}/edit")
    print(sid)


if __name__ == "__main__":
    main()
