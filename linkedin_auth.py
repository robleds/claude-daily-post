#!/usr/bin/env python3
"""
Gera o LINKEDIN_ACCESS_TOKEN via OAuth2 no browser local.
Execute uma única vez: python3 linkedin_auth.py
"""

import os
import json
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI  = "http://localhost:8080/callback"
SCOPES        = "openid profile w_member_social"

_auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h2>Autorizado! Pode fechar esta aba.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Erro: code nao encontrado")

    def log_message(self, *args):
        pass


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Erro: defina LINKEDIN_CLIENT_ID e LINKEDIN_CLIENT_SECRET no .env")
        return

    state = secrets.token_urlsafe(16)
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={urllib.parse.quote(SCOPES)}"
        f"&state={state}"
    )

    print(f"\nAbrindo navegador para autorização LinkedIn...")
    print(f"Se não abrir, acesse: {auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()

    if not _auth_code:
        print("Erro: não foi possível obter o authorization code")
        return

    token_resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": _auth_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    token_resp.raise_for_status()
    token_data = token_resp.json()
    access_token = token_data["access_token"]

    me_resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    me_resp.raise_for_status()
    me = me_resp.json()
    sub = me.get("sub", "")
    person_urn = f"urn:li:person:{sub}"
    name = me.get("name", "")

    print(f"✓ Autorizado como: {name}")
    print(f"\nAdicione ao seu .env:\n")
    print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
    print(f"LINKEDIN_PERSON_URN={person_urn}")
    print()

    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text()
        for key, val in [("LINKEDIN_ACCESS_TOKEN", access_token), ("LINKEDIN_PERSON_URN", person_urn)]:
            if f"{key}=" in content:
                import re
                content = re.sub(rf"^{key}=.*$", f"{key}={val}", content, flags=re.MULTILINE)
            else:
                content += f"\n{key}={val}"
        env_path.write_text(content)
        print(f"✓ .env atualizado automaticamente")


if __name__ == "__main__":
    main()
