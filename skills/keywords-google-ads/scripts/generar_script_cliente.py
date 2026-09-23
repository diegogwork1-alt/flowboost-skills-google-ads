#!/usr/bin/env python3
"""Genera el Ads Script de UN cliente, listo para pegar en Google Ads.

    python3 generar_script_cliente.py "<Cliente>" "<URL de su hoja de reportes>" [salida.js]
        [--estacional "<URL del archivo Estacionalidad - Cliente>"]

Hace cuatro cosas que importan:

1. Rellena SHEET_URL y CLIENTE (y SHEET_URL_ESTACIONAL si ya existe el archivo), para que no
   haya que tocar nada al pegarlo.
2. Quita el bloque de ejemplo del MCC, que nombra a OTROS clientes. Cada cliente recibe un
   script donde solo aparece el suyo.
3. Deja el fichero en caracteres seguros. El editor de Google Ads no siempre pega bien los
   símbolos de dibujo (═ ─ ▸ — …) y revienta con «Invalid or unexpected token (line 1)».
   Se sustituyen por equivalentes ASCII; las tildes se quedan. Por eso el archivo que crea el
   script se llama «Estacionalidad - <Cliente>», con guion normal.
4. Escapa las comillas del nombre del cliente, que si no rompen el JS.
"""
import argparse, os, re, sys

SEGURO = {
    '═': '=', '─': '-', '━': '-', '—': '-', '–': '-',
    '→': '->', '←': '<-', '↑': '^', '▸': '>', '…': '...',
    '“': '"', '”': '"', '‘': "'", '’': "'", ' ': ' ',
    '⛔': '[!]', '✅': '[ok]', '⚠': '[!]', '️': '',
}


def limpiar(texto):
    for malo, bueno in SEGURO.items():
        texto = texto.replace(malo, bueno)
    return ''.join(c if ord(c) < 256 else '?' for c in texto)


def js_str(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cliente')
    ap.add_argument('url_reportes', help='URL de la hoja «Reporte Ads — <Cliente> — <año>»')
    ap.add_argument('salida', nargs='?', help='fichero .js de salida')
    ap.add_argument('--estacional', default='', help='URL del archivo de estacionalidad, si ya existe')
    a = ap.parse_args()

    salida = a.salida or f"{a.cliente.lower().replace(' ', '')}.js"
    plantilla = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ads-script-estacionalidad.js')
    s = open(plantilla, encoding='utf-8').read()

    s = re.sub(r"var SHEET_URL = '[^']*';", f"var SHEET_URL = '{js_str(a.url_reportes)}';", s, count=1)
    s = re.sub(r"var CLIENTE   = '[^']*';", f"var CLIENTE   = '{js_str(a.cliente)}';", s, count=1)
    if a.estacional:
        s = re.sub(r"var SHEET_URL_ESTACIONAL = '[^']*';",
                   f"var SHEET_URL_ESTACIONAL = '{js_str(a.estacional)}';", s, count=1)

    # Fuera el bloque del MCC (nombra a otros clientes) y la línea de la cabecera que lo cita
    s = re.split(r"/\*\s*[─-]{3,}\s*\n\s*VERSI[OÓ]N MCC", s)[0].rstrip() + '\n'
    s = re.sub(r"\n \* DESDE UN MCC:.*", "", s)
    s = s.replace('PLANTILLA — copiar TODO y pegar en Google Ads.\n   Cambiar SHEET_URL y CLIENTE, y nada más.',
                  f'{a.cliente} — YA RELLENO. Copiar TODO y pegar en Google Ads. No hay que cambiar nada.')

    s = limpiar(s)
    if '??' in s:
        print("  aviso: algún carácter no se pudo convertir, revisa los '??'")
    open(salida, 'w', encoding='utf-8').write(s)
    print(f"OK  {salida}\n    cliente: {a.cliente}\n    hoja de reportes: {a.url_reportes[:60]}…")
    print(f"    estacionalidad: {a.estacional[:60] + '…' if a.estacional else '(se creará en la primera pasada)'}")
    print(f"    {len(s.splitlines())} líneas, solo caracteres seguros, sin mención a otros clientes")
    print("\nPégalo en Google Ads: Herramientas → Acciones en bloque → Secuencias de comandos (en inglés: Tools → Bulk actions → Scripts)")


if __name__ == '__main__':
    main()
