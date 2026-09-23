#!/usr/bin/env python3
"""Pasa por Google Trends los términos que MEJOR CONVIERTEN de la cuenta, en lote.

    python3 trends.py <URL_O_ID_del_archivo_de_estacionalidad> --marca "cliente" --top 8
    python3 trends.py --terminos "dejar de beber,alcoholicos anonimos" --geo ES

Responde a lo que la cuenta no puede: **¿este patrón se repite en años anteriores, en todo el
mercado, o es solo cosa de esta cuenta?** Trends llega a 5 años; la cuenta, a los meses que lleve.

CÓMO EVITA LAS DOS TRAMPAS DE TRENDS
1. Trends compara un máximo de 5 términos por consulta y sus valores son RELATIVOS a esa consulta:
   dos lotes distintos no son comparables. Este script mete el mismo **término ancla** en todos los
   lotes y reescala por él, así todo queda en la misma regla.
2. La API interna devuelve 429 a pelo. Se abre antes la portada de Trends para recoger la cookie
   NID (aunque esa primera llamada falle) y con ella responde. Entre lotes se espera, porque
   pedir deprisa vuelve a bloquear.

No usa pytrends (archivado en 2025) ni ninguna API de pago.
"""
import argparse, http.cookiejar, json, sys, time, urllib.parse, urllib.request
from collections import defaultdict

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140 Safari/537")
MESES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']


def sesion(geo):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "es-ES,es;q=0.9"),
                     ("Accept", "text/html,application/xhtml+xml,*/*;q=0.8")]
    try:                      # suele devolver 429 y aun así deja la cookie NID: es lo que importa
        op.open(f"https://trends.google.es/trends/explore?geo={geo}", timeout=25).read()
    except Exception:
        pass
    if not any(c.name == 'NID' for c in cj):
        print("  aviso: no se obtuvo la cookie NID; es probable que Trends conteste 429")
    return op


def json_de(texto):
    return json.loads(texto[texto.index("{"):])


def lote(op, keywords, geo, periodo, reintentos=3):
    """Serie semanal de hasta 5 términos. Devuelve [{time, value:[...]}] o None."""
    req = {"comparisonItem": [{"keyword": k, "geo": geo, "time": periodo} for k in keywords],
           "category": 0, "property": ""}
    u = ("https://trends.google.es/trends/api/explore?hl=es&tz=-120&req="
         + urllib.parse.quote(json.dumps(req)))
    for intento in range(reintentos):
        try:
            j = json_de(op.open(u, timeout=25).read().decode())
            w = [x for x in j["widgets"] if x["id"] == "TIMESERIES"][0]
            time.sleep(1.5)
            u2 = ("https://trends.google.es/trends/api/widgetdata/multiline?hl=es&tz=-120&req="
                  + urllib.parse.quote(json.dumps(w["request"])) + "&token=" + w["token"])
            return json_de(op.open(u2, timeout=25).read().decode())["default"]["timelineData"]
        except Exception as e:
            espera = 5 * (intento + 1)
            print(f"  reintento {intento+1}/{reintentos} en {espera}s ({type(e).__name__})")
            time.sleep(espera)
    return None


def indice_mensual(serie, col):
    """Media del mismo mes en todos los años -> índice 100 = mes medio."""
    por_mes = defaultdict(list)
    for p in serie:
        m = time.gmtime(int(p["time"])).tm_mon
        por_mes[m].append(p["value"][col])
    medias = {m: sum(v)/len(v) for m, v in por_mes.items()}
    media = sum(medias.values()) / len(medias) if medias else 0
    return ({m: round(v/media*100) for m, v in medias.items()} if media else {},
            round(media, 1))


def terminos_de_la_cuenta(hoja, marca, top, remoto):
    """Los que más convierten, leídos del archivo de estacionalidad."""
    import os, re, subprocess, tempfile, openpyxl
    m = re.search(r'/spreadsheets/d/([A-Za-z0-9_-]{20,})', hoja)
    fid = m.group(1) if m else hoja.strip()
    tmp = os.path.join(tempfile.mkdtemp(), 'h.xlsx')
    subprocess.run(['rclone', 'backend', 'copyid', remoto, fid, tmp,
                    '--drive-export-formats', 'xlsx'], capture_output=True)
    if not os.path.exists(tmp):
        sys.exit("✗ rclone no pudo bajar el archivo de estacionalidad")
    wb = openpyxl.load_workbook(tmp, read_only=True, data_only=True)
    hoja_t = next((n for n in ('terminos-mes', 'datos-google-terminos') if n in wb.sheetnames), None)
    if not hoja_t:
        sys.exit(f"✗ No hay pestaña de términos. El archivo tiene: {', '.join(wb.sheetnames)}")
    cab, acum = None, defaultdict(lambda: defaultdict(float))
    for f in wb[hoja_t].iter_rows(values_only=True):
        if cab is None:
            cab = [str(c) for c in f]; continue
        d = dict(zip(cab, f))
        t = str(d.get('termino') or '').lower().strip()
        if not t or any(p in t for p in marca):
            continue
        acum[t]['conv'] += float(d.get('conversiones') or 0)
        acum[t]['clics'] += float(d.get('clics') or 0)
    orden = sorted(acum.items(), key=lambda x: (-x[1]['conv'], -x[1]['clics']))
    return [t for t, _ in orden[:top]], acum


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('hoja', nargs='?', help='URL o id del archivo de estacionalidad')
    ap.add_argument('--terminos', help='lista separada por comas, en vez de leer la hoja')
    ap.add_argument('--marca', default='', help='palabras de la marca, que no se consultan')
    ap.add_argument('--top', type=int, default=8)
    ap.add_argument('--geo', default='ES')
    ap.add_argument('--periodo', default='today 5-y')
    ap.add_argument('--remoto', default='gdrive:')
    a = ap.parse_args()

    marca = [p.strip().lower() for p in a.marca.split(',') if p.strip()]
    if a.terminos:
        terminos, acum = [t.strip() for t in a.terminos.split(',') if t.strip()], {}
    elif a.hoja:
        terminos, acum = terminos_de_la_cuenta(a.hoja, marca, a.top, a.remoto)
    else:
        sys.exit(__doc__)
    if not terminos:
        sys.exit("✗ No hay términos que consultar")

    # El ancla es el de más clics: el más estable y con más volumen
    ancla = max(terminos, key=lambda t: acum.get(t, {}).get('clics', 0)) if acum else terminos[0]
    resto = [t for t in terminos if t != ancla]
    print(f"Google Trends · {a.geo} · {a.periodo}")
    print(f"Ancla: «{ancla}» (va en todos los lotes para que los índices sean comparables)")
    print(f"{len(terminos)} términos en {-(-len(resto)//4)} lote(s)\n")

    op = sesion(a.geo)
    salida, nivel_ancla = {}, None
    for i in range(0, len(resto), 4):
        grupo = [ancla] + resto[i:i+4]
        print(f"  lote {i//4+1}: {', '.join(grupo[1:])}")
        s = lote(op, grupo, a.geo, a.periodo)
        if not s:
            print("    (sin respuesta de Trends; se salta)")
            continue
        idx_a, med_a = indice_mensual(s, 0)
        if nivel_ancla is None:
            nivel_ancla, salida[ancla] = med_a, (idx_a, 100.0)
        for j, k in enumerate(grupo[1:], start=1):
            idx, med = indice_mensual(s, j)
            rel = round(med / med_a * 100, 1) if med_a else 0   # volumen relativo al ancla
            salida[k] = (idx, rel)
        time.sleep(4)

    print(f"\n{'='*74}\nÍNDICE POR MES (100 = mes medio de ESE término)")
    print(f"{'término':<34}" + "".join(f"{m:>5}" for m in MESES) + "   vol")
    for k, (idx, rel) in salida.items():
        if not idx or all(v == 0 for v in idx.values()):
            continue
        fila = "".join(f"{idx.get(m, 0):>5}" for m in range(1, 13))
        print(f"{k[:33]:<34}{fila}  {rel:>5.0f}")
    sin = [k for k, (i, _) in salida.items() if not i or all(v == 0 for v in i.values())]
    if sin:
        print(f"\nSin volumen suficiente en Trends (devuelve ceros): {', '.join(sin)}")
        print("Eso no significa que no se busquen: significa que están por debajo del umbral que")
        print("Trends publica. Para esos, manda el dato de la cuenta.")
    print("\n«vol» = volumen relativo al ancla (ancla = 100). Compara tamaños entre términos.")
    print("Trends mide TODO el mercado del país: si difiere de la cuenta, la cuenta manda para")
    print("decidir presupuesto, y Trends sirve para saber si el patrón es de años o de este año.")


if __name__ == '__main__':
    main()
