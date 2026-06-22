#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Trae la OCUPACIÓN por noche (# cabañas) desde Cloudbeds y la escribe a
data/ocupacion.json, que consume validador_reglas.py.

Cuenta las reservas ACTIVAS que ocupan cada noche (startDate <= noche < endDate),
excluyendo canceladas / no-show. En este hotel boutique ~1 reserva = 1 cabaña;
si una reserva tuviera varias habitaciones, este conteo la subestima (mejora
futura: usar detalle room-level).

El token se lee del entorno (CLOUDBEDS_API_TOKEN) o del vault local
key-apis/apis.json (campo cloudbeds.api_key). NUNCA se imprime ni se guarda en el repo.

Uso:
    python ocupacion_cloudbeds.py                       # semana actual + siguiente
    python ocupacion_cloudbeds.py --semana 2026-06-15   # esa semana (lun-dom)
    python ocupacion_cloudbeds.py --from 2026-06-15 --to 2026-06-28
"""
import os, sys, json, ssl, datetime as dt
import urllib.request, urllib.parse, urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
OCUP = os.path.join(AQUI, "data", "ocupacion.json")
HOST = "https://hotels.cloudbeds.com/api/v1.2"
ACTIVAS = {"confirmed", "checked_in", "checked_out", "not_confirmed"}  # excluye canceled/no_show

VAULTS = [
    os.path.expanduser("~/.claude/projects/C--Users-USUARIO/memory/key-apis/apis.json"),
    os.path.expanduser("~/.claude/projects/C--Users-zteba/memory/key-apis/apis.json"),
]

def get_creds():
    tok = os.environ.get("CLOUDBEDS_API_TOKEN")
    pid = os.environ.get("CLOUDBEDS_PROPERTY_ID")
    if tok:
        return tok, pid or "203345"
    for v in VAULTS:
        if os.path.exists(v):
            cb = json.load(open(v, encoding="utf-8-sig")).get("cloudbeds", {})
            tok = cb.get("api_key") or cb.get("api_token")
            if tok:
                return tok, str(cb.get("property_id", "203345"))
    return None, "203345"

def call(token, path, params):
    url = f"{HOST}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"success": False, "body": e.read().decode()[:300]}

def traer_reservas(token, pid, d_ini, d_fin):
    """Reservas cuyo check-in cae entre d_ini-14d y d_fin (cubre estancias en curso)."""
    desde = (d_ini - dt.timedelta(days=14)).isoformat()
    hasta = d_fin.isoformat()
    out, page = [], 1
    while True:
        st, j = call(token, "getReservations", {
            "propertyID": pid, "checkInFrom": desde, "checkInTo": hasta,
            "pageNumber": page, "pageSize": 100})
        if st != 200 or not j.get("success"):
            print(f"ERROR getReservations HTTP {st}: {j.get('body','')}")
            break
        data = j.get("data", [])
        out += data
        if len(data) < 100:
            break
        page += 1
    return out

def contar_por_noche(reservas, fechas):
    conteo = {f.isoformat(): 0 for f in fechas}
    for r in reservas:
        if str(r.get("status", "")).lower() not in ACTIVAS:
            continue
        try:
            s = dt.date.fromisoformat(r["startDate"])
            e = dt.date.fromisoformat(r["endDate"])
        except Exception:
            continue
        for f in fechas:
            if s <= f < e:                      # ocupa la noche f
                conteo[f.isoformat()] += 1
    return conteo

def main():
    args = sys.argv[1:]
    hoy = dt.date.today()
    if "--semana" in args:
        lun = dt.date.fromisoformat(args[args.index("--semana") + 1])
        lun -= dt.timedelta(days=lun.weekday())
        d_ini, d_fin = lun, lun + dt.timedelta(days=7)
    elif "--from" in args:
        d_ini = dt.date.fromisoformat(args[args.index("--from") + 1])
        d_fin = dt.date.fromisoformat(args[args.index("--to") + 1])
    else:  # semana actual + siguiente
        lun = hoy - dt.timedelta(days=hoy.weekday())
        d_ini, d_fin = lun, lun + dt.timedelta(days=14)

    token, pid = get_creds()
    if not token:
        print("ERROR: sin token (CLOUDBEDS_API_TOKEN o vault apis.json).")
        sys.exit(1)

    fechas = [d_ini + dt.timedelta(days=i) for i in range((d_fin - d_ini).days)]
    print(f"Cloudbeds property {pid} · noches {fechas[0]} → {fechas[-1]}")
    reservas = traer_reservas(token, pid, d_ini, d_fin)
    print(f"  reservas traídas: {len(reservas)}")
    conteo = contar_por_noche(reservas, fechas)

    actual = {}
    if os.path.exists(OCUP):
        try:
            actual = json.load(open(OCUP, encoding="utf-8"))
        except Exception:
            actual = {}
    actual = {k: v for k, v in actual.items() if not k.startswith("_")}
    actual.update(conteo)
    json.dump(dict(sorted(actual.items())), open(OCUP, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"  → escrito {OCUP}")
    for f in fechas:
        k = f.isoformat()
        print(f"    {k} {f.strftime('%a')}: {conteo[k]} cabañas")

if __name__ == "__main__":
    main()
