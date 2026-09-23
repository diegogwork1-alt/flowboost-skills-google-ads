#!/usr/bin/env python3
"""Instala MoneyPrinterTurbo, que es de donde sale el B-ROLL de las skills de edición.

No va dentro del repo: es software de terceros (2,2 GB con sus vídeos descargados) y tiene su
propio proyecto público. Esto lo clona, instala lo que necesita y deja el `config.toml` listo
para que cada uno ponga SU clave de Pexels — que es gratis y se saca en dos minutos.

⚠️ Solo hace falta para EDITAR vídeo. Para guiones, copy o campañas, no.

  python3 instalar_moneyprinter.py            # avisa y pregunta
  python3 instalar_moneyprinter.py --si       # sin preguntar
  python3 instalar_moneyprinter.py --revisar  # solo mira si está
"""
import argparse, os, shutil, subprocess, sys

REPO = "https://github.com/harry0703/MoneyPrinterTurbo.git"
DESTINO = os.path.expanduser("~/Desktop/MoneyPrinterTurbo")


def estado():
    if not os.path.isdir(DESTINO):
        return "no está"
    cfg = os.path.join(DESTINO, "config.toml")
    if not os.path.isfile(cfg):
        return "clonado, sin configurar"
    t = open(cfg, encoding="utf-8", errors="ignore").read()
    # ¿hay alguna clave puesta? No se lee su valor, solo si la lista está vacía.
    for linea in t.split("\n"):
        if linea.strip().startswith(("pexels_api_keys", "pixabay_api_keys")):
            if "[]" not in linea.replace(" ", ""):
                return "listo"
    return "sin clave de Pexels"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--si", action="store_true")
    ap.add_argument("--revisar", action="store_true")
    a = ap.parse_args()

    e = estado()
    print(f"  MoneyPrinterTurbo: {e}")
    if e == "listo":
        print("  ✅ Nada que hacer.")
        return 0
    if a.revisar:
        return 1

    if e == "no está":
        print(f"\n  ⚠️  Hay que clonar MoneyPrinterTurbo (proyecto público de terceros).")
        print(f"     Va a: {DESTINO}")
        print("     Ocupa unos 200 MB al clonar, y crece según descargue b-roll.")
        print("     Solo hace falta si vas a EDITAR vídeo.")
        if not a.si:
            try:
                r = input("\n  ¿Lo instalo? (s/n): ").strip().lower()
            except EOFError:
                print("\n  (sin respuesta: no se instala. Usa --si)"); return 1
            if r not in ("s", "si", "sí", "y", "yes"):
                print("  No se instala."); return 1
        if not shutil.which("git"):
            print("  ⛔ Falta git."); return 1
        print("\n  ▸ Clonando…")
        if subprocess.run(["git", "clone", "--depth", "1", REPO, DESTINO]).returncode != 0:
            print("  ⛔ No se pudo clonar."); return 1

    cfg = os.path.join(DESTINO, "config.toml")
    ej = os.path.join(DESTINO, "config.example.toml")
    if not os.path.isfile(cfg) and os.path.isfile(ej):
        shutil.copy2(ej, cfg)
        print("  ▸ config.toml creado a partir del ejemplo")

    print(f"""
  ─────────────────────────────────────────────────────────
  FALTA TU CLAVE DE PEXELS (gratis, 2 minutos)

    1. Entra en  https://www.pexels.com/api/
    2. Regístrate y copia tu API key
    3. Ábrelo:   open -e {cfg}
    4. Busca la línea  pexels_api_keys = []
       y déjala así:   pexels_api_keys = ["TU-CLAVE"]
    5. Guarda

  Cada uno usa SU clave: son gratuitas y así no se comparten
  entre gente, que es lo que hace que Pexels las bloquee.
  ─────────────────────────────────────────────────────────
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
