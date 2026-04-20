#!/usr/bin/env python3
"""
claude-daily-post — Rodrigo Robledo (@robleds)

Fluxo diário (06:30):
1. Busca notícia recente sobre IA/produtividade não publicada em PT-BR
2. Gera conteúdo personalizado para cada plataforma via Claude API
3. Gera imagens (fal.ai) e vídeo (D-ID) se configurado
4. Publica em LinkedIn, Instagram, TikTok, YouTube e Medium
5. Salva tudo em output/YYYY-MM-DD/

Retomada inteligente: se output/YYYY-MM-DD/ já existe com conteúdo gerado,
pula geração e vai direto para publicação (evita regerar e gastar créditos).
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "src"))

from config import OUTPUT_DIR
from src.news_fetcher import fetch_recent_ai_news, filter_not_in_portuguese, pick_best_article, fetch_full_content
from src.content_generator import generate_all_content
from src.image_generator import generate_images
from src.video_generator import generate_video
from src.publishers.linkedin_publisher import LinkedInPublisher
from src.publishers.instagram_publisher import InstagramPublisher
from src.publishers.tiktok_publisher import TikTokPublisher
from src.publishers.youtube_publisher import YouTubePublisher
from src.publishers.medium_publisher import MediumPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("daily-post")

PLATFORMS = ["linkedin", "instagram", "tiktok", "youtube", "medium"]


def _load_existing_content(output_dir: Path) -> dict | None:
    """Load already-generated content from disk if it exists."""
    content = {}
    for platform in PLATFORMS:
        f = output_dir / f"{platform}.txt"
        if not f.exists():
            return None
        content[platform] = f.read_text(encoding="utf-8")

    script_file = output_dir / "videos" / "video_script.txt"
    content["video_script"] = script_file.read_text(encoding="utf-8") if script_file.exists() else ""

    concepts_file = output_dir / "image_results.json"
    content["image_concept"] = {}
    if concepts_file.exists():
        try:
            results = json.loads(concepts_file.read_text(encoding="utf-8"))
            content["image_concept"] = {k: v.get("prompt", "") for k, v in results.items()}
        except Exception:
            pass

    return content


def _load_existing_article(output_dir: Path) -> dict | None:
    f = output_dir / "source_article.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_previous_publish_results(output_dir: Path) -> dict:
    f = output_dir / "publish_results.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _platforms_needing_publish(previous: dict) -> list[str]:
    """Return platforms that haven't been successfully published yet."""
    pending = []
    for platform in PLATFORMS:
        result = previous.get(platform, {})
        if result.get("status") != "published":
            pending.append(platform)
    return pending


def run(seed_article: dict | None = None, force_regenerate: bool = False):
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_DIR / today
    output_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"=== claude-daily-post starting — {today} ===")

    # --- RETOMADA INTELIGENTE ---
    existing_content = None if force_regenerate else _load_existing_content(output_dir)
    existing_article = None if force_regenerate else _load_existing_article(output_dir)

    if existing_content and existing_article:
        log.info("Conteúdo já gerado hoje — pulando geração, indo direto para publicação")
        content = existing_content
        article = existing_article
    else:
        # 1. Encontrar artigo
        if seed_article:
            article = seed_article
            log.info(f"Usando seed article: {article['title']}")
        else:
            log.info("Buscando notícias recentes de IA...")
            articles = fetch_recent_ai_news(max_age_days=7)
            log.info(f"Encontrados {len(articles)} artigos relevantes")
            fresh = filter_not_in_portuguese(articles)
            log.info(f"Ainda não em português: {len(fresh)} artigos")
            article = pick_best_article(fresh) or pick_best_article(articles)
            if not article:
                log.error("Nenhum artigo encontrado. Abortando.")
                return

        # 2. Buscar conteúdo completo
        if article.get("url") and not article.get("full_content"):
            log.info(f"Buscando conteúdo completo de: {article['url']}")
            article["full_content"] = fetch_full_content(article["url"])

        (output_dir / "source_article.json").write_text(
            json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 3. Gerar conteúdo via Claude
        log.info("Gerando conteúdo por plataforma via Claude...")
        content = generate_all_content(article)

        for platform in PLATFORMS:
            (output_dir / f"{platform}.txt").write_text(content[platform], encoding="utf-8")
            log.info(f"[{platform}] Conteúdo salvo")

        (output_dir / "videos").mkdir(exist_ok=True)
        (output_dir / "videos" / "video_script.txt").write_text(content["video_script"], encoding="utf-8")

        # 4. Gerar imagens
        log.info("Gerando imagens...")
        image_results = generate_images(content["image_concept"], output_dir)
        (output_dir / "image_results.json").write_text(
            json.dumps(image_results, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 5. Gerar vídeo
        log.info("Gerando vídeo...")
        generate_video(content["video_script"], output_dir)

    # --- PUBLICAÇÃO ---
    previous_results = _load_previous_publish_results(output_dir)
    pending_platforms = _platforms_needing_publish(previous_results)

    if not pending_platforms:
        log.info("Todas as plataformas já foram publicadas hoje!")
        _print_summary(today, output_dir, article, previous_results)
        return

    log.info(f"Publicando em: {', '.join(pending_platforms)}")

    video_path = _find_video(output_dir)
    publishers = {
        "linkedin":  LinkedInPublisher(),
        "instagram": InstagramPublisher(),
        "tiktok":    TikTokPublisher(),
        "youtube":   YouTubePublisher(),
        "medium":    MediumPublisher(),
    }

    publish_results = dict(previous_results)
    for platform in pending_platforms:
        log.info(f"Publicando em {platform}...")
        image_path = _find_image(output_dir, platform)
        result = publishers[platform].safe_publish(content[platform], image_path, video_path)
        publish_results[platform] = result

    (output_dir / "publish_results.json").write_text(
        json.dumps(publish_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info("=== Daily post completo ===")
    _print_summary(today, output_dir, article, publish_results)


def _find_image(output_dir: Path, platform: str) -> Path | None:
    img_map = {
        "linkedin":  "linkedin.png",
        "instagram": "instagram.png",
        "tiktok":    "tiktok.png",
        "youtube":   "youtube_thumbnail.png",
        "medium":    "medium.png",
    }
    path = output_dir / "images" / img_map.get(platform, "")
    return path if path.exists() else None


def _find_video(output_dir: Path) -> Path | None:
    path = output_dir / "videos" / "video.mp4"
    return path if path.exists() else None


def _print_summary(today: str, output_dir: Path, article: dict, results: dict):
    print("\n" + "=" * 60)
    print(f"  RESUMO DO DIA — {today}")
    print("=" * 60)
    print(f"  Notícia: {article['title'][:70]}")
    print(f"  Fonte:   {article.get('source', 'N/A')}")
    print(f"  Output:  {output_dir}")
    print()
    for platform in PLATFORMS:
        result = results.get(platform, {})
        status = result.get("status", "pending")
        icon = "✓" if status == "published" else "○" if status == "skipped" else "✗"
        detail = result.get("url") or result.get("post_id") or result.get("reason", "")
        print(f"  {icon} {platform:<12} {status}  {detail}")
    print("=" * 60 + "\n")


# Seed article — PwC 2026 AI Performance Study
SEED_ARTICLE = {
    "title": "Three-quarters of AI's economic gains are being captured by just 20% of companies",
    "url": "https://www.pwc.com/gx/en/news-room/press-releases/2026/pwc-2026-ai-performance-study.html",
    "source": "PwC Global",
    "published": "2026-04-13T00:00:00+00:00",
    "summary": (
        "PwC's 2026 AI Performance Study of 1,217 senior executives across 25 sectors reveals "
        "that 74% of AI's economic value is captured by just 20% of organizations. "
        "These AI leaders generate 7.2x more AI-driven gains than average competitors. "
        "The key differentiator is strategic: leaders use AI for growth and new revenue "
        "opportunities, not just cost-cutting. They automate decisions at 2.8x the rate of peers, "
        "are 1.7x more likely to have a Responsible AI framework, and their employees are "
        "twice as likely to trust AI outputs. 88% of respondents say AI increased annual revenue, "
        "with 30% reporting >10% increase. 65% of employees at AI-implementing organizations "
        "report improved productivity and efficiency."
    ),
}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="claude-daily-post")
    parser.add_argument("--seed", action="store_true", help="Usar seed article do dia (PwC study)")
    parser.add_argument("--dry-run", action="store_true", help="Gerar conteúdo sem publicar")
    parser.add_argument("--force", action="store_true", help="Forçar regeneração mesmo se conteúdo já existe")
    args = parser.parse_args()

    if args.dry_run:
        for key in ["LINKEDIN_ACCESS_TOKEN", "INSTAGRAM_ACCESS_TOKEN", "TIKTOK_ACCESS_TOKEN", "MEDIUM_INTEGRATION_TOKEN"]:
            os.environ.setdefault(key, "")

    run(seed_article=SEED_ARTICLE if args.seed else None, force_regenerate=args.force)
