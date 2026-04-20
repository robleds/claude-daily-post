import feedparser
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from config import NEWS_RSS_FEEDS, PT_NEWS_RSS_FEEDS, NEWS_KEYWORDS


def fetch_recent_ai_news(max_age_days: int = 7) -> list[dict]:
    """Fetch recent AI/productivity articles from RSS feeds."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    articles = []

    for feed_url in NEWS_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                pub = _parse_date(entry)
                if pub and pub < cutoff:
                    continue

                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")

                if not _is_ai_productivity_relevant(title, summary):
                    continue

                articles.append({
                    "title": title,
                    "url": entry.get("link", ""),
                    "summary": _clean_html(summary)[:1500],
                    "source": feed.feed.get("title", feed_url),
                    "published": pub.isoformat() if pub else "",
                })
        except Exception as e:
            print(f"[news_fetcher] Error fetching {feed_url}: {e}")

    return articles


def filter_not_in_portuguese(articles: list[dict]) -> list[dict]:
    """Keep only articles that haven't been published in Portuguese yet."""
    pt_titles = _fetch_pt_news_titles()
    result = []
    for article in articles:
        if not _is_covered_in_portuguese(article["title"], pt_titles):
            result.append(article)
    return result


def pick_best_article(articles: list[dict]) -> Optional[dict]:
    """Return the most recent relevant article."""
    if not articles:
        return None
    articles_sorted = sorted(
        articles,
        key=lambda a: a.get("published", ""),
        reverse=True,
    )
    return articles_sorted[0]


def fetch_full_content(url: str) -> str:
    """Fetch and extract text content from article URL."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
        return text[:5000]
    except Exception as e:
        print(f"[news_fetcher] Could not fetch full content from {url}: {e}")
        return ""


def _is_ai_productivity_relevant(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    ai_terms = ["ai", "artificial intelligence", "llm", "generative ai", "gpt", "claude", "copilot", "automation"]
    business_terms = ["productivity", "enterprise", "business", "workplace", "workforce", "revenue", "roi", "efficiency", "company", "companies"]
    has_ai = any(term in text for term in ai_terms)
    has_business = any(term in text for term in business_terms)
    return has_ai and has_business


def _fetch_pt_news_titles() -> list[str]:
    titles = []
    for feed_url in PT_NEWS_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                titles.append(entry.get("title", "").lower())
        except Exception:
            pass
    return titles


def _is_covered_in_portuguese(title: str, pt_titles: list[str]) -> bool:
    keywords = [w for w in title.lower().split() if len(w) > 4]
    if len(keywords) < 3:
        return False
    matches = sum(
        1 for kw in keywords
        if any(kw in pt_title for pt_title in pt_titles)
    )
    return matches >= 3


def _parse_date(entry) -> Optional[datetime]:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        import time
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return None


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()
