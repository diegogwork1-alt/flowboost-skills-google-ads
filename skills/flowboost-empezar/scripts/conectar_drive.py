#!/usr/bin/env python3
"""Conecta el remoto `gdrive:` de rclone con un client_id PROPIO, sin teclear ni enseñar el secreto.

El client_id compartido de rclone se retira en 2026; un remoto que lo use deja de subir y bajar
de Drive de un día para otro. Este script lee el JSON que da Google Cloud al crear el cliente
(tipo «App de escritorio»), lo guarda junto a rclone.conf, crea o actualiza `gdrive:`, abre el
navegador para autorizar y comprueba que el aviso del client_id compartido ya no sale.

    python3 conectar_drive.py ~/Downloads/client_secret_XXXX.json   # conectar o cambiar de cliente
    python3 conectar_drive.py --cuenta                              # con qué Google está gdrive:

Nunca imprime el client_secret ni el token.
"""
import json, os, re, shutil, subprocess, sys, urllib.request

REMOTO = "gdrive"
AVISO = "shared Google Drive client_id"


def rclone(*args, **kw):
    return subprocess.run(["rclone", *args], capture_output=True, text=True, **kw)


def carpeta_config():
    salida = rclone("config", "file").stdout.strip().splitlines()
    return os.path.dirname(salida[-1]) if salida else os.path.expanduser("~/.config/rclone")


def cuenta(remoto):
    rclone("lsd", f"{remoto}:", "--max-depth", "1")  # renueva el token si ha caducado
    cfg = json.loads(rclone("config", "dump").stdout or "{}")
    if remoto not in cfg or not cfg[remoto].get("token"):
        sys.exit(f"✗ No hay remoto «{remoto}» autorizado. Conéctalo primero con el JSON del cliente.")
    tok = json.loads(cfg[remoto]["token"])
    req = urllib.request.Request("https://www.googleapis.com/drive/v3/about?fields=user(emailAddress)",
                                 headers={"Authorization": "Bearer " + tok["access_token"]})
    return json.load(urllib.request.urlopen(req))["user"]["emailAddress"]


def conectar(ruta_json, remoto):
    try:
        datos = json.load(open(os.path.expanduser(ruta_json)))
    except (OSError, ValueError) as e:
        sys.exit(f"✗ No se puede leer el JSON: {e}")
    if "installed" not in datos:
        sys.exit("✗ Ese JSON no es de un cliente «App de escritorio». En Google Cloud → Clientes, crea uno "
                 "de tipo App de escritorio y descarga su JSON.")
    c = datos["installed"]

    # Guardar el JSON junto a rclone.conf (Google no deja volver a ver el secreto)
    destino = os.path.join(carpeta_config(), f"{remoto}-oauth-client.json")
    if os.path.abspath(os.path.expanduser(ruta_json)) != os.path.abspath(destino):
        shutil.copyfile(os.path.expanduser(ruta_json), destino)
    try:
        os.chmod(destino, 0o600)
    except OSError:
        pass
    print(f"· JSON guardado en {destino}")

    existe = f"{remoto}:" in rclone("listremotes").stdout.split()
    claves = ["client_id", c["client_id"], "client_secret", c["client_secret"]]
    print("· Se abre el navegador: entra con tu cuenta de Flowboost y acepta.")
    if existe:
        r = rclone("config", "update", remoto, *claves, "--auto-confirm")
        if r.returncode == 0:
            r = rclone("config", "reconnect", f"{remoto}:", "--auto-confirm")
    else:
        r = rclone("config", "create", remoto, "drive", *claves, "scope", "drive", "--auto-confirm")
    if r.returncode != 0:
        error = re.sub(r"(ya29\.|GOCSPX-)\S+", "…", r.stderr)  # por si acaso, nada de secretos
        sys.exit(f"✗ rclone no pudo conectar:\n{error[-600:]}")

    prueba = rclone("lsd", f"{remoto}:")
    if prueba.returncode != 0:
        sys.exit(f"✗ Conectado, pero no lista el Drive:\n{prueba.stderr[-400:]}")
    if AVISO in prueba.stderr:
        sys.exit("✗ Sigue usando el client_id compartido de rclone: revisa que el JSON sea el bueno.")
    n = len(prueba.stdout.splitlines())
    print(f"✓ {remoto}: conectado con tu client_id propio · cuenta {cuenta(remoto)} · {n} carpetas en la raíz")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not shutil.which("rclone"):
        sys.exit("✗ Falta rclone (Mac: brew install rclone · Windows: winget install -e --id Rclone.Rclone)")
    if args == ["--cuenta"]:
        print(cuenta(REMOTO))
    elif len(args) == 1:
        conectar(args[0], REMOTO)
    else:
        sys.exit(__doc__)
