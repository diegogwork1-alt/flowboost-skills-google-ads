#!/usr/bin/env python3
"""Audita (y opcionalmente crea) la estructura de carpetas de un cliente en Drive.

Solo lectura por defecto. Con --crear añade lo que falte. NUNCA renombra ni borra.

Uso:
  python3 auditar-carpetas-cliente.py --todos
  python3 auditar-carpetas-cliente.py Cliente 04
  python3 auditar-carpetas-cliente.py Cliente 04 --crear
  python3 auditar-carpetas-cliente.py Cliente 04 --guiones 3   # crea Script 1..3 en vez de 1..5
"""
import argparse, re, subprocess, sys, unicodedata

NIVEL1 = ["0. Onboarding", "1. Branding", "2. Ads", "3. Landing", "4. Formulario",
          "5. Cierre", "6. Reportes", "7. Leads", "8. RRSS"]
ADS = ["Vídeos crudos", "Estáticos", "EGC"]

# variantes historicas que valen como equivalentes (no se renombran, solo se reconocen)
EQUIV = {
    "5. Cierre": ["5. Closer", "5. Closing"],
    "6. Reportes": ["6. Reporting"],
    "Estáticos": ["Estaticos"],
    "EGC": ["EGC-UGC", "Vídeos EGC - UGC", "Vídeos EGC - UGC/"],
}


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout.strip().splitlines() if r.returncode == 0 else None


def listar(path):
    out = run(["rclone", "lsf", "--dirs-only", path])
    return [d.rstrip("/") for d in out] if out else []


def clientes():
    out = run(["rclone", "lsf", "--dirs-only", "gdrive:"]) or []
    return sorted(d.rstrip("/")[2:] for d in out if d.startswith("i_"))


def base(cli):
    """la subcarpeta interna suele ser c_<Cliente>, pero no siempre: se detecta"""
    raiz = f"gdrive:i_{cli}/"
    dentro = listar(raiz)
    if f"c_{cli}" in dentro:
        return raiz + f"c_{cli}/"
    candidatos = [d for d in dentro if d.startswith("c_")]
    if candidatos:
        return raiz + candidatos[0] + "/"
    # si ya cuelga del primer nivel
    if any(d.startswith(("0.", "1.", "2.")) for d in dentro):
        return raiz
    return raiz + (dentro[0] + "/" if dentro else "")


def norm(x):
    """quita el prefijo 'N. ', tildes, mayusculas y espacios extra"""
    x = re.sub(r"^\s*\d+\.\s*", "", x).strip().lower()
    x = "".join(c for c in unicodedata.normalize("NFD", x)
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s_-]+", " ", x).strip()


def encontrada(esperada, presentes):
    """compara por NOMBRE, ignorando el numero de prefijo y las tildes"""
    if esperada in presentes:
        return esperada
    objetivo = norm(esperada)
    candidatos = [objetivo] + [norm(a) for a in EQUIV.get(esperada, [])]
    for pres in presentes:
        if norm(pres) in candidatos:
            return pres
    return None


def auditar(cli, crear=False, guiones=5):
    b = base(cli)
    presentes = listar(b)
    if not presentes:
        print(f"\n{cli}: no se puede leer la carpeta ({b})")
        return
    faltan, variantes = [], []
    print(f"\n=== {cli} ===")
    for esp in NIVEL1:
        hall = encontrada(esp, presentes)
        if hall is None:
            faltan.append((b, esp))
            print(f"  FALTA   {esp}")
        elif hall != esp:
            variantes.append((esp, hall))
            print(f"  VARIANTE {hall}  (estándar: {esp})")

    ads_hall = encontrada("2. Ads", presentes)
    if ads_hall:
        ads_path = b + ads_hall + "/"
        ads_pres = listar(ads_path)
        for esp in ADS:
            hall = encontrada(esp, ads_pres)
            if hall is None:
                faltan.append((ads_path, esp))
                print(f"  FALTA   2. Ads/{esp}")
            elif hall != esp:
                variantes.append((f"2. Ads/{esp}", f"2. Ads/{hall}"))
                print(f"  VARIANTE 2. Ads/{hall}  (estándar: {esp})")

        crudos_hall = encontrada("Vídeos crudos", ads_pres)
        if crudos_hall:
            cp = ads_path + crudos_hall + "/"
            sub = listar(cp)
            for s in [f"Script {i}" for i in range(1, guiones + 1)] + ["VSL"]:
                if s not in sub:
                    faltan.append((cp, s))
                    print(f"  FALTA   2. Ads/{crudos_hall}/{s}")
        else:
            cp = ads_path + "Vídeos crudos/"
            for s in [f"Script {i}" for i in range(1, guiones + 1)] + ["VSL"]:
                faltan.append((cp, s))

    if not faltan and not variantes:
        print("  OK — estructura completa y con los nombres estándar")
    if faltan and crear:
        print(f"  → creando {len(faltan)} carpetas…")
        for padre, nombre in faltan:
            subprocess.run(["rclone", "mkdir", padre + nombre], capture_output=True)
        print("  → hecho")
    elif faltan:
        print(f"  ({len(faltan)} carpetas por crear — usa --crear)")
    if variantes:
        print("  (las variantes NO se renombran solas: decisión de Dirección)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cliente", nargs="?")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--crear", action="store_true")
    ap.add_argument("--guiones", type=int, default=5)
    a = ap.parse_args()
    if a.todos:
        for c in clientes():
            auditar(c, a.crear, a.guiones)
    elif a.cliente:
        auditar(a.cliente, a.crear, a.guiones)
    else:
        ap.print_help(); sys.exit(1)


if __name__ == "__main__":
    main()
