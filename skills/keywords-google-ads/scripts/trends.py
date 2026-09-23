#!/usr/bin/env python3
"""Google Trends en lote: ¿cada concepto del servicio crece o se hunde, y tiene temporada?

    python3 trends.py --terminos "dejar de beber,terapia online,alcoholismo" --excluir "centro,clinica"
    python3 trends.py "<URL del archivo de estacionalidad>" --marca "cliente" --top 8 --excluir "…"

El primer modo consulta los conceptos que le das (lo normal: los de la landing). El segundo saca
de la cuenta los que más convierten y los convierte en conceptos cortos (quita ciudades y
arranques de frase, porque Trends no publica la cola larga).

CÓMO MIDE, y por qué así
- La TENDENCIA de cada término se calcula con el término CONSULTADO SOLO, en su propia escala
  0-100, comparando las últimas 52 semanas con las primeras 52. Nunca a partir de un lote con
  ancla: ahí los términos pequeños quedan en valores de 1-3 y el porcentaje sale del ruido
  (comprobado: el mismo término daba +69 % o +309 % según con quién fuera en el lote).
- El VOLUMEN relativo (`vol`) sí sale de lotes de 5 con un término ancla común, que es la única
  forma de comparar tamaños entre términos. Un `vol` por debajo de 10 no es fiable.
- El 429: la API interna contesta 429 a pelo. Abrir antes la portada deja la cookie NID, y con
  ella responde. Entre llamadas se espera; pedir deprisa vuelve a bloquear.
"""
import argparse, http.cookiejar, json, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from comun import MESES, lista, norm

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140 Safari/537")
CIUDADES = {'madrid', 'barcelona', 'valencia', 'sevilla', 'bilbao', 'zaragoza', 'malaga', 'murcia',
            'palma', 'alicante', 'cordoba', 'valladolid', 'vigo', 'gijon', 'granada', 'coruna',
            'santander', 'pamplona', 'donostia', 'san sebastian', 'espana', 'cerca de mi', 'cerca'}
ARRANQUES = ('como ', 'quiero ', 'necesito ', 'donde ', 'que ', 'el mejor ', 'mejor ', 'un ',
             'una ', 'los ', 'las ', 'me ')


def raiz(termino):
    """«tratamiento alcoholismo madrid» -> «tratamiento alcoholismo»: lo que Trends sí publica."""
    t = norm(termino)
    for a_ in ARRANQUES:
        if t.startswith(a_):
            t = t[len(a_):]
    for c in sorted(CIUDADES, key=len, reverse=True):
        t = re.sub(rf'\b{re.escape(c)}\b', '', t)
    return ' '.join(t.split()[:4])


def sesion(geo):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "es-ES,es;q=0.9"),
                     ("Accept", "text/html,application/xhtml+xml,*/*;q=0.8")]
    try:
        op.open(f"https://trends.google.es/trends/explore?geo={geo}", timeout=25).read()
    except Exception:
        pass
    if not any(c.name == 'NID' for c in cj):
        print("⚠️  No llegó la cookie NID: Trends contestará 429. Espera unos minutos y reintenta.")
    return op


def J(t):
    return json.loads(t[t.index("{"):])


def serie(op, keywords, geo, periodo, reintentos=3):
    """Serie semanal de 1-5 términos: lista de {time, value:[…], isPartial?} o None."""
    req = {"comparisonItem": [{"keyword": k, "geo": geo, "time": periodo} for k in keywords],
           "category": 0, "property": ""}
    u = ("https://trends.google.es/trends/api/explore?hl=es&tz=-120&req="
         + urllib.parse.quote(json.dumps(req)))
    for i in range(reintentos):
        try:
            j = J(op.open(u, timeout=25).read().decode())
            w = [x for x in j["widgets"] if x["id"] == "TIMESERIES"][0]
            time.sleep(1.5)
            u2 = ("https://trends.google.es/trends/api/widgetdata/multiline?hl=es&tz=-120&req="
                  + urllib.parse.quote(json.dumps(w["request"])) + "&token=" + w["token"])
            return J(op.open(u2, timeout=25).read().decode())["default"]["timelineData"]
        except Exception as e:
            print(f"    reintento {i+1}/{reintentos} ({type(e).__name__}); espero {5*(i+1)} s")
            time.sleep(5 * (i + 1))
    return None


def tendencia(valores):
    """(cambio %, estado): últimas 52 semanas frente a las primeras 52."""
    if len(valores) < 104:
        return None, 'corto'
    ini, fin = sum(valores[:52]) / 52, sum(valores[-52:]) / 52
    if ini == 0:
        return None, 'nuevo' if fin > 0 else 'vacio'
    return (fin / ini - 1) * 100, 'ok'


def indice_mensual(puntos, col):
    por_mes = defaultdict(list)
    for p in puntos:
        por_mes[time.gmtime(int(p["time"])).tm_mon].append(p["value"][col])
    medias = {m: sum(v) / len(v) for m, v in por_mes.items()}
    media = sum(medias.values()) / len(medias) if medias else 0
    return {m: round(v / media * 100) for m, v in medias.items()} if media else {}


def desde_la_cuenta(hoja, marca, top, remoto):
    from comun import agregar_terminos, bajar_archivo, leer_pestana
    filas, _ = leer_pestana(bajar_archivo(hoja, remoto), ('terminos-mes', 'datos-google-terminos'))
    T, _ = agregar_terminos(filas, marca)
    r = defaultdict(lambda: defaultdict(float))
    for t, v in T.items():
        k = raiz(t)
        if k:
            r[k]['conv'] += v['conversiones']; r[k]['clics'] += v['clics']; r[k]['n'] += 1
    orden = sorted(r.items(), key=lambda x: (-x[1]['conv'], -x[1]['clics']))[:top]
    print(f"{len(T)} términos de la cuenta → {len(r)} conceptos → los {len(orden)} que más convierten:")
    for k, v in orden:
        print(f"   {k:<34}{v['conv']:5.0f} conv · {v['n']:.0f} variantes")
    return [k for k, _ in orden]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('hoja', nargs='?', help='URL del archivo de estacionalidad (modo cuenta)')
    ap.add_argument('--terminos', help='conceptos separados por comas (modo normal)')
    ap.add_argument('--marca', default='')
    ap.add_argument('--excluir', default='', help='lo que el servicio NO ofrece: se descarta aunque crezca')
    ap.add_argument('--top', type=int, default=8, help='solo en modo cuenta: cuántos conceptos')
    ap.add_argument('--geo', default='ES', help='ES, o regional como ES-MD (Madrid)')
    ap.add_argument('--periodo', default='today 5-y')
    ap.add_argument('--remoto', default='gdrive:')
    a = ap.parse_args()

    marca, excluir = lista(a.marca), lista(a.excluir)
    if a.terminos:
        terminos = [t.strip() for t in a.terminos.split(',') if t.strip()]
    elif a.hoja:
        terminos = desde_la_cuenta(a.hoja, marca, a.top, a.remoto)
    else:
        sys.exit(__doc__)
    fuera = [t for t in terminos if any(x in norm(t) for x in excluir)]
    terminos = [t for t in terminos if t not in fuera]
    if fuera:
        print(f"Descartados por no encajar con el servicio: {', '.join(fuera)}")
    if not excluir:
        print("⚠️  Sin --excluir: lo que el servicio no ofrece (un centro físico, un ingreso…) saldrá\n"
              "   aquí aunque nunca pueda convertir.")
    if not terminos:
        sys.exit("✗ No queda ningún término que consultar.")

    op = sesion(a.geo)
    print(f"\nGoogle Trends · {a.geo} · {a.periodo} · {len(terminos)} términos, cada uno consultado solo "
          f"para su tendencia (+ lotes con ancla para el volumen)\n")

    # ── 1. Cada término SOLO: tendencia e índice mensual en su propia escala ──
    solo, fallos = {}, 0
    for t in terminos:
        print(f"  {t}…")
        s = serie(op, [t], a.geo, a.periodo)
        if not s:
            fallos += 1; continue
        pts = [p for p in s if not p.get("isPartial")]
        vals = [p["value"][0] for p in pts]
        cambio, estado = tendencia(vals)
        anual = defaultdict(list)
        for p in pts:
            anual[time.gmtime(int(p["time"])).tm_year].append(p["value"][0])
        solo[t] = {'cambio': cambio, 'estado': estado, 'idx': indice_mensual(pts, 0),
                   'anual': {y: sum(v) / len(v) for y, v in anual.items()}}
        time.sleep(3)
    if not solo:
        sys.exit(f"✗ Trends no respondió a ninguno de los {len(terminos)} términos ({fallos} fallos). "
                 "Suele ser 429: espera 10-15 minutos y vuelve a lanzarlo.")
    if fallos:
        print(f"⚠️  {fallos} término(s) sin respuesta de Trends: no salen en las tablas.")

    # ── 2. Lotes con ancla: volumen relativo ──
    vivos = [t for t in terminos if t in solo]
    ancla = max(vivos, key=lambda t: sum(solo[t]['anual'].values()) / max(len(solo[t]['anual']), 1))
    resto = [t for t in vivos if t != ancla]
    vol = {ancla: 100.0}
    for i in range(0, len(resto), 4):
        grupo = [ancla] + resto[i:i + 4]
        s = serie(op, grupo, a.geo, a.periodo)
        if not s:
            continue
        medias = [sum(p["value"][j] for p in s) / len(s) for j in range(len(grupo))]
        for j, k in enumerate(grupo[1:], 1):
            vol[k] = round(medias[j] / medias[0] * 100, 1) if medias[0] else 0
        time.sleep(4)

    # ── Salida ──
    anios = sorted({y for t in solo for y in solo[t]['anual']})
    print(f"\n{'='*78}\nTENDENCIA — últimas 52 semanas frente a las primeras 52 (cada término en su escala)")
    print(f"{'término':<30}{'cambio':>9}   {'vol':>5}   " + "".join(f"{y:>6}" for y in anios))
    poco = []
    for t in sorted(solo, key=lambda t: -(solo[t]['cambio'] if solo[t]['cambio'] is not None else -999)):
        d = solo[t]; v = vol.get(t, 0)
        if v and v < 10:
            poco.append(t)
        c = f"{d['cambio']:+.0f} %" if d['cambio'] is not None else d['estado']
        aviso = ' ⚠' if d['cambio'] is not None and abs(d['cambio']) >= 25 else ''
        print(f"{t[:29]:<30}{c:>9}{aviso:<3}{v:>5.0f}   " + "".join(f"{d['anual'].get(y, 0):>6.0f}" for y in anios))
    print(f"\n({anios[0]} y {anios[-1]} son parciales: la serie son 5 años hacia atrás desde hoy; por eso el cambio\n"
          " se mide con ventanas de 52 semanas y no comparando esos dos años. «nuevo» = sin volumen al principio.)")
    if poco:
        print("\nVolumen relativo por debajo de 10 (poco fiables, la escala de Trends los deja en ceros): "
              + ", ".join(poco))

    print(f"\n{'='*78}\nÍNDICE MENSUAL (100 = mes medio de ESE término; ±15 % no es una temporada)")
    print(f"{'término':<30}" + "".join(f"{m:>5}" for m in MESES))
    for t in solo:
        ix = solo[t]['idx']
        print(f"{t[:29]:<30}" + "".join(f"{ix.get(m, 0):>5}" for m in range(1, 13)))
    print(f"\n«vol» = tamaño respecto al ancla «{ancla}» (=100), el único dato comparable entre términos.\n"
          "Trends mide TODO el mercado del país: la cuenta manda para decidir presupuesto; Trends dice\n"
          "si el patrón es del mercado o lo fabricó la gestión, y hacia dónde va la demanda.")


if __name__ == '__main__':
    main()
