#!/usr/bin/env python3
"""Piezas comunes del modo rápido de estáticos (`estaticos-meta` y `variaciones-estaticos-meta`).

Por qué existe (consejo, 13-09-2026): las dos skills repetían a mano lo mismo en cada tanda —rutas
del cliente, número de tanda, dónde cae la descarga de Chrome, qué ficheros son de ESTA tanda— y
cada repetición era un viaje más al navegador o a Drive. Aquí vive una sola vez y lo usan
`preparar_tanda.py`, `recoger_png.py`, `cronometro_tanda.py` y `cerrar_tanda.py`.

No se ejecuta solo: se importa.
"""
import csv, datetime as dt, glob, json, os, re, subprocess

CLIENTES = os.path.expanduser("~/Desktop/CLIENTES")
# Carpeta de descargas de Chrome en esta máquina (ver estaticos-meta/SKILL.md §Fase 4).
# Carpeta donde Chrome deja las descargas. En el Mac de Dirección es «Cliente 25»; en cualquier otro
# ordenador (Windows incluido) es la carpeta Descargas normal. CHROME_DESCARGAS manda sobre las dos.
_CHAU = os.path.expanduser("~/Desktop/Cliente 25")
DESCARGAS = os.environ.get("CHROME_DESCARGAS") or (_CHAU if os.path.isdir(_CHAU) else os.path.expanduser("~/Downloads"))
SKILLS = os.path.expanduser("~/.claude/skills")


def dir_cliente(cli):
    return os.path.join(CLIENTES, cli)


def dir_insumos(cli):
    return os.path.join(dir_cliente(cli), "Insumos")


def dir_salida(cli):
    """Destino local de los PNG: `Ads/GPT/`, sin subcarpetas (regla de Dirección)."""
    d = os.path.join(dir_cliente(cli), "Ads", "GPT")
    os.makedirs(d, exist_ok=True)
    return d


def tanda_local_siguiente(cli):
    """Número provisional de tanda leyendo SOLO lo local. El definitivo lo fija `cerrar_tanda.py`
    contra Drive justo antes de subir: así no hace falta entrar a Drive al empezar."""
    # Solo gastan número las tandas con algo PRODUCIDO: piezas, specs o un registro con piezas.
    # PROGRESO, TIEMPOS y manifiesto no cuentan: un `preparar_tanda.py` que falla o se repite
    # no debe saltarse números (pasó en la prueba del 13-09-2026: tres intentos, Tanda 3).
    usados = [0]
    for f in glob.glob(os.path.join(dir_cliente(cli), "Ads", "GPT", "**", "*"), recursive=True):
        if f"{os.sep}_auditoria{os.sep}" in f:
            continue  # `_auditoria/Tanda<N>/` la crea preparar_tanda.py antes de producir nada
        nombre = os.path.basename(f)
        m = re.search(r"_Tanda(\d+)_.*\.(png|jpe?g)$|^specs_Tanda(\d+)\.md$|^Tanda[ _-]?(\d+)$", nombre, re.I)
        if m:
            usados.append(int(next(g for g in m.groups() if g and g.isdigit())))
        m = re.match(r"^\.registro-Tanda(\d+)\.json$", nombre)
        if m and json.load(open(f, encoding="utf-8")):
            usados.append(int(m.group(1)))
    return max(usados) + 1


def fichero_tiempos(cli, n):
    return os.path.join(dir_salida(cli), f"TIEMPOS-Tanda{n}.csv")


def marcar(cli, n, evento, pieza="", nota=""):
    """Apunta un evento con hora. Es lo que permite medir dónde se va el tiempo de verdad."""
    p = fichero_tiempos(cli, n)
    nuevo = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if nuevo:
            w.writerow(["ts", "evento", "pieza", "nota"])
        w.writerow([dt.datetime.now().isoformat(timespec="seconds"), evento, pieza, nota])


def registro(cli, n):
    """Lista de ficheros que pertenecen a ESTA tanda (nombre base, sin `_PEND`).
    Hace falta porque las variaciones se llaman `Madre<m>_VAR<v>_…` sin número de tanda y conviven en
    `Ads/GPT/` con las de tandas anteriores: sin registro se resubirían las viejas."""
    p = os.path.join(dir_salida(cli), f".registro-Tanda{n}.json")
    datos = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
    return p, datos


def registrar(cli, n, nombre):
    p, datos = registro(cli, n)
    base = quitar_pend(nombre)
    if base not in datos:
        datos.append(base)
        json.dump(datos, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def desregistrar(cli, n, nombre):
    p, datos = registro(cli, n)
    base = quitar_pend(nombre)
    if base in datos:
        datos.remove(base)
        json.dump(datos, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# Naming de variaciones (Dirección, 14-09-2026): de qué pieza madre sale, qué variación, qué formato,
# qué versión y qué ratio, todo en el nombre. Antes era `VAR<n>_<formato>_<angulo>_<ratio>`: no decía
# la madre y cada ronda nueva se llamaba igual que la anterior.
#   Madre<m>_VAR<v>_<formato>_<angulo>_v<k>_<1x1|9x16>[_PEND].png
VAR_RE = re.compile(r"^Madre(\d+)_VAR(\d+)_([a-z0-9-]+)_([a-z0-9-]+)_v(\d+)_(1x1|9x16)(_PEND)?\.png$")


def partes_var(nombre):
    """(madre, var, formato, angulo, version, ratio) o None si el nombre no sigue el naming."""
    m = VAR_RE.match(nombre)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), m.group(3), m.group(4), int(m.group(5)), m.group(6)


def quitar_pend(nombre):
    raiz, ext = os.path.splitext(nombre)
    return (raiz[:-5] if raiz.endswith("_PEND") else raiz) + ext


def actual_en_disco(carpeta, base):
    """Devuelve el fichero vivo de una pieza: `base.png` o `base_PEND.png`."""
    raiz, ext = os.path.splitext(base)
    for c in (base, f"{raiz}_PEND{ext}"):
        if os.path.exists(os.path.join(carpeta, c)):
            return c
    return None


def run(args, timeout=180):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout.strip().splitlines() if r.returncode == 0 else None


def drive_base(cli):
    """`gdrive:i_<C>/c_<C>/` detectando la subcarpeta interna (misma lógica que `estado_cliente.py`).
    Devuelve None si el cliente no existe en Drive: la carpeta la crea Operaciones, nunca el agente."""
    raiz = f"gdrive:i_{cli}/"
    dentro = run(["rclone", "lsf", "--dirs-only", raiz])
    if dentro is None:
        return None
    dentro = [d.rstrip("/") for d in dentro]
    if f"c_{cli}" in dentro:
        return raiz + f"c_{cli}/"
    c = [d for d in dentro if d.startswith("c_")]
    if c:
        return raiz + c[0] + "/"
    return raiz if any(d.startswith(("0.", "1.", "2.")) for d in dentro) else None
