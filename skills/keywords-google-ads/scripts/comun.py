#!/usr/bin/env python3
"""Lo que comparten todos los scripts: normalizar texto, bajar el archivo, leer pestañas, familias.

Vive aquí para que un fallo se arregle una vez. Antes cada script tenía su copia y, por ejemplo,
ninguna quitaba las tildes: `'clinica' in 'clínica privada'` daba False y el --excluir dejaba pasar
lo que tenía que parar.
"""
import json, os, re, subprocess, sys, tempfile, unicodedata
from collections import defaultdict

MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

# Palabras que no definen nada: aparecen en todo
VACIAS = {'de', 'la', 'el', 'en', 'y', 'a', 'para', 'con', 'por', 'que', 'los', 'las', 'un',
          'una', 'del', 'al', 'como', 'mi', 'me', 'se', 'es', 'no', 'si', 'lo', 'su', 'mas',
          'o', 'sin', 'sobre', 'te', 'tu', 'yo', 'e', 'u'}


def norm(s):
    """Minúsculas, sin tildes, espacios normalizados. Se aplica a LOS DOS lados de cada comparación."""
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.lower().split())


def lista(csv):
    """'a, B ,c' -> ['a','b','c'] ya normalizados."""
    return [norm(x) for x in str(csv or '').split(',') if x.strip()]


def contiene(termino, palabras):
    """¿El término (normalizado) contiene alguna de las palabras (normalizadas)?"""
    t = norm(termino)
    return any(p in t for p in palabras)


def resolver_id(txt):
    m = re.search(r'/spreadsheets/d/([A-Za-z0-9_-]{20,})', txt)
    return m.group(1) if m else txt.strip()


def bajar_archivo(hoja, remoto='gdrive:'):
    """Baja el archivo de estacionalidad como xlsx. Si falla, dice POR QUÉ y qué hacer."""
    fid = resolver_id(hoja)
    destino = os.path.join(tempfile.mkdtemp(), 'estacionalidad.xlsx')
    r = subprocess.run(['rclone', 'backend', 'copyid', remoto, fid, destino,
                        '--drive-export-formats', 'xlsx'], capture_output=True, text=True)
    if not os.path.exists(destino) or os.path.getsize(destino) == 0:
        err = (r.stderr or '').strip()
        pista = ("  → Comprueba `rclone listremotes`: tiene que salir el remoto que has pasado "
                 f"({remoto}).\n"
                 "  → El archivo lo crea el Ads Script en el Drive del Google que lo autorizó. Si ese\n"
                 "    Google no es el de rclone, hay que COMPARTIRLE el archivo (con ver basta).\n"
                 "  → Si la URL es la de la hoja de REPORTES, no es esta: busca en Drive\n"
                 "    «Estacionalidad - <Cliente>».")
        sys.exit(f"✗ rclone no pudo bajar el archivo {fid[:14]}…\n  rclone dijo: {err[-400:] or '(nada)'}\n{pista}")
    return destino


def leer_pestana(ruta, nombres):
    """Devuelve (filas como dicts, nombre usado). Prueba varios nombres, en orden."""
    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    nombre = next((n for n in nombres if n in wb.sheetnames), None)
    if not nombre:
        sys.exit(f"✗ No encuentro ninguna pestaña {nombres} en el archivo.\n"
                 f"  Tiene: {', '.join(wb.sheetnames)}\n"
                 "  → Si son las pestañas de un reporte (Reporte Meta, datos…), has pasado la hoja del\n"
                 "    cliente en vez del archivo «Estacionalidad - <Cliente>».\n"
                 "  → Si el archivo está vacío, el Ads Script aún no ha corrido: Vista previa en Google Ads.")
    filas = list(wb[nombre].iter_rows(values_only=True))
    if len(filas) < 2:
        sys.exit(f"✗ La pestaña «{nombre}» existe pero está vacía. Ejecuta el Ads Script (Vista previa).")
    cab = [str(c).strip() if c is not None else '' for c in filas[0]]
    return [dict(zip(cab, f)) for f in filas[1:] if any(v is not None for v in f)], nombre


def mes_de(v):
    """La columna `mes` llega como fecha; a veces como texto. Devuelve (año, mes) o None."""
    if hasattr(v, 'year'):
        return v.year, v.month
    try:
        a, m = str(v)[:10].split('-')[:2]
        return int(a), int(m)
    except Exception:
        return None


def cargar_familias(ruta):
    """{'familia': ['palabra', ...]} con todo normalizado. Si falta el fichero, avisa y sigue sin él."""
    if not ruta:
        return {}
    if not os.path.exists(ruta):
        print(f"⚠️  No existe {ruta}: sigo sin familias. Créalo con los conceptos de la landing:\n"
              '   {"dejar de beber": ["dejar de beber", "dejar el alcohol"], "online": ["online", "terapia"]}')
        return {}
    try:
        d = json.load(open(ruta, encoding='utf-8'))
    except Exception as e:
        sys.exit(f"✗ {ruta} no es un JSON válido: {e}")
    return {str(k): [norm(p) for p in v] for k, v in d.items()}


def familia_de(termino, familias):
    """UNA familia por término: la primera cuya palabra aparezca (el orden del JSON manda).
    Sin familias: la palabra más larga con contenido. Mismo criterio en todos los scripts."""
    t = norm(termino)
    if familias:
        for nombre, palabras in familias.items():
            if any(p in t for p in palabras):
                return nombre
        return 'resto'
    palabras = [p for p in re.findall(r'[a-z]+', t) if p not in VACIAS and len(p) > 3]
    return max(palabras, key=len) if palabras else '(sin clasificar)'


def agregar_terminos(filas, marca, excluir=()):
    """Suma por término normalizado. Devuelve (dict término->métricas, filas de marca fuera)."""
    T, n_marca = defaultdict(lambda: defaultdict(float)), 0
    for f in filas:
        t = norm(f.get('termino'))
        if not t:
            continue
        if marca and any(p in t for p in marca):
            n_marca += 1
            continue
        for c in ('clics', 'coste', 'conversiones', 'impresiones'):
            T[t][c] += float(f.get(c) or 0)
        T[t]['_excluido'] = 1.0 if excluir and any(x in t for x in excluir) else 0.0
    return T, n_marca


def fmt_n(n):
    """1234.5 -> '1.235' (miles con punto, sin decimales)."""
    return f"{n:,.0f}".replace(',', '.')
