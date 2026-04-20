#!/usr/bin/env python3
"""
claude-daily-post — Rodrigo Robledo (@robleds)

Fluxo diário (06:30):
1. Busca notícia recente sobre IA/produtividade não publicada em PT-BR
2. Gera conteúdo personalizado para cada plataforma via Claude API
3. Gera imagens (fal.ai) e vídeo (D-ID) se configurado
4. Publica em LinkedIn, Instagram, TikTok, YouTube e Medium
5. Salva tudo em output/YYYY-MM-DD/
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


def run(seed_article: dict | None = None):
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_DIR / today
    output_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"=== claude-daily-post starting — {today} ===")

    # 1. Find article
    if seed_article:
        article = seed_article
        log.info(f"Using seed article: {article['title']}")
    else:
        log.info("Fetching recent AI news...")
        articles = fetch_recent_ai_news(max_age_days=7)
        log.info(f"Found {len(articles)} relevant articles")
        fresh = filter_not_in_portuguese(articles)
        log.info(f"Not yet in Portuguese: {len(fresh)} articles")
        article = pick_best_article(fresh)
        if not article:
            log.warning("No fresh article found — using most recent regardless of PT coverage")
            article = pick_best_article(articles)
        if not article:
            log.error("No articles found at all. Aborting.")
            return

    # 2. Fetch full content
    if article.get("url") and not article.get("full_content"):
        log.info(f"Fetching full content from: {article['url']}")
        article["full_content"] = fetch_full_content(article["url"])

    (output_dir / "source_article.json").write_text(
        json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 3. Generate content
    log.info("Generating platform-specific content via Claude...")
    content = generate_all_content(article)

    for platform in ["linkedin", "instagram", "tiktok", "youtube", "medium"]:
        (output_dir / f"{platform}.txt").write_text(content[platform], encoding="utf-8")
        log.info(f"[{platform}] Content saved")

    (output_dir / "video_script.txt").write_text(content["video_script"], encoding="utf-8")

    # 4. Generate images
    log.info("Generating images...")
    image_results = generate_images(content["image_concept"], output_dir)
    (output_dir / "image_results.json").write_text(
        json.dumps(image_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 5. Generate video
    log.info("Generating video...")
    video_result = generate_video(content["video_script"], output_dir)

    # 6. Publish to platforms
    publishers = {
        "linkedin":  LinkedInPublisher(),
        "instagram": InstagramPublisher(),
        "tiktok":    TikTokPublisher(),
        "youtube":   YouTubePublisher(),
        "medium":    MediumPublisher(),
    }

    publish_results = {}
    for platform, publisher in publishers.items():
        log.info(f"Publishing to {platform}...")
        image_path = _find_image(output_dir, platform)
        video_path = Path(video_result["video_path"]) if video_result.get("video_path") else None
        result = publisher.safe_publish(content[platform], image_path, video_path)
        publish_results[platform] = result

    (output_dir / "publish_results.json").write_text(
        json.dumps(publish_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info("=== Daily post complete ===")
    _print_summary(today, output_dir, article, publish_results)


def _find_image(output_dir: Path, platform: str) -> Path | None:
    img_map = {
        "linkedin": "linkedin.png",
        "instagram": "instagram.png",
        "tiktok": "tiktok.png",
        "youtube": "youtube_thumbnail.png",
        "medium": "medium.png",
    }
    if platform in img_map:
        path = output_dir / "images" / img_map[platform]
        return path if path.exists() else None
    return None


def _print_summary(today: str, output_dir: Path, article: dict, results: dict):
    print("\n" + "="*60)
    print(f"  RESUMO DO DIA — {today}")
    print("="*60)
    print(f"  Notícia: {article['title'][:70]}")
    print(f"  Fonte:   {article.get('source', 'N/A')}")
    print(f"  Output:  {output_dir}")
    print()
    for platform, result in results.items():
        status = result.get("status", "unknown")
        icon = "✓" if status == "published" else "○" if status == "skipped" else "✗"
        detail = result.get("url") or result.get("post_id") or result.get("reason", "")
        print(f"  {icon} {platform:<12} {status}  {detail}")
    print("="*60 + "\n")


# Seed article for first run (PwC 2026 AI Performance Study)
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
    parser.add_argument("--seed", action="store_true", help="Use today's seed article (PwC study)")
    parser.add_argument("--dry-run", action="store_true", help="Generate content but don't publish")
    args = parser.parse_args()

    if args.dry_run:
        os.environ.setdefault("LINKEDIN_ACCESS_TOKEN", "")
        os.environ.setdefault("INSTAGRAM_ACCESS_TOKEN", "")
        os.environ.setdefault("TIKTOK_ACCESS_TOKEN", "")
        os.environ.setdefault("MEDIUM_INTEGRATION_TOKEN", "")

    run(seed_article=SEED_ARTICLE if args.seed else None)
