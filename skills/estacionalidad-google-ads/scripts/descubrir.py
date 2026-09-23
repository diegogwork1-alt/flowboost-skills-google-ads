#!/usr/bin/env python3
"""Encuentra en Google Trends la demanda que la cuenta NO está capturando.

    python3 descubrir.py --semillas "adiccion,dejar de beber" --hoja "<URL estacionalidad>"
    python3 descubrir.py --semillas "adiccion" --marca "cliente"

No sirve para confirmar lo que ya se sabe (que «alcoholismo» es plano). Sirve para lo contrario:
por cada concepto del servicio, Trends devuelve las búsquedas RELACIONADAS y las que están
CRECIENDO. Cruzadas con los términos que la cuenta ya puja, lo que queda es **demanda real que
nadie está trabajando**.

Filtra el ruido que siempre trae Trends: nombres de famosos, títulos de series y películas,
preguntas informacionales («qué es…»), que aparecen arriba y no son clientes.
"""
import argparse, http.cookiejar, json, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140 Safari/537")

# Lo que Trends devuelve arriba y nunca es un cliente
RUIDO = re.compile(
    r'\b(que es|qué es|significado|definicion|definición|sinonimo|pelicula|película|serie|'
    r'capitulo|capítulo|temporada|reparto|actor|actriz|dailymotion|netflix|completa|online gratis|'
    r'libro|cancion|canción|letra|frases|memes|wikipedia|rae|ingles|inglés|test|pdf|'
    r'mi profesor|mi extraña|documental|programa)\b', re.I)
# Un nombre propio de persona famosa suele ir con apellido y sin palabra de servicio
PERSONA = re.compile(r'\b(joaquin|joaquín|prat|levy|andrea|hermano de|hijo de|mujer de)\b', re.I)


def sesion():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "es-ES,es;q=0.9")]
    try:
        op.open("https://trends.google.es/trends/explore?geo=ES", timeout=25).read()
    except Exception:
        pass
    return op


def J(t):
    return json.loads(t[t.index("{"):])


def relacionadas(op, termino, geo, periodo):
    """Devuelve (top, en_aumento) para un término."""
    req = {"comparisonItem": [{"keyword": termino, "geo": geo, "time": periodo}],
           "category": 0, "property": ""}
    u = ("https://trends.google.es/trends/api/explore?hl=es&tz=-120&req="
         + urllib.parse.quote(json.dumps(req)))
    for intento in range(3):
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
            time.sleep(5 * (intento + 1))
    return [], []


EXCLUIR = []   # lo rellena main() con --excluir


def util(q):
    """¿Es una búsqueda de alguien que podría contratar ESTE servicio, o es ruido?"""
    if RUIDO.search(q) or PERSONA.search(q):
        return False
    return not any(x in q.lower() for x in EXCLUIR)


def terminos_de_la_cuenta(hoja, marca, remoto):
    import os, subprocess, tempfile, openpyxl
    m = re.search(r'/spreadsheets/d/([A-Za-z0-9_-]{20,})', hoja)
    fid = m.group(1) if m else hoja.strip()
    tmp = os.path.join(tempfile.mkdtemp(), 'h.xlsx')
    subprocess.run(['rclone', 'backend', 'copyid', remoto, fid, tmp,
                    '--drive-export-formats', 'xlsx'], capture_output=True)
    if not os.path.exists(tmp):
        return set()
    wb = openpyxl.load_workbook(tmp, read_only=True, data_only=True)
    hoja_t = next((n for n in ('terminos-mes', 'datos-google-terminos') if n in wb.sheetnames), None)
    if not hoja_t:
        return set()
    cab, vistos = None, set()
    for f in wb[hoja_t].iter_rows(values_only=True):
        if cab is None:
            cab = [str(c) for c in f]; continue
        d = dict(zip(cab, f))
        t = str(d.get('termino') or '').lower().strip()
        if t and not any(p in t for p in marca):
            vistos.add(t)
    return vistos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--semillas', required=True, help='conceptos del servicio, separados por comas')
    ap.add_argument('--hoja', help='URL del archivo de estacionalidad, para cruzar con lo ya pujado')
    ap.add_argument('--marca', default='')
    ap.add_argument('--geo', default='ES')
    ap.add_argument('--periodo', default='today 12-m')
    ap.add_argument('--remoto', default='gdrive:')
    ap.add_argument('--excluir', default='', help='lo que el servicio NO ofrece')
    a = ap.parse_args()
    excluir = [p.strip().lower() for p in a.excluir.split(',') if p.strip()]

    global EXCLUIR
    EXCLUIR = excluir
    marca = [p.strip().lower() for p in a.marca.split(',') if p.strip()]
    semillas = [s.strip() for s in a.semillas.split(',') if s.strip()]
    ya = terminos_de_la_cuenta(a.hoja, marca, a.remoto) if a.hoja else set()
    if a.hoja:
        print(f"La cuenta ya puja {len(ya)} términos distintos\n")

    op = sesion()
    top_all, sube_all = defaultdict(list), defaultdict(list)
    for s in semillas:
        print(f"  consultando «{s}»…")
        top, sube = relacionadas(op, s, a.geo, a.periodo)
        for q, v in top:
            top_all[q].append((s, v))
        for q, v in sube:
            sube_all[q].append((s, v))
        time.sleep(4)

    def cubierto(q):
        """¿La cuenta ya recibe algo parecido?"""
        pal = set(q.lower().split())
        return any(len(pal & set(t.split())) >= 2 for t in ya)

    print(f"\n{'='*78}")
    print("DEMANDA QUE LA CUENTA NO ESTÁ CAPTURANDO")
    print(f"{'='*78}")

    print("\n▸ LAS MÁS BUSCADAS del sector que NO aparecen en la cuenta")
    n = 0
    for q, apar in sorted(top_all.items(), key=lambda x: -max(int(v) if str(v).isdigit() else 0 for _, v in x[1])):
        if not util(q) or (ya and cubierto(q)):
            continue
        fuerza = max(int(v) if str(v).isdigit() else 0 for _, v in apar)
        print(f"   {q:<44} {fuerza:>3}   (sale de: {apar[0][0]})")
        n += 1
        if n >= 15:
            break
    if not n:
        print("   (ninguna: la cuenta ya cubre lo que más se busca)")

    print("\n▸ EN AUMENTO — demanda creciendo ahora mismo")
    n = 0
    for q, apar in sube_all.items():
        if not util(q):
            continue
        v = apar[0][1]
        marca_ya = " · YA SE PUJA" if ya and cubierto(q) else ""
        print(f"   {q:<44} {v:<16}{marca_ya}")
        n += 1
        if n >= 15:
            break
    if not n:
        print("   (nada relevante por encima del ruido)")

    print("\nLas que salen sin marcar son términos con demanda real que hoy no se trabajan.")
    print("Antes de meterlos: comprobar que encajan con el servicio y mirar su intención.")


if __name__ == '__main__':
    main()
