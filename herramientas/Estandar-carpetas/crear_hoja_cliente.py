#!/usr/bin/env python3
"""Crea (una sola vez por cliente) la hoja de reportes dentro de su Drive.

La hoja vive en la carpeta «6. Reportes» del cliente y la rellena cada mañana el
flujo de n8n `datos-diarios-meta` (una fila por día y campaña). Aquí sólo se crea
el contenedor: nombre, pestaña «datos» y cabeceras en el orden que escribe n8n.

IDEMPOTENTE: si la hoja ya existe en esa carpeta, no crea otra — devuelve su ID.

Uso:
  python3 crear_hoja_cliente.py "<Cliente>" "gdrive:i_X/c_X/6. Reportes" [correo-de-n8n]

Imprime el ID de la hoja: es el `sheet_id` que se pega en el nodo «Clientes diario»
del flujo de n8n.

El tercer argumento es OBLIGATORIO en la práctica: la hoja se crea con la identidad
de rclone, pero quien escribe cada mañana es la credencial de Google Sheets de n8n,
que es otra cuenta. Sin darle permiso de edición, el flujo falla con 403 aunque la
hoja exista. Pasá el correo de esa credencial y se comparte como editor.
"""
import json, sys, urllib.parse
from subir_a_drive import api, folder_id

HOJA = "application/vnd.google-apps.spreadsheet"
CABECERAS = ["id", "fecha", "cliente", "campana", "gasto", "leads", "cpl", "actualizado"]


def buscar_hoja(nombre, fid):
    n = nombre.replace("\\", "\\\\").replace("'", "\\'")
    q = (f"name = '{n}' and '{fid}' in parents and trashed = false "
         f"and mimeType = '{HOJA}'")
    url = ("https://www.googleapis.com/drive/v3/files?"
           + urllib.parse.urlencode({"q": q, "fields": "files(id,name)",
                                     "supportsAllDrives": "true",
                                     "includeItemsFromAllDrives": "true"}))
    return api(url).get("files", [])


def compartir(sid, correo):
    """Permiso de editor para la cuenta con la que n8n escribe en la hoja."""
    api(f"https://www.googleapis.com/drive/v3/files/{sid}/permissions"
        f"?supportsAllDrives=true&sendNotificationEmail=false",
        data=json.dumps({"role": "writer", "type": "user",
                         "emailAddress": correo}).encode(),
        headers={"Content-Type": "application/json"})
    print(f"✓ Compartida como editor con {correo}")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cliente, carpeta = sys.argv[1], sys.argv[2]
    nombre = f"Reporte diario — {cliente}"
    fid = folder_id(carpeta)

    correo = sys.argv[3] if len(sys.argv) > 3 else None

    ya = buscar_hoja(nombre, fid)
    if ya:
        sid = ya[0]["id"]
        print(f"= Ya existía, no se duplica: {nombre}")
        if correo:
            compartir(sid, correo)
        print(sid)
        return

    meta = {"name": nombre, "mimeType": HOJA, "parents": [fid]}
    hoja = api("https://www.googleapis.com/drive/v3/files?supportsAllDrives=true",
               data=json.dumps(meta).encode(),
               headers={"Content-Type": "application/json"})
    sid = hoja["id"]

    # Pestaña «datos» + cabeceras: n8n busca la pestaña por nombre y mapea por columna.
    api(f"https://sheets.googleapis.com/v4/spreadsheets/{sid}:batchUpdate",
        data=json.dumps({"requests": [
            {"updateSheetProperties": {"properties": {"sheetId": 0, "title": "datos"},
                                       "fields": "title"}}]}).encode(),
        headers={"Content-Type": "application/json"})
    api(f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/"
        f"datos!A1:H1?valueInputOption=RAW",
        data=json.dumps({"values": [CABECERAS]}).encode(),
        headers={"Content-Type": "application/json"}, metodo="PUT")

    if correo:
        compartir(sid, correo)
    else:
        print("! Sin correo de n8n: acordate de darle permiso de editor o el flujo dará 403.")

    print(f"✓ Creada: {nombre}  →  {carpeta}")
    print(sid)


if __name__ == "__main__":
    main()
