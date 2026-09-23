#!/usr/bin/env python3
"""Lo que hace la CUENTA mes a mes y año a año, desde el archivo «Estacionalidad - <Cliente>».

    python3 estacionalidad.py "<URL del archivo de estacionalidad>" --marca "cliente,fundador" \
        [--excluir "centro,clinica"] [--familias ~/Desktop/CLIENTES/<Cliente>/google-ads/familias.json]

La URL NO es la de la hoja de reportes: es la del archivo que crea el Ads Script (está en la
línea SHEET_URL_ESTACIONAL del script, o buscando en Drive «Estacionalidad - <Cliente>»).

Saca:
  1. La cuenta por AÑO: clics, gasto, conversiones, CPA. Aquí se ve si la cuenta crece o cae,
     que es distinto de la estacionalidad y el índice mensual lo esconde.
  2. El índice mensual (100 = mes medio) de impresiones, clics y conversiones, promediando el
     mismo mes de los años completos. El mes en curso se enseña APARTE: está a medias.
  3. Gasto y coste por lead de cada mes.
  4. La cuota de impresiones perdida por presupuesto y por ranking, ponderada por las impresiones
     elegibles de cada campaña (una campaña de 3 € no pesa lo que la principal).
  5. Las familias de términos con su índice y su pico.
"""
import argparse, sys
from collections import defaultdict
from datetime import date
from comun import (MESES, bajar_archivo, cargar_familias, familia_de, fmt_n, leer_pestana,
                   lista, mes_de, norm)


def indice(por_mes):
    vals = [v for v in por_mes.values()]
    media = sum(vals) / len(vals) if vals else 0
    return {m: round(v / media * 100) for m, v in por_mes.items()} if media else {}


def fila(etq, d, meses, fmt=lambda v: f"{v:>5}"):
    print(f"   {etq:<14}" + " ".join(fmt(d[m]) if m in d else "    ·" for m in meses))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('hoja', help='URL del archivo «Estacionalidad - <Cliente>» (NO la hoja de reportes)')
    ap.add_argument('--marca', default='', help='marca y nombres propios, separados por comas')
    ap.add_argument('--excluir', default='', help='lo que el servicio NO ofrece; se enseña aparte')
    ap.add_argument('--familias', help='JSON {"familia": ["palabra", ...]}')
    ap.add_argument('--top', type=int, default=10, help='cuántas familias mostrar')
    ap.add_argument('--remoto', default='gdrive:')
    a = ap.parse_args()

    marca, excluir = lista(a.marca), lista(a.excluir)
    familias = cargar_familias(a.familias)
    if not marca:
        print("⚠️  Sin --marca: quien busca al cliente por su nombre ya lo conocía; eso no es demanda "
              "y falsea el índice. Relánzalo con --marca \"nombre,variantes\".")

    ruta = bajar_archivo(a.hoja, a.remoto)
    terminos, _ = leer_pestana(ruta, ('terminos-mes', 'datos-google-terminos'))
    try:
        is_filas, _ = leer_pestana(ruta, ('is-mes', 'datos-google-is'))
    except SystemExit:
        is_filas = []

    hoy = date.today()
    actual = (hoy.year, hoy.month)

    # ── Agregado por (año, mes) y por familia ──
    tot = defaultdict(lambda: defaultdict(float))          # (a,m) -> métricas
    fam = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))  # familia -> (a,m) -> métricas
    n_marca = n_excl = 0
    for f in terminos:
        am = mes_de(f.get('mes'))
        t = norm(f.get('termino'))
        if not am or not t:
            continue
        if marca and any(p in t for p in marca):
            n_marca += 1
            continue
        if excluir and any(x in t for x in excluir):
            n_excl += 1
            continue
        fa = familia_de(t, familias)
        for c in ('impresiones', 'clics', 'conversiones', 'coste'):
            v = float(f.get(c) or 0)
            tot[am][c] += v
            fam[fa][am][c] += v
    if not tot:
        sys.exit("✗ No hay filas con fecha. Ejecuta el Ads Script (Vista previa) y vuelve.")

    meses_completos = [am for am in sorted(tot) if am != actual]
    anios = sorted({a_ for a_, _ in tot})
    print(f"\n{'═'*70}\nLA CUENTA · {len(tot)} meses con datos ({anios[0]}–{anios[-1]})"
          + (f" · el mes en curso ({MESES[actual[1]-1]} {actual[0]}) se enseña aparte" if actual in tot else ""))
    print(f"{fmt_n(len(terminos))} filas de términos · {fmt_n(n_marca)} de marca fuera"
          + (f" · {fmt_n(n_excl)} de lo que el servicio no ofrece, fuera" if excluir else ""))
    if len(meses_completos) < 24:
        print("⚠️  Menos de 24 meses completos: lo que sigue es una HIPÓTESIS, no un patrón. Con menos de\n"
              "   2 años no se distingue temporada de crecimiento.")

    # ── 1. Por año: ¿la cuenta crece o cae? ──
    print(f"\n{'─'*70}\n1 · LA CUENTA POR AÑO (¿crece o cae? — esto el índice mensual lo esconde)")
    print(f"   {'año':<8}{'meses':>6}{'gasto':>10}{'clics':>8}{'conv':>7}{'CPA':>8}")
    por_anio = defaultdict(lambda: defaultdict(float))
    for (y, m), v in tot.items():
        por_anio[y]['meses'] += 1
        for c in ('coste', 'clics', 'conversiones'):
            por_anio[y][c] += v[c]
    for y in anios:
        v = por_anio[y]
        cpa = v['coste'] / v['conversiones'] if v['conversiones'] else 0
        parcial = ' (parcial)' if v['meses'] < 12 else ''
        print(f"   {str(y)+parcial:<8}{v['meses']:>6.0f}{v['coste']:>9.0f}€{v['clics']:>8.0f}{v['conversiones']:>7.0f}{cpa:>7.0f}€")
    # mismo mes, año anterior
    ult = meses_completos[-1] if meses_completos else None
    if ult and (ult[0]-1, ult[1]) in tot:
        u, p = tot[ult], tot[(ult[0]-1, ult[1])]
        cu = u['coste']/u['conversiones'] if u['conversiones'] else 0
        cp = p['coste']/p['conversiones'] if p['conversiones'] else 0
        print(f"\n   Último mes completo, {MESES[ult[1]-1]} {ult[0]} frente a {MESES[ult[1]-1]} {ult[0]-1}: "
              f"gasto {u['coste']:.0f}€ vs {p['coste']:.0f}€ · conv {u['conversiones']:.0f} vs {p['conversiones']:.0f} · CPA {cu:.0f}€ vs {cp:.0f}€")

    # ── 2. Índice mensual (años completos, sin el mes en curso) ──
    def por_mes(c):
        acum = defaultdict(list)
        for (y, m) in meses_completos:
            acum[m].append(tot[(y, m)][c])
        return {m: sum(v)/len(v) for m, v in acum.items()}
    meses = sorted({m for _, m in meses_completos})
    print(f"\n{'─'*70}\n2 · ÍNDICE MENSUAL (100 = mes medio; promedio del mismo mes en los años completos)")
    print(f"   {'':<14}" + " ".join(f"{MESES[m-1]:>5}" for m in meses))
    etq = {'impresiones': 'impresiones*', 'clics': 'clics', 'conversiones': 'conversiones'}
    idx = {}
    for c in ('impresiones', 'clics', 'conversiones'):
        idx[c] = indice(por_mes(c))
        fila(etq[c], idx[c], meses)
    print("   * impresiones de los términos que tuvieron al menos un clic: no es toda la demanda.")
    ic = idx['conversiones']
    if ic:
        alto = sorted(ic.items(), key=lambda x: -x[1])[:3]
        bajo = sorted(ic.items(), key=lambda x: x[1])[:3]
        print(f"\n   Mejores meses (conversiones): {', '.join(f'{MESES[m-1]} {v}' for m, v in alto)}")
        print(f"   Peores meses  (conversiones): {', '.join(f'{MESES[m-1]} {v}' for m, v in bajo)}")

    # ── 3. Gasto y coste por lead, por mes ──
    print(f"\n{'─'*70}\n3 · GASTO Y COSTE POR LEAD (media de los años completos)")
    print(f"   {'':<14}" + " ".join(f"{MESES[m-1]:>5}" for m in meses))
    g = por_mes('coste'); cv = por_mes('conversiones')
    fila('gasto €', {m: round(g[m]) for m in g}, meses)
    fila('leads', {m: round(cv[m], 1) for m in cv}, meses, lambda v: f"{v:>5.1f}")
    fila('CPA €', {m: round(g[m]/cv[m]) for m in g if cv.get(m)}, meses)
    if actual in tot:
        v = tot[actual]
        print(f"\n   Mes en curso ({MESES[actual[1]-1]} {actual[0]}, día {hoy.day}): {v['coste']:.0f}€ · "
              f"{v['conversiones']:.0f} conv · CPA {v['coste']/v['conversiones'] if v['conversiones'] else 0:.0f}€ — incompleto, fuera de las medias.")

    # ── 4. Cuota perdida, ponderada por impresiones elegibles ──
    if is_filas:
        eleg = defaultdict(float); ppres = defaultdict(float); prank = defaultdict(float)
        for f in is_filas:
            am = mes_de(f.get('mes'))
            try:
                imp = float(f.get('impresiones') or 0); s = float(f.get('is') or 0)
                bp = float(f.get('is_perdida_presupuesto') or 0); br = float(f.get('is_perdida_ranking') or 0)
            except (TypeError, ValueError):
                continue
            if not am or am == actual or s <= 0 or imp <= 0:
                continue          # sin IS no se puede saber cuántas eran elegibles
            e = imp / s
            eleg[am[1]] += e; ppres[am[1]] += e * bp; prank[am[1]] += e * br
        print(f"\n{'─'*70}\n4 · CUOTA DE IMPRESIONES PERDIDA (ponderada por impresiones elegibles, Búsqueda)")
        print(f"   {'':<14}" + " ".join(f"{MESES[m-1]:>5}" for m in meses))
        dp = {m: round(ppres[m]/eleg[m]*100) for m in eleg if eleg[m]}
        dr = {m: round(prank[m]/eleg[m]*100) for m in eleg if eleg[m]}
        fila('presupuesto', dp, meses, lambda v: f"{v:>4}%")
        fila('ranking', dr, meses, lambda v: f"{v:>4}%")
        print("   Lo perdido por PRESUPUESTO se compra con dinero. Lo perdido por RANKING no: es\n"
              "   relevancia del anuncio, calidad de la keyword y landing.")
        fuga = sorted([(m, dp[m]) for m in dp if ic.get(m, 0) >= 100 and dp[m] >= 10], key=lambda x: -x[1])[:4]
        if fuga:
            print("\n   💰 Meses con demanda alta y presupuesto corto:")
            for m, p in fuga:
                print(f"      {MESES[m-1]}: índice de conversión {ic[m]} · {p} % de impresiones perdidas por presupuesto")

    # ── 5. Familias ──
    print(f"\n{'─'*70}\n5 · POR FAMILIA (por conversiones)" + ("" if familias else "  — agrupado solo; pasa --familias para afinar"))
    orden = sorted(fam.items(), key=lambda x: -sum(v['conversiones'] for v in x[1].values()))[:a.top]
    for nombre, d in orden:
        conv = sum(v['conversiones'] for v in d.values()); coste = sum(v['coste'] for v in d.values())
        if conv < 1:
            continue
        acum = defaultdict(list)
        for (y, m), v in d.items():
            if (y, m) != actual:
                acum[m].append(v['conversiones'])
        ix = indice({m: sum(v)/len(v) for m, v in acum.items()})
        pico = max(ix.items(), key=lambda x: x[1]) if ix else None
        print(f"\n   ▸ {nombre}  · {conv:.0f} conv · {coste:.0f} € · CPA {coste/conv:.0f} €"
              + (f" · pico {MESES[pico[0]-1]} ({pico[1]})" if pico else ""))
        fila('índice conv', ix, meses)

    print(f"\n{'═'*70}\nÍndices relativos a la propia cuenta. Las impresiones dependen del presupuesto de ese\n"
          "mes: un mes sin dinero parece un mes sin demanda. Léelas con la tabla 4.")


if __name__ == '__main__':
    main()
