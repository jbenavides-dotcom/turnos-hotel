#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GENERADOR de propuesta de parrilla semanal para el Hotel LP&ET.

A partir de la OCUPACIÓN por noche (Cloudbeds → data/ocupacion.json) y las reglas
de Lina, propone un horario para la semana. SOLO LECTURA / PREVIEW:
  - NO toca la hoja de Google.
  - Escribe una vista HTML en data/ y una tabla en consola.
  - Se auto-valida con validador_reglas.validar() para confirmar que cumple.

Es una propuesta v1 con heurísticas explícitas (la rotación exacta no está fijada
en el documento), pensada para revisar con Lina y ajustar.

Uso:
    python generar_parrilla.py                  # próxima semana (lun-dom)
    python generar_parrilla.py --semana 2026-06-22
"""
import os, sys, json, datetime as dt
import validador_reglas as V

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))

# --- Personal y roles (de REGLAS DE TURNOS) ---
PERSONAS = [
    ("CLAUDIA TORRES", "cocina"), ("MARIBEL PAEZ", "cocina"), ("ZAIRA", "cocina"),
    ("NICOLAS SARMIENTO", "servicio"), ("SHEAN PAUL GUTIERREZ", "servicio"),
    ("KELLY CRUZ", "guia"), ("DANIELA MONROY", "admin"), ("GERWIN", "comercial"),
    ("CLAUDIA MONTENEGRO", "areas_publicas"), ("DEISY RODRIGUEZ", "areas_publicas"),
    ("DIEGO DIAZ", "conductor"),
]
ROL = dict(PERSONAS)

# Elegibilidad por función (primario -> backups, según la matriz de Lina)
ELEGIBLES = {
    "cocina":         ["CLAUDIA TORRES", "MARIBEL PAEZ", "ZAIRA",
                       "CLAUDIA MONTENEGRO", "DEISY RODRIGUEZ"],  # ClauM/Deisy apoyan AM con 1-2 cab
    "servicio":       ["NICOLAS SARMIENTO", "SHEAN PAUL GUTIERREZ",
                       "GERWIN", "KELLY CRUZ", "DANIELA MONROY", "ZAIRA"],
    "guia":           ["KELLY CRUZ", "DANIELA MONROY"],
    "areas_publicas": ["CLAUDIA MONTENEGRO", "DEISY RODRIGUEZ"],
    "conductor":      ["DIEGO DIAZ"],
    "admin":          ["DANIELA MONROY"],
}

# Turnos (etiqueta -> (entrada, salida) en el formato de la hoja)
TURNOS = {
    "AM":        ("7:00 am", "3:00 pm"),
    "PM":        ("2:00 pm", "CIERRE"),
    "DIA":       ("8:00 am", "4:00 pm"),
    "CONDUCTOR": ("9:00 am", "5:00 pm"),
    "TOUR":      ("9:00 am", "5:00 pm"),
    "LIGHT":     ("8:00 am", "4:00 pm"),   # día sin huéspedes: sale <= 6pm
    "AMCIERRE":  ("7:00 am", "CIERRE"),    # domingo checkout-total: mañana se queda
}


def necesidades(cab, weekday):
    """Lista de (función, turno) que requiere el día según ocupación y reglas."""
    need = []
    refuerzo = cab is not None and cab > V.UMBRAL_REFUERZO
    if cab == 0 and weekday < 5:
        # entre semana sin huéspedes -> operación mínima, salir máx 6pm
        return [("cocina", "LIGHT"), ("areas_publicas", "LIGHT")]
    if cab == 0 and weekday == 6:
        # domingo sin huéspedes (checkout-total) -> mañana hasta cierre, resto descansa
        return [("cocina", "AMCIERRE"), ("servicio", "AMCIERRE")]
    # con huéspedes (o fin de semana)
    need += [("cocina", "AM"), ("servicio", "PM")]          # abre desayuno + cierra servicio
    if cab and cab >= 1:
        need += [("areas_publicas", "DIA")]                 # aseo/montaje cabañas
    if cab and cab >= 3:
        need += [("cocina", "PM"), ("guia", "TOUR"),        # cena + tour
                 ("areas_publicas", "DIA")]
    if refuerzo:                                            # > 7 cabañas
        need += [("servicio", "AM"),                        # 2ª persona en servicio
                 ("cocina", "PM")]                          # Zaira a cocina (se prioriza abajo)
    need += [("conductor", "CONDUCTOR")]
    return need


def generar(week_mon, occ):
    fechas = [week_mon + dt.timedelta(days=i) for i in range(7)]
    trabajados = {p: 0 for p, _ in PERSONAS}        # para repartir parejo
    parrilla = {p: {} for p, _ in PERSONAS}          # formato validador

    for f in fechas:
        cab = occ.get(f.isoformat())
        need = necesidades(cab, f.weekday())
        ocupados = set()
        refuerzo = cab is not None and cab > V.UMBRAL_REFUERZO
        for func, turno in need:
            cands = [p for p in ELEGIBLES.get(func, []) if p not in ocupados]
            if not cands:
                continue
            # En refuerzo, la 2ª de cocina debe ser Zaira (apoya a Claudia)
            if refuerzo and func == "cocina" and turno == "PM" and "ZAIRA" in cands:
                elegido = "ZAIRA"
            else:
                # primero quien menos ha trabajado (rotación/equidad), respeta orden de elegibilidad
                elegido = min(cands, key=lambda p: (trabajados[p], ELEGIBLES[func].index(p)))
            ocupados.add(elegido)
            trabajados[elegido] += 1
            e, s = TURNOS[turno]
            pe, ps = V.parse_hora(e), V.parse_hora(s)
            parrilla[elegido][f] = {"in": pe[1], "out": ps[1],
                                    "cierre": ps[0] == "CIERRE", "raw": (e, s),
                                    "turno": turno}
        # quien no quedó asignado ese día -> DESCANSO
        for p, _ in PERSONAS:
            if f not in parrilla[p]:
                parrilla[p][f] = {"estado": "DESCANSO"}

    # Garantía: cada persona descansa >=1 día/semana (con esta ocupación baja se cumple solo)
    return parrilla, fechas


def render_html(parrilla, fechas, occ, ruta):
    def celda(r):
        if not r:
            return ('<td style="background:#fff"></td>')
        if r.get("estado") == "DESCANSO":
            return '<td style="background:#eceff1;color:#90a4ae">descanso</td>'
        e, s = r["raw"]
        t = r.get("turno", "")
        col = {"AM": "#e8f5e9", "AMCIERRE": "#c8e6c9", "PM": "#e3f2fd",
               "DIA": "#fff8e1", "LIGHT": "#fce4ec", "TOUR": "#f3e5f5",
               "CONDUCTOR": "#e0f7fa"}.get(t, "#f5f5f5")
        return f'<td style="background:{col}"><b>{e}</b><br>{s}</td>'

    th = "".join(
        f'<th>{f.strftime("%a")} {f.day}<br><span style="font-weight:400">'
        f'🛏 {occ.get(f.isoformat(), "?")} cab</span></th>' for f in fechas)
    rows = ""
    for p, _rol in PERSONAS:
        tds = "".join(celda(parrilla[p].get(f)) for f in fechas)
        rows += f'<tr><td class="nm">{p.title()}<br><span class="rol">{ROL[p]}</span></td>{tds}</tr>'
    html = f"""<!doctype html><html lang="es"><meta charset="utf-8">
<title>Propuesta de turnos · semana {fechas[0]}</title>
<style>
 body{{font-family:'Segoe UI',Arial,sans-serif;margin:24px;color:#263238;background:#fafafa}}
 h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#607d8b;margin:0 0 18px}}
 table{{border-collapse:collapse;width:100%;font-size:12px;background:#fff;box-shadow:0 1px 4px #0001}}
 th,td{{border:1px solid #e0e0e0;padding:6px 8px;text-align:center;vertical-align:middle}}
 th{{background:#37474f;color:#fff;font-weight:600}}
 td.nm{{text-align:left;font-weight:600;background:#fafafa;white-space:nowrap}}
 .rol{{font-weight:400;color:#90a4ae;font-size:10px}}
 .leg{{margin-top:14px;font-size:12px;color:#546e7a}} .leg span{{padding:2px 8px;border-radius:3px;margin-right:6px}}
 .note{{margin-top:10px;font-size:12px;color:#78909c;max-width:900px}}
</style>
<h1>Propuesta de turnos — Hotel LP&amp;ET</h1>
<p class="sub">Semana {fechas[0].strftime('%d/%m')} – {fechas[-1].strftime('%d/%m/%Y')} ·
ocupación en vivo de Cloudbeds · <b>PROPUESTA (no escrita en la hoja)</b></p>
<table><tr><th>Colaborador</th>{th}</tr>{rows}</table>
<div class="leg">
 <span style="background:#e8f5e9">AM 7–3</span>
 <span style="background:#e3f2fd">PM 2–cierre</span>
 <span style="background:#fff8e1">Día 8–4</span>
 <span style="background:#f3e5f5">Tour 9–5</span>
 <span style="background:#e0f7fa">Conductor 9–5</span>
 <span style="background:#fce4ec">Light ≤6pm</span>
 <span style="background:#eceff1">descanso</span>
</div>
<p class="note">Heurística v1 a partir de las reglas: con 0 cabañas entre semana → operación mínima ≤6pm;
con huéspedes → apertura AM + cierre de servicio; ≥3 cab → cena + tour + aseo reforzado;
&gt;7 cab → 2 en servicio + Zaira a cocina. Cada persona descansa ≥1 día. Ajustable con Lina.</p>
</html>"""
    open(ruta, "w", encoding="utf-8").write(html)


def main():
    args = sys.argv[1:]
    hoy = dt.date.today()
    if "--semana" in args:
        mon = dt.date.fromisoformat(args[args.index("--semana") + 1])
        mon -= dt.timedelta(days=mon.weekday())
    else:
        mon = hoy + dt.timedelta(days=(0 - hoy.weekday()) % 7)  # próximo lunes (o hoy si es lunes)

    occ = V.cargar_ocupacion()
    parrilla, fechas = generar(mon, occ)

    # --- consola ---
    print(f"== Propuesta de turnos · semana {fechas[0]} → {fechas[-1]} ==")
    print("   (PREVIEW, no se escribe en la hoja de Google)\n")
    cab_line = "        " + " ".join(f"{(occ.get(f.isoformat(),'?')):>10}" for f in fechas)
    print("CABAÑAS:" + cab_line)
    hdr = " " * 22 + " ".join(f"{f.strftime('%a')+str(f.day):>10}" for f in fechas)
    print(hdr)
    for p, _r in PERSONAS:
        cells = []
        for f in fechas:
            r = parrilla[p][f]
            if r.get("estado") == "DESCANSO":
                cells.append(f"{'desc':>10}")
            else:
                cells.append(f"{r['raw'][0].replace(' ',''):>10}")
        print(f"{p.title():22}" + " ".join(cells))

    # --- auto-validación con el motor de reglas ---
    Vio, War, Inf = V.validar(parrilla, fechas, occ)
    print("\n-- Auto-validación de la propuesta --")
    print(f"   violaciones: {len(Vio)} · advertencias: {len(War)}")
    for x in Vio: print("   ❌", x)
    for x in War: print("   ⚠️", x)
    if not Vio and not War:
        print("   ✅ la propuesta cumple las reglas de Lina.")

    # --- HTML ---
    ruta = os.path.join(AQUI, "data", f"propuesta_{fechas[0].isoformat()}.html")
    render_html(parrilla, fechas, occ, ruta)
    print(f"\n   Vista HTML: {ruta}")


if __name__ == "__main__":
    main()
