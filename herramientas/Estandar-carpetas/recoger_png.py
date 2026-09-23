#!/usr/bin/env python3
"""Recoge el PNG que acaba de bajar Chrome y lo deja listo para auditar, en UNA llamada:
espera a que termine la descarga → lo mueve a `Ads/GPT/` → lo normaliza a 1080 conservando la
credencial C2PA → mide las zonas seguras → lo apunta en el registro y en el cronómetro.

Por qué (consejo, 13-09-2026): eran cuatro pasos sueltos por imagen (mover, normalizar, medir,
anotar), por 18 imágenes y sus rondas. Además se auditaba a veces antes de normalizar, y
`zonas_seguras.py` no mide nada que no sea 1080: la compuerta no llegaba a medir.

Uso:
  python3 recoger_png.py "Cliente 04" Cliente 04_Tanda2_review-claim_miedo-a-la-obra_1x1.png --tanda 2 --pieza 03 --ronda 1
  python3 recoger_png.py "Cliente 13" Madre2_VAR1_review-claim_confianza_v1_9x16.png --tanda 3 --pieza Madre2_VAR1 --ronda 1 --skill variaciones-estaticos-meta

En variaciones el nombre tiene que ser `Madre<m>_VAR<v>_<formato>_<angulo>_v<k>_<1x1|9x16>.png`, con
`v<k>` = `--ronda`, y nunca pisa un fichero que ya existe (cada ronda es una versión nueva). Al
recoger la v<k>, las versiones anteriores de esa misma variación y ratio salen del registro (no se
suben a Drive, se quedan en local), salvo `--conservar-anteriores` (Dirección quiere quedarse con varias).

Imprime un JSON con la ruta final, el tamaño, si conserva C2PA y el veredicto de zonas seguras.
Sale con 1 si el fichero no llega (la descarga falló: se repite la descarga) o, en variaciones, si
el nombre no sigue el naming o ya existe (se corrige el nombre y se vuelve a descargar).
"""
import argparse, json, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tanda_lib as L


def esperar(nombre, segundos):
    """Chrome escribe `.crdownload` mientras baja y, si el nombre existe, añade ` (1)`."""
    raiz, ext = os.path.splitext(nombre)
    fin = time.time() + segundos
    while time.time() < fin:
        candidatos = [f for f in os.listdir(L.DESCARGAS)
                      if f.startswith(raiz) and f.endswith(ext) and not f.endswith(".crdownload")]
        if candidatos:
            p = max((os.path.join(L.DESCARGAS, f) for f in candidatos), key=os.path.getmtime)
            s1 = os.path.getsize(p); time.sleep(0.6)
            if s1 > 0 and s1 == os.path.getsize(p):
                return p
        time.sleep(0.8)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente"); ap.add_argument("nombre")
    ap.add_argument("--tanda", type=int, required=True)
    ap.add_argument("--pieza", default=""); ap.add_argument("--ronda", default="1")
    ap.add_argument("--skill", default="estaticos-meta")
    ap.add_argument("--esperar", type=int, default=45)
    ap.add_argument("--origen", help="ruta exacta si no cayó en la carpeta de descargas")
    ap.add_argument("--conservar-anteriores", action="store_true",
                    help="variaciones: no sacar del registro las versiones anteriores de esta variación y ratio")
    a = ap.parse_args()

    def fallo(motivo):
        print(json.dumps({"ok": False, "motivo": motivo}, ensure_ascii=False))
        sys.exit(1)

    salida = L.dir_salida(a.cliente)
    dst = os.path.join(salida, a.nombre)
    partes = None
    if a.skill == "variaciones-estaticos-meta":
        partes = L.partes_var(a.nombre)
        if not partes:
            fallo(f"{a.nombre} no sigue el naming Madre<m>_VAR<v>_<formato>_<angulo>_v<k>_<1x1|9x16>.png")
        if str(partes[4]) != str(a.ronda):
            fallo(f"{a.nombre} dice v{partes[4]} pero --ronda es {a.ronda}: la versión es la ronda")
        if L.actual_en_disco(salida, L.quitar_pend(a.nombre)):
            fallo(f"{a.nombre} ya existe en {salida}: una ronda nueva es v{partes[4] + 1}, no se pisa la anterior")

    src = os.path.expanduser(a.origen) if a.origen else esperar(a.nombre, a.esperar)
    if not src or not os.path.exists(src):
        fallo(f"no ha llegado {a.nombre} a {L.DESCARGAS}")

    shutil.move(src, dst)  # nunca se queda en Descargas

    scripts = os.path.join(L.SKILLS, a.skill, "scripts")
    norm = subprocess.run([sys.executable, os.path.join(scripts, "normalizar_png.py"), dst, "--json"],
                          capture_output=True, text=True)
    zonas = subprocess.run([sys.executable, os.path.join(scripts, "zonas_seguras.py"), dst, "--json"],
                           capture_output=True, text=True)

    def js(r):
        try:
            return json.loads(r.stdout)
        except Exception:
            return (r.stdout or r.stderr).strip()[-600:]

    from PIL import Image
    w, h = Image.open(dst).size
    fuera = []
    if partes and not a.conservar_anteriores:
        for b in L.registro(a.cliente, a.tanda)[1]:
            p = L.partes_var(b)
            if p and (p[0], p[1], p[5]) == (partes[0], partes[1], partes[5]) and p[4] < partes[4]:
                L.desregistrar(a.cliente, a.tanda, b)
                fuera.append(b)
    L.registrar(a.cliente, a.tanda, a.nombre)
    L.marcar(a.cliente, a.tanda, "gpt_imagen", a.pieza, f"ronda={a.ronda} {a.nombre}")
    print(json.dumps({"ok": True, "ruta": dst, "tamano": f"{w}x{h}", "normalizar": js(norm),
                      "zonas_seguras": js(zonas), "zonas_codigo": zonas.returncode,
                      "versiones_que_ya_no_se_suben": fuera},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
