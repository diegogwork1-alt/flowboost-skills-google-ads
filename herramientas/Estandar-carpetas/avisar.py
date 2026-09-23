#!/usr/bin/env python3
"""Avisa a Dirección. Es el ÚNICO camino: ninguna skill inventa el suyo.

Antes, media docena de skills decían "avisar a Dirección" sin decir cómo, y el aviso solo
existía si había una sesión de chat abierta y él la estaba mirando. Con esto sale un correo
de verdad a <correo-direccion>, corra el agente donde corra.

Uso:
  python3 avisar.py --cliente "Cliente 02" --asunto "Falta el branding" \
      --cuerpo "No hay logo ni paleta en 1. Branding, así que no puedo montar los estáticos." \
      --accion "Súbelos a 1. Branding o dime de dónde los saco." \
      [--nivel urgente|aviso|info] [--enlace https://...]

Cuándo se usa cada nivel:
  urgente  algo está roto y cuesta dinero cada hora (landing caída, píxel que no dispara,
           campaña gastando sin leads). Dirección tiene que mirarlo hoy.
  aviso    hace falta algo suyo para seguir (branding, una decisión, un dato del brief).
  info     se entregó algo y no hay que hacer nada (tanda subida, informe guardado).

REGLA: si hay una sesión de chat abierta, lo que sea de esa sesión se le cuenta ahí y NO se
manda correo — el correo es para lo que pasa cuando él no está mirando. Un aviso duplicado
por dos canales entrena a ignorarlos.
"""
import argparse, json, sys, urllib.error, urllib.request

URL = "https://<tu-subdominio>/webhook/aviso-agente"


def avisar(cliente, asunto, cuerpo, accion="", nivel="aviso", enlace="", url=URL):
    datos = json.dumps({"cliente": cliente, "asunto": asunto, "cuerpo": cuerpo,
                        "accion": accion, "nivel": nivel, "enlace": enlace}).encode()
    pet = urllib.request.Request(url, data=datos,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pet, timeout=20) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        print(f"✗ El aviso NO salió (HTTP {e.code}). "
              f"Cuéntaselo a Dirección en el resumen de la sesión.", file=sys.stderr)
    except Exception as e:
        print(f"✗ El aviso NO salió ({type(e).__name__}). "
              f"Cuéntaselo a Dirección en el resumen de la sesión.", file=sys.stderr)
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--asunto", required=True)
    ap.add_argument("--cuerpo", required=True)
    ap.add_argument("--accion", default="")
    ap.add_argument("--nivel", default="aviso", choices=["urgente", "aviso", "info"])
    ap.add_argument("--enlace", default="")
    a = ap.parse_args()
    ok = avisar(a.cliente, a.asunto, a.cuerpo, a.accion, a.nivel, a.enlace)
    print("✓ Aviso enviado a Dirección" if ok else "✗ No se pudo enviar")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
