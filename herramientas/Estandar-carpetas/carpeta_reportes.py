#!/usr/bin/env python3
"""Encuentra la carpeta de Reportes de un cliente SIN suponer el número.

El número cambia de un cliente a otro (`5. Reportes`, `6. Reportes`, `7. Reportes`…) porque
las carpetas anteriores no son iguales en todos: Cliente 02 tiene `5. Closer` y `6. Reportes`,
otros tienen `5. Cierre`. Así que se busca **por nombre**, ignorando el número, las tildes y
las variantes conocidas (`Reporting`). Nunca se escribe "6. Reportes" a pelo en el código.

Uso:
  python3 carpeta_reportes.py "gdrive:i_Cliente 02/c_Cliente 02"
  → gdrive:i_Cliente 02/c_Cliente 02/6. Reportes
"""
import json, re, subprocess, sys, unicodedata

# El nombre real varía: «6. Reportes», «5. Reportes／Informes», «6. Reporting»…
VARIANTES = {"reportes", "reporting", "reports", "informes", "informe", "reporte"}


def _palabras(nombre):
    """«5. Reportes／Informes» → {'reportes', 'informes'}.

    Quita el número de delante, las tildes, y parte por cualquier separador: barra normal,
    barra ancha （／, que es la que usa Drive cuando el nombre lleva una barra）, guion, coma…
    """
    n = re.sub(r"^\s*\d+\s*[.\-_)]?\s*", "", nombre)
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return {t for t in re.split(r"[^a-zA-Z]+", n.lower()) if t}


def buscar(raiz_cliente):
    """raiz_cliente = 'gdrive:i_X/c_X' → ruta de su carpeta de reportes, o None."""
    out = subprocess.run(["rclone", "lsjson", "--dirs-only", raiz_cliente],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"No se pudo listar {raiz_cliente}: {out.stderr.strip()}")
    for d in json.loads(out.stdout or "[]"):
        if _palabras(d["Name"]) & VARIANTES:
            return f"{raiz_cliente.rstrip('/')}/{d['Name']}"
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = buscar(sys.argv[1])
    if not r:
        sys.exit(f"✗ No hay carpeta de reportes en {sys.argv[1]}. "
                 f"La crea Operaciones; el agente no la inventa.")
    print(r)


if __name__ == "__main__":
    main()
