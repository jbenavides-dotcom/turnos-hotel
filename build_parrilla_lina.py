#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lee la hoja de turnos de Lina (Google Sheet 'TURNOS 2025', exportada a .xlsx) y
genera docs/parrilla_lina.json con su programación REAL, para que la herramienta
la muestre donde exista (y solo genere/edite lo vacío).

SOLO LECTURA: nunca escribe en la hoja de Lina.

Formato de salida: {"generated": "...", "plan": {"<empId>|<YYYY-MM-DD>": {tipo,ini,fin}}}
  tipo: manana (trabajo diurno, amarillo) | tarde (cierre, azul) | descanso | vacaciones

Uso: python build_parrilla_lina.py [ruta.xlsx]   (default: data/TURNOS_2025_gsheet_LIVE.xlsx)
"""
import sys, os, json, datetime as dt
import openpyxl
import validador_reglas as V

AQUI = os.path.dirname(os.path.abspath(__file__))
XLSX = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "data", "TURNOS_2025_gsheet_LIVE.xlsx")
SALIDA = os.path.join(AQUI, "docs", "parrilla_lina.json")

# Nombre en la hoja de Lina (MAYÚSCULAS) -> id en la herramienta
NAME2ID = {
    "CLAUDIA TORRES": "ctorres", "MARIBEL PAEZ": "maribel", "ZAIRA": "zaira",
    "NICOLAS SARMIENTO": "nicolas", "SHEAN PAUL GUTIERREZ": "shean", "KELLY CRUZ": "kelly",
    "DANIELA MONROY": "daniela", "GERWIN": "gerwin", "CLAUDIA MONTENEGRO": "cmonte",
    "DEISY RODRIGUEZ": "deisy", "DIEGO DIAZ": "diego", "NICOLLE": "nicolle", "SANTIAGO": "santiago",
}

def hhmm(m):
    return f"{m//60:02d}:{m%60:02d}"

def to_shift(e, s):
    est = V.es_estado(e)
    if est == "DESCANSO":
        return {"tipo": "descanso"}
    if est in ("VACACIONES", "CALAMIDAD", "INCAPACIDAD", "LICENCIA", "PERMISO", "SUSPENSION"):
        return {"tipo": "vacaciones"}
    pe = V.parse_hora(e)
    if not pe or pe[0] != "HORA":
        return None
    ini = hhmm(pe[1])
    ps = V.parse_hora(s)
    if ps and ps[0] == "CIERRE":
        return {"tipo": "tarde", "ini": ini, "fin": "cierre"}      # azul = cierre
    if ps and ps[0] == "HORA":
        return {"tipo": "manana", "ini": ini, "fin": hhmm(ps[1])}  # amarillo = trabajo diurno
    return {"tipo": "manana", "ini": ini, "fin": "15:00"}

def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    plan = {}
    sin_mapear = set()
    for tab in wb.sheetnames:
        ws = wb[tab]
        dias = V.fechas_de_cabecera(ws, tab)   # [(col, fecha, wd)]
        if not dias:
            continue
        for r in range(2, 30):
            nom = str(ws.cell(r, 1).value or "").strip().upper()
            if not nom:
                continue
            eid = NAME2ID.get(nom)
            for (c, f, _w) in dias:
                e = ws.cell(r, c).value
                s = ws.cell(r, c + 1).value
                if e is None or not str(e).strip():
                    continue
                sh = to_shift(e, s)
                if sh is None:
                    continue
                if not eid:
                    sin_mapear.add(nom)
                    continue
                plan[f"{eid}|{f.isoformat()}"] = sh   # último tab gana en solapes

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    out = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "plan": plan}
    json.dump(out, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"-> {SALIDA}  ({len(plan)} celdas de Lina)")
    if sin_mapear:
        print("  Personas con datos en la hoja pero SIN id en la herramienta:", sorted(sin_mapear))

if __name__ == "__main__":
    main()
