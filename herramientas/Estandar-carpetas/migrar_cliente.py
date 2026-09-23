#!/usr/bin/env python3
"""Rehace la hoja de UN cliente con las semanas nuevas. Uso: migrar_cliente.py <clave> [--subir]"""
import os, subprocess, sys, tempfile, openpyxl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migrar_semanas as MS
import montar_hoja_reportes as M
import anadir_hoja_google as G
import montar_hoja_reportes_funnels as MF

CLIENTES = {
 "Cliente 05":  dict(carpeta="i_Cliente 05/c_Cliente 05/6. Reportes", nombre="Reporte Ads — Cliente 05", cliente="Cliente 05", cuenta="<ID_META>", desde=9,
                   sid="<ID_DRIVE>"),
 "jh":        dict(carpeta="i_Cliente 11/c_Cliente 11/6. Reportes", nombre="Reporte Ads — Cliente 11", cliente="Cliente 11", cuenta="act_2052994931821977", desde=7,
                   sid="<ID_DRIVE>"),
 "Cliente 13":dict(carpeta="i_Cliente 13/c_Cliente 13/6. Reportes", nombre="Reporte Ads — Cliente 13", cliente="Cliente 13", cuenta="act_829620521134769", desde=6, google=True,
                   sid="<ID_DRIVE>"),
 "mms":       dict(carpeta="i_Cliente 03/c_Cliente 03/6. Reportes", nombre="Reporte Ads — Cliente 03", cliente="Cliente 03", cuenta="act_3952812701645788", desde=6, google=True,
                   sid="<ID_DRIVE>"),
 "smart":     dict(carpeta="i_Cliente 14/c_Cliente 14/4. Reportes", nombre="Reporte Ads — Cliente 14", cliente="Cliente 14", cuenta="<ID_META>", desde=1,
                   sid="<ID_DRIVE>"),
 "Cliente 06":   dict(carpeta="i_Cliente 06/c_Cliente 06/5. Reportes",
                   nombre="Reporte Ads — Cliente 06", cliente="Cliente 06",
                   cuenta="<ID_META>", desde=4, plantilla="funnels",
                   sid="<ID_DRIVE>"),
 "Cliente 02": dict(carpeta="i_Cliente 02/c_Cliente 02/6. Reportes", nombre="Reporte Ads — Cliente 02", cliente="Cliente 02", cuenta="<ID_META>", desde=6, corte=9,
                   sid="<ID_DRIVE>",
                   funnels=[("Inversión", ["LANDING INVERSION", "FUNNEL INVERSION", "INVERSORES"]),
                            ("Gestión de pisos", ["LANDING GESTION", "FUNNEL GESTION",
                                                  "FORM INTERNO", "| INT |"])]),
}


def bajar(c, destino_dir):
    """Se baja la hoja convertida a xlsx. Se hace con rclone y no con la API de Drive porque
    el endpoint `export` devuelve 403 con el token del remoto `gdrive` (el mismo motivo por
    el que la API de Sheets tampoco está disponible: ese proyecto no la tiene habilitada)."""
    subprocess.run(["rclone", "copy", "gdrive:" + c["carpeta"], destino_dir,
                    "--include", c["nombre"] + "*", "--drive-export-formats", "xlsx"],
                   check=True, capture_output=True)
    hojas = [f for f in os.listdir(destino_dir) if f.endswith(".xlsx")]
    if not hojas:
        raise SystemExit(f"✗ No se pudo bajar la hoja de {c['cliente']}")
    return os.path.join(destino_dir, hojas[0])


def migrar(clave, subir=False):
    c = CLIENTES[clave]
    tmp = tempfile.mkdtemp()
    viejo = bajar(c, tmp)
    resc = MS.rescatar(viejo)
    datos = resc["motor"].get("datos", [])
    print(f"· {c['cliente']}: rescatadas {len(datos)} filas de `datos`, "
          f"{len(resc['motor'].get('ventas', []))} de `ventas`, "
          f"{len(resc['motor'].get('datos-google', []))} de `datos-google`, "
          f"{sum(len(t['manual']) for t in resc['tabs'].values())} celdas a mano")

    if c.get("plantilla") == "funnels":
        # Cliente 06 no usa la plantilla de la casa: Resumen + una pestaña por funnel, y los
        # tres funnels ya están escritos dentro de su script.
        orden = ["Captación de propiedades", "Piso Burriana", "Casas de hormigón"]
        pest = sorted(MF.FUNNELS, key=lambda f: orden.index(f.nombre))
        # Su `construir` espera DICCIONARIOS por fila (mira r["fecha"] y r["gasto"]),
        # no listas como la plantilla de la casa.
        filas_d = [dict(zip(MF.DATOS, list(f[:len(MF.DATOS)]))) for f in datos]
        wb = MF.construir(c["cliente"], c["cuenta"], 2026, c["desde"], MF.FUNNELS,
                          filas_d, pest)
    else:
        wb = M.construir(c["cliente"], c["cuenta"], 2026, c["desde"],
                         [f[:len(M.DATOS)] for f in datos],
                         funnels=c.get("funnels"), corte_mes=c.get("corte"))
    # `ventas` la rehace construir() con la cabecera: se le devuelven sus filas.
    ws = wb["ventas"]
    ancho_v = len(MF.VENTAS) if c.get("plantilla") == "funnels" else len(M.VENTAS)
    for i, f in enumerate(resc["motor"].get("ventas", [])):
        for j, v in enumerate(f[:ancho_v], start=1):
            ws.cell(i + 2, j).value = v
    if c.get("google"):
        G.pestana_reporte(wb, c["cliente"], 2026, c["desde"])
        wsg = G.pestana_datos(wb)
        for i, f in enumerate(resc["motor"].get("datos-google", [])):
            for j, v in enumerate(f[:len(G.DATOS_G)], start=1):
                wsg.cell(i + 2, j).value = v
    puestos, perdidos = MS.devolver(wb, resc)
    for p in puestos:
        print("   ✓", p)
    for p in perdidos:
        print("   ⚠", p)
    nuevo = os.path.join(tmp, "nuevo.xlsx"); wb.save(nuevo)
    if subir:
        MS.subir(nuevo, c["sid"])
        print(f"   ↑ subida: https://docs.google.com/spreadsheets/d/{c['sid']}/edit")
    else:
        print("   (ensayo: no se ha subido nada)", nuevo)
    return nuevo


if __name__ == "__main__":
    migrar(sys.argv[1], "--subir" in sys.argv)
