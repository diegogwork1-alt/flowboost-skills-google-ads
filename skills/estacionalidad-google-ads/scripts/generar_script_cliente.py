#!/usr/bin/env python3
"""Genera el Ads Script de UN cliente, listo para pegar en Google Ads.

    python3 generar_script_cliente.py "<Cliente>" "<URL de su hoja de reportes>" [salida.js]

Hace tres cosas que importan:

1. Rellena SHEET_URL y CLIENTE, para que no haya que tocar nada al pegarlo.
2. Quita el bloque de ejemplo del MCC, que nombra a OTROS clientes. Cada cliente
   recibe un script donde solo aparece el suyo.
3. Deja el fichero en caracteres seguros. El editor de Google Ads no siempre pega
   bien los simbolos de dibujo (═ ─ ▸ — …) y revienta con «Invalid or unexpected
   token (line 1)». Se sustituyen por equivalentes ASCII; las tildes se quedan.
"""
import os, re, sys

# Caracteres que el editor de Google Ads puede romper al pegar -> equivalente seguro
SEGURO = {
    '═': '=', '─': '-', '━': '-', '—': '-', '–': '-',
    '→': '->', '←': '<-', '↑': '^', '▸': '>', '…': '...',
    '“': '"', '”': '"', '‘': "'", '’': "'", ' ': ' ',
    '⛔': '[!]', '✅': '[ok]', '⚠': '[!]', '️': '',
}


def limpiar(texto):
    for malo, bueno in SEGURO.items():
        texto = texto.replace(malo, bueno)
    # Cualquier otro caracter fuera de Latin-1 fuera: las tildes y la ñ sí pasan
    return ''.join(c if ord(c) < 256 else '?' for c in texto)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cliente, url = sys.argv[1], sys.argv[2]
    salida = sys.argv[3] if len(sys.argv) > 3 else f"{cliente.lower().replace(' ', '')}.js"

    plantilla = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'ads-script-estacionalidad.js')
    s = open(plantilla, encoding='utf-8').read()

    s = re.sub(r"var SHEET_URL = '[^']*';", f"var SHEET_URL = '{url}';", s, count=1)
    s = re.sub(r"var CLIENTE   = '[^']*';", f"var CLIENTE   = '{cliente}';", s, count=1)

    # Fuera el bloque del MCC: nombra a otros clientes y no se usa en la instalacion normal
    s = re.split(r"/\*\s*-{3,}\s*\n\s*VERSION MCC|/\*\s*─{3,}", s)[0].rstrip() + '\n'
    s = re.sub(r"/\*[^*]*VERSI[OÓ]N MCC.*?\*/", '', s, flags=re.S)

    s = s.replace('PLANTILLA - copiar TODO y pegar en Google Ads.',
                  f'{cliente} - YA RELLENO. Copiar TODO y pegar en Google Ads.')
    s = s.replace('PLANTILLA — copiar TODO y pegar en Google Ads.',
                  f'{cliente} - YA RELLENO. Copiar TODO y pegar en Google Ads.')

    s = limpiar(s)
    if '?' * 2 in s:
        print("  aviso: algun caracter no se pudo convertir, revisa los '??'")

    open(salida, 'w', encoding='utf-8').write(s)
    print(f"OK  {salida}")
    print(f"    cliente: {cliente}")
    print(f"    hoja:    {url[:60]}...")
    print(f"    {len(s.splitlines())} lineas, solo caracteres seguros, sin mencion a otros clientes")
    print("\nPegalo en Google Ads: Herramientas > Acciones en bloque > Secuencias de comandos")


if __name__ == '__main__':
    main()
