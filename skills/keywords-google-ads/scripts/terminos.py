#!/usr/bin/env python3
"""De los términos de búsqueda REALES de la cuenta al plan de keywords.

    python3 terminos.py "<URL del archivo de estacionalidad>" --marca "cliente,fundador" \
        --excluir "centro,clinica,ingreso" --familias ~/Desktop/CLIENTES/<Cliente>/google-ads/familias.json

Saca lo que un brief nunca da (todo sobre la ventana del archivo, normalmente 24 meses):
  1. Los que CONVIERTEN, con su coste por lead: la base del plan.
  2. Los que QUEMAN dinero sin una conversión: candidatos a negativa (por familias, no uno a uno).
  3. Cuánto se va en lo que el servicio NO puede cumplir (--excluir) y a qué CPA frente al resto.
     Suelen convertir peor, no cero.
  4. Gasto y CPA por familia, con una fila «resto». Un término cuenta en UNA familia (la primera
     del JSON que encaje), igual que en estacionalidad.py.
  5. Alertas de medición: más conversiones que clics = la conversión cuenta de más. Antes de
     fiarse de ningún CPA.
"""
import argparse
from collections import defaultdict
from comun import (agregar_terminos, bajar_archivo, cargar_familias, familia_de, fmt_n,
                   leer_pestana, lista)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('hoja', help='URL del archivo «Estacionalidad - <Cliente>»')
    ap.add_argument('--marca', default='', help='marca y nombres propios (fundador, etc.)')
    ap.add_argument('--excluir', default='', help='lo que el servicio NO ofrece')
    ap.add_argument('--familias', help='JSON {"familia": ["palabra", ...]}')
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--remoto', default='gdrive:')
    a = ap.parse_args()

    marca, excl = lista(a.marca), lista(a.excluir)
    fams = cargar_familias(a.familias)
    filas, _ = leer_pestana(bajar_archivo(a.hoja, a.remoto), ('terminos-mes', 'datos-google-terminos'))
    T, n_marca = agregar_terminos(filas, marca, excl)
    meses = {str(f.get('mes'))[:7] for f in filas if f.get('mes')}

    coste = sum(v['coste'] for v in T.values())
    conv = sum(v['conversiones'] for v in T.values())
    cpa_media = coste / conv if conv else 0
    print(f"{fmt_n(len(T))} términos · {fmt_n(coste)} € · {conv:.0f} conversiones · CPA medio "
          f"{cpa_media:.1f} €  · ventana: {len(meses)} meses · {n_marca} filas de marca fuera")
    if coste == 0:
        raise SystemExit("✗ Gasto cero en la ventana: no hay nada que analizar.")

    print(f"\n{'='*74}\n1 · LOS QUE CONVIERTEN — la base del plan\n{'='*74}")
    for t, v in sorted(T.items(), key=lambda x: (-x[1]['conversiones'], x[1]['coste']))[:a.top]:
        if v['conversiones'] <= 0:
            break
        print(f"   {t[:46]:<47}{v['conversiones']:4.0f} conv  {v['coste']:6.0f} €  CPA {v['coste']/v['conversiones']:6.1f}"
              + ("  ← no lo cumple el servicio" if v['_excluido'] else ""))

    print(f"\n{'='*74}\n2 · LOS QUE QUEMAN DINERO — cero conversiones, más gasto\n{'='*74}")
    sin = [(t, v) for t, v in T.items() if v['conversiones'] == 0]
    for t, v in sorted(sin, key=lambda x: -x[1]['coste'])[:a.top]:
        print(f"   {t[:50]:<51}{v['coste']:6.0f} €  {v['clics']:4.0f} clics")
    g = sum(v['coste'] for _, v in sin)
    print(f"\n   Sin ninguna conversión en {len(meses)} meses: {fmt_n(g)} € ({g/coste*100:.0f} % del gasto) en "
          f"{fmt_n(len(sin))} términos.\n   La mayoría es cola larga de pocos euros: se negativizan FAMILIAS que se repiten, no términos\n"
          "   sueltos, y nunca una que comparta raíz con un término que convierte.")

    if excl:
        print(f"\n{'='*74}\n3 · LO QUE EL SERVICIO NO PUEDE CUMPLIR ({', '.join(excl)})\n{'='*74}")
        ex = [(t, v) for t, v in T.items() if v['_excluido']]
        for t, v in sorted(ex, key=lambda x: -x[1]['coste'])[:12]:
            print(f"   {t[:50]:<51}{v['coste']:6.0f} €  {v['conversiones']:3.0f} conv")
        ce = sum(v['coste'] for _, v in ex); cve = sum(v['conversiones'] for _, v in ex)
        rc, rv = coste - ce, conv - cve
        print(f"\n   Gastado ahí: {fmt_n(ce)} € en {len(ex)} términos → {cve:.0f} conversiones")
        if cve and rv:
            print(f"   CPA {ce/cve:.1f} € frente a {rc/rv:.1f} € del resto ({(ce/cve)/(rc/rv)*100-100:+.0f} %).\n"
                  "   Convierten peor, no cero: dejan sus datos y luego no cierran. Comprobar en el CRM.")
        elif cve:
            print(f"   CPA {ce/cve:.1f} € — y el resto de la cuenta no tiene conversiones para comparar.")
        else:
            print("   Ninguna conversión: gasto perdido entero.")

    print(f"\n{'='*74}\n4 · POR FAMILIA" + ("" if fams else "  (sin --familias: agrupado por la palabra principal)") + f"\n{'='*74}")
    F = defaultdict(lambda: defaultdict(float))
    for t, v in T.items():
        f = familia_de(t, fams)
        F[f]['n'] += 1; F[f]['coste'] += v['coste']; F[f]['conv'] += v['conversiones']
    print(f"   {'familia':<30}{'términos':>9}{'gasto':>9}{'conv':>6}{'CPA':>8}   vs media {cpa_media:.0f} €")
    for f, v in sorted(F.items(), key=lambda x: -x[1]['coste'])[:a.top]:
        cpa = v['coste'] / v['conv'] if v['conv'] else 0
        lect = ('sin conversiones' if not cpa else 'más barata' if cpa < cpa_media * .85
                else 'más cara' if cpa > cpa_media * 1.15 else 'en la media')
        print(f"   {f[:29]:<30}{v['n']:>9.0f}{v['coste']:>8.0f}€{v['conv']:>6.0f}{cpa:>8.1f}   {lect}")
    print("\n   Una familia más barata que la media y con poco gasto está infrafinanciada. Antes de fiarse\n"
          "   de un CPA, mirar la sección 5.")

    print(f"\n{'='*74}\n5 · ALERTAS DE MEDICIÓN\n{'='*74}")
    raros = [(t, v) for t, v in T.items() if v['conversiones'] > v['clics'] > 0]
    if raros:
        for t, v in sorted(raros, key=lambda x: -x[1]['conversiones'])[:8]:
            print(f"   {t[:50]:<51}{v['conversiones']:3.0f} conv con {v['clics']:3.0f} clics")
        print("\n   Más conversiones que clics: o la acción cuenta «Cada una» en vez de «Una», o hay varias\n"
              "   acciones principales (formulario + llamada) contando la misma persona. El CPA de esos\n"
              "   términos —y de su familia— sale más barato de lo que es. Revisar en Google Ads antes de\n"
              "   recomendar nada con ellos.")
    else:
        print("   Nada raro: ningún término con más conversiones que clics.")


if __name__ == '__main__':
    main()
