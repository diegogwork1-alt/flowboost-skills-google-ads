#!/usr/bin/env python3
"""Renderiza HTML a PDF o PNG con Chrome headless y SIEMPRE lo cierra.

Por qué existe (07-09-2026): Chrome headless **genera el fichero y NO sale**. Catorce
render del PDF de la guía dejaron 45 procesos vivos y ~2,9 GB de RAM ocupados en el Mac
de Dirección. Un `subprocess.run(...)` sin timeout se queda colgado esperando a un proceso
que nunca termina; y sin perfil propio, además, se pisan entre ejecuciones.

Aquí Chrome se lanza en su propia sesión, se espera al FICHERO (no al proceso) y se mata
el árbol entero en un `finally`: salga bien, falle o se cuelgue, no queda nada corriendo
ni perfiles temporales tirados.

Uso:
  python3 render_chrome.py entrada.html salida.pdf
  python3 render_chrome.py entrada.html salida.png --size 1080x1920
"""
import argparse, os, shutil, signal, subprocess, sys, tempfile, time

WIN = os.name == "nt"
CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    # Windows (15-09-2026): antes solo se buscaba en rutas de Mac y en Windows no se encontraba Chrome
    os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
    os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    shutil.which("chrome") or "",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "", shutil.which("chromium") or "",
]


def find_chrome():
    for c in CHROMES:
        if c and os.path.exists(c):
            return c
    sys.exit("No se encontró Chrome/Chromium.")


def render(entrada, salida, size=None, espera=45, budget=12000):
    """Devuelve la ruta de salida. Mata Chrome pase lo que pase."""
    salida = os.path.abspath(salida)
    if os.path.exists(salida):
        os.unlink(salida)
    perfil = tempfile.mkdtemp(prefix="chrome-render-")
    import pathlib
    url = entrada if "://" in entrada else pathlib.Path(os.path.abspath(entrada)).as_uri()   # C:\… bien formado en Windows
    cmd = [find_chrome(), "--headless=old", "--disable-gpu", "--hide-scrollbars",
           "--no-first-run", "--no-default-browser-check",
           f"--user-data-dir={perfil}", f"--virtual-time-budget={budget}"]
    if salida.lower().endswith(".pdf"):
        cmd += ["--no-pdf-header-footer", f"--print-to-pdf={salida}"]
    else:
        cmd += [f"--screenshot={salida}", "--force-device-scale-factor=1"]
        if size:
            cmd += [f"--window-size={size}"]
    cmd.append(url)

    if WIN:
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)   # sesión propia → se puede matar el árbol
    try:
        # Se espera al FICHERO, no al proceso: Chrome headless a menudo no sale nunca.
        t0, estable = time.time(), 0
        while time.time() - t0 < espera:
            if os.path.exists(salida) and os.path.getsize(salida) > 0:
                tam = os.path.getsize(salida)
                time.sleep(0.4)
                if os.path.getsize(salida) == tam:
                    estable += 1
                    if estable >= 2:
                        break
                else:
                    estable = 0
            else:
                time.sleep(0.3)
        else:
            raise SystemExit(f"✋ Chrome no generó {salida} en {espera}s")
    finally:
        # PASE LO QUE PASE: matar el árbol entero y borrar el perfil.
        try:
            if WIN:   # en Windows no hay killpg: taskkill /T mata el árbol entero
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
            else:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                time.sleep(0.6)
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        shutil.rmtree(perfil, ignore_errors=True)
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada"); ap.add_argument("salida")
    ap.add_argument("--size", help="AxB para PNG, p. ej. 1080x1920")
    ap.add_argument("--espera", type=int, default=45)
    a = ap.parse_args()
    out = render(a.entrada, a.salida, a.size, a.espera)
    print(f"OK → {out} ({os.path.getsize(out)} bytes) · Chrome cerrado")


if __name__ == "__main__":
    main()
