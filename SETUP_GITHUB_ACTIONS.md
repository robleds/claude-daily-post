# Setup GitHub Actions — Publicação Automática Diária

O workflow `.github/workflows/daily-post.yml` roda às **6:30 BRT** todo dia.
Nenhum servidor necessário — tudo roda nos servidores gratuitos do GitHub.

---

## 1. Secrets obrigatórios

Acesse: **GitHub > Settings > Secrets and variables > Actions > New repository secret**

### ANTHROPIC_API_KEY (obrigatório)
```
console.anthropic.com > API Keys
```

### LINKEDIN_ACCESS_TOKEN + LINKEDIN_PERSON_URN
```bash
# Execute na sua máquina local:
python3 linkedin_auth.py
# Ele imprime o token e o person URN
```

### MEDIUM_INTEGRATION_TOKEN
```
https://medium.com/me/settings > Integration tokens > Generate
```

---

## 2. Secrets opcionais (cada rede)

### FAL_KEY — geração de imagens
```
https://fal.ai > Dashboard > API Keys
```

### CLOUDINARY_URL — hosting de imagens para Instagram
```
https://cloudinary.com > Dashboard > API Environment variable
Formato: cloudinary://api_key:api_secret@cloud_name
```

### INSTAGRAM_ACCESS_TOKEN + INSTAGRAM_ACCOUNT_ID
```
https://developers.facebook.com > Conta Business conectada à Page
```

### TIKTOK_ACCESS_TOKEN + TIKTOK_OPEN_ID
```
https://developers.tiktok.com > Content Posting API
```

### YOUTUBE_TOKEN_B64 — token OAuth2 em base64
```bash
# Execute na sua máquina local UMA VEZ:
python3 youtube_auth.py
# Ele abre o browser, autentica e imprime o valor base64
# Copie e cole como secret YOUTUBE_TOKEN_B64
```

### DID_API_KEY + DID_PRESENTER_IMAGE_URL — vídeos com avatar
```
https://www.d-id.com > API Keys
DID_PRESENTER_IMAGE_URL = URL pública de uma foto sua
```

### NEWSAPI_KEY — melhora a busca de notícias (opcional)
```
https://newsapi.org > Get API Key (free: 100 req/dia)
```

---

## 3. Rodando manualmente

No GitHub: **Actions > Daily AI Post > Run workflow**

Opções disponíveis:
- **Usar artigo de seed**: usa o artigo PwC 2026 em vez de buscar notícia nova
- **Forçar regeneração**: regenera conteúdo mesmo que já exista output do dia

---

## 4. Ver resultados

Após cada run:
- **Actions > [run] > Artifacts** — baixe `daily-post-XXXXX` com todo o conteúdo gerado
- **Actions > [run] > Logs** — veja o log completo de cada plataforma

---

## 5. Tokens que expiram

| Token | Validade | Como renovar |
|---|---|---|
| LinkedIn | 60 dias | `python3 linkedin_auth.py` → atualiza secret |
| Instagram | 60 dias | Renovar via Facebook Developer |
| TikTok | varia | Renovar via TikTok Developer Console |
| YouTube | não expira* | O refresh token é permanente |
| Medium | não expira | Token de integração permanente |

*O YouTube token se auto-renova via refresh token.

---

## 6. Verificar se está funcionando

```bash
# Ver próximas execuções agendadas:
# GitHub > Actions > Daily AI Post > (ícone de relógio no canto superior)

# Testar localmente antes de commitar:
python3 main.py --seed --dry-run
```
