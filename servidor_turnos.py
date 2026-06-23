#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Backend local del Sistema de Turnos - Hotel La Palma y el Tucan.

Sirve el frontend (app.html) y expone una API local:
    GET  /api/health                              -> estado del token + hotel
    GET  /api/ocupacion?desde=YYYY-MM-DD&dias=N   -> cabanas reservadas por noche
    GET  /api/parrilla                            -> ediciones guardadas
    POST /api/parrilla                            -> guarda ediciones (JSON)

SEGURIDAD: el token de Cloudbeds se lee de la variable de entorno
CLOUDBEDS_API_TOKEN o del vault local apis.json. NUNCA se envia al navegador.

Uso:
    python servidor_turnos.py
    -> abre http://localhost:8787
"""
import os
import sys
import json
import ssl
import time
import datetime
import webbrowser
import threading
import urllib.request
import urllib.parse
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
PARRILLA_FILE = os.path.join(DATA_DIR, "parrilla.json")
HOST_API = "https://hotels.cloudbeds.com/api/v1.2"
PROPERTY_ID = os.environ.get("CLOUDBEDS_PROPERTY_ID", "203345")
PORT = int(os.environ.get("TURNOS_PORT", "8787"))
VAULT = os.path.expanduser(
    "~/.claude/projects/C--Users-zteba/memory/key-apis/apis.json"
)
VALID_STATUS = {"confirmed", "checked_in", "not_confirmed"}
DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def get_token():
    t = os.environ.get("CLOUDBEDS_API_TOKEN")
    if t:
        return t
    try:
        with open(VAULT, encoding="utf-8") as f:
            return json.load(f)["cloudbeds"]["api_token"]
    except Exception:
        return None


def cloudbeds(path, params):
    url = f"{HOST_API}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {get_token()}"}
    )
    with urllib.request.urlopen(
        req, timeout=30, context=ssl.create_default_context()
    ) as r:
        return json.loads(r.read())


_health_cache = {"ts": 0, "val": None}


def health():
    if _health_cache["val"] and (time.time() - _health_cache["ts"]) < 120:
        return _health_cache["val"]
    if not get_token():
        val = {"ok": False, "error": "Sin token (define CLOUDBEDS_API_TOKEN o vault)"}
    else:
        try:
            j = cloudbeds("getHotelDetails", {"propertyID": PROPERTY_ID})
            val = {
                "ok": bool(j.get("success")),
                "hotel": j.get("data", {}).get("propertyName"),
                "propertyID": PROPERTY_ID,
            }
        except Exception as e:
            val = {"ok": False, "error": str(e)[:120]}
    _health_cache.update(ts=time.time(), val=val)
    return val


_occ_cache = {"key": None, "ts": 0, "val": None}


def ocupacion(desde, dias):
    key = f"{desde}:{dias}"
    if _occ_cache["key"] == key and (time.time() - _occ_cache["ts"]) < 300:
        return _occ_cache["val"]
    try:
        d0 = datetime.date.fromisoformat(desde)
    except Exception:
        return {"success": False, "error": "fecha invalida"}
    try:
        j = cloudbeds(
            "getReservations",
            {"propertyID": PROPERTY_ID, "checkOutFrom": desde, "pageSize": 200},
        )
    except Exception as e:
        return {"success": False, "error": str(e)[:120], "dias": []}
    data = j.get("data", []) if j.get("success") else []
    out = []
    for i in range(int(dias)):
        night = d0 + datetime.timedelta(days=i)
        cnt = 0
        for r in data:
            if (r.get("status") or "").lower() not in VALID_STATUS:
                continue
            try:
                s = datetime.date.fromisoformat(r["startDate"])
                e = datetime.date.fromisoformat(r["endDate"])
            except Exception:
                continue
            if s <= night < e:
                cnt += 1
        out.append(
            {"fecha": night.isoformat(), "dow": DIAS_ES[night.weekday()], "cabanas": cnt}
        )
    res = {"success": bool(j.get("success")), "dias": out, "fuente": "Cloudbeds en vivo"}
    _occ_cache.update(key=key, ts=time.time(), val=res)
    return res


def load_parrilla():
    try:
        with open(PARRILLA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": 1, "overrides": {}, "notas": {}}


def save_parrilla(obj):
    os.makedirs(DATA_DIR, exist_ok=True)
    obj["version"] = 1
    with open(PARRILLA_FILE, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass  # silencio

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path in ("/", "/app.html"):
            return self._serve_file("app.html", "text/html; charset=utf-8")
        if u.path == "/api/health":
            return self._send(200, health())
        if u.path == "/api/ocupacion":
            desde = q.get("desde", [datetime.date.today().isoformat()])[0]
            dias = q.get("dias", ["7"])[0]
            return self._send(200, ocupacion(desde, dias))
        if u.path == "/api/parrilla":
            return self._send(200, load_parrilla())
        if u.path.lstrip("/") in ("prototipo-parrilla.html", "DISENO-TURNOS.md", "README.md"):
            ctype = "text/html; charset=utf-8" if u.path.endswith(".html") else "text/plain; charset=utf-8"
            return self._serve_file(u.path.lstrip("/"), ctype)
        return self._send(404, {"error": "no encontrado"})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/api/parrilla":
            return self._send(404, {"error": "no encontrado"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            save_parrilla({
                "overrides": body.get("overrides", {}),
                "notas": body.get("notas", {}),
                "bases": body.get("bases", {}),
            })
            return self._send(200, {"ok": True})
        except Exception as e:
            return self._send(400, {"ok": False, "error": str(e)[:120]})

    def _serve_file(self, name, ctype):
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path):
            return self._send(404, {"error": f"{name} no existe"})
        with open(path, "rb") as f:
            return self._send(200, f.read(), ctype)


def main():
    print("=" * 56)
    print(" Sistema de Turnos - Hotel La Palma y el Tucan")
    print("=" * 56)
    h = health()
    if h.get("ok"):
        print(f" Cloudbeds OK -> {h.get('hotel')} (property {h.get('propertyID')})")
    else:
        print(f" Cloudbeds NO disponible: {h.get('error')}")
        print(" (la app abre igual; la ocupacion saldra vacia)")
    url = f"http://localhost:{PORT}"
    print(f" Abriendo {url}  (Ctrl+C para detener)")
    print("=" * 56)
    try:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    except Exception:
        pass
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
        srv.server_close()


if __name__ == "__main__":
    main()
