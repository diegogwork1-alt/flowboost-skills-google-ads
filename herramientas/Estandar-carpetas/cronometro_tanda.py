#!/usr/bin/env python3
"""Cronómetro de la tanda: dónde se va el tiempo de verdad.

Por qué (consejo, 13-09-2026): nadie había medido una tanda por fases. La sospecha es que el tiempo
no está en Drive sino en las RONDAS DE CAMBIOS (18 imágenes con hasta 4 rondas son ~40
generaciones). Antes de meter más agentes o recortar piezas, se mide. `preparar_tanda.py`,
`recoger_png.py` y `cerrar_tanda.py` marcan solos; el resto se marca con este comando.

Eventos que se marcan a mano (los demás van solos):
  gpt_envio   → justo después de enviar un mensaje de generación al GPT (--pieza 03 --nota "1x1 r1")
  cambios     → al mandar un CAMBIOS (--pieza 03)
  veredicto   → al recibir el veredicto del auditor (--nota PASA|CAMBIOS|REGENERATE)
  pieza_ok    → al cerrar una pieza (panel aprobado)

Uso:
  python3 cronometro_tanda.py "Cliente 04" 2 marca gpt_envio --pieza 03 --nota "1x1 r1"
  python3 cronometro_tanda.py "Cliente 04" 2 resumen
"""
import argparse, csv, datetime as dt, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tanda_lib as L


def mmss(s):
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"


def resumen(cli, n):
    p = L.fichero_tiempos(cli, n)
    if not os.path.exists(p):
        sys.exit(f"✗ No hay cronómetro de la Tanda {n} en {p}")
    ev = [(dt.datetime.fromisoformat(r["ts"]), r["evento"], r["pieza"], r["nota"])
          for r in csv.DictReader(open(p, encoding="utf-8"))]
    if not ev:
        sys.exit("✗ Cronómetro vacío")
    total = (ev[-1][0] - ev[0][0]).total_seconds()

    def entre(a, b):
        t0 = next((e[0] for e in ev if e[1] == a), None)
        t1 = next((e[0] for e in reversed(ev) if e[1] == b), None)
        return (t1 - t0).total_seconds() if t0 and t1 else 0

    fase0 = entre("fase0_ini", "fase0_fin")
    cierre = entre("cierre_ini", "cierre_fin")
    # Generación = de cada envío a la siguiente imagen recogida.
    gen, pendiente = 0, None
    for t, e, _, _ in ev:
        if e == "gpt_envio":
            pendiente = t
        elif e == "gpt_imagen" and pendiente:
            gen += (t - pendiente).total_seconds(); pendiente = None
    rondas = defaultdict(int)
    for _, e, pz, _ in ev:
        if e == "cambios":
            rondas[pz] += 1
    piezas = sorted({pz for _, e, pz, _ in ev if pz})
    a_la_primera = sum(1 for pz in piezas if rondas[pz] == 0)
    envios = sum(1 for e in ev if e[1] == "gpt_envio")
    imagenes = sum(1 for e in ev if e[1] == "gpt_imagen")

    print(f"TIEMPOS — {cli} · Tanda {n}")
    print(f"  total {mmss(total)} · fase 0 {mmss(fase0)} · esperando al GPT {mmss(gen)}"
          f" ({gen / total:.0%}) · cierre {mmss(cierre)}")
    print(f"  {imagenes} imágenes para {len(piezas)} piezas · {envios} envíos · "
          f"{sum(rondas.values())} CAMBIOS · a la primera: {a_la_primera}/{len(piezas)}")
    if piezas:
        print("  CAMBIOS por pieza: " + ", ".join(f"{pz}:{rondas[pz]}" for pz in piezas))
    if total and sum(rondas.values()) > len(piezas):
        print("  → Las rondas de CAMBIOS pesan más que las piezas: la palanca es el mensaje base "
              "(y menos piezas), no más agentes. Ver consejo del 13-09-2026.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente"); ap.add_argument("tanda", type=int)
    ap.add_argument("accion", choices=["marca", "resumen"])
    ap.add_argument("evento", nargs="?")
    ap.add_argument("--pieza", default=""); ap.add_argument("--nota", default="")
    a = ap.parse_args()
    if a.accion == "marca":
        if not a.evento:
            sys.exit("✗ Falta el evento")
        L.marcar(a.cliente, a.tanda, a.evento, a.pieza, a.nota)
    else:
        resumen(a.cliente, a.tanda)


if __name__ == "__main__":
    main()
