#!/usr/bin/env python3
"""Monta la hoja de reportes de un cliente como HOJA DE GOOGLE nativa, con diseño.

CÓMO ESTÁ PENSADA:
  · Una fila por SEMANA (1-7, 8-14, 15-21, 22-28, 29-fin), no por día: al cliente no le
    interesa el detalle diario, le interesa la tendencia.
  · Un bloque por MES, uno debajo de otro, con dos filas de aire entre medias. El año
    entero queda montado de una vez: cuando llegue octubre, su bloque ya está esperando.
  · La pestaña `datos` es la ÚNICA que toca n8n cada mañana. Todo lo demás son **fórmulas**
    que leen de ahí, así que el informe se actualiza solo y este script se ejecuta UNA vez
    por cliente.

Por qué no se usa la API de Sheets para el formato: el token sale del remoto `gdrive` de
rclone y ese proyecto no tiene habilitada `sheets.googleapis.com` (403 PERMISSION_DENIED).
La hoja se compone con openpyxl y se sube a Drive **con conversión**: en Drive queda un
Sheet nativo, no un .xlsx.

Uso:
  python3 montar_hoja_reportes.py --cliente Cliente 02 --cuenta 1438... --anio 2026 \\
      --carpeta-id <ID> [--datos datos.json] [--desde-mes 9]
"""
import argparse, calendar, datetime, json, os, sys, tempfile, urllib.parse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.utils import get_column_letter
from subir_a_drive import api, _multipart

HOJA = "application/vnd.google-apps.spreadsheet"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# Paleta de META: azul de Meta + negro + blanco. Antes eran el morado y el rosa de Flowboost,
# y con la llegada del reporte de Google los dos se confundían de un vistazo (Dirección, 10-09-2026).
# Los nombres MORADO/ROSA se conservan para no tocar las 15 líneas que los usan: lo que cambia
# es el valor. MORADO = azul Meta (cabeceras de mes), ROSA = acento del bloque de totales.
MORADO, ROSA, NEGRO, GRIS = "0866FF", "5AA9FF", "0B0B0F", "8A8A94"
SUAVE, BLANCO, ROJO, ROJOBG = "F5F8FF", "FFFFFF", "C0392B", "FDEBE9"
# Fondo de TODA celda que se rellena a mano. Un tono claramente más fuerte que SUAVE: si no
# se distingue del blanco, nadie sabe dónde tiene que escribir. Va con el azul de la casa.
A_MANO_BG = "BBD6FF"
EUR, ENT, PCT, PCT0, DEC2 = '"€"#,##0.00', '#,##0', '0.00%', '0%', '0.00'
# Secciones del formato: positivo;negativo;CERO;texto. El cero va en la TERCERA.
# Ponerlo en la cuarta dejaba la celda EN BLANCO en vez de escribir el guion.
EURG  = '"€"#,##0.00;-"€"#,##0.00;"—"'
ENTG  = '#,##0;-#,##0;"—"'
PCTG  = '0.00%;-0.00%;"—"'
PCT0G = '0%;-0%;"—"'
DEC2G = '0.00;-0.00;"—"'
ROASG = '0.00"×";-0.00"×";"—"'

MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
# Orden EXACTO en que n8n escribe en `datos`. Si cambia aquí, cambia en el nodo «Armar filas».
DATOS = ["id", "fecha", "cliente", "campana", "gasto", "impresiones", "alcance",
         "frecuencia", "cpm", "clics", "clics_enlace", "ctr", "vistas_landing",
         "leads", "actualizado"]
# Pestaña `ventas`: la rellena el flujo `crmVentasAReportes01` con las oportunidades que el
# cliente marca como GANADO en su CRM. Es lo que convierte el ROAS de estimación en dato.
VENTAS = ["id", "fecha", "cliente", "oportunidad", "importe", "actualizado"]
V = {n: get_column_letter(i+1) for i, n in enumerate(VENTAS)}
C = {n: get_column_letter(i+1) for i, n in enumerate(DATOS)}
FIN = 5000

COLS_BASE = [("Semana", 22, "left"), ("Inversión", 13, "right"), ("Impresiones", 13, "right"),
        ("CTR", 10, "right"),
        ("Clics en el enlace", 17, "right"), ("Clientes potenciales", 20, "right"),
        ("Coste por lead", 15, "right"), ("Coste por clic", 15, "right"),
        ("Cierres (a mano)", 17, "right"),
        # De cada 100 leads de ESA fila, cuántos cerraron. Sale de la propia fila (cierres ÷
        # clientes potenciales), no del año: así se ve qué semana convirtió mejor y no solo
        # la media (Dirección, 22-09-2026).
        ("% de cierre", 13, "right"),
        # UN solo «Facturado», y es un HUECO que se escribe a mano (Dirección, 22-09-2026).
        # Antes intentaba ser tres cosas —dato del CRM, dato a mano y estimación—, y por eso
        # necesitaba una columna que la alimentara, otra que la calculara y una tercera
        # («Origen») que explicara cuál de las tres había salido. Con una sola fuente por
        # fila no hay nada que explicar: si está vacía, está vacía, y el ROAS también.
        # ⛔ Se quitó la ESTIMACIÓN a propósito: un ROAS estimado es un ROAS inventado, y la
        # regla de la casa es no inventar cifras (por eso el resto sale «—» sin datos).
        ("Facturado (a mano)", 18, "right"),
        ("Coste total", 14, "right"),
        ("ROAS", 11, "right"), ("ROAS mínimo", 14, "right")]
# X: la letra de cada columna, DEDUCIDA de COLS. Antes las letras estaban escritas a mano
# repartidas por el fichero («CIERRES_COL = "K"», «L{r}/M{r}», «col_sum('K')»...), así que
# quitar o mover una columna dejaba fórmulas apuntando a la de al lado SIN dar error: el
# reporte seguía saliendo, con números de otra columna. Nunca más una letra a pelo aquí.
# ---- FUNNELS: dos negocios en la MISMA cuenta ------------------------------------
# Un cliente puede correr dos funnels distintos con un solo `act_` (Cliente 02: inversión
# inmobiliaria y gestión de pisos). Sumarlos en la misma fila esconde cuál de los dos paga.
# Con `--funnel` la tabla gana una columna «Funnel» y cada semana pasa a tener una fila por
# funnel. Cada funnel es (nombre, [marcas]); una «marca» es un TROZO del nombre de la campaña.
# `datos` trae una fila por día y CAMPAÑA, así que el nombre es lo único con lo que se puede
# separar: por eso las campañas TIENEN que llevar la marca de su funnel en el nombre.
FUNNELS = []
N_ETIQ = 1          # columnas de etiqueta a la izquierda: «Semana» (+ «Funnel» si hay)
COLS, X, DESTACADAS, CIERRES_COL, FACTURADO_COL = [], {}, set(), "", ""


def _configurar(funnels=None):
    """Fija COLS y TODO lo que se deduce de ella. Se llama una vez, al construir.

    Las letras de columna nunca se escriben a mano (ver el aviso de más abajo): con la
    columna «Funnel» delante, todas se corren una posición y cualquier «K» suelta apuntaría
    a la columna de al lado sin dar error."""
    global FUNNELS, N_ETIQ, COLS, X, DESTACADAS, CIERRES_COL, FACTURADO_COL
    FUNNELS = list(funnels or [])
    COLS = list(COLS_BASE)
    if FUNNELS:
        COLS.insert(1, ("Funnel", 20, "left"))
    N_ETIQ = 2 if FUNNELS else 1
    X = {n: get_column_letter(i + 1) for i, (n, _, _) in enumerate(COLS)}
    DESTACADAS = {X["Coste por lead"], X["Coste por clic"]}
    CIERRES_COL = X["Cierres (a mano)"]
    FACTURADO_COL = X["Facturado (a mano)"]


_configurar()

# ⛔ ALCANCE y FRECUENCIA fuera del reporte (10-09-2026). No son sumables: la misma persona
# alcanzada por dos campañas, o el mismo día en dos filas, se cuenta dos veces. En Cliente 13
# la suma daba 373.176 de alcance cuando el real de la cuenta era 123.540, y como la
# frecuencia es impresiones/alcance salía 1,33 cuando la de verdad era 4,03 — justo al revés
# de lo que hay que ver: parecía que quedaba público de sobra mientras se estaba saturando.
# Se siguen guardando en `datos` (n8n las escribe y el orden de columnas no se toca): solo
# se ha dejado de MOSTRARLAS, igual que «Llegan a la landing».

# «Coste total» = inversión publicitaria + la parte del FEE DE AGENCIA que toca a esa semana.
# El ROAS se calcula sobre esto, no sobre la inversión sola: el cliente paga las dos cosas
# (Dirección, 10-09-2026). El fee es mensual y se reparte por DÍAS, así la última semana del mes,
# que suele tener 2 o 3 días, no carga un mes entero de fee.
# La única columna de la TABLA que se escribe a mano (las otras tres van en la fila 6:
# ticket, margen y fee). Fondo A_MANO_BG y «(a mano)» en el rótulo, para que se vea que es un
# hueco y no un resultado. Si cambia de sitio, cambiar CIERRES_COL.
# Las dos que se resaltan en la fila de TOTAL: son las que se miran primero.
# DESTACADAS, CIERRES_COL y ORIGEN_COL los fija `_configurar()`: dependen de si hay
# columna «Funnel» o no, y tienen que moverse con ella.

# Celdas del bloque de parámetros. El ROAS de una cuenta de captación NO sale de Meta:
# Meta no sabe cuánto factura el cliente por un lead. Sale de estas tres cifras.
TICKET, MARGEN, CIERRE = "$B$6", "$D$6", "$H$6"   # H6 = % que cierra, CALCULADO
FEE = "$J$6"                                      # fee de agencia AL MES, a mano
FEE_DEF = 1100                                    # el que se escribe al crear la hoja.
# Sirve para saber si alguien lo CAMBIÓ: la guarda solo salta si es distinto de este,
# porque si no saltaría en todas las hojas y no se podría regenerar ninguna.


def F(ws, ref, valor, *, tam=10, bold=False, color=NEGRO, fondo=None,
      fmt=None, hor=None, italic=False):
    c = ws[ref]; c.value = valor
    c.font = Font(name="Inter", size=tam, bold=bold, color=color, italic=italic)
    if fondo: c.fill = PatternFill("solid", fgColor=fondo)
    if fmt:   c.number_format = fmt
    c.alignment = Alignment(horizontal=hor, vertical="center")
    return c


# Desde SEPTIEMBRE de 2026 la semana va de LUNES A DOMINGO (Equipo, 15-09-2026): el informe
# se lee por semana natural, y los bloques fijos de 7 días partían los lunes por la mitad.
# Los meses ANTERIORES se quedan como estaban: ya se enseñaron así, y recolocarlos movería
# filas de meses cerrados sin que nadie lo haya pedido.
LUNES_DESDE = (2026, 9)


def semanas(anio, mes):
    """(etiqueta, primer día, último día).

    Hasta agosto de 2026: bloques fijos de 7 días (1-7, 8-14, 15-21, 22-28, 29-fin).
    Desde septiembre de 2026: de lunes a domingo. La primera semana del mes empieza el día 1
    y termina el primer domingo, así que sale corta; la última también. Consecuencia que hay
    que tener presente: un mes puede necesitar **6 filas** y no siempre 5 (en 2026: marzo,
    agosto y noviembre). Nada puede dar por hecho que un bloque de mes ocupa 5 filas.
    """
    n = calendar.monthrange(anio, mes)[1]
    out, d = [], 1
    while d <= n:
        if (anio, mes) >= LUNES_DESDE:
            # weekday(): lunes=0 … domingo=6. Lo que falta para llegar al domingo.
            h = min(d + (6 - datetime.date(anio, mes, d).weekday()), n)
        else:
            h = min(d + 6, n)
        out.append((f"Del {d} al {h}", f"{anio}-{mes:02d}-{d:02d}", f"{anio}-{mes:02d}-{h:02d}"))
        d = h + 1
    return out


def _marca(m):
    """Factor 0/1: ¿aparece esta marca en el nombre de la campaña de esa fila de `datos`?"""
    ca = f'datos!${C["campana"]}$2:${C["campana"]}${FIN}'
    return f'ISNUMBER(SEARCH("{m}",{ca}))'


def _filtro(marcas=None, excluir=None):
    """El trozo de SUMPRODUCT que deja pasar solo las campañas de un funnel.

    `marcas`  → cuenta la fila si aparece ALGUNA de las marcas.
    `excluir` → cuenta la fila si NO aparece NINGUNA: es la fila «Sin clasificar», que
                existe a propósito para que el gasto de una campaña mal nombrada SE VEA
                en vez de desaparecer del reporte sin que salte nada.
    """
    if marcas:
        return "*((" + "+".join(_marca(m) for m in marcas) + ")>0)"
    if excluir:
        return "".join(f"*(1-{_marca(m)})" for m in excluir)
    return ""


def suma(col, ini, fin, marcas=None, excluir=None):
    """Suma una columna de `datos` entre dos fechas, opcionalmente filtrando por funnel.

    SUMIFS NO sirve aquí: con un criterio como ">=2026-09-01" Sheets lo interpreta como
    FECHA, mientras que la columna `fecha` es TEXTO (n8n escribe la cadena ISO tal cual),
    así que no casa ni una fila y todas las semanas salen vacías. Con SUMPRODUCT la
    comparación es texto contra texto, y en formato ISO el orden alfabético ES el
    cronológico. Las celdas vacías dan FALSO y no suman.
    """
    fe = f'datos!${C["fecha"]}$2:${C["fecha"]}${FIN}'
    return (f'SUMPRODUCT(({fe}>="{ini}")*({fe}<="{fin}"){_filtro(marcas, excluir)}*'
            f'N(datos!${col}$2:${col}${FIN}))')


def suma_ventas(col, ini, fin):
    """Lo mismo, sobre la pestaña `ventas` (lo que viene del CRM). Sin funnel: el CRM no
    dice de qué campaña vino la venta."""
    fe = f'ventas!${V["fecha"]}$2:${V["fecha"]}${FIN}'
    return (f'SUMPRODUCT(({fe}>="{ini}")*({fe}<="{fin}")*'
            f'N(ventas!${col}$2:${col}${FIN}))')


def cuenta_ventas(ini, fin):
    fe = f'ventas!${V["fecha"]}$2:${V["fecha"]}${FIN}'
    return f'SUMPRODUCT(({fe}>="{ini}")*({fe}<="{fin}")*1)'


def bloque_formulas(ini, fin, r, marcas=None, excluir=None):
    """Fórmulas de una fila: SUMPRODUCT por rango de fechas sobre `datos`.

    Con `marcas`/`excluir` la fila deja de ser «la semana entera» y pasa a ser «la semana
    de ESTE funnel» (ver `_filtro`).

    El FEE: en una fila de SEMANA entra PRORRATEADO POR DÍAS (ver `coste_total` abajo). En
    una fila de FUNNEL no entra: «el fee es por los funnels, no es un fee por funnel»
    (Dirección, 10-09-2026), así que ahí va entero y una sola vez en el TOTAL DEL MES. Son dos
    casos distintos y por eso se tratan distinto: trocear un mes en el TIEMPO reparte un
    coste que existe; trocearlo entre CANALES inventa uno que nadie factura.
    """
    por_funnel = bool(marcas or excluir)
    INV = X["Inversión"]

    def s(col):
        return suma(col, ini, fin, marcas, excluir)

    g, im, al = s(C["gasto"]), s(C["impresiones"]), s(C["alcance"])
    ce, vl, ld = s(C["clics_enlace"]), s(C["vistas_landing"]), s(C["leads"])
    # Coste total de la SEMANA = su inversión + la parte del fee que le toca, repartido por
    # DÍAS y no a partes iguales: una semana de 3 días no puede cargar un mes entero de fee.
    # La guarda `=0 → 0` es la misma que lleva la fila TOTAL: una semana sin inversión —las
    # que aún no han llegado— no arrastra fee, o el mes en curso enseñaría un coste inventado.
    # Las filas de FUNNEL se quedan sin fee a propósito (ver el docstring).
    # Ya no hay cascada ni «Origen»: «Facturado» es un hueco que se rellena a mano.
    if por_funnel:
        coste_total = f"={INV}{r}"
    else:
        d_ini = datetime.date.fromisoformat(ini)
        dias = (datetime.date.fromisoformat(fin) - d_ini).days + 1
        dias_mes = calendar.monthrange(d_ini.year, d_ini.month)[1]
        coste_total = f"=IF({INV}{r}=0,0,{INV}{r}+{FEE}*{dias}/{dias_mes})"
    return [
        (f"={g}", EURG), (f"={im}", ENTG),
        (f"=IFERROR({ce}/{im},0)", PCTG),
        (f"={ce}", ENTG),
        (f"={ld}", ENTG),
        (f"=IFERROR({g}/{ld},0)", EURG),
        (f"=IFERROR({g}/{ce},0)", EURG),
        (None, ENTG),                       # Cierres: el ÚNICO hueco a mano de la tabla
        (f'=IFERROR(${CIERRES_COL}{r}/({ld}),0)', PCTG),   # % de cierre de ESA fila
        (None, EURG),                       # Facturado: el segundo y último hueco a mano
        (coste_total, EURG),                # inversión + la parte del fee (prorrateada por días)
        # ROAS y ROAS mínimo leen la propia fila: se entienden de un vistazo y se recalculan
        # solos en cuanto se tocan los cierres, el ticket o el margen.
        (f'=IFERROR({X["Facturado (a mano)"]}{r}/{X["Coste total"]}{r},0)', ROASG),  # sobre el COSTE TOTAL
        (f"=IFERROR(1/{MARGEN},0)", ROASG),
    ], (g, im, al, ce, vl, ld)



def _comprobar_parentesis(celdas, donde):
    """Una fórmula con los paréntesis descuadrados NO da error al montar el libro: rompe la
    celda en Sheets y el cliente ve un #ERROR. Pasó el 22-09-2026 con «Origen» al quitar una
    columna: cuatro IF abiertos y tres cerrados. Se comprueba al construir, que es gratis."""
    for i, (v, _fmt) in enumerate(celdas):
        if isinstance(v, str) and v.startswith("=") and v.count("(") != v.count(")"):
            raise SystemExit(
                f"⛔ Fórmula con los paréntesis descuadrados en {donde}, columna "
                f"{COLS[i + N_ETIQ][0]!r}: abre {v.count('(')} y cierra {v.count(')')}.\n"
                f"   {v[:160]}")


def _comprobar_columnas():
    """Se planta si COLS y las fórmulas por fila no encajan.

    COLS y `bloque_formulas` son dos listas que hay que cambiar A LA VEZ. El 10-09-2026 se
    generó una hoja de cliente con el fichero a medio editar —COLS ya sin «Alcance» y las
    fórmulas todavía con él— y salió TODO corrido una columna: el alcance en la casilla de la
    frecuencia, el CPL en la del coste por clic. Nada dio error: los números eran válidos, solo
    estaban en el sitio de al lado. Antes que publicar eso, no publicar nada.
    """
    f, _ = bloque_formulas("2026-01-01", "2026-01-07", 10)
    if len(f) != len(COLS) - N_ETIQ:
        raise SystemExit(
            f"⛔ El script está a medio editar: {len(COLS)} columnas en COLS "
            f"({len(COLS)-N_ETIQ} sin las de etiqueta) y {len(f)} fórmulas por fila.\n"
            f"   COLS: {[c[0] for c in COLS]}\n"
            f"   Cuadra las dos listas antes de generar nada.")
    # Y la fila de TOTAL DEL MES, que es OTRA lista que hay que cambiar a la vez. El
    # 15-09-2026 se añadió «Facturado (a mano)» a COLS y a las filas de semana pero no aquí:
    # el total escribió cada cifra una columna a la izquierda y, al convertir a Google, la
    # hoja salió con #REF!. En local el .xlsx parecía correcto, que es lo peor del caso.
    if len(_CELDAS_TOTAL_PRUEBA()) != len(COLS) - N_ETIQ:
        raise SystemExit(
            f"⛔ La fila de TOTAL DEL MES tiene {len(_CELDAS_TOTAL_PRUEBA())} celdas y la "
            f"tabla {len(COLS)-N_ETIQ} columnas. Cuadra `celdas_total` con COLS.")


def _CELDAS_TOTAL_PRUEBA():
    """Las celdas de un TOTAL DEL MES cualquiera, solo para contarlas."""
    return [
        ("", EURG), ("", ENTG), ("", PCTG), ("", ENTG), ("", ENTG), ("", EURG), ("", EURG),
        ("", ENTG), ("", PCTG), ("", EURG), ("", EURG), ("", ROASG), ("", ROASG)]


def hoja_reporte(wb, titulo, cliente, cuenta, anio, meses, principal=True, color=None):
    """Monta UNA pestaña de reporte con los meses que se le pidan.

    `principal=False` es una pestaña secundaria (el histórico de los meses ya cerrados): el
    ticket, el margen y el fee NO se vuelven a escribir a mano, se LEEN de «Reporte Meta». Así hay una sola fuente de verdad y no pueden divergir,
    igual que hace `Reporte Google`. Los cierres y el «% que cierra», en cambio, son suyos:
    salen de su propia columna.
    """
    ws = wb.create_sheet(titulo) if wb.sheetnames != ["Sheet"] else wb.active
    ws.title = titulo
    ws.sheet_properties.tabColor = color or MORADO
    ws.sheet_view.showGridLines = False
    for j, (_, an, _) in enumerate(COLS, start=1):
        ws.column_dimensions[get_column_letter(j)].width = an
    ncol = len(COLS); ultima = get_column_letter(ncol)

    ws.merge_cells(f"A1:{ultima}1"); ws.row_dimensions[1].height = 44
    F(ws, "A1", f"  {cliente.upper()}   ·   REPORTE DE META ADS",
      tam=18, bold=True, color=BLANCO, fondo=NEGRO)
    for j in range(2, ncol+1):
        ws[f"{get_column_letter(j)}1"].fill = PatternFill("solid", fgColor=NEGRO)
    ws.merge_cells(f"A2:{ultima}2")
    meses = list(meses)
    if principal:
        sub = f"  Año {anio}  ·  cuenta {cuenta}  ·  se actualiza solo cada mañana a las 8:00"
    else:
        sub = (f"  Año {anio}  ·  cuenta {cuenta}  ·  meses ya CERRADOS, aparte para no "
               f"mezclarlos con el mes en curso. Mismos ticket, margen y fee")
    if FUNNELS:
        sub += "  ·  una fila por semana Y POR FUNNEL: " + " / ".join(f for f, _ in FUNNELS)
    F(ws, "A2", sub, tam=9, color=GRIS)

    # ---- Parámetros para el ROAS ----
    # SOLO DOS se escriben a mano: el ticket medio y el margen. Nadie tiene por qué calcular un
    # porcentaje (Dirección, 10-09-2026): el «% que cierra» se DEDUCE de los cierres que se van
    # escribiendo cada semana, y al lado se ve el total de cierres del año.
    F(ws, "A4", "PARA CALCULAR EL ROAS — aquí solo se rellena el MARGEN" if principal
      else "PARA CALCULAR EL ROAS — se leen de «Reporte Meta», aquí no se tocan",
      tam=9, bold=True, color=GRIS)
    # En la pestaña secundaria las tres celdas son FÓRMULAS que apuntan a «Reporte Meta»: una
    # sola fuente de verdad. Si se dejaran a mano, alguien cambiaría el ticket en una y no en
    # la otra y los dos ROAS dejarían de comparar lo mismo.
    # El TICKET MEDIO vuelve a escribirse A MANO (Dirección, 22-09-2026). Entre el 15 y el 22 de
    # septiembre se deducía de la columna «Facturado (a mano)», pero esa columna se quitó por
    # confundirse con «Facturado», así que ya no hay de dónde deducirlo. Lo dice el cliente,
    # igual que el margen.
    F(ws, "A5", "Ticket medio (se calcula)" if principal else "Ticket medio (de «Reporte Meta»)",
      tam=8, bold=True, color=GRIS)
    if not principal:
        F(ws, "B6", "='Reporte Meta'!$B$6", tam=13, bold=True, color=NEGRO,
          fmt=EURG, hor="right")   # la fórmula de la principal se escribe al final
    F(ws, "C5", "Margen (a mano)" if principal else "Margen (de «Reporte Meta»)",
      tam=8, bold=True, color=GRIS)
    F(ws, "D6", 0 if principal else "='Reporte Meta'!$D$6",
      tam=13, bold=True, color=NEGRO, fondo=A_MANO_BG if principal else None,
      fmt=PCT0G, hor="right")
    F(ws, "I5", "Fee de agencia al mes (a mano)" if principal
      else "Fee de agencia al mes (de «Reporte Meta»)", tam=8, bold=True, color=GRIS)
    F(ws, "J6", FEE_DEF if principal else "='Reporte Meta'!$J$6",
      tam=13, bold=True, color=NEGRO, fondo=A_MANO_BG if principal else None,
      fmt=EURG, hor="right")
    for ref_t, txt_t in [("E5", "Cierres totales (se calcula)"),
                         ("G5", "% que cierra (se calcula)")]:
        F(ws, ref_t, txt_t, tam=8, bold=True, color=GRIS)
    # Las fórmulas se escriben al final, cuando ya se sabe en qué filas quedaron los totales.
    F(ws, "L5", "CADA SEMANA, DOS NÚMEROS en las casillas azules: cuántos CERRASTEIS y "
                "cuánto FACTURASTEIS. Nada más. El ticket medio, el % de cierre y el ROAS "
                "salen solos de ahí. Arriba, una sola vez, el MARGEN (el fee ya está puesto). "
                "Si una semana no tiene cierres, se deja vacía: no se inventa nada.",
      tam=8, color=GRIS, italic=True)
    ws.row_dimensions[6].height = 22

    r = 8
    filas_total = []                    # las filas «TOTAL <MES>», para sumar el año entero
    bloques = []                        # (primera, última) fila de SEMANA de cada mes
    for mes in meses:
        ws.merge_cells(f"A{r}:{ultima}{r}")
        F(ws, f"A{r}", f"  {MESES[mes].upper()} {anio}", tam=11, bold=True,
          color=BLANCO, fondo=MORADO)
        for j in range(2, ncol+1):
            ws[f"{get_column_letter(j)}{r}"].fill = PatternFill("solid", fgColor=MORADO)
        ws.row_dimensions[r].height = 24
        r += 1

        for j, (t, _, hor) in enumerate(COLS, start=1):
            F(ws, f"{get_column_letter(j)}{r}", t, tam=8, bold=True, color=BLANCO,
              fondo=NEGRO, hor="center" if j > 1 else "left")
        r += 1

        sem = semanas(anio, mes)
        d_ini, d_fin = sem[0][1], sem[-1][2]
        # Sin funnels, un solo grupo sin nombre: la hoja queda exactamente como antes.
        grupos = FUNNELS or [(None, None)]
        primera, filas_fn = r, {}
        for i, (etq, d1, d2) in enumerate(sem):
            for fn, marcas in grupos:
                fondo = SUAVE if i % 2 else None
                F(ws, f"A{r}", etq, tam=9, fondo=fondo)
                if FUNNELS:
                    F(ws, f'{X["Funnel"]}{r}', fn, tam=9, color=GRIS, fondo=fondo)
                celdas, _ = bloque_formulas(d1, d2, r, marcas=marcas)
                _comprobar_parentesis(celdas, f'semana {etq}')
                for j, (v, fmt) in enumerate(celdas, start=N_ETIQ + 1):
                    letra = get_column_letter(j)
                    editable = letra in (CIERRES_COL, FACTURADO_COL)
                    F(ws, f"{letra}{r}", v, tam=9, fmt=fmt,
                      hor="right", color=NEGRO,
                      fondo=A_MANO_BG if editable else fondo)
                filas_fn.setdefault(fn, []).append(r)
                r += 1
        ultima_fila = r - 1
        bloques.append((primera, ultima_fila))

        # ---- Totales del mes ----------------------------------------------------------
        # Con funnels son: una fila por funnel, una de «Sin clasificar» y el TOTAL DEL MES.
        # Los ratios SIEMPRE se calculan sobre las SUMAS del mes, nunca promediando las
        # semanas (las que aún no han pasado valen 0 y hunden la media).
        INV, IMP = X["Inversión"], X["Impresiones"]
        CLE, LEA = X["Clics en el enlace"], X["Clientes potenciales"]
        FACC = X["Facturado (a mano)"]
        fila_sin = r + len(FUNNELS)                  # «Sin clasificar» (solo si hay funnels)
        fila_mes = fila_sin + 1 if FUNNELS else r    # TOTAL DEL MES

        def sueltas(letra, filas):
            """SUM de celdas NO contiguas: las filas de un funnel van intercaladas."""
            return "SUM(" + ",".join(f"{letra}{f}" for f in filas) + ")"

        def rango(letra):
            return f"SUM({letra}{primera}:{letra}{ultima_fila})"

        def celdas_total(B, IM, G, H, CIE=None, FA=None, CT=None):
            # Sin CIE/FA/CT (la fila «Sin clasificar») las cuatro últimas van vacías: ese
            # gasto no tiene funnel al que atribuirle facturación, y un ROAS ahí sería falso.
            # ⛔ CADA trozo va entre PARÉNTESIS. La suma del mes es «SUM(C10:C19)+C22», y sin
            # paréntesis «B/H» se convierte en «SUM(...)+C22/SUM(...)+G22»: la división solo
            # afecta a UN sumando y el coste por lead sale mal SIN dar ningún error.
            return [
                (f"={B}", EURG), (f"={IM}", ENTG),
                (f"=IFERROR(({G})/({IM}),0)", PCTG), (f"={G}", ENTG), (f"={H}", ENTG),
                (f"=IFERROR(({B})/({H}),0)", EURG), (f"=IFERROR(({B})/({G}),0)", EURG),
                (f"={CIE}" if CIE else "", ENTG),
                # El % de cierre del MES se calcula sobre las SUMAS del mes, nunca promediando
                # los porcentajes de las semanas: una semana sin leads valdría lo mismo que una
                # con cien y hundiría la media (es el fallo 1 de la skill).
                (f"=IFERROR(({CIE})/({H}),0)" if CIE else "", PCTG),
                (f"={FA}" if FA else "", EURG),
                (f"={CT}" if CT else "", EURG),
                (f"=IFERROR(({FA})/({CT}),0)" if FA else "", ROASG),
                (f"=IFERROR(1/{MARGEN},0)" if FA else "", ROASG)]

        def pinta(fila, funnel, celdas, fondo=NEGRO, color=BLANCO, destacar=True):
            F(ws, f"A{fila}", f"TOTAL {MESES[mes].upper()}", tam=9, bold=True,
              color=color, fondo=fondo)
            if FUNNELS:
                F(ws, f'{X["Funnel"]}{fila}', funnel, tam=9, bold=True, color=color,
                  fondo=fondo)
            for j, (v, fmt) in enumerate(celdas, start=N_ETIQ + 1):
                letra = get_column_letter(j)
                F(ws, f"{letra}{fila}", v, tam=9, bold=True,
                  color=ROSA if (destacar and letra in DESTACADAS) else color,
                  fondo=fondo, fmt=fmt, hor="right")

        if FUNNELS:
            # ⛔ El fee NO se trocea entre los funnels (Dirección, 10-09-2026): «el fee es por los
            # funnels, no es un fee por funnel». Es UN pago mensual por la cuenta entera, así
            # que entra una sola vez, en la fila TOTAL DEL MES. Cada funnel enseña solo SU
            # inversión —igual que las filas de semana—, y su ROAS se mide contra eso.
            for fn, _ in FUNNELS:
                fl = filas_fn[fn]
                B = sueltas(INV, fl)
                CT = f"{INV}{r}"
                pinta(r, fn, celdas_total(B, sueltas(IMP, fl), sueltas(CLE, fl),
                                          sueltas(LEA, fl), sueltas(CIERRES_COL, fl),
                                          sueltas(FACC, fl), CT),
                      fondo=ROSA, color=NEGRO, destacar=False)
                r += 1
            # Lo que no cae en NINGÚN funnel. Se mide contra `datos` con el filtro al revés,
            # no restando: si alguien crea una campaña sin la marca de su funnel en el nombre,
            # su gasto aparece AQUÍ en vez de esfumarse del reporte sin que salte nada. En
            # rojo porque, si lleva número, es que hay una campaña mal nombrada.
            todas = [m for _, ms in FUNNELS for m in ms]
            pinta(fila_sin, "Sin clasificar",
                  celdas_total(suma(C["gasto"], d_ini, d_fin, excluir=todas),
                               suma(C["impresiones"], d_ini, d_fin, excluir=todas),
                               suma(C["clics_enlace"], d_ini, d_fin, excluir=todas),
                               suma(C["leads"], d_ini, d_fin, excluir=todas)),
                  fondo=ROJOBG, color=ROJO, destacar=False)
            r += 1

        # TOTAL DEL MES. La inversión, las impresiones, los clics y los leads incluyen la
        # fila «Sin clasificar»: el total del mes tiene que cuadrar con la cuenta de Meta
        # aunque haya campañas fuera de los funnels.
        B  = rango(INV) + (f"+{INV}{fila_sin}" if FUNNELS else "")
        IM = rango(IMP) + (f"+{IMP}{fila_sin}" if FUNNELS else "")
        G  = rango(CLE) + (f"+{CLE}{fila_sin}" if FUNNELS else "")
        H  = rango(LEA) + (f"+{LEA}{fila_sin}" if FUNNELS else "")
        FA = rango(FACC)
        if FUNNELS:
            # El CRM sí manda en el total: las filas de funnel no pueden mirar `ventas`
            # (se apuntarían la misma factura las dos), así que el dato real entra aquí.
            vm = suma_ventas(V["importe"], d_ini, d_fin)
            FA = f"IF({cuenta_ventas(d_ini, d_fin)}>0,{vm},{FA})"
        # Coste total del mes = inversión + el fee ENTERO, una sola vez: el fee es un
        # PAGO ÚNICO MENSUAL, no un coste diario. Si el mes no tuvo inversión no hubo
        # servicio y tampoco fee, así que el mes entero queda a cero.
        CT = f"IF(({B})=0,0,({B})+{FEE})"
        filas_total.append(fila_mes)
        pinta(fila_mes, "TODO (con fee)",
              celdas_total(B, IM, G, H, rango(CIERRES_COL), FA, CT))
        r = fila_mes + 3      # dos filas de aire antes del mes siguiente

    F(ws, f"A{r}", "El coste por lead es BRUTO: con los leads cualificados, el real es del orden "
                   "de 2,5 veces mayor. El ROAS se mide contra el COSTE TOTAL (la inversión más la "
                   "parte del fee que toca a esa semana), no contra la inversión sola. El ROAS mínimo "
                   "es el punto de equilibrio (1 ÷ margen): por debajo se pierde dinero.",
      tam=8, color=GRIS, italic=True)

    # Cierres totales y % que cierra: se suman las filas de TOTAL de cada mes (no toda la
    # columna, que contaría dos veces las semanas y su total).
    cierres_tot = "+".join(f"N({CIERRES_COL}{f})" for f in filas_total) or "0"
    # Por NOMBRE: esta línea estaba fijada a «H», que era «Clientes potenciales» hasta que
    # se quitaron Alcance y Frecuencia. Con el nuevo orden, H es «Coste por clic»: el
    # «% que cierra» habría dividido los cierres entre el CPC, sin dar ningún error.
    leads_tot = "+".join(f'N({X["Clientes potenciales"]}{f})' for f in filas_total) or "0"
    F(ws, "F6", f"={cierres_tot}", tam=13, bold=True, color=NEGRO, fmt=ENTG, hor="right")
    F(ws, "H6", f"=IFERROR(({cierres_tot})/({leads_tot}),0)", tam=13, bold=True,
      color=NEGRO, fmt=PCT0G, hor="right")
    # TICKET MEDIO = lo facturado ÷ los cierres, de las SEMANAS (no de las filas de TOTAL,
    # que contarían cada semana dos veces). Ya no lo escribe nadie: sale de lo que Equipo
    # apunta. Y no hay referencia circular porque «Facturado» ya no depende del ticket.
    if principal:
        fa = "+".join(f"SUM({FACTURADO_COL}{a}:{FACTURADO_COL}{b})" for a, b in bloques) or "0"
        ci = "+".join(f"SUM({CIERRES_COL}{a}:{CIERRES_COL}{b})" for a, b in bloques) or "0"
        F(ws, "B6", f"=IFERROR(({fa})/({ci}),0)", tam=13, bold=True,
          color=NEGRO, fmt=EURG, hor="right")

    return ws


def construir(cliente, cuenta, anio, desde_mes, filas_iniciales, funnels=None, corte_mes=None):
    """El libro entero. Con `corte_mes`, los meses anteriores se van a su propia pestaña.

    Nace de Cliente 02 (Dirección, 10-09-2026): con cuatro meses en la misma tabla no se leía
    ninguno. OJO: el corte es de PRESENTACIÓN, no de facturación — el fee sigue cargándose en
    todos los meses que lleve la cuenta, histórico incluido.
    """
    _configurar(funnels)
    _comprobar_columnas()
    wb = Workbook()
    if corte_mes and corte_mes > desde_mes:
        # Primero la que mira el cliente, que es la que manda y donde viven ticket/margen/fee.
        hoja_reporte(wb, "Reporte Meta", cliente, cuenta, anio, range(corte_mes, 13))
        hoja_reporte(wb, f"Histórico hasta {MESES[corte_mes - 1].lower()}", cliente, cuenta,
                     anio, range(desde_mes, corte_mes), principal=False, color=GRIS)
    else:
        hoja_reporte(wb, "Reporte Meta", cliente, cuenta, anio, range(desde_mes, 13))

    # ---- datos: lo único que toca n8n ----
    ws2 = wb.create_sheet("datos"); ws2.sheet_properties.tabColor = GRIS
    ws2.freeze_panes = "B2"
    anchos = [26, 12, 16, 42, 12, 13, 11, 12, 10, 9, 13, 10, 15, 9, 15]
    for j, (c, an) in enumerate(zip(DATOS, anchos), start=1):
        ws2.column_dimensions[get_column_letter(j)].width = an
        F(ws2, f"{get_column_letter(j)}1", c, tam=8, bold=True, color=BLANCO, fondo=NEGRO,
          hor="center" if j > 4 else "left")
    fmts = [None, None, None, None, EUR, ENT, ENT, DEC2, EUR, ENT, ENT, PCT, ENT, ENT, None]
    for i, f in enumerate(filas_iniciales):
        for j, (v, fmt) in enumerate(zip(f, fmts), start=1):
            F(ws2, f"{get_column_letter(j)}{i+2}", v, tam=9, fmt=fmt,
              hor="right" if j > 4 else "left", color=GRIS if j in (1, 3, 15) else NEGRO,
              fondo=SUAVE if i % 2 else None)
    ws2.auto_filter.ref = f"A1:O{max(len(filas_iniciales)+1, 2)}"

    # ---- ventas: la rellena el CRM, no el agente ----
    ws4 = wb.create_sheet("ventas"); ws4.sheet_properties.tabColor = "16794A"
    ws4.freeze_panes = "B2"
    for j, (c, an) in enumerate(zip(VENTAS, [30, 12, 16, 40, 14, 15]), start=1):
        ws4.column_dimensions[get_column_letter(j)].width = an
        F(ws4, f"{get_column_letter(j)}1", c, tam=8, bold=True, color=BLANCO, fondo=NEGRO,
          hor="center" if j > 3 else "left")
    F(ws4, "A3", "OPCIONAL. Solo hace falta si queréis el importe REAL de cada venta en vez del "
                 "ticket medio. Si tenéis un CRM conectado, se rellena sola; si no, se puede "
                 "escribir a mano o dejarla vacía: con los «Cierres (a mano)» de la otra pestaña "
                 "ya salen el facturado y el ROAS.",
      tam=9, color=GRIS, italic=True)
    F(ws4, "A4", "La fecha, en texto y así: 2026-09-05. Si la escribís 05/09/2026 no cuenta.",
      tam=9, color=ROJO, italic=True)
    ws2.conditional_formatting.add(f"{C['gasto']}2:{C['gasto']}{FIN}",
        ColorScaleRule(start_type="min", start_color=BLANCO, end_type="max", end_color="EDE9FF"))
    return wb


def datos_a_mano(sheet_id):
    """Qué hay escrito a mano en una hoja que ya existe. Vacío = se puede regenerar tranquilo.

    Existe porque `construir()` rehace el libro entero: los cierres de Equipo, el ticket, el
    margen y lo que trajo el CRM se perderían sin avisar. Mismo criterio que
    `montar_hoja_estado.py`, que tampoco pisa lo que alguien ya marcó.
    """
    from marcar_etapa import _descargar_xlsx
    tmp = os.path.join(tempfile.mkdtemp(), "actual.xlsx")
    if not _descargar_xlsx(sheet_id, tmp):
        # Si no se puede mirar, se avisa igual: más vale parar que borrar a ciegas.
        return ["no se ha podido leer la hoja actual para comprobarlo"]
    from openpyxl import load_workbook
    wb = load_workbook(tmp)
    fuera = []

    def a_mano(v):
        return v not in (None, "", 0) and not (isinstance(v, str) and v.startswith("="))

    # La pestaña se ha llamado «Reporte» y ahora «Reporte Meta»; puede volver a cambiar.
    # Se busca por prefijo para que la guarda no deje de proteger en silencio.
    # TODAS las pestañas de reporte, no solo la primera: desde que existe «Histórico hasta
    # <mes>» hay cierres escritos fuera de «Reporte Meta», y mirar solo una los borraría sin
    # avisar. Se reconocen por tener filas de semana («Del 1 al 7»), no por el nombre.
    hojas = [n for n in wb.sheetnames if n not in ("datos", "ventas", "datos-google")]
    for hoja in hojas:
        ws = wb[hoja]
        # F6 y H6 ya NO se miran: desde el 10-09-2026 son fórmulas (cierres totales y
        # % que cierra), y a_mano() las descarta sola. El que sí hay que proteger es el
        # FEE: entra en el ROAS de las dos pestañas, así que perderlo falsea el número
        # sin que se note. Solo cuenta si lo han cambiado respecto del que se pone al crear.
        # B6 ya NO se mira: el ticket medio vuelve a ser una fórmula (facturado ÷ cierres)
        # y a_mano() descarta las fórmulas sola.
        if a_mano(ws["D6"].value):
            fuera.append(f"{hoja} · margen (D6): {ws['D6'].value}")
        fee = ws["J6"].value
        if a_mano(fee) and fee != FEE_DEF:
            fuera.append(f"{hoja} · fee de agencia (J6): {fee} — distinto del de por defecto")
        # Solo las filas de SEMANA. Si no, la cabecera («Cierres», «Ventas cerradas»…) cuenta
        # como dato escrito y la guarda salta siempre.
        def es_semana(f):
            v = ws[f"A{f}"].value
            return isinstance(v, str) and v.strip().lower().startswith("del ")
        for col, que in ((CIERRES_COL, "cierres"),
                         (FACTURADO_COL, "importes facturados")):
            n = sum(1 for f in range(1, ws.max_row + 1)
                    if es_semana(f) and a_mano(ws[f"{col}{f}"].value))
            if n:
                fuera.append(f"{hoja} · {n} semana(s) con {que} escritos a mano")
    if "ventas" in wb.sheetnames:
        ws = wb["ventas"]
        n = sum(1 for f in range(2, ws.max_row + 1) if a_mano(ws[f"B{f}"].value))
        if n:
            fuera.append(f"{n} venta(s) apuntadas en la pestaña «ventas»")
    # Google: `construir()` no monta estas pestañas, así que regenerar las BORRA. Y el
    # histórico de `datos-google` solo se recupera reejecutando el script en la cuenta.
    if "datos-google" in wb.sheetnames:
        ws = wb["datos-google"]
        n = sum(1 for f in range(2, ws.max_row + 1) if ws[f"A{f}"].value not in (None, ""))
        if n:
            fuera.append(f"{n} fila(s) en «datos-google» (solo se recuperan reejecutando "
                         f"el script en Google Ads)")
    if any(n.strip().lower() == "reporte google" for n in wb.sheetnames):
        fuera.append("la pestaña «Reporte Google» (habría que volver a montarla "
                     "con anadir_hoja_google.py)")
    return fuera


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cliente", required=True); ap.add_argument("--cuenta", required=True)
    ap.add_argument("--anio", type=int, required=True)
    ap.add_argument("--desde-mes", type=int, default=1)
    ap.add_argument("--carpeta-id", required=True); ap.add_argument("--datos", default=None)
    ap.add_argument("--nombre", default=None)
    ap.add_argument("--rehacer", action="store_true",
                    help="rehacer la hoja AUNQUE tenga datos escritos a mano (se pierden)")
    # Repetible. «Nombre=marca;marca»: una marca es un TROZO del nombre de la campaña, y
    # basta con que aparezca una para que esa campaña cuente en ese funnel. Lo que no case
    # con ninguno cae en la fila «Sin clasificar», a la vista.
    #   --funnel "Inversión=LANDING INVERSION;FUNNEL INVERSION"
    ap.add_argument("--funnel", action="append", default=[],
                    metavar="NOMBRE=MARCA;MARCA",
                    help="separa el reporte por funnel (repetible)")
    # Los meses anteriores a este se van a una pestaña «Histórico hasta <mes>»: son de antes
    # de que lleváramos la cuenta y mezclarlos en la misma tabla no deja leer ninguno.
    ap.add_argument("--corte-mes", type=int, default=None, metavar="MES",
                    help="mes en que arranca el reporte vivo; lo anterior va al histórico")
    a = ap.parse_args()

    funnels = []
    for f in a.funnel:
        if "=" not in f:
            sys.exit(f"✗ --funnel se escribe «Nombre=MARCA;MARCA», y llegó: {f}")
        nombre, marcas = f.split("=", 1)
        marcas = [m.strip() for m in marcas.split(";") if m.strip()]
        if not marcas:
            sys.exit(f"✗ El funnel «{nombre}» se ha quedado sin ninguna marca.")
        funnels.append((nombre.strip(), marcas))

    filas = []
    if a.datos:
        d = json.load(open(a.datos)); camps = d["campanas"]
        for f in sorted(d["filas"], key=lambda x: (x[0], x[1])):
            filas.append([f"{f[0]}|{camps[f[1]]['nombre']}", f[0], d["cliente"],
                          camps[f[1]]["nombre"], f[2], f[3], f[7], f[8], f[9], f[4],
                          f[5], f[10]/100, f[6], f[11], "carga inicial"])

    # El archivo perdió el «Meta» al meter Google dentro. Los creados antes llevan el nombre
    # viejo: hay que buscar los DOS, o sobre un cliente antiguo se crearía un SEGUNDO archivo
    # y el script de Google seguiría escribiendo en el otro.
    nombre = a.nombre or f"Reporte Ads — {a.cliente} — {a.anio}"
    viejo = f"Reporte Meta Ads — {a.cliente} — {a.anio}"
    wb = construir(a.cliente, a.cuenta, a.anio, a.desde_mes, filas, funnels, a.corte_mes)
    tmp = os.path.join(tempfile.mkdtemp(), "hoja.xlsx"); wb.save(tmp)

    def buscar(n):
        q = f"name = '{n}' and '{a.carpeta_id}' in parents and trashed = false"
        url = ("https://www.googleapis.com/drive/v3/files?"
               + urllib.parse.urlencode({"q": q, "fields": "files(id,name)",
                                         "supportsAllDrives": "true",
                                         "includeItemsFromAllDrives": "true"}))
        return api(url).get("files", [])
    ya = buscar(nombre) or (buscar(viejo) if not a.nombre else [])
    if ya and not a.rehacer:
        escrito = datos_a_mano(ya[0]["id"])
        if escrito:
            sys.exit("✗ Esa hoja ya tiene datos escritos a mano y regenerarla los BORRARÍA:\n"
                     + "".join(f"   · {x}\n" for x in escrito)
                     + "  Si de verdad querés rehacerla, repetí el comando con --rehacer.\n"
                     "  Para cambiar el diseño sin perder nada, mejor tocar la hoja a mano.")
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
    print("  No se vuelve a generar: n8n escribe en `datos` y las semanas se recalculan solas.")
    print(sid)


if __name__ == "__main__":
    main()
