#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Genera docs/ocupacion.json para el sitio estático de GitHub Pages.

Trae las cabañas/noche de Cloudbeds (vía ocupacion_cloudbeds) para un rango
amplio (hoy-7 … hoy+42) y escribe {generated, dias:{YYYY-MM-DD: n}}.

Lo corre el GitHub Action con CLOUDBEDS_API_TOKEN como Secret: el token nunca
se publica, solo los números de ocupación. Local: `python build_pages_ocupacion.py`.
"""
import os, json, datetime as dt
import ocupacion_cloudbeds as OC

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "docs", "ocupacion.json")
DIAS_ATRAS, DIAS_ADELANTE = 7, 42

def main():
    token, pid = OC.get_creds()
    hoy = dt.date.today()
    d_ini = hoy - dt.timedelta(days=DIAS_ATRAS)
    d_fin = hoy + dt.timedelta(days=DIAS_ADELANTE)
    fechas = [d_ini + dt.timedelta(days=i) for i in range((d_fin - d_ini).days)]

    dias = {}
    if token:
        reservas = OC.traer_reservas(token, pid, d_ini, d_fin)
        dias = OC.contar_por_noche(reservas, fechas)
        print(f"Cloudbeds OK · {len(reservas)} reservas · {len(dias)} noches")
    else:
        print("SIN token: se publica ocupacion vacía.")

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    out = {"generated": dt.datetime.now().isoformat(timespec="seconds"),
           "property": pid, "dias": dias}
    json.dump(out, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"-> {SALIDA}  (rango {d_ini} … {d_fin})")

if __name__ == "__main__":
    main()
