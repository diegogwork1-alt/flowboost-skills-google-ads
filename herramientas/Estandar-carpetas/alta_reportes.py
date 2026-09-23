#!/usr/bin/env python3
"""Da de alta a un cliente en el sistema de reportes. Se ejecuta UNA vez por cliente.

Después de esto no hay que volver a abrir n8n nunca: los flujos leen la lista de clientes
de la hoja maestra, así que un cliente nuevo entra solo en los envíos.

Qué deja hecho:
  1. La hoja MAESTRA (se crea la primera vez) con sus tres pestañas y cabeceras:
     · `datos`    — una fila por día y campaña, de todos los clientes (la que lee Looker)
     · `clientes` — la lista que leen los tres flujos de n8n
     · `landing`  — una fila por día y cliente con lo de Clarity
     · `ventas`   — las oportunidades GANADAS que trae el CRM de cada cliente
  2. La hoja del CLIENTE en su carpeta de reportes del Drive, con el DISEÑO de la casa
     (`montar_hoja_reportes.py`): una fila por semana, un bloque por mes, el año entero
     montado, y ROAS. El número de la carpeta se busca por nombre (5., 6., 7.…), no se supone.
  3. La hoja de ESTADO DE CUENTA del cliente (`montar_hoja_estado.py`): todas las etapas del
     funnel ya escritas, con desplegable de estado. **Solo se crea si no existe**: regenerarla
     borraría lo que estuviera marcado.
  4. La fila del cliente en la pestaña `clientes`.

Los envíos NO empiezan por esto: el flujo semanal solo manda el reporte cuando ve gasto en
la semana, o sea cuando las campañas ya están en el aire. No hay ningún interruptor que
tocar ni nadie a quien avisar.

Uso:
  python3 alta_reportes.py "<Cliente>" \
      --cuenta act_123456789 \
      --correo cliente@sudominio.com \
      --carpeta "gdrive:i_X/c_X/6. Reportes" \
      [--landing https://...] [--logo https://...] \
      [--objetivos '{"Nombre de campaña":"frase que ve el cliente"}'] \
      [--n8n correo-de-la-credencial-de-n8n] \
      [--maestra <ID>]   # si ya existe; si no, se crea y se imprime

Quién escribe en las hojas: la CUENTA DE SERVICIO
  <cuenta-de-servicio>@<proyecto>.iam.gserviceaccount.com
Vive en el proyecto `<proyecto-google-cloud>`, dentro de la organización de Flowboost. Se
usa una cuenta de servicio y no OAuth porque el OAuth caducaba cada 7 días (la app estaba en
modo Prueba) y había que reconectarlo a mano. Una cuenta de servicio no caduca nunca.
A cada hoja que se crea se le da permiso de editor a esa dirección; sin eso, n8n da 403.

El token de Clarity NO se pone aquí: va en la variable de entorno CLARITY_TOKENS del
contenedor de n8n, como JSON {"<Cliente>":"<token>"}. La hoja acaba en el Drive del
cliente y un token de Clarity da acceso a sus grabaciones.
"""
import argparse, json, os, subprocess, sys, urllib.parse
from datetime import date
from subir_a_drive import api

HOJA = "application/vnd.google-apps.spreadsheet"
PESTANAS = {
    # Mismo orden EXACTO que DATOS en montar_hoja_reportes.py y que el nodo «Armar filas»
    # del flujo diario. Los tres tienen que ir a la par o las fórmulas leen columnas que no son.
    "datos":    ["id","fecha","cliente","campana","gasto","impresiones","alcance","frecuencia",
                 "cpm","clics","clics_enlace","ctr","vistas_landing","leads","actualizado"],
    "clientes": ["cliente","ad_account_id","email","logo_url","objetivos","landing_url",
                 "sheet_id","crm_url","activo"],
    "landing":  ["id","fecha","cliente","sesiones","usuarios","movil_pct","rage_clicks",
                 "dead_clicks","quickback","errores_script","scroll_medio","actualizado"],
    "ventas":   ["id","fecha","cliente","oportunidad","importe","actualizado"],
}


# ─────────────────────────────────────────────────────────────────────────────────────────
# POR QUÉ NO SE USA LA SHEETS API AQUÍ
# El token sale del remoto de rclone, y ese client_id pertenece al proyecto de rclone
# (202264815644), no a Flowboost: la Sheets API está deshabilitada ahí y no la podemos
# habilitar porque el proyecto no es nuestro. Da 403 PERMISSION_DENIED.
# La Drive API sí está habilitada, así que se hace lo mismo que `marcar_etapa.py`:
# exportar la hoja a .xlsx → editarla con openpyxl → volver a subirla al MISMO fichero con
# conversión. Se conservan fórmulas, formatos y desplegables (comprobado).
# ─────────────────────────────────────────────────────────────────────────────────────────
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def crear_maestra():
    h = api("https://www.googleapis.com/drive/v3/files?supportsAllDrives=true",
            data=json.dumps({"name": "Flowboost · Datos Meta", "mimeType": HOJA}).encode(),
            headers={"Content-Type": "application/json"})
    return h["id"]


def _bajar(sid):
    """La hoja de Drive → workbook de openpyxl en un fichero temporal.

    Se reutiliza el descargador de `marcar_etapa.py`: `api()` solo devuelve JSON, y esto es
    un binario. No se duplica la lógica de reintentos.
    """
    import tempfile
    from openpyxl import load_workbook
    from marcar_etapa import _descargar_xlsx
    tmp = os.path.join(tempfile.mkdtemp(), "hoja.xlsx")
    _descargar_xlsx(sid, tmp)
    return load_workbook(tmp), tmp


def _subir(sid, wb, tmp):
    from subir_a_drive import _multipart
    wb.save(tmp)
    cuerpo, cabs = _multipart({"mimeType": HOJA}, tmp, XLSX)
    api(f"https://www.googleapis.com/upload/drive/v3/files/{sid}"
        f"?uploadType=multipart&supportsAllDrives=true",
        data=cuerpo, headers=cabs, metodo="PATCH")


def asegurar_pestanas(sid):
    """Crea las pestañas que falten y escribe las cabeceras. No toca las que ya están."""
    wb, tmp = _bajar(sid)
    creadas = []
    for nombre, cols in PESTANAS.items():
        if nombre in wb.sheetnames:
            ws = wb[nombre]
        else:
            # La hoja nace con una pestaña por defecto ("Sheet1"/"Hoja 1"): se reaprovecha
            # para la primera en vez de dejarla suelta.
            sobrante = [n for n in wb.sheetnames if n not in PESTANAS]
            if sobrante and len(wb.sheetnames) == 1:
                ws = wb[sobrante[0]]; ws.title = nombre
            else:
                ws = wb.create_sheet(nombre)
            creadas.append(nombre)
        if not any(c.value for c in ws[1]):          # cabecera vacía → se escribe
            for j, c in enumerate(cols, start=1):
                ws.cell(row=1, column=j, value=c)
    _subir(sid, wb, tmp)
    return creadas or list(PESTANAS)


def fila_cliente(sid, datos):
    """Escribe o ACTUALIZA la fila del cliente. Nunca duplica: busca por nombre."""
    cols = PESTANAS["clientes"]
    wb, tmp = _bajar(sid)
    ws = wb["clientes"]
    fila = [str(datos.get(c, "")) for c in cols]
    objetivo, accion = None, "añadida"
    for i in range(2, ws.max_row + 1):
        v = ws.cell(row=i, column=1).value
        if v and str(v).strip().lower() == datos["cliente"].strip().lower():
            objetivo, accion = i, "actualizada"
            break
    if objetivo is None:
        # La primera fila con la columna A VACÍA. No vale ws.max_row: la hoja exportada trae
        # ~1000 filas con formato pero sin contenido, y metía al cliente en la fila 1001.
        objetivo = 2
        while ws.cell(row=objetivo, column=1).value not in (None, ""):
            objetivo += 1
    for j, v in enumerate(fila, start=1):
        # Al actualizar, un campo vacío NO borra lo que ya había (día 1 sin cuenta ni correo).
        if accion == "actualizada" and v == "" and ws.cell(row=objetivo, column=j).value:
            continue
        ws.cell(row=objetivo, column=j, value=v)
    _subir(sid, wb, tmp)
    return accion, objetivo


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cliente")
    p.add_argument("--cuenta", default="",
                   help="ad_account_id de Meta. Puede faltar el primer día: llega con los "
                        "accesos. Se rellena volviendo a ejecutar este mismo comando.")
    p.add_argument("--correo", default="",
                   help="a quién se le manda el reporte semanal (puede faltar al principio)")
    p.add_argument("--onboarding", action="store_true",
                   help="es un cliente NUEVO y se está montando el funnel: crea también la hoja de "
                        "«Estado de cuenta». Sin este flag NO se crea — en un cliente que ya está "
                        "en marcha esa hoja estorba (Dirección, 10-09-2026) y el estado del sistema "
                        "vive en Sistemas/ESTADO.md")
    p.add_argument("--carpeta-id", default="",
                   help="ID de Drive de la carpeta de reportes. Salta rclone: es la única vía "
                        "para clientes que están FUERA del remoto anclado (p.ej. Cliente 01, que "
                        "cuelga de la raíz y no de la carpeta madre de clientes)")
    p.add_argument("--carpeta", default="",
                   help="ruta exacta de la carpeta de reportes; si se omite se busca sola "
                        "dentro de --cliente-raiz")
    p.add_argument("--cliente-raiz", default="",
                   help="gdrive:i_X/c_X — de ahí se localiza la carpeta de reportes por "
                        "nombre, sea 5., 6. o 7.")
    p.add_argument("--landing", default="")
    p.add_argument("--crm", default="", help="https://<cliente>.<tu-dominio>")
    p.add_argument("--logo", default="")
    p.add_argument("--objetivos", default="{}",
                   help='JSON {"campaña":"frase para el cliente"}')
    p.add_argument("--n8n", default="<cuenta-de-servicio>@<proyecto>.iam.gserviceaccount.com",
                   help="cuenta de servicio con la que n8n escribe. Por defecto la de la casa.")
    p.add_argument("--maestra", default="", help="ID de la hoja maestra si ya existe")
    p.add_argument("--anio", type=int, default=date.today().year)
    p.add_argument("--desde-mes", type=int, default=date.today().month,
                   help="primer mes que se monta en la hoja (por defecto, el actual)")
    p.add_argument("--datos", default="",
                   help="JSON de histórico para dejar la hoja ya rellena la primera vez")
    a = p.parse_args()

    try:
        json.loads(a.objetivos)
    except json.JSONDecodeError as e:
        sys.exit(f"✗ --objetivos no es JSON válido: {e}")

    # El número de la carpeta de reportes cambia según el cliente: se busca por nombre.
    carpeta = a.carpeta
    if a.carpeta_id:
        carpeta = None                      # se usa el ID tal cual, sin pasar por rclone
    elif not carpeta:
        if not a.cliente_raiz:
            sys.exit("✗ Hace falta --carpeta-id, --carpeta o --cliente-raiz.")
        from carpeta_reportes import buscar
        carpeta = buscar(a.cliente_raiz)
        if not carpeta:
            sys.exit(f"✗ No hay carpeta de reportes dentro de {a.cliente_raiz}. "
                     f"La crea Operaciones; el agente no la inventa.")
        print(f"✓ Carpeta de reportes encontrada: {carpeta}")

    # Al reejecutar no se pisa con vacío lo que ya estaba puesto.
    previo = {}
    if a.maestra:
        try:
            wb, _ = _bajar(a.maestra)
            cols = PESTANAS["clientes"]
            ws = wb["clientes"]
            for i in range(2, ws.max_row + 1):
                v0 = ws.cell(row=i, column=1).value
                if v0 and str(v0).strip().lower() == a.cliente.strip().lower():
                    f = [ws.cell(row=i, column=j).value or "" for j in range(1, len(cols) + 1)]
                    previo = dict(zip(cols, [str(x) for x in f]))
                    break
        except Exception:
            previo = {}

    maestra = a.maestra or crear_maestra()
    if not a.maestra:
        print(f"✓ Hoja maestra creada: {maestra}")
        print("  ⚠ Pégala en los tres flujos de n8n (campo `documentId`). Solo esta vez.")
    print("✓ Pestañas:", ", ".join(asegurar_pestanas(maestra)))
    if a.n8n:
        api(f"https://www.googleapis.com/drive/v3/files/{maestra}/permissions"
            f"?supportsAllDrives=true&sendNotificationEmail=false",
            data=json.dumps({"role": "writer", "type": "user",
                             "emailAddress": a.n8n}).encode(),
            headers={"Content-Type": "application/json"})
        print(f"✓ Maestra compartida con {a.n8n}")

    # La hoja del cliente se monta con la plantilla de la casa (diseño + fórmulas por semana).
    from subir_a_drive import folder_id
    carpeta_id = a.carpeta_id or folder_id(carpeta)
    aqui = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, os.path.join(aqui, "montar_hoja_reportes.py"),
           "--cliente", a.cliente, "--cuenta", a.cuenta or previo.get("ad_account_id", "") or "(pendiente)",
           "--anio", str(a.anio), "--desde-mes", str(a.desde_mes),
           "--carpeta-id", carpeta_id]
    if a.datos:
        cmd += ["--datos", a.datos]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=aqui)
    if r.returncode != 0:
        sys.exit(f"✗ No se pudo montar la hoja del cliente:\n{r.stdout}{r.stderr}")
    print(r.stdout.strip())
    sheet_id = r.stdout.strip().splitlines()[-1]

    # Permiso de edición para la cuenta con la que n8n escribe cada mañana.
    if a.n8n:
        api(f"https://www.googleapis.com/drive/v3/files/{sheet_id}/permissions"
            f"?supportsAllDrives=true&sendNotificationEmail=false",
            data=json.dumps({"role": "writer", "type": "user",
                             "emailAddress": a.n8n}).encode(),
            headers={"Content-Type": "application/json"})
        print(f"✓ Hoja del cliente compartida con {a.n8n}")

    def mantener(nuevo, clave):
        return nuevo or previo.get(clave, "")

    # Hoja de estado de cuenta: SOLO para clientes NUEVOS.
    # Sirve para MONTAR un cliente (en qué punto va el proceso). En una cuenta que ya lleva
    # meses funcionando no aporta nada y estorba: Dirección borró la de Cliente 03 por eso
    # (10-09-2026, «no es un set-up, esto ya es cliente y hay que mejorar cosas»).
    if not a.onboarding:
        print("= Hoja de estado: NO se crea. Solo va en ONBOARDING NUEVO (--onboarding);\n"
              "  para clientes en marcha, el estado vive en Sistemas/ESTADO.md.")
        est = None
    else:
        est = subprocess.run(
        [sys.executable, os.path.join(aqui, "montar_hoja_estado.py"),
         "--cliente", a.cliente, "--carpeta-id", carpeta_id],
        capture_output=True, text=True, cwd=aqui)
    if est is not None and est.returncode == 0:
        if "regenerada" in est.stdout:
            print("= Hoja de estado: ya existía, se deja como está (tiene marcas dentro).")
        else:
            print(est.stdout.strip().splitlines()[0])
        if a.n8n:
            try:
                api(f"https://www.googleapis.com/drive/v3/files/"
                    f"{est.stdout.strip().splitlines()[-1]}/permissions"
                    f"?supportsAllDrives=true&sendNotificationEmail=false",
                    data=json.dumps({"role": "writer", "type": "user",
                                     "emailAddress": a.n8n}).encode(),
                    headers={"Content-Type": "application/json"})
            except Exception:
                pass
    else:
        print(f"! No se pudo montar la hoja de estado:\n{est.stdout}{est.stderr}")

    accion, n = fila_cliente(maestra, {
        "cliente": a.cliente,
        "ad_account_id": mantener(a.cuenta, "ad_account_id"),
        "email": mantener(a.correo, "email"),
        "logo_url": mantener(a.logo, "logo_url"),
        "objetivos": a.objetivos if a.objetivos != "{}" else mantener("", "objetivos") or "{}",
        "landing_url": mantener(a.landing, "landing_url"),
        "crm_url": mantener(a.crm, "crm_url"),
        "sheet_id": sheet_id, "activo": "si"})
    print(f"✓ Fila del cliente {accion} (fila {n}) en la pestaña `clientes`")
    print(f"\n{a.cliente} queda dado de alta.")
    print("  · Cada mañana a las 8:00 se rellena su hoja sola.")
    print("  · El reporte al cliente sale el primer VIERNES con gasto en la cuenta —o sea, "
          "cuando las campañas ya están publicadas—. No hay que activar nada.")
    faltan = []
    if not mantener(a.cuenta, "ad_account_id"):
        faltan.append("la cuenta de Meta (llega con los accesos, etapa 2)")
    if not mantener(a.correo, "email"):
        faltan.append("el correo del cliente")
    if not mantener(a.landing, "landing_url"):
        faltan.append("la landing (se publica en A7)")
    if not mantener(a.crm, "crm_url"):
        faltan.append("el CRM (se monta en A7-bis; sin él el ROAS se queda en estimación)")
    print(f"\n  Las hojas quedan compartidas con {a.n8n}")
    if faltan:
        print("\n  ⚠ Todavía falta: " + "; ".join(faltan) + ".")
        print("    Se rellena volviendo a ejecutar ESTE MISMO comando con el dato. "
              "No duplica: actualiza la fila.")


if __name__ == "__main__":
    main()
