#!/usr/bin/env python3
"""Lee la hoja «Estado de cuenta» de un cliente y dice QUÉ TOCA HACER AHORA.

Para qué existe: el agente encadena sus propias etapas solo (lo dice `/funnel`), pero hay
cosas que NO son suyas —la landing y el formulario los hace Dirección, la carpeta la crea Operaciones,
los vídeos los graba el cliente— y hasta ahora no tenía forma de enterarse de que ya estaban
hechas si nadie se lo decía en el chat.

Con esto, **la hoja del Drive es la señal**: Dirección marca «Hecho» en su fila cuando termina, y
el agente lo lee al arrancar. No hace falta que le cuente nada.

Se lee con el mismo token de Drive que ya usa el agente (rclone), así que **no depende de n8n
ni de la credencial de Google Sheets**.

Uso:
  python3 leer_estado.py "Cliente 02" --cliente-raiz "gdrive:i_Cliente 02/c_Cliente 02"
  python3 leer_estado.py "Cliente 02" --sheet-id <ID> [--json]
"""
import argparse, csv, io, json, sys, urllib.parse, urllib.request
from subir_a_drive import api, token

# Quién es dueño de cada etapa lo dice la propia hoja (columna «Quién»).
DEL_AGENTE = {"agente"}


def exportar_csv(sheet_id):
    u = f"https://www.googleapis.com/drive/v3/files/{sheet_id}/export?mimeType=text/csv"
    for i in range(5):
        try:
            r = urllib.request.Request(u, headers={"Authorization": "Bearer " + token(refrescar=i > 0)})
            return urllib.request.urlopen(r, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            if i == 4:
                sys.exit(f"✗ No se pudo leer la hoja: {type(e).__name__}: {e}")
    return ""


def buscar_hoja(cliente, raiz):
    sys.path.insert(0, ".")
    from carpeta_reportes import buscar
    from subir_a_drive import folder_id
    carpeta = buscar(raiz)
    if not carpeta:
        return None
    fid = folder_id(carpeta)
    nombre = f"Estado de cuenta — {cliente}"
    n = nombre.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name = '{n}' and '{fid}' in parents and trashed = false"
    url = ("https://www.googleapis.com/drive/v3/files?"
           + urllib.parse.urlencode({"q": q, "fields": "files(id)",
                                     "supportsAllDrives": "true",
                                     "includeItemsFromAllDrives": "true"}))
    f = api(url).get("files", [])
    return f[0]["id"] if f else None


def leer(sheet_id):
    filas = list(csv.reader(io.StringIO(exportar_csv(sheet_id))))
    # La cabecera de la tabla está en la fila 7 (debajo del título y el semáforo).
    cab = None
    for i, f in enumerate(filas):
        if f and f[0].strip().lower() == "carril":
            cab, ini = f, i + 1
            break
    if not cab:
        sys.exit("✗ Esa hoja no tiene la tabla de etapas (falta la cabecera «Carril»).")
    idx = {c.strip().lower(): j for j, c in enumerate(cab)}
    etapas = []
    carril = ""
    for f in filas[ini:]:
        if not f or not (len(f) > idx["etapa"] and f[idx["etapa"]].strip()):
            continue
        carril = f[idx["carril"]].strip() or carril
        etapas.append({
            "carril": carril,
            "etapa": f[idx["etapa"]].strip(),
            "estado": (f[idx["estado"]].strip() if len(f) > idx["estado"] else "") or "Pendiente",
            "quien": (f[idx["quién"]].strip() if "quién" in idx and len(f) > idx["quién"] else ""),
            "notas": (f[idx["notas"]].strip() if "notas" in idx and len(f) > idx["notas"] else ""),
        })
    return etapas


def analizar(etapas):
    hechas = [e for e in etapas if e["estado"].lower() == "hecho"]
    bloq = [e for e in etapas if e["estado"].lower() == "bloqueado"]
    curso = [e for e in etapas if e["estado"].lower() == "en curso"]
    pend = [e for e in etapas if e["estado"].lower() == "pendiente"]

    # Lo que el agente puede hacer YA: sus etapas pendientes. El carril A y el B corren en
    # paralelo, así que se devuelve la siguiente de cada carril, no una sola.
    mias, ajenas = [], []
    vistos = set()
    for e in pend:
        if e["quien"].lower() in DEL_AGENTE:
            if e["carril"] not in vistos:
                mias.append(e); vistos.add(e["carril"])
        else:
            ajenas.append(e)
    return {"hechas": len(hechas), "total": len(etapas), "bloqueadas": bloq,
            "en_curso": curso, "siguientes_del_agente": mias, "esperando_a_otros": ajenas}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente")
    ap.add_argument("--sheet-id", default="")
    ap.add_argument("--cliente-raiz", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    sid = a.sheet_id or (buscar_hoja(a.cliente, a.cliente_raiz) if a.cliente_raiz else None)
    if not sid:
        sys.exit("✗ Hace falta --sheet-id o --cliente-raiz para encontrar la hoja.")

    r = analizar(leer(sid))
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2)); return

    print(f"\n  {a.cliente.upper()} — {r['hechas']} de {r['total']} etapas hechas\n")
    if r["bloqueadas"]:
        print("  BLOQUEADO:")
        for e in r["bloqueadas"]:
            print(f"    ✗ {e['etapa']} ({e['quien']}) — {e['notas'] or 'sin motivo apuntado'}")
        print()
    if r["en_curso"]:
        print("  EN CURSO:")
        for e in r["en_curso"]:
            print(f"    · {e['etapa']} ({e['quien']})")
        print()
    if r["siguientes_del_agente"]:
        print("  LO QUE ME TOCA AHORA:")
        for e in r["siguientes_del_agente"]:
            print(f"    → [{e['carril']}] {e['etapa']}")
    else:
        print("  No hay ninguna etapa mía pendiente.")
    if r["esperando_a_otros"]:
        print("\n  ESPERANDO A OTROS (no las toco):")
        for e in r["esperando_a_otros"][:6]:
            print(f"    · {e['etapa']} — {e['quien']}")
    print()


if __name__ == "__main__":
    main()
