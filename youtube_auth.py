#!/usr/bin/env python3
"""
Autenticação inicial do YouTube — rode UMA VEZ na sua máquina local.

Gera youtube_token.pickle e imprime o valor base64 para usar como
secret YOUTUBE_TOKEN_B64 no GitHub Actions.

Pré-requisito: credentials.json baixado de https://console.cloud.google.com/
  APIs & Services > Credenciais > OAuth 2.0 > Desktop app > Baixar JSON
  Salve como credentials.json neste diretório.

Uso:
  python3 youtube_auth.py
"""

import sys
import base64
import pickle
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "youtube_token.pickle"


def main():
    if not Path(CREDENTIALS_FILE).exists():
        print(f"Erro: {CREDENTIALS_FILE} não encontrado.")
        print("Baixe em: https://console.cloud.google.com/")
        print("  APIs & Services > Credenciais > Criar > ID cliente OAuth > Desktop app > Baixar JSON")
        print(f"  Salve como '{CREDENTIALS_FILE}' neste diretório.")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Instale: pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    print("Abrindo browser para autenticar com o Google...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)

    token_b64 = base64.b64encode(Path(TOKEN_FILE).read_bytes()).decode()

    print("\n" + "=" * 60)
    print("✓ Token gerado com sucesso!")
    print("=" * 60)
    print()
    print("PRÓXIMOS PASSOS — adicione ao GitHub como Secret:")
    print()
    print("  Nome do secret: YOUTUBE_TOKEN_B64")
    print("  Valor (copie tudo abaixo desta linha):")
    print()
    print(token_b64)
    print()
    print("  GitHub > Settings > Secrets and variables > Actions > New repository secret")
    print("=" * 60)


if __name__ == "__main__":
    main()
