import json
import os
import re
import feedparser

def _parse_json_response(raw: str) -> dict | list:
    """Parse JSON from Claude response, handling markdown code fences."""
    raw = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw.strip(), flags=re.MULTILINE)
    m = re.search(r'[\[{].+[\]}]', raw.strip(), re.DOTALL)
    if m:
        return json.loads(m.group())
    return json.loads(raw.strip())
import requests
from datetime import datetime, timedelta, timezone, date
from typing import Optional
from config import (
    NEWS_RSS_FEEDS, PT_NEWS_RSS_FEEDS, NEWS_KEYWORDS,
    EXECUTIVE_SIGNAL_KEYWORDS, INSIGHT_KEYWORDS, OUTPUT_DIR, RODRIGO_PERSONA,
)

# Points per tier: 1=strategic/research, 2=top media, 3=specialist, 4=regional
_TIER_SCORE = {1: 40, 2: 30, 3: 20, 4: 15}


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_recent_ai_news(max_age_days: int = 7) -> list[dict]:
    """Fetch recent AI/productivity articles. Uses NewsAPI if key set, else RSS feeds."""
    newsapi_key = os.environ.get("NEWSAPI_KEY")
    if newsapi_key:
        articles = _fetch_from_newsapi(newsapi_key, max_age_days)
        if articles:
            return articles

    return _fetch_from_rss(max_age_days)


def _fetch_from_newsapi(api_key: str, max_age_days: int) -> list[dict]:
    """Fetch articles from NewsAPI.org."""
    from_date = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    query = (
        "(artificial intelligence OR AI OR LLM OR generative AI) AND "
        "(productivity OR enterprise OR business OR workplace OR workforce OR ROI)"
    )
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "from": from_date,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 30,
                "apiKey": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data.get("articles", []):
            title = item.get("title", "")
            description = item.get("description", "") or ""
            if not _is_ai_relevant(title, description):
                continue
            pub_str = item.get("publishedAt", "")
            articles.append({
                "title": title,
                "url": item.get("url", ""),
                "summary": description[:1500],
                "source": item.get("source", {}).get("name", "NewsAPI"),
                "published": pub_str,
            })
        print(f"[news_fetcher] NewsAPI: {len(articles)} relevant articles found")
        return articles
    except Exception as e:
        print(f"[news_fetcher] NewsAPI error: {e} — falling back to RSS")
        return []


def _fetch_from_rss(max_age_days: int) -> list[dict]:
    """Fetch recent AI/productivity articles from RSS feeds."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    articles = []

    for feed_config in NEWS_RSS_FEEDS:
        feed_url = feed_config["url"]
        source_tier = feed_config.get("tier", 3)
        source_region = feed_config.get("region", "US")

        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                pub = _parse_date(entry)
                if pub and pub < cutoff:
                    continue

                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")

                if not _is_ai_relevant(title, summary):
                    continue

                articles.append({
                    "title": title,
                    "url": entry.get("link", ""),
                    "summary": _clean_html(summary)[:1500],
                    "source": feed.feed.get("title", feed_url),
                    "source_tier": source_tier,
                    "source_region": source_region,
                    "published": pub.isoformat() if pub else "",
                })
        except Exception as e:
            print(f"[news_fetcher] Error fetching {feed_url}: {e}")

    print(f"[news_fetcher] {len(articles)} articles collected from {len(NEWS_RSS_FEEDS)} feeds")
    return articles


def filter_not_in_portuguese(articles: list[dict], api_key: str = "") -> list[dict]:
    """
    Keep only articles not yet covered in Portuguese media.

    Three-stage pipeline:
      1. Entity-based fast filter (no API cost)
         - 'covered'   (2+ entities match PT title) → drop
         - 'fresh'     (0 matches)                  → keep
         - 'ambiguous' (exactly 1 match)            → stage 2
      2. Claude batch check for ambiguous cases (single API call, haiku)
         - If no api_key: treat all ambiguous as fresh (let them through)
    """
    pt_titles = _fetch_pt_news_titles(max_age_hours=72)

    fresh: list[dict] = []
    ambiguous: list[dict] = []

    for article in articles:
        verdict = _coverage_verdict(article["title"], pt_titles)
        if verdict == "covered":
            pass  # drop silently
        elif verdict == "ambiguous":
            ambiguous.append(article)
        else:
            fresh.append(article)

    # Resolve ambiguous cases via Claude (one batch call)
    if ambiguous and api_key:
        covered_urls = _claude_coverage_batch(ambiguous, pt_titles, api_key)
        for article in ambiguous:
            if article["url"] not in covered_urls:
                fresh.append(article)
        resolved = len(ambiguous) - len(covered_urls)
        print(
            f"[news_fetcher] Claude resolved {len(ambiguous)} ambiguous: "
            f"{resolved} passed, {len(covered_urls)} filtered"
        )
    else:
        fresh.extend(ambiguous)  # conservative: let them through without Claude

    total_filtered = len(articles) - len(fresh)
    print(
        f"[news_fetcher] {len(fresh)}/{len(articles)} articles not yet covered "
        f"in Portuguese ({total_filtered} filtered)"
    )
    return fresh


def filter_not_recently_published(articles: list[dict], days: int = 7) -> list[dict]:
    """Remove articles that cover topics already published in the last N days."""
    published_titles = _get_recent_published_titles(days)
    if not published_titles:
        return articles

    result = [a for a in articles if not _overlaps_published(a["title"], published_titles)]
    skipped = len(articles) - len(result)
    if skipped:
        print(f"[news_fetcher] {skipped} articles filtered — topic already published recently")
    return result


def pick_best_article(articles: list[dict]) -> Optional[dict]:
    """Return the highest-scored article (numerical fallback, no LLM)."""
    if not articles:
        return None

    scored = sorted(articles, key=_score_article, reverse=True)
    best = scored[0]
    print(
        f"[news_fetcher] Best by score: '{best['title']}' "
        f"(score={_score_article(best):.1f}, region={best.get('source_region','?')}, "
        f"source={best.get('source','?')})"
    )
    for a in scored[1:3]:
        print(f"[news_fetcher]   Runner-up: '{a['title']}' (score={_score_article(a):.1f})")
    return best


def select_with_claude(articles: list[dict], api_key: str) -> Optional[dict]:
    """
    Use Claude to pick the best article for Rodrigo's executive LinkedIn audience.
    Takes the top-8 by numerical score, asks Claude to choose the most impactful one.
    Falls back to pick_best_article on any error.
    """
    if not articles or not api_key:
        return pick_best_article(articles)

    # Pre-rank numerically and take top 8 candidates
    candidates = sorted(articles, key=_score_article, reverse=True)[:8]

    lines = []
    for i, a in enumerate(candidates, 1):
        lines.append(
            f"[{i}] {a['title']}\n"
            f"Fonte: {a.get('source','?')} ({a.get('source_region','?')}) | "
            f"Publicado: {a.get('published','?')[:10]}\n"
            f"Resumo: {a.get('summary','')[:400]}\n---"
        )
    candidates_text = "\n".join(lines)

    prompt = f"""Você é curador de conteúdo para Rodrigo Robledo (@robleds), consultor GovTech e especialista em IA.

Audiência-alvo: executivos C-suite, gestores sênior e líderes de transformação digital no Brasil.
Plataforma: LinkedIn executivo.

Selecione o artigo com MAIOR potencial para um post de alto impacto. Priorize (nesta ordem):
1. Dados e pesquisas concretas que surpreendem — números, ROI, estudos de referência
2. Relevância estratégica para o mercado brasileiro e GovTech
3. Ângulo ainda não explorado pela mídia brasileira
4. Provoca reflexão executiva real ("isso muda o que faço na segunda-feira")

Evite: sensacionalismo, benchmarks técnicos sem impacto de negócio, notícias de produto sem implicação estratégica.

Candidatos:
{candidates_text}

Responda APENAS com JSON válido neste formato exato:
{{"choice": <número 1 a {len(candidates)}>, "reason": "<uma frase direta explicando a escolha>"}}"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        result = _parse_json_response(raw)
        idx = int(result["choice"]) - 1
        selected = candidates[idx]
        selected["claude_selection_reason"] = result.get("reason", "")
        print(f"[news_fetcher] Claude chose #{result['choice']}: '{selected['title']}'")
        print(f"[news_fetcher] Reason: {result.get('reason', '')}")
        return selected
    except Exception as e:
        print(f"[news_fetcher] Claude selection failed ({e}), falling back to score-based pick")
        return pick_best_article(articles)


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


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score_article(article: dict) -> float:
    """
    Score on four dimensions (total 0-100+):
      Source authority   0-40  (tier 1 = 40, 2 = 30, 3 = 20, 4 = 15)
      Recency            0-25  (authority matters more than freshness)
      Executive signals  0-20  (keywords relevant to C-suite audience)
      Data points        0-10  (specific numbers/% = higher credibility)
      Content depth       0-5  (longer summary = richer article)
    """
    score = 0.0
    title_lower = article["title"].lower()
    text = title_lower + " " + article["summary"].lower()

    # Source authority
    score += _TIER_SCORE.get(article.get("source_tier", 3), 15)

    # Recency (reduced weight vs. authority)
    pub_str = article.get("published", "")
    if pub_str:
        try:
            pub = datetime.fromisoformat(pub_str)
            age_h = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
            if age_h < 12:
                score += 25
            elif age_h < 24:
                score += 20
            elif age_h < 48:
                score += 14
            elif age_h < 72:
                score += 8
            else:
                score += 3
        except Exception:
            score += 8

    # Executive signal keywords in title (3 pts each, max 20)
    exec_hits = sum(1 for kw in EXECUTIVE_SIGNAL_KEYWORDS if kw in title_lower)
    score += min(exec_hits * 3, 20)

    # Specific data in text (numbers, percentages, dollar amounts)
    data_hits = len(re.findall(r"\d+\s*%|\$\s*\d+|\d+\s*billion|\d+\s*million", text))
    score += min(data_hits * 2, 10)

    # Content depth (summary length signals article substance)
    summary_len = len(article.get("summary", ""))
    if summary_len > 800:
        score += 5
    elif summary_len > 400:
        score += 3
    elif summary_len > 150:
        score += 1

    return score


# ── Relevance filter ──────────────────────────────────────────────────────────

def _is_ai_relevant(title: str, summary: str) -> bool:
    """
    Pass articles that discuss AI + any signal of business/strategic value,
    research findings, practical productivity impact, or executive curiosity.
    Requires explicit AI compound context — avoids generic matches.
    """
    text = (title + " " + summary).lower()

    # Require a clear AI/ML reference (no standalone "model" or "agent")
    ai_terms = [
        "artificial intelligence", "machine learning", "deep learning",
        "large language model", "llm", "generative ai", "foundation model",
        "ai model", "ai agent", "ai system", "ai tool", "ai platform",
        "gpt", "claude", "gemini", "copilot", "chatgpt", "chatbot",
        " ai ", "a.i.", "neural network", "automation", "algorithm",
    ]

    value_terms = [
        # Business & strategy
        "productivity", "enterprise", "business", "workplace", "workforce",
        "revenue", "roi", "efficiency", "company", "companies", "teams",
        "employees", "cost", "strategy", "competitive", "industry",
        # Research & credibility
        "study", "research", "survey", "report", "found", "reveals",
        "according to", "scientists", "researchers", "data shows",
        # Practical impact
        "saves", "automates", "replaces", "eliminates", "transforms",
        "faster", "better", "cheaper", "hours", "deployment", "adoption",
        # Executive curiosity
        "breakthrough", "record", "first", "unexpected", "regulation",
        "policy", "governance", "compliance",
    ]

    has_ai = any(term in text for term in ai_terms)
    has_value = any(term in text for term in value_terms)
    return has_ai and has_value


# ── Portuguese coverage check ─────────────────────────────────────────────────

# Tech/AI proper nouns that appear identically in PT and EN articles
_KNOWN_TECH_ENTITIES = {
    "openai", "chatgpt", "gpt-4", "gpt-5", "gpt4", "gpt4o", "o3", "o4",
    "anthropic", "claude",
    "google", "deepmind", "gemini",
    "microsoft", "copilot",
    "meta", "llama",
    "apple", "nvidia", "tesla", "amazon", "aws",
    "linkedin", "huggingface", "mistral", "cohere",
    "sam altman", "elon musk", "sundar pichai", "satya nadella",
    "ai act", "chatbot", "llm",
}


def _extract_entities(title: str) -> set[str]:
    """
    Extract language-invariant entities from an English title:
    known tech brands + capitalized proper nouns (skip first word).
    """
    entities = set()
    title_lower = title.lower()

    for entity in _KNOWN_TECH_ENTITIES:
        if entity in title_lower:
            entities.add(entity)

    words = title.split()
    for word in words[1:]:  # skip first word — always capitalized in titles
        cleaned = word.strip(".,!?:;\"'()[]{}|/\\")
        cleaned = re.sub(r"'s$", "", cleaned)   # remove possessives
        if cleaned and cleaned[0].isupper() and len(cleaned) > 2:
            entities.add(cleaned.lower())

    return entities


def _coverage_verdict(title: str, pt_titles: list[str]) -> str:
    """
    Returns 'covered', 'fresh', or 'ambiguous'.
      covered   — 2+ entities match a PT title → same story
      fresh     — 0 entities match → not yet covered
      ambiguous — exactly 1 entity matches → send to Claude
    """
    entities = _extract_entities(title)
    if not entities:
        return "fresh"

    max_matches = 0
    for pt_title in pt_titles:
        pt_lower = pt_title.lower()
        matches = sum(1 for e in entities if e in pt_lower)
        max_matches = max(max_matches, matches)

    if max_matches >= 2:
        return "covered"
    elif max_matches == 1:
        return "ambiguous"
    return "fresh"


def _fetch_pt_news_titles(max_age_hours: int = 72) -> list[str]:
    """Fetch recent PT-BR tech news titles, filtered to the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    titles = []
    for feed_url in PT_NEWS_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                pub = _parse_date(entry)
                if pub and pub < cutoff:
                    continue
                title = entry.get("title", "")
                if title:
                    titles.append(title.lower())
        except Exception:
            pass
    return titles


def _claude_coverage_batch(ambiguous: list[dict], pt_titles: list[str], api_key: str) -> set[str]:
    """
    Single Claude call to decide which ambiguous articles are already covered in PT media.
    Returns a set of article URLs that Claude considers covered.
    """
    pt_sample = "\n".join(f"- {t}" for t in pt_titles[:60])
    cases = "\n".join(f"[{i+1}] {a['title']}" for i, a in enumerate(ambiguous))

    prompt = f"""You are checking whether English AI news articles have already been reported by Brazilian Portuguese tech media.

Recent Brazilian tech news (last 72h):
{pt_sample}

English articles to evaluate:
{cases}

For each article, answer YES if the same story has already been covered in the Brazilian media listed above, or NO if it has not.
Respond ONLY with valid JSON: {{"results": [{{"id": 1, "covered": true}}, {{"id": 2, "covered": false}}, ...]}}"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _parse_json_response(response.content[0].text)
        covered_urls: set[str] = set()
        for item in data.get("results", []):
            if item.get("covered"):
                idx = int(item["id"]) - 1
                if 0 <= idx < len(ambiguous):
                    covered_urls.add(ambiguous[idx]["url"])
        return covered_urls
    except Exception as e:
        print(f"[news_fetcher] Claude coverage batch failed ({e}), treating ambiguous as fresh")
        return set()


# ── Published history deduplication ──────────────────────────────────────────

def _get_recent_published_titles(days: int) -> list[str]:
    """Read source_article.json from the last N days of output."""
    titles = []
    for i in range(1, days + 1):
        day = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        article_file = OUTPUT_DIR / day / "source_article.json"
        if article_file.exists():
            try:
                data = json.loads(article_file.read_text(encoding="utf-8"))
                title = data.get("title", "")
                if title:
                    titles.append(title.lower())
            except Exception:
                pass
    return titles


def _overlaps_published(title: str, published_titles: list[str]) -> bool:
    """True if 40%+ of significant words in title match a previously published title."""
    keywords = [w for w in title.lower().split() if len(w) > 4]
    if len(keywords) < 3:
        return False
    for pub_title in published_titles:
        matches = sum(1 for kw in keywords if kw in pub_title)
        if matches / len(keywords) >= 0.40:
            return True
    return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(entry) -> Optional[datetime]:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return None


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()
