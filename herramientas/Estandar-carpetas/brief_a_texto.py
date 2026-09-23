#!/usr/bin/env python3
"""Deja el brief como TEXTO plano, listo para adjuntar al GPT.

Por qué (Dirección, 08-09-2026): el PDF del brief pesa —de 56 KB a casi 1 MB— y la subida a ChatGPT
falló de verdad una vez: se envió el mensaje igual y el GPT se inventó el cliente entero. Un .txt
de unos pocos KB sube al instante, no se acerca al tope de 10 MB por llamada, y además el modelo
lo lee directo en vez de tener que interpretar un PDF.

Orden de preferencia:
  1. `Brief_<Cliente>.md`  ← el canónico que deja `brief-desde-onboarding`. Se copia tal cual.
  2. `Brief_<Cliente>.pdf` ← se extrae el texto con PyMuPDF.

Uso:
  python3 brief_a_texto.py "Cliente 02"
  python3 brief_a_texto.py "Cliente 02" --pdf "/ruta/Brief.pdf"

Imprime la ruta del .txt, que es lo que se adjunta.
"""
import argparse, pathlib, re, sys

def limpiar(t):
    """Quita saltos de página y espacios de sobra: el PDF los mete a puñados."""
    t = t.replace("\x0c", "\n")
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cliente")
    ap.add_argument("--pdf", default="", help="ruta del PDF si no está donde se espera")
    ap.add_argument("--md", default="", help="ruta del .md si no está donde se espera")
    a = ap.parse_args()

    base = pathlib.Path.home()/"Desktop/CLIENTES"
    ins = None
    for d in (base/a.cliente/"Insumos", base/f"{a.cliente} Test"/"Insumos", base/a.cliente):
        if d.is_dir(): ins = d; break
    if ins is None:
        sys.exit(f"✗ No encuentro la carpeta de {a.cliente} en ~/Desktop/CLIENTES/")

    md = pathlib.Path(a.md) if a.md else next(
        (p for p in ins.glob(f"Brief_{a.cliente}*.md") if "operativo" not in p.name.lower()), None)
    pdf = pathlib.Path(a.pdf) if a.pdf else next(iter(ins.glob(f"Brief_{a.cliente}*.pdf")), None)
    salida = ins/f"Brief_{a.cliente}_para_GPT.txt"

    if md and md.is_file():
        texto = limpiar(md.read_text(encoding="utf-8", errors="replace"))
        origen = f"el .md canónico ({md.name})"
    elif pdf and pdf.is_file():
        try:
            import fitz
        except ImportError:
            sys.exit("✗ Falta PyMuPDF para leer el PDF:  pip install pymupdf")
        doc = fitz.open(pdf)
        texto = limpiar("\n".join(p.get_text() for p in doc))
        origen = f"el PDF ({pdf.name}, {pdf.stat().st_size//1024} KB)"
        if len(texto) < 400:
            sys.exit(f"✗ Del PDF solo salieron {len(texto)} caracteres: puede ser un PDF escaneado "
                     f"(imágenes, sin texto). NO se adjunta esto: se pide el brief en texto.")
    else:
        sys.exit(f"✗ No hay ni Brief_{a.cliente}.md ni .pdf en {ins}")

    salida.write_text(texto, encoding="utf-8")
    kb = salida.stat().st_size/1024
    print(f"✓ Brief en texto desde {origen}")
    print(f"  {len(texto):,} caracteres · {kb:.1f} KB")
    if pdf and pdf.is_file():
        print(f"  (el PDF pesaba {pdf.stat().st_size//1024} KB → "
              f"{pdf.stat().st_size/max(salida.stat().st_size,1):.0f} veces más)")
    print(salida)


if __name__ == "__main__":
    main()
