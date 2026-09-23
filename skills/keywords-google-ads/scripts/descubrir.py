#!/usr/bin/env python3
"""Lo que se busca en el sector y la cuenta NO recibe, según Google Trends.

    python3 descubrir.py --semillas "adiccion,dejar de beber" --excluir "centro,clinica" \
        --hoja "<URL del archivo de estacionalidad>" --marca "cliente"

Por cada concepto, Trends devuelve las búsquedas RELACIONADAS (las más buscadas junto a él) y las
que están EN AUMENTO. Cruzadas con los términos que la cuenta ya recibe, queda lo que nadie trabaja.

Filtra el ruido que siempre trae Trends (series, canciones, «qué es…») y, con --excluir, lo que el
servicio no puede cumplir. Si Trends no responde, LO DICE y sale con error: nunca imprime
«la cuenta ya lo cubre» por falta de datos.

TODO lo que salga se revisa a mano antes de proponerlo: el cruce con la cuenta es aproximado.
"""
import argparse, http.cookiejar, json, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from comun import VACIAS, lista, norm

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140 Safari/537")

# Lo que Trends pone arriba y no es un cliente de nadie: contenido, no intención de contratar
RUIDO = re.compile(
    r'\b(que es|significado|definicion|sinonimo|pelicula|serie|capitulo|temporada|reparto|actor|'
    r'actriz|dailymotion|netflix|completa|online gratis|libro|cancion|letra|frases|memes|wikipedia|'
    r'rae|pdf|documental|trailer|episodio|ver online)\b', re.I)


def sesion(geo):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "es-ES,es;q=0.9")]
    try:
        op.open(f"https://trends.google.es/trends/explore?geo={geo}", timeout=25).read()
    except Exception:
        pass
    return op


def J(t):
    return json.loads(t[t.index("{"):])


def relacionadas(op, termino, geo, periodo):
    """(top, en_aumento) o None si Trends no respondió."""
    req = {"comparisonItem": [{"keyword": termino, "geo": geo, "time": periodo}],
           "category": 0, "property": ""}
    u = ("https://trends.google.es/trends/api/explore?hl=es&tz=-120&req="
         + urllib.parse.quote(json.dumps(req)))
    for i in range(3):
        try:
            j = J(op.open(u, timeout=25).read().decode())
            w = [x for x in j["widgets"] if x["id"] == "RELATED_QUERIES"]
            if not w:
                return [], []
            time.sleep(2)
            u2 = ("https://trends.google.es/trends/api/widgetdata/relatedsearches?hl=es&tz=-120&req="
                  + urllib.parse.quote(json.dumps(w[0]["request"])) + "&token=" + w[0]["token"])
            d = J(op.open(u2, timeout=25).read().decode())["default"]["rankedList"]
            top = [(x["query"], x.get("formattedValue", "")) for x in d[0]["rankedKeyword"]] if d else []
            sube = [(x["query"], x.get("formattedValue", "")) for x in d[1]["rankedKeyword"]] if len(d) > 1 else []
            return top, sube
        except Exception as e:
            print(f"    reintento {i+1}/3 ({type(e).__name__}); espero {5*(i+1)} s")
            time.sleep(5 * (i + 1))
    return None


def terminos_de_la_cuenta(hoja, marca, remoto):
    from comun import bajar_archivo, leer_pestana
    filas, _ = leer_pestana(bajar_archivo(hoja, remoto), ('terminos-mes', 'datos-google-terminos'))
    ya = set()
    for f in filas:
        t = norm(f.get('termino'))
        if t and not any(p in t for p in marca):
            ya.add(t)
    return ya


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--semillas', required=True, help='conceptos del servicio, separados por comas')
    ap.add_argument('--hoja', help='URL del archivo de estacionalidad, para cruzar con lo que ya recibe')
    ap.add_argument('--marca', default='')
    ap.add_argument('--excluir', default='', help='lo que el servicio NO ofrece')
    ap.add_argument('--ruido', default='', help='palabras extra a descartar (famosos, series del sector…)')
    ap.add_argument('--geo', default='ES')
    ap.add_argument('--periodo', default='today 12-m')
    ap.add_argument('--remoto', default='gdrive:')
    a = ap.parse_args()

    marca, excluir, ruido = lista(a.marca), lista(a.excluir), lista(a.ruido)
    semillas = [s.strip() for s in a.semillas.split(',') if s.strip()]
    ya = terminos_de_la_cuenta(a.hoja, marca, a.remoto) if a.hoja else set()
    if a.hoja:
        print(f"La cuenta ya recibe {len(ya)} términos distintos (se cruzan con lo que salga)\n")

    def util(q):
        n = norm(q)
        if RUIDO.search(n) or any(r in n for r in ruido):
            return False
        return not any(x in n for x in excluir)

    def cubierto(q):
        """¿La cuenta ya recibe esto o algo muy parecido?"""
        n = norm(q)
        if n in ya:
            return True
        pal = {p for p in n.split() if p not in VACIAS}
        if not pal:
            return False
        for t in ya:
            tp = {p for p in t.split() if p not in VACIAS}
            if pal <= tp or (len(pal) >= 3 and len(pal & tp) >= 2):
                return True
        return False

    op = sesion(a.geo)
    top_all, sube_all, fallos = defaultdict(list), defaultdict(list), []
    for s in semillas:
        print(f"  consultando «{s}»…")
        r = relacionadas(op, s, a.geo, a.periodo)
        if r is None:
            fallos.append(s); continue
        for q, v in r[0]:
            top_all[q].append((s, v))
        for q, v in r[1]:
            sube_all[q].append((s, v))
        time.sleep(4)
    if len(fallos) == len(semillas):
        sys.exit("✗ Trends no respondió a ninguna semilla (suele ser 429). Espera 10-15 minutos y reintenta. "
                 "No hay conclusión posible.")
    if fallos:
        print(f"⚠️  Sin respuesta para: {', '.join(fallos)}. Lo que sigue NO las incluye.")

    def fuerza(apar):
        return max((int(v) for _, v in apar if str(v).isdigit()), default=0)

    print(f"\n{'='*78}\nLO QUE SE BUSCA EN EL SECTOR Y LA CUENTA NO RECIBE\n{'='*78}")
    print("\n▸ De las más buscadas junto a cada concepto:")
    n = 0
    for q, apar in sorted(top_all.items(), key=lambda x: -fuerza(x[1])):
        if not util(q) or (ya and cubierto(q)):
            continue
        print(f"   {q:<44} {fuerza(apar):>3}   (junto a: {apar[0][0]})")
        n += 1
        if n >= 15:
            break
    if not n:
        print("   (nada por encima del ruido" + (" que la cuenta no reciba ya)" if ya else ")"))

    print("\n▸ En aumento ahora mismo:")
    n = 0
    for q, apar in sube_all.items():
        if not util(q):
            continue
        print(f"   {q:<44} {apar[0][1]:<16}" + (" · ya la recibe" if ya and cubierto(q) else ""))
        n += 1
        if n >= 15:
            break
    if not n:
        print("   (nada relevante por encima del ruido)")
    print("\nRevisar a mano antes de proponer nada: que encaje con el servicio y que la intención sea de contratar.")


if __name__ == '__main__':
    main()
