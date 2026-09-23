#!/usr/bin/env python3
"""De los términos de búsqueda REALES de la cuenta al plan de keywords.

    python3 terminos.py "<URL del archivo de estacionalidad>" --marca "cliente,fundador" \
        --excluir "centro,clinica,ingreso" [--familias familias.json]

Saca lo que un brief nunca puede dar:
  1. Los términos que CONVIERTEN, con su coste por lead: la base del plan.
  2. Los que QUEMAN dinero sin una sola conversión: candidatos a negativa.
  3. Cuánto se gasta en búsquedas que el servicio NO puede cumplir (--excluir), y cómo convierten
     frente al resto. Suelen convertir peor, no cero: se dice con el número.
  4. Las familias de términos con su gasto y su coste por lead, para ver qué está infrafinanciado.
  5. Alertas de medición: términos con MÁS conversiones que clics (la conversión cuenta de más).
"""
import argparse, json, os, re, subprocess, sys, tempfile
from collections import defaultdict


def bajar(hoja, remoto):
    import openpyxl
    m = re.search(r'/spreadsheets/d/([A-Za-z0-9_-]{20,})', hoja)
    fid = m.group(1) if m else hoja.strip()
    tmp = os.path.join(tempfile.mkdtemp(), 'h.xlsx')
    subprocess.run(['rclone', 'backend', 'copyid', remoto, fid, tmp,
                    '--drive-export-formats', 'xlsx'], capture_output=True)
    if not os.path.exists(tmp):
        sys.exit("✗ rclone no pudo bajar el archivo")
    wb = openpyxl.load_workbook(tmp, read_only=True, data_only=True)
    h = next((n for n in ('terminos-mes', 'datos-google-terminos') if n in wb.sheetnames), None)
    if not h:
        sys.exit(f"✗ No hay pestaña de términos. Tiene: {', '.join(wb.sheetnames)}")
    return wb[h]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('hoja')
    ap.add_argument('--marca', default='', help='marca y nombres propios (fundador, etc.)')
    ap.add_argument('--excluir', default='', help='lo que el servicio NO ofrece')
    ap.add_argument('--familias', help='JSON {"familia": ["palabra", ...]}')
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--remoto', default='gdrive:')
    a = ap.parse_args()

    marca = [x.strip().lower() for x in a.marca.split(',') if x.strip()]
    excl = [x.strip().lower() for x in a.excluir.split(',') if x.strip()]
    fams = json.load(open(a.familias, encoding='utf-8')) if a.familias else {}

    ws = bajar(a.hoja, a.remoto)
    cab, T, n_marca = None, defaultdict(lambda: defaultdict(float)), 0
    for f in ws.iter_rows(values_only=True):
        if cab is None:
            cab = [str(c) for c in f]; continue
        d = dict(zip(cab, f))
        t = ' '.join(str(d.get('termino') or '').lower().split())
        if not t:
            continue
        if any(m in t for m in marca):
            n_marca += 1; continue
        for c in ('clics', 'coste', 'conversiones', 'impresiones'):
            T[t][c] += float(d.get(c) or 0)

    coste = sum(v['coste'] for v in T.values())
    conv = sum(v['conversiones'] for v in T.values())
    cpa_media = coste / conv if conv else 0
    print(f"{len(T):,} términos distintos · {coste:,.0f} € · {conv:.0f} conversiones · "
          f"CPA medio {cpa_media:.1f} €  (sin marca: {n_marca} filas fuera)".replace(',', '.'))

    print(f"\n{'='*74}\n1 · LOS QUE CONVIERTEN — la base del plan\n{'='*74}")
    for t, v in sorted(T.items(), key=lambda x: (-x[1]['conversiones'], x[1]['coste']))[:a.top]:
        if v['conversiones'] <= 0:
            break
        cpa = v['coste'] / v['conversiones']
        print(f"   {t[:46]:<47}{v['conversiones']:4.0f} conv  {v['coste']:6.0f} €  CPA {cpa:6.1f}")

    print(f"\n{'='*74}\n2 · LOS QUE QUEMAN DINERO — cero conversiones, más gasto\n{'='*74}")
    sin = [(t, v) for t, v in T.items() if v['conversiones'] == 0]
    for t, v in sorted(sin, key=lambda x: -x[1]['coste'])[:a.top]:
        print(f"   {t[:50]:<51}{v['coste']:6.0f} €  {v['clics']:4.0f} clics")
    g = sum(v['coste'] for _, v in sin)
    print(f"\n   Total en términos sin ninguna conversión: {g:,.0f} € ({g/coste*100:.0f} % del gasto) "
          f"repartido en {len(sin):,} términos.".replace(',', '.'))
    print("   Ojo: la mayoría son cola larga de pocos euros. Negativizar solo las FAMILIAS que se repiten,")
    print("   no término a término, y nunca las que comparten raíz con un término que sí convierte.")

    if excl:
        print(f"\n{'='*74}\n3 · LO QUE EL SERVICIO NO PUEDE CUMPLIR ({', '.join(excl)})\n{'='*74}")
        ex = [(t, v) for t, v in T.items() if any(x in t for x in excl)]
        for t, v in sorted(ex, key=lambda x: -x[1]['coste'])[:12]:
            print(f"   {t[:50]:<51}{v['coste']:6.0f} €  {v['conversiones']:3.0f} conv")
        ce = sum(v['coste'] for _, v in ex); cve = sum(v['conversiones'] for _, v in ex)
        resto_c, resto_v = coste - ce, conv - cve
        print(f"\n   Gastado ahí: {ce:,.0f} € en {len(ex)} términos → {cve:.0f} conversiones".replace(',', '.'))
        if cve:
            print(f"   CPA {ce/cve:.1f} € frente a {resto_c/resto_v:.1f} € del resto "
                  f"({(ce/cve)/(resto_c/resto_v)*100-100:+.0f} %).")
            print("   Convierten peor, no cero: quien entra buscando un sitio físico rellena el formulario y")
            print("   luego no cierra. Merece mirar en el CRM si esos leads llegaron a cerrar.")
        else:
            print("   Ninguna conversión: gasto perdido entero.")

    if fams:
        print(f"\n{'='*74}\n4 · POR FAMILIA\n{'='*74}")
        filas = []
        for fam, ks in fams.items():
            s = [v for t, v in T.items() if any(k in t for k in ks)]
            c = sum(v['coste'] for v in s); cv = sum(v['conversiones'] for v in s)
            filas.append((fam, len(s), c, cv, c / cv if cv else 0))
        print(f"   {'familia':<30}{'términos':>9}{'gasto':>9}{'conv':>6}{'CPA':>8}   vs media")
        for fam, n, c, cv, cpa in sorted(filas, key=lambda x: -x[2]):
            marca_cpa = ('más barata' if cpa and cpa < cpa_media * .85 else
                         'más cara' if cpa > cpa_media * 1.15 else ('sin conversiones' if not cpa else 'en la media'))
            print(f"   {fam:<30}{n:>9}{c:>8.0f}€{cv:>6.0f}{cpa:>8.1f}   {marca_cpa}")
        print("\n   Una familia MÁS BARATA que la media y con poco gasto está infrafinanciada.")

    print(f"\n{'='*74}\n5 · ALERTAS DE MEDICIÓN\n{'='*74}")
    raros = [(t, v) for t, v in T.items() if v['conversiones'] > v['clics'] and v['clics'] > 0]
    if raros:
        for t, v in sorted(raros, key=lambda x: -x[1]['conversiones'])[:8]:
            print(f"   {t[:50]:<51}{v['conversiones']:3.0f} conv con {v['clics']:3.0f} clics")
        print("\n   Más conversiones que clics = la acción de conversión cuenta varias veces por persona.")
        print("   Revisar en Google Ads si está en «Cada una» en vez de «Una». Hasta entonces, el CPA")
        print("   de esos términos es falso (sale demasiado barato).")
    else:
        print("   Nada raro: ningún término con más conversiones que clics.")


if __name__ == '__main__':
    main()
