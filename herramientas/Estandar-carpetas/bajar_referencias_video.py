#!/usr/bin/env python3
"""Descarga del Drive los vídeos de referencia para editar (VSL y anuncios).

No van dentro del repo: son 2,6 GB y GitHub no admite ficheros así. Viven en el Drive de
Flowboost, en «referencias-video», y esto los baja a ~/Desktop/BLS/Referencias/, que es donde
las skills de vídeo los buscan.

AVISA ANTES y espera confirmación: son muchos GB y puede tardar. Con --si no pregunta.

  python3 bajar_referencias_video.py            # dice qué falta y pregunta
  python3 bajar_referencias_video.py --si       # baja sin preguntar
  python3 bajar_referencias_video.py --revisar  # solo mira, no baja
"""
import argparse, os, subprocess, sys

CARPETAS = {   # nombre local  →  id de la carpeta en el Drive
    "VSL":      "<ID_DRIVE>",
    "ANUNCIOS": "<ID_DRIVE>",
}
DESTINO = os.path.expanduser("~/Desktop/BLS/Referencias")
VIDEO = (".mp4", ".mov", ".m4v", ".webm")


def del_drive(fid):
    """Los vídeos que hay en esa carpeta del Drive: [(nombre, bytes)]."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from subir_a_drive import api
    import urllib.parse
    r = api("https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(
        {"q": f"'{fid}' in parents and trashed=false", "fields": "files(name,size)",
         "pageSize": 200, "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}))
    return [(f["name"], int(f.get("size", 0)))
            for f in r.get("files", []) if f["name"].lower().endswith(VIDEO)]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--si", action="store_true", help="no preguntar, bajar directamente")
    ap.add_argument("--revisar", action="store_true", help="solo comprobar qué falta")
    a = ap.parse_args()

    plan, total = [], 0
    for nombre, fid in CARPETAS.items():
        local = os.path.join(DESTINO, nombre)
        ya = set(os.listdir(local)) if os.path.isdir(local) else set()
        faltan = [(n, s) for n, s in del_drive(fid) if n not in ya]
        if faltan:
            plan.append((nombre, fid, faltan))
            total += sum(s for _, s in faltan)
        print(f"  {nombre}: {len(ya)} ya tienes · {len(faltan)} por bajar")

    if not plan:
        print("\n✅ Ya están todos los vídeos de referencia.")
        return 0
    if a.revisar:
        return 1

    # EL AVISO. Son muchos GB: no se baja nada sin decirlo.
    print(f"\n  ⚠️  Hay que bajar {sum(len(f) for _,_,f in plan)} vídeos · "
          f"{total/1e9:.1f} GB desde el Drive.")
    print(f"     Van a: {DESTINO}")
    print("     Con una conexión normal esto tarda un buen rato y ocupa ese espacio en disco.")
    print("     Solo hacen falta si vas a EDITAR vídeo; para lo demás, no.")
    if not a.si:
        try:
            r = input("\n  ¿Los bajo? (s/n): ").strip().lower()
        except EOFError:
            print("\n  (sin respuesta: no se baja nada. Usa --si para bajarlos)"); return 1
        if r not in ("s", "si", "sí", "y", "yes"):
            print("  No se baja nada."); return 1

    for nombre, fid, faltan in plan:
        local = os.path.join(DESTINO, nombre)
        os.makedirs(local, exist_ok=True)
        print(f"\n  ▸ {nombre}: {len(faltan)} vídeos…")
        r = subprocess.run(["rclone", "copy", "--drive-root-folder-id", fid, "gdrive:", local,
                            "--include", "*.{mp4,mov,m4v,webm}", "--progress", "--transfers", "2"])
        print(f"    {'✅' if r.returncode == 0 else '⛔'} {nombre}")
    print(f"\n✅ Listo: {DESTINO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
