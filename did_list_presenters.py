#!/usr/bin/env python3
"""
Lista os presenters/avatares disponíveis na sua conta D-ID.
Execute: python3 did_list_presenters.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("DID_API_KEY", "")
if not api_key:
    print("Erro: DID_API_KEY não encontrado no .env")
    exit(1)

resp = requests.get(
    "https://api.d-id.com/clips/presenters",
    headers={"Authorization": f"Basic {api_key}"},
    timeout=10,
)

if resp.status_code != 200:
    print(f"Erro {resp.status_code}: {resp.text}")
    exit(1)

presenters = resp.json().get("presenters", [])
if not presenters:
    print("Nenhum presenter encontrado. Use uma foto pública (Opção A).")
    exit(0)

print(f"\n{len(presenters)} presenter(s) encontrado(s):\n")
for p in presenters:
    print(f"  ID:    {p.get('id')}")
    print(f"  Nome:  {p.get('name', 'sem nome')}")
    print(f"  URL:   {p.get('thumbnail_url') or p.get('image_url', 'N/A')}")
    print()

print("Use a URL acima como DID_PRESENTER_IMAGE_URL no seu .env")
