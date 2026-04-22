"""
LinkedIn visual generator: carousel PDF or single infographic.

Flow:
  1. Claude reads article + LinkedIn post and structures slides as JSON
  2. Python renders HTML/CSS → PDF via weasyprint
  3. PDF published directly to LinkedIn (native carousel support)

Slide dimensions: 1080×1350px (4:5 portrait — optimal for LinkedIn carousel)
Single image:     1200×628px  (1.91:1 — standard LinkedIn post image)
"""

import html
import json
import re
import os
from pathlib import Path
from typing import Optional

import anthropic

_STRUCTURE_PROMPT = """\
Você vai estruturar conteúdo em um carrossel executivo para LinkedIn.

POST LINKEDIN JÁ ESCRITO:
{linkedin_post}

ARTIGO ORIGINAL:
Título: {title}
Fonte: {source} ({region})
Conteúdo: {content}

---
TAREFA: decida o formato e estruture os slides. Retorne APENAS JSON válido, sem nenhum texto antes ou depois.

REGRAS DE FORMATO:
- 2+ estatísticas ou insights distintos → "carousel" com 5 a 7 slides
- 1 dado muito forte e único → "single"

REGRAS DE CONTEÚDO:
- Texto ultra-curto: máximo 12 palavras por linha, 3 linhas por slide
- Dados EXATOS do artigo — nunca invente números
- Cada slide deve funcionar sozinho, sem depender do anterior
- O slide de closing deve ter uma pergunta que provoque comentários

TIPOS DE SLIDE DISPONÍVEIS:
- cover   → headline + subtitle + source
- stat    → number + label + context
- insight → title + body  (title com borda laranja, destaque visual)
- list    → title + items (lista de 3 a 4 itens)
- quote   → text + author
- closing → cta (pergunta) + handle

FORMATO JSON para carousel:
{{
  "format": "carousel",
  "slides": [
    {{"type": "cover",   "headline": "...", "subtitle": "...", "source": "Fonte"}},
    {{"type": "stat",    "number": "74%",  "label": "das empresas capturam menos de 30% do valor", "context": "PwC Global AI Study 2026"}},
    {{"type": "insight", "title": "O diferencial não é tecnologia", "body": "Líderes automatizam decisões. Seguidores automatizam tarefas. A diferença de resultado é 7x."}},
    {{"type": "list",    "title": "O que os líderes fazem diferente", "items": ["Automatizam decisões, não só processos", "Framework de IA Responsável adotado", "Confiança dos colaboradores 2x maior"]}},
    {{"type": "closing", "cta": "Sua empresa está no grupo dos 20% ou dos 80%?", "handle": "@robleds"}}
  ]
}}

FORMATO JSON para single:
{{
  "format": "single",
  "headline": "7x",
  "subheadline": "mais valor capturado pelos líderes em IA",
  "body": "Não é tecnologia. É estratégia de adoção.",
  "source": "PwC 2026 AI Performance Study"
}}"""


# ── Public API ────────────────────────────────────────────────────────────────

def build_linkedin_visual(
    article: dict,
    linkedin_post: str,
    api_key: str,
    output_dir: Path,
) -> Optional[Path]:
    """
    Generate a LinkedIn carousel PDF or single infographic PNG.
    Returns the path to the generated file, or None on failure.
    """
    try:
        structure = _generate_structure(article, linkedin_post, api_key)
        fmt = structure.get("format", "carousel")

        if fmt == "single":
            return _render_single(structure, output_dir)
        else:
            return _render_carousel(structure.get("slides", []), output_dir)

    except Exception as e:
        print(f"[linkedin_carousel] Failed: {e}")
        return None


# ── Structure generation ──────────────────────────────────────────────────────

def _generate_structure(article: dict, linkedin_post: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _STRUCTURE_PROMPT.format(
        linkedin_post=linkedin_post[:800],
        title=article.get("title", ""),
        source=article.get("source", ""),
        region=article.get("source_region", ""),
        content=(article.get("full_content") or article.get("summary", ""))[:1500],
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw.strip(), flags=re.MULTILINE)
    json_match = re.search(r'\{.+\}', raw, re.DOTALL)
    if not json_match:
        raise ValueError(f"Claude returned no valid JSON: {raw[:200]}")
    return json.loads(json_match.group())


# ── PDF rendering (carousel) ──────────────────────────────────────────────────

def _render_carousel(slides: list[dict], output_dir: Path) -> Optional[Path]:
    try:
        from weasyprint import HTML
    except ImportError:
        print("[linkedin_carousel] weasyprint not installed — skipping PDF render")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    html_doc = _build_carousel_html(slides)
    out_path = output_dir / "linkedin_carousel.pdf"
    HTML(string=html_doc).write_pdf(str(out_path))
    print(f"[linkedin_carousel] Carousel PDF saved: {out_path}")
    return out_path


def _render_single(data: dict, output_dir: Path) -> Optional[Path]:
    try:
        from weasyprint import HTML
    except ImportError:
        print("[linkedin_carousel] weasyprint not installed — skipping render")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    html_doc = _build_single_html(data)
    out_path = output_dir / "linkedin_single.pdf"
    HTML(string=html_doc).write_pdf(str(out_path))
    print(f"[linkedin_carousel] Single infographic saved: {out_path}")
    return out_path


# ── HTML builders ─────────────────────────────────────────────────────────────

_CSS_BASE = """\
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body { background: #000; }

.slide {
  width: 1080px;
  height: 1350px;
  background: #0A1628;
  position: relative;
  overflow: hidden;
  page-break-after: always;
  font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
  color: #FFFFFF;
}

/* Decorative accents */
.corner-glow {
  position: absolute;
  top: -100px; right: -100px;
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(255,107,53,0.12) 0%, transparent 70%);
  border-radius: 50%;
}
.bottom-line {
  position: absolute;
  bottom: 0; left: 0;
  width: 100%; height: 5px;
  background: linear-gradient(to right, #FF6B35 0%, rgba(255,107,53,0.1) 60%, transparent 100%);
}

/* Slide inner — flex column, centered content */
.inner {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 90px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 90px 90px 40px 90px;
}

/* Footer */
.footer {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 90px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 90px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.footer-name { font-size: 22px; font-weight: 600; color: rgba(255,255,255,0.35); }
.footer-num  { font-size: 20px; color: rgba(255,255,255,0.25); }

/* Accent line */
.accent-line {
  width: 72px; height: 6px;
  background: #FF6B35;
  border-radius: 3px;
  margin: 36px 0;
}

/* ── Cover ── */
.tag {
  font-size: 20px; font-weight: 700;
  color: #FF6B35;
  letter-spacing: 4px;
  text-transform: uppercase;
  margin-bottom: 28px;
}
.cover-headline {
  font-size: 70px; font-weight: 900;
  line-height: 1.08;
  margin-bottom: 0;
}
.cover-subtitle {
  font-size: 30px; font-weight: 400;
  color: rgba(255,255,255,0.65);
  line-height: 1.55;
}
.cover-source {
  font-size: 20px; font-weight: 600;
  color: rgba(255,107,53,0.8);
  margin-top: 32px;
  letter-spacing: 1px;
}

/* ── Stat ── */
.stat-number {
  font-size: 170px; font-weight: 900;
  color: #FF6B35;
  line-height: 0.85;
  margin-bottom: 36px;
}
.stat-label {
  font-size: 38px; font-weight: 600;
  line-height: 1.4;
  margin-bottom: 20px;
}
.stat-context {
  font-size: 22px;
  color: rgba(255,255,255,0.45);
}

/* ── Insight ── */
.insight-title {
  font-size: 54px; font-weight: 900;
  line-height: 1.15;
  padding-left: 32px;
  border-left: 8px solid #FF6B35;
  margin-bottom: 44px;
}
.insight-body {
  font-size: 32px; font-weight: 400;
  color: rgba(255,255,255,0.82);
  line-height: 1.65;
}

/* ── List ── */
.list-title {
  font-size: 50px; font-weight: 900;
  line-height: 1.15;
  margin-bottom: 48px;
}
.list-items { list-style: none; }
.list-items li {
  font-size: 30px;
  color: rgba(255,255,255,0.88);
  line-height: 1.5;
  padding: 18px 0 18px 36px;
  border-bottom: 1px solid rgba(255,255,255,0.09);
  position: relative;
}
.list-items li:last-child { border-bottom: none; }
.list-items li::before {
  content: '';
  position: absolute;
  left: 0; top: 26px;
  width: 14px; height: 14px;
  background: #FF6B35;
  border-radius: 50%;
}

/* ── Quote ── */
.quote-mark {
  font-size: 140px; font-weight: 900;
  color: #FF6B35;
  line-height: 0.7;
  font-family: Georgia, 'Times New Roman', serif;
  margin-bottom: 20px;
}
.quote-text {
  font-size: 42px; font-weight: 600;
  font-style: italic;
  line-height: 1.45;
  margin-bottom: 44px;
}
.quote-author {
  font-size: 24px;
  color: rgba(255,255,255,0.5);
}

/* ── Closing ── */
.closing-cta {
  font-size: 54px; font-weight: 900;
  line-height: 1.2;
  margin-bottom: 64px;
}
.closing-handle {
  font-size: 44px; font-weight: 800;
  color: #FF6B35;
  margin-bottom: 16px;
}
.closing-tagline {
  font-size: 24px;
  color: rgba(255,255,255,0.4);
  letter-spacing: 1px;
}
"""

_CSS_SINGLE = """\
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }

@page { size: 1200px 628px; margin: 0; }

.slide {
  width: 1200px; height: 628px;
  background: #0A1628;
  position: relative;
  overflow: hidden;
  font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
  color: #FFFFFF;
}
.corner-glow {
  position: absolute;
  top: -80px; right: -80px;
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(255,107,53,0.15) 0%, transparent 70%);
  border-radius: 50%;
}
.bottom-line {
  position: absolute;
  bottom: 0; left: 0;
  width: 100%; height: 5px;
  background: linear-gradient(to right, #FF6B35, rgba(255,107,53,0.1) 60%, transparent);
}
.inner {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 70px 80px;
}
.s-headline {
  font-size: 110px; font-weight: 900;
  color: #FF6B35;
  line-height: 0.9;
  margin-bottom: 20px;
}
.s-subheadline {
  font-size: 38px; font-weight: 700;
  line-height: 1.3;
  margin-bottom: 24px;
}
.s-body {
  font-size: 28px;
  color: rgba(255,255,255,0.7);
  line-height: 1.5;
  margin-bottom: 32px;
}
.s-source {
  font-size: 18px; font-weight: 600;
  color: rgba(255,107,53,0.75);
  letter-spacing: 1px;
}
.s-handle {
  position: absolute;
  bottom: 28px; right: 48px;
  font-size: 20px; font-weight: 700;
  color: rgba(255,255,255,0.3);
}
"""


def _build_carousel_html(slides: list[dict]) -> str:
    total = len(slides)
    page_css = f"@page {{ size: 1080px 1350px; margin: 0; }}"
    rendered = [_render_slide(s, i + 1, total) for i, s in enumerate(slides)]
    return (
        f"<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        f"<style>{page_css}\n{_CSS_BASE}</style></head>"
        f"<body>{''.join(rendered)}</body></html>"
    )


def _build_single_html(data: dict) -> str:
    e = html.escape
    body = (
        f"<div class='slide'>"
        f"<div class='corner-glow'></div>"
        f"<div class='inner'>"
        f"<div class='s-headline'>{e(data.get('headline',''))}</div>"
        f"<div class='s-subheadline'>{e(data.get('subheadline',''))}</div>"
        f"<div class='s-body'>{e(data.get('body',''))}</div>"
        f"<div class='s-source'>{e(data.get('source',''))}</div>"
        f"</div>"
        f"<div class='s-handle'>@robleds</div>"
        f"<div class='bottom-line'></div>"
        f"</div>"
    )
    return (
        f"<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        f"<style>{_CSS_SINGLE}</style></head>"
        f"<body>{body}</body></html>"
    )


def _render_slide(slide: dict, index: int, total: int) -> str:
    e = html.escape
    t = slide.get("type", "insight")
    footer = (
        f"<div class='footer'>"
        f"<span class='footer-name'>Rodrigo Robledo</span>"
        f"<span class='footer-num'>{index} / {total}</span>"
        f"</div>"
    )
    deco = "<div class='corner-glow'></div><div class='bottom-line'></div>"

    if t == "cover":
        inner = (
            f"<div class='tag'>Rodrigo Robledo</div>"
            f"<div class='cover-headline'>{e(slide.get('headline',''))}</div>"
            f"<div class='accent-line'></div>"
            f"<div class='cover-subtitle'>{e(slide.get('subtitle',''))}</div>"
            f"<div class='cover-source'>{e(slide.get('source',''))}</div>"
        )

    elif t == "stat":
        inner = (
            f"<div class='stat-number'>{e(slide.get('number',''))}</div>"
            f"<div class='stat-label'>{e(slide.get('label',''))}</div>"
            f"<div class='accent-line'></div>"
            f"<div class='stat-context'>{e(slide.get('context',''))}</div>"
        )

    elif t == "insight":
        inner = (
            f"<div class='insight-title'>{e(slide.get('title',''))}</div>"
            f"<div class='insight-body'>{e(slide.get('body',''))}</div>"
        )

    elif t == "list":
        items_html = "".join(
            f"<li>{e(item)}</li>" for item in slide.get("items", [])
        )
        inner = (
            f"<div class='list-title'>{e(slide.get('title',''))}</div>"
            f"<ul class='list-items'>{items_html}</ul>"
        )

    elif t == "quote":
        inner = (
            f"<div class='quote-mark'>\u201c</div>"
            f"<div class='quote-text'>{e(slide.get('text',''))}</div>"
            f"<div class='quote-author'>\u2014 {e(slide.get('author','Rodrigo Robledo'))}</div>"
        )

    elif t == "closing":
        inner = (
            f"<div class='closing-cta'>{e(slide.get('cta',''))}</div>"
            f"<div class='closing-handle'>{e(slide.get('handle','@robleds'))}</div>"
            f"<div class='closing-tagline'>GovTech &middot; IA Aplicada &middot; Transformação Digital</div>"
        )

    else:  # fallback: treat as insight
        inner = (
            f"<div class='insight-title'>{e(slide.get('title', slide.get('headline','')))}</div>"
            f"<div class='insight-body'>{e(slide.get('body', slide.get('text','')))}</div>"
        )

    return (
        f"<div class='slide'>{deco}"
        f"<div class='inner'>{inner}</div>"
        f"{footer}</div>"
    )
