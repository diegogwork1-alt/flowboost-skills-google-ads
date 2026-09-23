#!/usr/bin/env python3
"""Rellena la plantilla del reporte semanal de Meta con datos reales.

Entrada: un JSON con el cliente, la semana y las campañas. Salida: el HTML del correo.
Réplica del reporte que Dirección ya envía (formato aprobado, 07-09-2026).

  python3 generar_reporte.py datos.json salida.html

Formato del JSON:
{
  "cliente": "Cliente 06",
  "logo_url": "https://…/logo.png",
  "semana": "Semana del 16 al 22 de agosto",
  "campanas": [
    {"nombre": "Venta de piso — Burriana",
     "objetivo": "encontrar compradores para pisos en Burriana.",
     "gasto": 55.88, "leads": 5}
  ]
}
Las campañas con gasto 0 NO se listan: se cuentan en la nota del pie.
"""
import json, os, sys, pathlib

TPL = pathlib.Path(__file__).resolve().parent.parent / "templates" / "reporte.html"


def eur(x):
    return "€" + f"{x:,.2f}".replace(",", "·").replace(".", ",").replace("·", ".")


def tarjeta(c):
    cpl = eur(c["gasto"] / c["leads"]) if c.get("leads") else "—"
    mini = lambda t, v: (
        '<td width="33%" valign="top" style="padding:0 4px">'
        '<table role="presentation" width="100%" style="background:#faf9fc;border-radius:6px"><tr><td style="padding:10px 12px">'
        f'<div style="font-size:10px;color:#8a8a94;font-weight:700">{t}</div>'
        f'<div style="font-size:16px;font-weight:800;color:#0b0b0f;margin-top:3px">{v}</div>'
        "</td></tr></table></td>")
    return (
        '<table role="presentation" width="100%" style="border:1px solid #e6e6ea;border-radius:8px;margin-top:10px">'
        '<tr><td style="padding:14px 14px 8px">'
        f'<div style="font-size:14px;font-weight:800;color:#0b0b0f">{c["nombre"]}</div>'
        f'<div style="font-size:12px;color:#6b6b76;margin-top:3px">Objetivo: {c["objetivo"]}</div>'
        '<table role="presentation" width="100%" style="margin-top:10px"><tr>'
        + mini("Invertido", eur(c["gasto"]))
        + mini("Clientes potenciales", str(c.get("leads", 0)))
        + mini("Coste x c. potencial", cpl)
        + "</tr></table></td></tr></table>")


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    d = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    activas = [c for c in d["campanas"] if c.get("gasto", 0) > 0]
    sin_inv = len(d["campanas"]) - len(activas)
    activas.sort(key=lambda c: -c["gasto"])

    gasto = sum(c["gasto"] for c in activas)
    leads = sum(c.get("leads", 0) for c in activas)
    nota = (f'<div style="margin-top:10px;font-size:11px;color:#9a9aa4">+ {sin_inv} '
            f'campaña{"s" if sin_inv != 1 else ""} sin inversión esta semana.</div>') if sin_inv else ""

    html = TPL.read_text(encoding="utf-8")
    for k, v in {
        "{{CLIENTE}}": d["cliente"], "{{LOGO_URL}}": d.get("logo_url", ""),
        "{{SEMANA}}": d["semana"], "{{GASTO}}": eur(gasto), "{{LEADS}}": str(leads),
        "{{CPL}}": eur(gasto / leads) if leads else "—",
        "{{CAMPANAS}}": "\n".join(tarjeta(c) for c in activas),
        "{{NOTA_SIN_INVERSION}}": nota,
    }.items():
        html = html.replace(k, v)

    pathlib.Path(sys.argv[2]).write_text(html, encoding="utf-8")
    print(f"OK → {sys.argv[2]} · {len(activas)} campañas con inversión, {sin_inv} sin · "
          f"{eur(gasto)} · {leads} leads · CPL {eur(gasto/leads) if leads else '—'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
