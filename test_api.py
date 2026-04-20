#!/usr/bin/env python3
"""Diagnóstico da API Anthropic."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
print(f"API Key encontrada: {'Sim' if api_key else 'NÃO'}")
if api_key:
    print(f"Key (primeiros 20 chars): {api_key[:20]}...")
    print(f"Key (últimos 6 chars):    ...{api_key[-6:]}")
    print(f"Tamanho: {len(api_key)} caracteres")
print()

try:
    import anthropic
    print(f"anthropic SDK versão: {anthropic.__version__}")
except ImportError as e:
    print(f"Erro ao importar anthropic: {e}")
    sys.exit(1)

print("\nTestando chamada mínima (haiku — mais barato)...")
try:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": "Diga apenas: OK"}],
    )
    print(f"✅ SUCESSO! Resposta: {response.content[0].text}")
except anthropic.AuthenticationError as e:
    print(f"❌ Erro de autenticação — API key inválida ou revogada\n{e}")
except anthropic.BadRequestError as e:
    print(f"❌ BadRequest: {e}")
except anthropic.PermissionDeniedError as e:
    print(f"❌ Sem permissão: {e}")
except Exception as e:
    print(f"❌ Erro inesperado ({type(e).__name__}): {e}")
