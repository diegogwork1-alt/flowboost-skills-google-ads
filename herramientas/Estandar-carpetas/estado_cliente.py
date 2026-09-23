#!/usr/bin/env python3
"""ESTADO.md por cliente — el fichero que dice a cualquier skill/agente en qué etapa está el cliente.

Lo crea la primera skill que trabaje con el cliente (si no existe) y lo actualizan todas.
Vive en DOS sitios sincronizados: local `~/Desktop/CLIENTES/<Cliente>/ESTADO.md` (regla: todo en la
carpeta del cliente) y Drive `i_<Cliente>/c_<Cliente>/0. Onboarding/ESTADO.md` (rclone copyto).

Uso:
  python3 estado_cliente.py <Cliente> show
  python3 estado_cliente.py <Cliente> set "<Etapa>" "<estado>" ["nota"]
      estado: pendiente | en curso | hecho | bloqueado | n/a
  python3 estado_cliente.py <Cliente> nota "<texto libre>"        # añade una línea al registro
Etapas (orden del funnel): ver ETAPAS abajo. Si la etapa no existe, se añade al final.
"""
import os, re, subprocess, sys
from datetime import date

# FUENTE ÚNICA de nombres de etapa (orden = tabla de /funnel, sincronizada 06-09-2026).
# Toda skill usa estos strings LITERALES; un string distinto crea fila nueva y el funnel no lo ve.
ETAPAS = [
    "Carpeta Drive verificada (estándar)", "Alta en reportes", "Brief", "Accesos del cliente",
    "Radar de competencia",
    "Guiones EGC", "Guion VSL", "Envío al cliente (EGC + VSL + Guía)", "Vídeos crudos recibidos", "Edición de vídeos", "Anuncios 9:16 editados",
    "Estáticos (tanda)", "Copy de anuncios",
    "Formulario y ruta del lead", "Medición: píxel y eventos",
    "Landing", "CRM montado", "Campaña armada (en pausa)", "Campaña activa (OK Dirección)",
    "Informe semanal de landing", "Operación semanal (cuenta)", "Baja del cliente",
]

def run(a):
    r = subprocess.run(a, capture_output=True, text=True); return r.stdout.strip().splitlines() if r.returncode == 0 else None

def drive_base(cli):
    raiz = f"gdrive:i_{cli}/"; dentro = [d.rstrip("/") for d in (run(["rclone","lsf","--dirs-only",raiz]) or [])]
    if f"c_{cli}" in dentro: return raiz + f"c_{cli}/"
    c = [d for d in dentro if d.startswith("c_")]
    return raiz + (c[0] + "/" if c else "")

def local_path(cli):
    d = os.path.expanduser(f"~/Desktop/CLIENTES/{cli}"); os.makedirs(d, exist_ok=True); return os.path.join(d, "ESTADO.md")

def plantilla(cli):
    hoy = date.today().isoformat()
    filas = "\n".join(f"| {e} | pendiente | | |" for e in ETAPAS)
    return (f"# ESTADO — {cli}\n\nCreado: {hoy}. Lo actualizan las skills; leerlo antes de hacer nada con el cliente.\n\n"
            f"| Etapa | Estado | Fecha | Nota |\n|---|---|---|---|\n{filas}\n\n## Registro\n")

def cargar(cli):
    p = local_path(cli)
    if os.path.exists(p): return open(p, encoding="utf-8").read()
    # intentar traer el de Drive si existiera
    b = drive_base(cli); tmp = p + ".drive"
    if b and run(["rclone","copyto", b + "0. Onboarding/ESTADO.md", tmp]) is not None and os.path.exists(tmp):
        s = open(tmp, encoding="utf-8").read(); os.remove(tmp); open(p,"w",encoding="utf-8").write(s); return s
    s = plantilla(cli); open(p,"w",encoding="utf-8").write(s); return s

def guardar(cli, s):
    p = local_path(cli); open(p,"w",encoding="utf-8").write(s)
    b = drive_base(cli)
    if b:
        subprocess.run(["rclone","mkdir", b + "0. Onboarding"], capture_output=True)
        subprocess.run(["rclone","copyto", p, b + "0. Onboarding/ESTADO.md"], capture_output=True)
    print(f"ESTADO.md actualizado → {p} (+ Drive 0. Onboarding/)")

def set_etapa(cli, etapa, estado, nota=""):
    s = cargar(cli); hoy = date.today().isoformat()
    pat = re.compile(r"^\| " + re.escape(etapa) + r" \|.*$", re.M)
    fila = f"| {etapa} | {estado} | {hoy} | {nota} |"
    s = pat.sub(fila, s) if pat.search(s) else s.replace("\n\n## Registro", f"\n{fila}\n\n## Registro")
    s += f"- {hoy} · {etapa}: {estado}" + (f" — {nota}" if nota else "") + "\n"
    guardar(cli, s)

def main():
    if len(sys.argv) < 3: print(__doc__); sys.exit(1)
    cli, cmd = sys.argv[1], sys.argv[2]
    if cmd == "show": print(cargar(cli))
    elif cmd == "set": set_etapa(cli, sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
    elif cmd == "nota":
        s = cargar(cli) + f"- {date.today().isoformat()} · {sys.argv[3]}\n"; guardar(cli, s)
    else: print(__doc__); sys.exit(1)

if __name__ == "__main__": main()
