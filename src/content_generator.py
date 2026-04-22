import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
from config import RODRIGO_PERSONA, ACTIVE_PLATFORMS

_client = None

# Tier labels for article context enrichment
_TIER_LABELS = {
    1: "Pesquisa/Estratégico (MIT Sloan, Stanford, WEF, OpenAI, Anthropic)",
    2: "Grande mídia tech (TechCrunch, Wired, VentureBeat, MIT TR, The Verge)",
    3: "Mídia especializada (Fast Company, ZDNet, TNW, Euractiv)",
    4: "Regional/Emergente (Nikkei Asia, TechInAsia, Inc42, Analytics India)",
}

# Image dimensions per platform key
_IMAGE_SPECS = {
    "linkedin":          "1200×628, retangular horizontal",
    "instagram":         "1080×1080, quadrado",
    "tiktok":            "1080×1920, vertical",
    "youtube_thumbnail": "1280×720, retangular horizontal",
    "medium":            "1200×630, retangular horizontal",
}

# Style guardrails shared by all platform prompts
_STYLE_RULES = """
REGRAS DE LINGUAGEM — OBRIGATÓRIAS:
- NUNCA use travessão (—) no meio de frases. Precisa de pausa? Ponto final e nova frase.
- NUNCA use "não só X, mas Y" ou "não apenas X, mas também Y"
- NUNCA comece frases com "Isso", "Este", "Esta" como sujeito genérico
- NUNCA use: "crucial", "fundamental", "primordial", "no mundo atual", "cada vez mais", "transformador", "revolucionário", "disruptivo"
- Frases curtas. Frase ficou longa? Quebre em duas.
- Para contrastar ideias: parágrafo novo, não conector com travessão
- Escreva como quem explica para um colega no café, não em apresentação corporativa
- Em português brasileiro
""".strip()


# ── Client & API call ─────────────────────────────────────────────────────────

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _call_claude(prompt: str, max_tokens: int = 2048) -> str:
    """Call Claude with prompt caching on the system prompt (persona)."""
    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=[{
            "type": "text",
            "text": RODRIGO_PERSONA,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ── Orchestration ─────────────────────────────────────────────────────────────

def generate_all_content(article: dict) -> dict:
    """
    Generate platform content in parallel, only for ACTIVE_PLATFORMS.
    Image concepts generated for active platforms only.
    Video script generated only when youtube or tiktok is active.
    """
    context = _build_article_context(article)
    active = ACTIVE_PLATFORMS
    print(f"[content_generator] Active platforms: {', '.join(active)}")

    _platform_generators = {
        "linkedin":  generate_linkedin,
        "instagram": generate_instagram,
        "tiktok":    generate_tiktok,
        "youtube":   generate_youtube,
        "medium":    generate_medium,
    }

    # Seed result with empty strings so downstream code never KeyErrors
    result: dict = {p: "" for p in ["linkedin", "instagram", "tiktok", "youtube", "medium"]}
    result.update({"image_concept": {}, "video_script": "", "source_article": article})

    # Build task map — closures capture context correctly
    tasks: dict[str, callable] = {}

    for p in active:
        if p in _platform_generators:
            fn = _platform_generators[p]
            tasks[p] = lambda _fn=fn: _fn(context)

    tasks["image_concept"] = lambda: generate_image_concept(context, active)

    if any(p in active for p in ("youtube", "tiktok")):
        tasks["video_script"] = lambda: generate_video_script(context)

    # Fire all tasks in parallel
    with ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                result[name] = future.result()
                print(f"[content_generator] ✓ {name}")
            except Exception as e:
                print(f"[content_generator] ✗ {name}: {e}")

    return result


# ── Platform generators ───────────────────────────────────────────────────────

def generate_linkedin(context: str) -> str:
    prompt = f"""{context}

Escreva um post para LinkedIn na minha voz.

ESTRUTURA:
- 3 a 4 parágrafos curtos (2 a 4 linhas cada)
- Primeiro parágrafo: começa com dado concreto ou situação real — 2 a 4 linhas
- Pergunta final que provoque resposta genuína
- Linha em branco
- 5 a 7 hashtags

PROIBIDO:
- NÃO escreva uma frase curta isolada antes do primeiro parágrafo
- NÃO crie linha de título, headline ou hook separado
- O post começa DIRETAMENTE na primeira linha do primeiro parágrafo, sem nenhuma linha anterior

{_STYLE_RULES}
- Sem emojis
- Pode usar reticências (...) com moderação para pausas de reflexão
- Máximo 1.300 caracteres no total (sem as hashtags)
- Tom: direto, levemente provocador, baseado em experiência real. Não motivacional.

Post:"""
    return _call_claude(prompt, max_tokens=800)


def generate_instagram(context: str) -> str:
    prompt = f"""{context}

Crie uma caption para Instagram.

ESTRUTURA:
- Primeira linha: frase de impacto que pare o scroll (máximo 10 palavras)
- Linha em branco
- Desenvolvimento em tópicos curtos ou parágrafos de 2 linhas
- CTA claro no final (salva, compartilha, comenta)
- 15 a 20 hashtags no final

{_STYLE_RULES}
- Emojis permitidos como marcadores visuais no início de tópicos (não como enfeite)
- Máximo 2.200 caracteres (sem hashtags)
- Linguagem levemente mais leve que LinkedIn, mas ainda profissional

Caption:"""
    return _call_claude(prompt, max_tokens=900)


def generate_tiktok(context: str) -> str:
    prompt = f"""{context}

Crie legenda e roteiro de fala para um TikTok de 60 a 90 segundos.

LEGENDA (máximo 300 caracteres):
- Frase de impacto que gera curiosidade imediata
- 5 a 8 hashtags

ROTEIRO FALADO (o que você diz no vídeo, palavra por palavra):
- Abertura: pergunta ou dado chocante nos primeiros 3 segundos
- Desenvolvimento: 3 revelações rápidas e concretas
- Fechamento: chamada para ação direta

{_STYLE_RULES}
- Tom: descontraído e rápido, como explicar para um amigo — mas sem perder a substância
- Sem jargão técnico sem contexto

Formato de resposta:
LEGENDA:
[legenda aqui]

ROTEIRO:
[roteiro aqui]"""
    return _call_claude(prompt, max_tokens=700)


def generate_youtube(context: str) -> str:
    prompt = f"""{context}

Crie os elementos completos para um vídeo curto do YouTube (3 a 5 minutos).

TÍTULO (máximo 70 caracteres, com gatilho de curiosidade real — não clickbait vazio):

DESCRIÇÃO (300 a 500 caracteres, com palavras-chave para SEO):

TAGS (20 tags separadas por vírgula):

SCRIPT DO VÍDEO (narração completa, aproximadamente 500 palavras):
- Abertura: problema ou dado impactante (0:00–0:30)
- Contexto: o que está acontecendo e por quê importa (0:30–1:30)
- Análise: 3 insights práticos com exemplos reais (1:30–3:30)
- Conclusão: o que muda na prática depois disso (3:30–4:00)
- CTA: inscrição + comentário

{_STYLE_RULES}
- No script: frases curtas, linguagem falada natural, sem "como vocês podem ver" ou bordões de youtuber"""
    return _call_claude(prompt, max_tokens=1500)


def generate_medium(context: str) -> str:
    prompt = f"""{context}

Escreva um artigo completo para o Medium.

ESTRUTURA:
- Título: direto, sem clickbait, que entregue a promessa do artigo
- Subtítulo: complementa o título com o argumento central
- 800 a 1.200 palavras
- Introdução + 3 a 4 seções com subtítulos + conclusão
- Cada seção: um insight acionável com dado ou exemplo concreto
- Final: chamada para reflexão ou ação — sem "deixa o like"

{_STYLE_RULES}
- Tom: reflexivo e consultivo, artigo de opinião embasado
- Use dados para sustentar o argumento, não para impressionar
- Cada subtítulo de seção deve ser uma afirmação, não um tema genérico

Artigo:"""
    return _call_claude(prompt, max_tokens=2000)


# ── Image concepts ────────────────────────────────────────────────────────────

def generate_image_concept(context: str, active_platforms: list[str]) -> dict:
    """
    Ask Claude for image prompts as JSON — one per active platform.
    LinkedIn is excluded: it uses the carousel PDF generator instead.
    Falls back to a shared prompt if JSON parsing fails.
    """
    # LinkedIn generates its own visual via linkedin_carousel.py
    platforms = [p for p in active_platforms if p != "linkedin"]
    if not platforms:
        return {}

    # Map platform names to image spec keys
    platform_to_key = {p: ("youtube_thumbnail" if p == "youtube" else p) for p in platforms}
    keys = list(dict.fromkeys(platform_to_key.values()))  # deduped, order preserved

    specs = "\n".join(f"- {k.upper()} ({_IMAGE_SPECS.get(k, '')})" for k in keys)

    json_template = json.dumps({k: "prompt here" for k in keys}, indent=2)

    prompt = f"""{context}

Crie prompts em inglês para geração de imagens via IA (Flux/DALL-E) para estas plataformas:
{specs}

Estilo visual: moderno, profissional, paleta azul profundo + laranja vibrante,
tipografia clean, elementos de tecnologia e negócios. SEM texto ou letras na imagem.

Responda APENAS com JSON válido, sem nenhum texto antes ou depois:
{json_template}"""

    raw = _call_claude(prompt, max_tokens=800)

    # Try to extract and parse JSON
    try:
        json_match = re.search(r'\{.+\}', raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            # Normalise keys to lowercase
            return {k.lower(): v for k, v in parsed.items()}
    except Exception:
        pass

    # Fallback: apply the raw output as prompt for all active platforms
    fallback = raw[:400]
    return {k: fallback for k in keys}


# ── Video script ──────────────────────────────────────────────────────────────

def generate_video_script(context: str) -> str:
    prompt = f"""{context}

Escreva um roteiro de 90 segundos para vídeo com avatar de IA (D-ID / HeyGen).
O texto será lido por síntese de voz, então escreva para ser ouvido, não lido.

- Sem marcações de cena ou direção
- Apenas o texto que será falado
- Pausas: [pausa]
- Ênfases: MAIÚSCULAS
- 200 a 250 palavras
- Tom: conversa séria mas informal, sem bordões

{_STYLE_RULES}"""
    return _call_claude(prompt, max_tokens=500)


# ── Article context ───────────────────────────────────────────────────────────

def _build_article_context(article: dict) -> str:
    tier_label = _TIER_LABELS.get(article.get("source_tier", 3), "Mídia especializada")
    selection_reason = article.get("claude_selection_reason", "")

    lines = [
        "Notícia original (ainda não publicada em português):",
        "",
        f"Título: {article['title']}",
        f"Fonte: {article.get('source', '?')} | Região: {article.get('source_region', '?')} | Tier: {tier_label}",
        f"Publicado em: {article.get('published', 'recentemente')[:10]}",
        f"URL: {article.get('url', '')}",
    ]

    if selection_reason:
        lines += ["", f"Por que esta notícia foi escolhida: {selection_reason}"]

    lines += [
        "",
        "Conteúdo:",
        article.get("full_content") or article.get("summary", ""),
        "",
        "---",
        "Com base nessa notícia, crie conteúdo autêntico na minha voz para a plataforma especificada.",
        "Traga seu ponto de vista como consultor que implementa IA no Brasil — não apenas repasse a notícia.",
    ]

    return "\n".join(lines)
