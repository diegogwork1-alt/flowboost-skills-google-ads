#!/usr/bin/env python3
"""Volcados del MCP de Meta → el datos.json que comen montar_hoja_reportes y actualizar_datos.

⚠ EL MCP CAMBIA EL FORMATO DE LOS NÚMEROS SIN AVISAR. Hasta el 17-09-2026 el gasto venía
como la cadena «€22,47 EUR» (coma decimal, es-ES); el 22-09 pasó a ser el objeto
{"value":"22.47","unit":"EUR"} (punto decimal). Parsearlo con la regla vieja daba
157.066 € en un mes de 1.819,78 € — un ×86 que no rompe nada, solo miente. Por eso aquí
no se asume ningún formato: se acepta dict o cadena, y el ÚLTIMO separador que aparece
es el decimal (vale para 22.47, 22,47, 1.087,07 y 1,087.07).
"""
import json, glob, os, re, sys, collections

LEAD = {"conversions:offsite_conversion.fb_pixel_custom.TypeformSubmit",
        "actions:leadgen.other", "actions:offsite_conversion.fb_pixel_complete_registration",
        "actions:lead"}

def dec(v):
    """Decimal. El formato lo decide el ORIGEN, no una heurística sobre las cifras.

    · dict {"value": "1,087.07"}  → como lo manda el MCP hoy: coma = miles, punto = decimal.
    · "€1.087,07 EUR"             → como lo mandaba hasta el 17-09: punto = miles, coma = decimal.
    · "1.305284" / "1,65%"        → sin símbolo de moneda no hay miles: el separador es decimal.

    Adivinar por el número de cifras NO vale: la frecuencia «1.525» se convertía en 1525.
    """
    if v is None: return 0.0
    if isinstance(v, dict):                      # en-US: la coma es de miles
        s = re.sub(r"[^\d.\-]", "", str(v.get("value", "")))
        return float(s) if s else 0.0
    s = str(v)
    if s in ("", "Not available"): return 0.0
    moneda = "€" in s or "EUR" in s
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s: return 0.0
    if moneda:                                   # es-ES: el punto es de miles
        return float(s.replace(".", "").replace(",", "."))
    return float(s.replace(",", "."))            # sin moneda: el separador es decimal


def ent(v):
    return int(round(dec(v)))


def leads(res):
    if not isinstance(res, dict): return 0, None
    ind = res.get("indicator")
    if ind not in LEAD: return 0, ind
    return int(sum(dec(x.get("value")) for x in res.get("values", []) or [])), None

def main(D, SAL, CLIENTE, MARCA=""):
    """MARCA: si la cuenta tiene campañas que NO gestionamos (publicaciones que promociona
    el propio cliente, por ejemplo), solo entran las que la contengan en el nombre. En
    Cliente 05 eran 166 € de gasto ajeno metidos en el reporte del cliente."""
    filas, campanas, ajenas = {}, {}, {}
    desc = collections.defaultdict(lambda: [0, 0.0])
    for f in sorted(glob.glob(os.path.join(D, "*ads_get_ad_entities*.txt"))):
        for r in json.loads(json.load(open(f))["ad_entities"]):
            gasto = dec(r.get("amount_spent")); n, raro = leads(r.get("results"))
            if raro and gasto > 0:
                desc[raro][0] += 1; desc[raro][1] += gasto
            if gasto == 0 and not n: continue
        if MARCA and MARCA.lower() not in str(r.get("name", "")).lower():
            ajenas[r.get("name", "")] = ajenas.get(r.get("name", ""), 0) + gasto
            continue
            cid, fecha = r["id"], r["date_start"]; campanas[cid] = {"nombre": r["name"]}
            filas[(fecha, cid)] = [fecha, cid, round(gasto, 2), ent(r.get("impressions")),
                ent(r.get("clicks")), ent(r.get("link_click")),
                ent(r.get("omni_landing_page_view")), ent(r.get("reach")),
                round(dec(r.get("frequency")), 6), round(dec(r.get("cpm")), 2),
                round(dec(r.get("ctr")), 4), n]

    json.dump({"cliente": CLIENTE, "campanas": campanas,
               "filas": sorted(filas.values(), key=lambda x: (x[0], x[1]))},
              open(SAL, "w"), ensure_ascii=False)
    # Sin filas no hay nada que escribir, y `max()` sobre vacío revienta. Pasa cuando el
    # volcado no trae ninguna campaña de este cliente (o el filtro `marca_campanas` las
    # deja todas fuera): es un aviso, no un error que deba tumbar la pasada de los demás.
    if not filas:
        print("filas: 0 — este volcado no trae ninguna campaña de este cliente"
              + (f" con la marca «{MARCA}»" if MARCA else ""))
        return
    print(f"filas: {len(filas)} · última fecha: {max(f[0] for f in filas.values())}")
    if ajenas:
        print(f"  campañas FUERA del reporte (no llevan «{MARCA}»): "
              f"{sum(ajenas.values()):.2f} € en {len(ajenas)}")
        for k, v in sorted(ajenas.items(), key=lambda x: -x[1]):
            print(f"     · {v:8.2f} €  {k[:60]}")
    for k, (n, g) in sorted(desc.items(), key=lambda x: -x[1][1]):
        print(f"  ⚠ indicador NO contado como lead: {k} ×{n} filas · {g:.2f} € de gasto afectado")
    t = collections.defaultdict(lambda: [0.0, 0])
    for f in filas.values(): m = f[0][:7]; t[m][0] += f[2]; t[m][1] += f[11]
    for m in sorted(t): print(f"  {m}  {t[m][0]:9.2f} €  {t[m][1]:3d} leads")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3],
         sys.argv[4] if len(sys.argv) > 4 else "")
