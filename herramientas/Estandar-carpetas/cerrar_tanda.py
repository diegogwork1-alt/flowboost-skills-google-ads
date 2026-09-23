#!/usr/bin/env python3
"""CIERRE de la tanda, lo único que toca Drive en el modo rápido. Pensado para correr EN SEGUNDO
PLANO mientras el agente sigue con lo siguiente.

Hace, en este orden:
  1. Comprueba que el cliente existe en Drive (si no: sale con 1; la carpeta la crea Operaciones).
  2. Fija el número de tanda DEFINITIVO: si `Tanda <N>` ya existe en Drive con piezas que no son
     de esta tanda, pasa a la siguiente libre y renombra los ficheros locales (nada se sobrescribe).
  3. Sube exactamente los PNG registrados de ESTA tanda (con su estado actual: con o sin `_PEND`)
     y manda a la papelera de Drive el gemelo con el estado viejo, si lo había.
  4. Sube `specs_Tanda<N>.md` como Documento de Google (`subir_a_drive.py`).
  5. Verifica con `rclone lsf` que está todo.
  6. Comprueba que el logo usado coincide con algún PNG final de `1. Branding` (aviso, no bloquea).

Por qué (consejo, 13-09-2026): si Dirección pasa el material al empezar, a Drive solo se entra al final.
El número de tanda se calcula aquí, justo antes de subir, y no al principio.

Uso:
  python3 cerrar_tanda.py "Cliente 04" --tanda 2
  python3 cerrar_tanda.py "Cliente 13" --tanda 3 --seco      # dice lo que haría, sin subir
"""
import argparse, glob, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tanda_lib as L

AQUI = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente"); ap.add_argument("--tanda", type=int, required=True)
    ap.add_argument("--seco", action="store_true")
    a = ap.parse_args()
    cli, n = a.cliente, a.tanda
    salida = L.dir_salida(cli)
    if not a.seco:
        L.marcar(cli, n, "cierre_ini")
    informe = {"cliente": cli, "tanda_local": n, "avisos": []}

    base = L.drive_base(cli)
    if not base:
        print(json.dumps({"ok": False, "motivo": f"{cli} no existe en Drive: avisar con avisar.py --nivel aviso"},
                         ensure_ascii=False))
        sys.exit(1)
    gpt = base + "2. Ads/Estáticos/GPT/"

    _, bases = L.registro(cli, n)
    vivos = {b: L.actual_en_disco(salida, b) for b in bases}
    faltan = [b for b, v in vivos.items() if not v]
    if faltan:
        informe["avisos"].append("registrados pero no están en disco: " + ", ".join(faltan))
    vivos = {b: v for b, v in vivos.items() if v}
    if not vivos:
        print(json.dumps({"ok": False, "motivo": "no hay piezas registradas en esta tanda"}, ensure_ascii=False))
        sys.exit(1)

    # 2. Número definitivo contra Drive.
    tandas = {int(m.group(1)): d for d in (L.run(["rclone", "lsf", "--dirs-only", gpt]) or [])
              for m in [re.match(r"Tanda\s*(\d+)/?$", d.strip(), re.I)] if m}
    definitivo = n
    while definitivo in tandas:
        dentro = {L.quitar_pend(f) for f in (L.run(["rclone", "lsf", "--files-only", gpt + f"Tanda {definitivo}/"]) or [])}
        nuestros = {L.quitar_pend(v) for v in vivos.values()}
        if not dentro or dentro & nuestros:
            break  # vacía o es esta misma tanda subida a medias: se reanuda
        definitivo += 1
    if definitivo != n:
        informe["avisos"].append(f"Tanda {n} ya existía en Drive con otras piezas → se sube como Tanda {definitivo}")
        if not a.seco:
            nuevos = {}
            for b, v in vivos.items():
                nv = re.sub(rf"_Tanda{n}_", f"_Tanda{definitivo}_", v)
                os.rename(os.path.join(salida, v), os.path.join(salida, nv))
                nuevos[L.quitar_pend(nv)] = nv
            vivos = nuevos
            for viejo in glob.glob(os.path.join(salida, f"*Tanda{n}.*")) + glob.glob(os.path.join(salida, f".registro-Tanda{n}.json")):
                os.rename(viejo, viejo.replace(f"Tanda{n}.", f"Tanda{definitivo}."))
            json.dump(sorted(vivos), open(L.registro(cli, definitivo)[0], "w", encoding="utf-8"), indent=1)
    # Variaciones: naming y los DOS ratios de cada variación (aviso, no bloquea).
    ratios = {}
    for v in vivos.values():
        p = L.partes_var(v)
        if p:
            ratios.setdefault(f"Madre{p[0]}_VAR{p[1]}", set()).add(p[5])
        elif v.startswith(("VAR", "Madre")):
            informe["avisos"].append(f"{v} no sigue el naming Madre<m>_VAR<v>_<formato>_<angulo>_v<k>_<ratio>")
    for var, rs in sorted(ratios.items()):
        if rs != {"1x1", "9x16"}:
            informe["avisos"].append(f"{var} solo tiene {'/'.join(sorted(rs))}: faltaría el otro ratio")

    destino = gpt + f"Tanda {definitivo}/"
    informe["tanda_drive"] = definitivo
    informe["destino"] = destino

    if a.seco:
        informe["subiria"] = sorted(vivos.values())
        print(json.dumps(informe, ensure_ascii=False, indent=1)); return

    # 3. Subida de las piezas + limpieza del gemelo con estado viejo.
    lista = os.path.join(salida, f".subir-Tanda{definitivo}.txt")
    open(lista, "w", encoding="utf-8").write("\n".join(sorted(vivos.values())) + "\n")
    r = subprocess.run(["rclone", "copy", salida, destino, "--files-from", lista], capture_output=True, text=True)
    if r.returncode:
        informe["avisos"].append("rclone copy falló: " + r.stderr.strip()[-300:])
    en_drive = set(L.run(["rclone", "lsf", "--files-only", destino]) or [])
    for b, v in vivos.items():
        raiz, ext = os.path.splitext(b)
        gemelo = b if v != b else f"{raiz}_PEND{ext}"
        if gemelo in en_drive and gemelo != v:
            subprocess.run(["rclone", "deletefile", destino + gemelo], capture_output=True)  # va a la papelera
            en_drive.discard(gemelo)

    # 3-bis. Variaciones: una versión que salió del registro (la sustituyó una ronda nueva) y que se
    # subió en un cierre anterior se manda a la papelera, para que en Drive no convivan v1 y v2 sin
    # que Dirección lo haya pedido.
    claves = {(p[0], p[1], p[5]) for p in map(L.partes_var, vivos.values()) if p}
    subidos = set(vivos.values())
    for f in sorted(en_drive):
        p = L.partes_var(f)
        if p and (p[0], p[1], p[5]) in claves and f not in subidos:
            subprocess.run(["rclone", "deletefile", destino + f], capture_output=True)
            informe.setdefault("versiones_retiradas_de_drive", []).append(f)

    # 4. Specs como Documento de Google.
    specs = os.path.join(salida, f"specs_Tanda{definitivo}.md")
    if os.path.exists(specs):
        r = subprocess.run([sys.executable, os.path.join(AQUI, "subir_a_drive.py"), specs, destino.rstrip("/"),
                            f"Specs Tanda {definitivo} - {cli}"], capture_output=True, text=True)
        if r.returncode:
            informe["avisos"].append("specs no subido: " + (r.stderr or r.stdout).strip()[-300:])
    else:
        informe["avisos"].append(f"falta specs_Tanda{definitivo}.md en local")

    # 5. Verificación.
    en_drive = set(L.run(["rclone", "lsf", "--files-only", destino]) or [])
    no_subidos = [v for v in vivos.values() if v not in en_drive]
    informe["subidos"] = len(vivos) - len(no_subidos)
    informe["no_subidos"] = no_subidos
    informe["pend"] = sorted(v for v in vivos.values() if "_PEND" in v)

    # 6. ¿El logo usado es el final de Branding? Se compara por tamaño exacto de fichero.
    logos = [p for p in glob.glob(os.path.join(L.dir_insumos(cli), "logo", "*.png"))]
    finales = L.run(["rclone", "lsf", "-R", "--files-only", "--format", "sp", "--include", "*.png",
                     base + "1. Branding/"], timeout=240) or []
    tam_finales = {int(l.split(";")[0]) for l in finales if ";" in l and "antig" not in l.lower()}
    if logos and tam_finales and not any(os.path.getsize(p) in tam_finales for p in logos):
        informe["avisos"].append("el logo de Insumos/logo no coincide con ningún PNG de 1. Branding: revisar que es el final")

    L.marcar(cli, definitivo, "cierre_fin", nota=f"subidos={informe['subidos']} fallan={len(no_subidos)}")
    informe["ok"] = not no_subidos
    print(json.dumps(informe, ensure_ascii=False, indent=1))
    sys.exit(0 if informe["ok"] else 1)


if __name__ == "__main__":
    main()
