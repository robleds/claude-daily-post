import os
import anthropic
from config import RODRIGO_PERSONA

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _call_claude(prompt: str, max_tokens: int = 2048) -> str:
    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=RODRIGO_PERSONA,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_all_content(article: dict) -> dict:
    """Generate platform-specific content for all platforms."""
    context = _build_article_context(article)
    print("[content_generator] Generating content for all platforms...")

    return {
        "linkedin": generate_linkedin(context),
        "instagram": generate_instagram(context),
        "tiktok": generate_tiktok(context),
        "youtube": generate_youtube(context),
        "medium": generate_medium(context),
        "image_concept": generate_image_concept(context),
        "video_script": generate_video_script(context),
        "source_article": article,
    }


def generate_linkedin(context: str) -> str:
    prompt = f"""
{context}

Escreva um post para LinkedIn na minha voz. Sigo abaixo com regras rígidas de estilo — leia com atenção antes de escrever.

ESTRUTURA:
- Linha 1: frase curta e direta que funciona como título (máximo 10 palavras). Sem ponto de interrogação. Deve parar o scroll.
- Linha em branco
- Desenvolvimento em 3 a 4 parágrafos curtos (2 a 4 linhas cada)
- Pergunta final que provoque resposta genuína
- Linha em branco
- 5 a 7 hashtags

REGRAS DE LINGUAGEM — OBRIGATÓRIAS:
- NUNCA use travessão (—) no meio de frases. Se precisar de pausa, use ponto final e comece nova frase.
- NUNCA use construções como "não só X, mas Y" ou "não apenas X, mas também Y"
- NUNCA comece frases com "Isso", "Este", "Esta" como sujeito genérico
- NUNCA use "crucial", "fundamental", "primordial", "no mundo atual", "cada vez mais"
- Sem emojis
- Frases curtas. Quando a frase ficar longa, quebre em duas.
- Use vírgula para pausas naturais, nunca travessão
- Escreva como se estivesse explicando para um colega no café, não em uma apresentação
- Quando quiser contrastar ideias, use parágrafo novo em vez de conector com travessão
- Pode usar reticências (...) com moderação para pausas de reflexão
- Máximo 1.300 caracteres no total (sem as hashtags)

Tom: direto, um pouco provocador, baseado em experiência real. Não motivacional.

Em português brasileiro.

Post:"""
    return _call_claude(prompt, max_tokens=800)


def generate_instagram(context: str) -> str:
    prompt = f"""
{context}

Crie um post para Instagram com as seguintes características:
- Máximo 2.200 caracteres
- Primeira linha: frase de impacto que pare o scroll (máximo 10 palavras)
- Use emojis estrategicamente como marcadores visuais
- Formato de lista ou passos numerados para facilitar leitura rápida
- Linguagem mais leve que o LinkedIn, mas ainda profissional
- CTA claro no final (salva, compartilha, comenta)
- 15 a 20 hashtags no final (mistura de amplas e nichadas)
- Em português brasileiro

Caption:"""
    return _call_claude(prompt, max_tokens=900)


def generate_tiktok(context: str) -> str:
    prompt = f"""
{context}

Crie uma legenda + roteiro de fala para TikTok (vídeo de 60-90 segundos):

LEGENDA (máximo 300 caracteres + hashtags):
- Frase de impacto que gera curiosidade
- 5-8 hashtags virais

ROTEIRO FALADO (o que você diria no vídeo, palavra por palavra):
- Abertura: pergunta ou dado chocante nos primeiros 3 segundos
- Desenvolvimento: 3 revelações rápidas
- Fechamento: chamada para ação
- Tom: descontraído, rápido, direto — como você explicaria para um amigo

Formato:
LEGENDA:
[legenda aqui]

ROTEIRO:
[roteiro aqui]

Em português brasileiro."""
    return _call_claude(prompt, max_tokens=700)


def generate_youtube(context: str) -> str:
    prompt = f"""
{context}

Crie os elementos completos para um vídeo curto do YouTube (3-5 minutos):

TÍTULO (máximo 70 caracteres, com gatilho de curiosidade):

DESCRIÇÃO (300-500 caracteres, com palavras-chave para SEO):

TAGS (20 tags separadas por vírgula):

SCRIPT DO VÍDEO (narração completa, ~500 palavras):
- Abertura forte: problema ou dado impactante (0:00-0:30)
- Contexto: o que está acontecendo e por quê importa (0:30-1:30)
- Análise: 3 insights práticos com exemplos reais (1:30-3:30)
- Conclusão: o que você faz diferente depois disso (3:30-4:00)
- CTA: inscrição + comentário

Em português brasileiro."""
    return _call_claude(prompt, max_tokens=1500)


def generate_medium(context: str) -> str:
    prompt = f"""
{context}

Escreva um artigo completo para o Medium com as seguintes características:
- Título: envolvente, direto, sem clickbait vazio
- Subtítulo: complementa o título com a promessa do artigo
- Tamanho: 800-1.200 palavras
- Estrutura: introdução + 3-4 seções com subtítulos + conclusão
- Cada seção deve ter um insight acionável
- Use dados e exemplos concretos
- Tom: reflexivo e consultivo, como um artigo de opinião embasado
- Termine com uma chamada para reflexão ou ação
- Em português brasileiro

Artigo:"""
    return _call_claude(prompt, max_tokens=2000)


def generate_image_concept(context: str) -> dict:
    prompt = f"""
{context}

Crie conceitos visuais detalhados para imagens de cada plataforma.
Para cada uma, escreva um prompt em inglês para geração de imagem via IA (DALL-E / Flux).

O estilo visual deve ser: moderno, profissional, com paleta azul profundo + laranja vibrante,
tipografia clean, elementos de tecnologia e negócios, sem texto na imagem.

Formato para cada plataforma:

LINKEDIN (1200x628, retangular):
[prompt]

INSTAGRAM (1080x1080, quadrado):
[prompt]

TIKTOK (1080x1920, vertical):
[prompt]

YOUTUBE_THUMBNAIL (1280x720, retangular):
[prompt]

MEDIUM (1200x630, retangular):
[prompt]"""
    raw = _call_claude(prompt, max_tokens=800)

    concepts = {}
    for platform in ["linkedin", "instagram", "tiktok", "youtube_thumbnail", "medium"]:
        key = platform.upper().replace("_THUMBNAIL", "") if platform != "youtube_thumbnail" else "YOUTUBE_THUMBNAIL"
        pattern = f"{key}[^:]*:(.+?)(?=(?:LINKEDIN|INSTAGRAM|TIKTOK|YOUTUBE_THUMBNAIL|MEDIUM):|$)"
        import re
        match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        concepts[platform] = match.group(1).strip() if match else raw[:300]

    return concepts


def generate_video_script(context: str) -> str:
    prompt = f"""
{context}

Escreva um roteiro detalhado para um vídeo curto (90 segundos) para uso com avatar de IA (D-ID / Heygen).
O roteiro deve ser falado naturalmente, como se você estivesse em uma conversa séria mas informal.

Formato:
- Sem marcações de cena
- Apenas o texto que será falado
- Pausas indicadas com [pausa]
- Ênfases indicadas com MAIÚSCULAS
- Total: 200-250 palavras
- Em português brasileiro"""
    return _call_claude(prompt, max_tokens=500)


def _build_article_context(article: dict) -> str:
    return f"""Notícia original (em inglês, não publicada em português ainda):

Título: {article['title']}
Fonte: {article['source']}
Publicado em: {article.get('published', 'recentemente')}
URL: {article.get('url', '')}

Resumo/Conteúdo:
{article.get('full_content') or article.get('summary', '')}

---
Baseado nessa notícia, adapte para o seu contexto e linguagem."""
