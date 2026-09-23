#!/usr/bin/env python3
"""Instala las skills de este paquete en el agente que tenga la máquina.

Lo ejecuta Claude cuando alguien le pasa la URL del repo. No hace falta saber nada:
detecta el agente, copia las skills, comprueba lo que falta y lo dice en castellano.

  python3 instalar.py            # instala
  python3 instalar.py --revisar  # solo dice qué falta, sin tocar nada
"""
import argparse, os, shutil, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))

# Dónde guarda las skills cada agente. Se instala en TODOS los que estén presentes.
DESTINOS = [
    ("Claude Code", "~/.claude/skills"),
    ("Codex",       "~/.codex/skills"),
    ("Cursor",      "~/.cursor/skills"),
    ("agentes varios", "~/.agents/skills"),
]

# Lo que hace falta para trabajar, por herramienta. `comprobar` devuelve True si está lista.
def _hay(cmd):
    return shutil.which(cmd) is not None

def _rclone_ok():
    if not _hay("rclone"):
        return False
    r = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True)
    return "gdrive:" in r.stdout

def _py(mod):
    return subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True).returncode == 0

REQUISITOS = [
    ("Python 3",  lambda: sys.version_info >= (3, 9), "Ya viene en el Mac. Si falla: brew install python"),
    ("rclone",    lambda: _hay("rclone"),  "brew install rclone"),
    ("Drive conectado", _rclone_ok,        "rclone config → n → nombre `gdrive` → drive → y entrar con la cuenta de Flowboost"),
    ("openpyxl",  lambda: _py("openpyxl"), "pip3 install openpyxl   (hojas de reportes)"),
    ("ffmpeg",    lambda: _hay("ffmpeg"),  "brew install ffmpeg     (solo para editar vídeo)"),
]

# Paquete de VÍDEO: la edición necesita bastante más que ffmpeg. La lista completa y el paso a paso están
# en skills/editar-vsl-cliente/INSTALACION.md; aquí solo se comprueba lo imprescindible para arrancar.
if os.path.basename(AQUI).endswith("-video"):
    REQUISITOS += [
        ("librerías de edición (numpy, pillow, imageio-ffmpeg, svg.path, opencv, faster-whisper)",
         lambda: all(_py(m) for m in ("numpy", "PIL", "imageio_ffmpeg", "svg.path", "cv2", "faster_whisper")),
         "python3 -m pip install --user numpy pillow imageio-ffmpeg svg.path opencv-python-headless faster-whisper static-ffmpeg"),
        ("ffprobe", lambda: _hay("ffprobe") or os.path.exists(os.path.expanduser("~/.local/bin/ffprobe")),
         "ver INSTALACION.md, paso 4"),
        ("ffmpeg-skill (QC y checks de Reels)",
         lambda: os.path.isfile(os.path.expanduser("~/.claude/tools/ffmpeg-skill/scripts/check.py")),
         "git clone https://github.com/kajisho5/ffmpeg-skill.git ~/.claude/tools/ffmpeg-skill"),
        ("MoneyPrinterTurbo (b-roll)",
         lambda: os.path.isfile(os.path.expanduser("~/Desktop/MoneyPrinterTurbo/.venv/bin/python")),
         "INSTALACION.md, paso 8"),
    ]


def area():
    """El nombre del área a partir del nombre de la carpeta."""
    n = os.path.basename(AQUI)
    return n.replace("flowboost-skills-", "") if n.startswith("flowboost-skills-") else n


def skills_del_paquete():
    d = os.path.join(AQUI, "skills")
    if not os.path.isdir(d):
        sys.exit("⛔ Aquí no hay carpeta `skills/`. ¿Se clonó el repo entero?")
    return sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)))


def destinos_presentes():
    out = []
    for nombre, ruta in DESTINOS:
        p = os.path.expanduser(ruta)
        # Existe la carpeta del agente (aunque aún no tenga skills)
        if os.path.isdir(os.path.dirname(p)):
            out.append((nombre, p))
    return out


def revisar():
    print(f"\n  PAQUETE: {area().upper()}")
    print(f"  {len(skills_del_paquete())} skills: {', '.join(skills_del_paquete())}\n")
    print("  Lo que hace falta en este ordenador:\n")
    faltan = []
    for nombre, test, arreglo in REQUISITOS:
        try:
            ok = test()
        except Exception:
            ok = False
        print(f"    {'✅' if ok else '⛔'}  {nombre}")
        if not ok:
            faltan.append((nombre, arreglo))
    if faltan:
        print("\n  Para arreglarlo:")
        for nombre, arreglo in faltan:
            print(f"    · {nombre}: {arreglo}")
    else:
        print("\n  Todo listo.")
    return faltan


def instalar():
    skills = skills_del_paquete()
    destinos = destinos_presentes()
    if not destinos:
        destinos = [("Claude Code", os.path.expanduser("~/.claude/skills"))]

    print(f"\n  Instalando el paquete {area().upper()} ({len(skills)} skills)\n")
    for nombre, dest in destinos:
        os.makedirs(dest, exist_ok=True)
        for s in skills:
            org = os.path.join(AQUI, "skills", s)
            dst = os.path.join(dest, s)
            if os.path.islink(dst):
                os.unlink(dst)          # nunca dejar enlaces: se rompen al mover la carpeta
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(org, dst, symlinks=False)
        print(f"    ✅ {nombre}: {dest}")

    # Las skills llaman a los scripts por su ruta absoluta. Se replica esa estructura, si no
    # `marcar_etapa.py`, `avisar.py` y compañía fallan con «no such file».
    herr = os.path.join(AQUI, "herramientas")
    if os.path.isdir(herr):
        raiz = os.path.expanduser("~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost")
        for sub in os.listdir(herr):
            org = os.path.join(herr, sub)
            dst = os.path.join(raiz, sub)
            if not os.path.isdir(org):
                continue
            os.makedirs(dst, exist_ok=True)
            n = 0
            for r, _, fs in os.walk(org):
                rel = os.path.relpath(r, org)
                d2 = os.path.join(dst, rel) if rel != "." else dst
                os.makedirs(d2, exist_ok=True)
                for f in fs:
                    # No se pisa lo que ya haya: si esta persona ya tenía el sistema, manda lo suyo.
                    if not os.path.exists(os.path.join(d2, f)):
                        shutil.copy2(os.path.join(r, f), os.path.join(d2, f)); n += 1
            print(f"    ✅ {sub}: {n} ficheros en ~/Desktop/FLOWBOOST-BACKUP-MAC/…/{sub}")

    print()
    faltan = revisar()

    # ¿Están los paquetes hermanos que este menciona? Si no, algunas rutas no resolverán.
    import json
    pj = os.path.join(AQUI, "paquete.json")
    necesita = json.load(open(pj, encoding="utf-8")).get("necesita", []) if os.path.isfile(pj) else []
    instalados = set()
    for _, d in destinos:
        if os.path.isdir(d):
            instalados |= set(os.listdir(d))
    AREA_SKILL = {"fundamentos": "fundamentos-copy", "meta-ads": "gestion-cuenta-meta",
                  "creatividades": "estaticos-meta", "guiones": "guiones-egc",
                  "video": "editar-vsl-cliente", "landing": "publicar-landing",
                  "onboarding": "brief-desde-onboarding", "direccion": "funnel"}
    sin = [a for a in necesita if AREA_SKILL.get(a) not in instalados]

    print("\n  ─────────────────────────────────────────────")
    if area() != "fundamentos" and "fundamentos-copy" not in instalados:
        print("  ⚠️  FALTA EL PAQUETE BASE. Sin él las skills funcionan a medias y NO avisan.")
        print("      Instálalo también: el repo `flowboost-skills-fundamentos`.")
    if sin:
        print(f"  ℹ️  Este paquete menciona ficheros de: {', '.join(sin)}.")
        print("      No es obligatorio: sin ellos, esas referencias concretas no se pueden abrir,")
        print("      pero el resto funciona. Si trabajas también esas áreas, instálalos.")
    print("  Cuando termines, dile a Claude: «guíame en la primera configuración»")
    if area() == "video":
        print("  Para EDITAR: sigue skills/editar-vsl-cliente/INSTALACION.md y comprueba con")
        print("      python3 ~/.claude/skills/editar-vsl-cliente/scripts/comprobar_entorno_edicion.py")
    print("  ─────────────────────────────────────────────\n")
    return 1 if faltan else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--revisar", action="store_true", help="solo comprobar, sin instalar")
    a = ap.parse_args()
    if a.revisar:
        sys.exit(1 if revisar() else 0)
    sys.exit(instalar())
