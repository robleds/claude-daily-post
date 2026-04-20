#!/usr/bin/env python3
"""
Gera o LINKEDIN_ACCESS_TOKEN via OAuth2.
Abre o browser, você autoriza, e cola a URL de retorno aqui.
Execute: python linkedin_auth.py
"""

import os
import re
import secrets
import webbrowser
import urllib.parse
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI  = "http://localhost:8080/callback"
SCOPES        = "openid profile w_member_social"


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

    print("\n=== LinkedIn OAuth2 ===\n")
    print("1. Abrindo o browser para autorização...")
    webbrowser.open(auth_url)
    print("   (se não abrir, acesse a URL abaixo manualmente)")
    print(f"\n   {auth_url}\n")

    print("2. Após autorizar, o browser vai redirecionar para uma URL")
    print("   que começa com:  http://localhost:8080/callback?code=...")
    print("   (pode aparecer erro de conexão no browser — isso é normal)\n")

    callback_url = input("3. Cole aqui a URL completa do callback e pressione Enter:\n> ").strip()

    code = _extract_code(callback_url)
    if not code:
        print("\nErro: não foi possível extrair o 'code' da URL.")
        print("Certifique-se de copiar a URL completa da barra de endereço do browser.")
        return

    print("\nTrocando código por access token...")
    token_resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  REDIRECT_URI,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )

    if not token_resp.ok:
        print(f"Erro ao obter token: {token_resp.status_code} — {token_resp.text}")
        return

    access_token = token_resp.json()["access_token"]

    me_resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    me_resp.raise_for_status()
    me = me_resp.json()
    person_urn = f"urn:li:person:{me.get('sub', '')}"
    name = me.get("name", "")

    print(f"\n✓ Autorizado como: {name}")
    print(f"  URN: {person_urn}\n")

    _update_env("LINKEDIN_ACCESS_TOKEN", access_token)
    _update_env("LINKEDIN_PERSON_URN", person_urn)
    print("✓ .env atualizado com o novo token!\n")


def _extract_code(url: str) -> str | None:
    match = re.search(r"[?&]code=([^&]+)", url)
    return match.group(1) if match else None


def _update_env(key: str, value: str):
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return
    content = env_path.read_text()
    if f"{key}=" in content:
        content = re.sub(rf"^{key}=.*$", f"{key}={value}", content, flags=re.MULTILINE)
    else:
        content += f"\n{key}={value}"
    env_path.write_text(content)


if __name__ == "__main__":
    main()
