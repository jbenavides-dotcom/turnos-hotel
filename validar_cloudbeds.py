#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Valida la conexion a la API de Cloudbeds del Hotel La Palma y el Tucan.

El token NO esta en este repo. Se lee de:
  1) la variable de entorno CLOUDBEDS_API_TOKEN, o
  2) el vault local key-apis/apis.json (clave 'cloudbeds').

Uso:
    python validar_cloudbeds.py
"""
import os
import sys
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

HOST = "https://hotels.cloudbeds.com/api/v1.2"
PROPERTY_ID = os.environ.get("CLOUDBEDS_PROPERTY_ID", "203345")
VAULT = os.path.expanduser(
    "~/.claude/projects/C--Users-zteba/memory/key-apis/apis.json"
)


def get_token():
    """Devuelve el token de Cloudbeds desde el entorno o el vault local."""
    t = os.environ.get("CLOUDBEDS_API_TOKEN")
    if t:
        return t
    try:
        with open(VAULT, encoding="utf-8") as f:
            return json.load(f)["cloudbeds"]["api_token"]
    except Exception:
        return None


def call(token, path, params):
    url = f"{HOST}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(
            req, timeout=30, context=ssl.create_default_context()
        ) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"success": False, "body": e.read().decode()[:200]}


def main():
    token = get_token()
    if not token:
        print("ERROR: define CLOUDBEDS_API_TOKEN o ten el vault apis.json.")
        sys.exit(1)

    st, j = call(token, "getHotelDetails", {"propertyID": PROPERTY_ID})
    hotel = j.get("data", {}).get("propertyName") if isinstance(j, dict) else None
    print(f"getHotelDetails  -> HTTP {st}  success={j.get('success')}  hotel={hotel}")
    if not j.get("success"):
        print("  Token invalido o expirado.")
        sys.exit(2)

    st2, j2 = call(token, "getReservations", {"propertyID": PROPERTY_ID, "pageSize": 5})
    print(
        f"getReservations  -> HTTP {st2}  success={j2.get('success')}  "
        f"reservas_pagina={len(j2.get('data', []))}"
    )
    print("\nOK: la conexion a Cloudbeds es valida.")


if __name__ == "__main__":
    main()
