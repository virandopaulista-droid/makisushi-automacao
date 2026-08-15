#!/usr/bin/env python3
"""TEMP diagnostic (not part of the normal pipeline): confirms the
FB_PAGE_ACCESS_TOKEN/IG_BUSINESS_ID secrets actually authenticate, without
ever printing the token itself -- same read-only Graph API pattern already
used by resolve_drive_url.py etc., just with the token sent as a Bearer
header instead of a URL query param."""
import json
import os
import sys
import urllib.error
import urllib.request

token = os.environ["FB_PAGE_ACCESS_TOKEN"]
ig_id = os.environ["IG_BUSINESS_ID"]
page_id = os.environ["FB_PAGE_ID"]


def get_json(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


try:
    me = get_json("https://graph.facebook.com/v20.0/me?fields=id,name")
    print(f"Pagina autenticada: id={me.get('id')} name={me.get('name')!r}")
    print(f"Pagina esperada (secret FB_PAGE_ID): {page_id}")
    print(f"BATE: {me.get('id') == page_id}")
except urllib.error.HTTPError as e:
    print(f"ERRO autenticando pagina: {e.read().decode('utf-8')}", file=sys.stderr)
    sys.exit(1)

try:
    ig = get_json(f"https://graph.facebook.com/v20.0/{ig_id}?fields=id,username")
    print(f"Instagram autenticado: id={ig.get('id')} username={ig.get('username')!r}")
except urllib.error.HTTPError as e:
    print(f"ERRO autenticando Instagram: {e.read().decode('utf-8')}", file=sys.stderr)
    sys.exit(1)
