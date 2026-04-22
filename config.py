import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

# Controla quais plataformas geram conteúdo e publicam.
# Configure via .env: ACTIVE_PLATFORMS=linkedin,instagram,medium
ACTIVE_PLATFORMS: list[str] = [
    p.strip()
    for p in os.getenv("ACTIVE_PLATFORMS", "linkedin").split(",")
    if p.strip()
]

RODRIGO_PERSONA = """
Você é Rodrigo Robledo (@robleds), fundador da DoctorWeb, consultor GovTech na EloGroup e Angel Advisor na PUC Angels.
Baseado no Rio de Janeiro, você começou na tecnologia em 2000 e hoje lidera iniciativas de transformação digital com IA.

Suas áreas de especialidade:
- IA aplicada a negócios: agentes, RAG, automação com n8n e Supabase
- Arquitetura e governança de dados
- Transformação digital no setor público e privado (GovTech)
- Conexão estratégica entre tecnologia e resultado financeiro

Seu estilo de comunicação:
- Humanizado, direto, sem enrolação nem jargão desnecessário
- Você fundamenta com dados mas traduz para o impacto real
- Tom de quem está na linha de frente implementando IA — não apenas teoriza
- Fala como consultor sênior, mas com a acessibilidade de quem gosta de compartilhar o que aprende
- Usa expressões naturais do dia a dia brasileiro, sem forçar gírias
- Provoca reflexão: faz o leitor pensar "isso muda o que eu faço na segunda-feira"
- Nunca soa como conteúdo de IA — sempre pessoal, com opinião própria
- Quando cita dados, sempre conecta com um "e daí?" — o que isso significa na prática

Você NÃO:
- Usa frases clichê como "no mundo cada vez mais digital"
- Começa com "Olá" ou saudações genéricas
- Escreve parágrafos longos sem respiro
- Faz promessas vazias ou conteúdo motivacional sem substância
"""

NEWS_KEYWORDS = [
    "AI productivity enterprise",
    "artificial intelligence workplace productivity 2026",
    "AI agents business automation",
    "generative AI ROI company",
    "LLM enterprise deployment",
    "AI workflow automation",
    "AI research study findings",
    "machine learning breakthrough",
    "AI regulation policy",
    "AI adoption workforce",
]

# Tier hierarchy:
#   1 = Strategic / research (think tanks, labs, top consulting) — highest authority
#   2 = Top tech media (broad reach + editorial rigor)
#   3 = Credible specialist media
#   4 = Regional / emerging market
NEWS_RSS_FEEDS = [
    # ── Tier 1: Strategic & Research ─────────────────────────────────────────
    {"url": "https://sloanreview.mit.edu/feed/",                         "tier": 1, "region": "US"},
    {"url": "https://hai.stanford.edu/news/feed/",                       "tier": 1, "region": "US"},
    {"url": "https://www.weforum.org/rss.xml",                          "tier": 1, "region": "EU"},
    {"url": "https://openai.com/blog/rss.xml",                          "tier": 1, "region": "US"},
    {"url": "https://www.anthropic.com/rss.xml",                        "tier": 1, "region": "US"},
    {"url": "https://blog.google/technology/ai/rss/",                   "tier": 1, "region": "US"},
    # ── Tier 2: Top Tech Media ────────────────────────────────────────────────
    {"url": "https://techcrunch.com/feed/",                             "tier": 2, "region": "US"},
    {"url": "https://feeds.feedburner.com/venturebeat/SZYF",           "tier": 2, "region": "US"},
    {"url": "https://www.technologyreview.com/feed/",                   "tier": 2, "region": "US"},
    {"url": "https://www.wired.com/feed/rss",                          "tier": 2, "region": "US"},
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab","tier": 2, "region": "US"},
    {"url": "https://www.theverge.com/rss/index.xml",                  "tier": 2, "region": "US"},
    {"url": "https://www.cnbc.com/id/19854910/device/rss/rss.html",    "tier": 2, "region": "US"},
    # ── Tier 3: Specialist Media ──────────────────────────────────────────────
    {"url": "https://www.fastcompany.com/technology/rss",              "tier": 3, "region": "US"},
    # Europa — França e Alemanha via cobertura em inglês
    {"url": "https://thenextweb.com/feed/",                            "tier": 3, "region": "EU"},
    {"url": "https://www.euractiv.com/section/digital/feed/",          "tier": 3, "region": "EU"},
    {"url": "https://www.zdnet.com/news/rss.xml",                      "tier": 3, "region": "EU"},
    # ── Tier 4: Regional ──────────────────────────────────────────────────────
    # Ásia — Japão e Sudeste Asiático
    {"url": "https://asia.nikkei.com/rss/feed/nar",                    "tier": 4, "region": "ASIA"},
    {"url": "https://www.techinasia.com/feed",                         "tier": 4, "region": "ASIA"},
    # Índia
    {"url": "https://analyticsindiamag.com/feed/",                     "tier": 4, "region": "IN"},
    {"url": "https://inc42.com/feed/",                                 "tier": 4, "region": "IN"},
    {"url": "https://economictimes.indiatimes.com/tech/rss.cms",       "tier": 4, "region": "IN"},
]

PT_NEWS_RSS_FEEDS = [
    # Consumer tech
    "https://canaltech.com.br/rss/",
    "https://www.tecmundo.com.br/rss",
    "https://olhardigital.com.br/feed/",
    # Executivo / negócios
    "https://exame.com/feed/",
    "https://computerworld.com.br/feed/",
    "https://www.infomoney.com.br/feed/",
    "https://mittechreview.com.br/feed/",
    "https://b9.com.br/feed/",
]

# Sinais executivos — vocabulário de C-suite e líderes empresariais
EXECUTIVE_SIGNAL_KEYWORDS = [
    # Impacto estratégico
    "ceo", "c-suite", "executive", "board", "strategy", "strategic",
    "fortune 500", "industry", "sector", "competitive advantage",
    # Dados e pesquisa (credibilidade)
    "study", "research", "survey", "report", "data", "percent", "%",
    "billion", "million", "roi", "revenue", "profit", "cost reduction",
    # Regulação e governança (pauta executiva)
    "regulation", "policy", "governance", "compliance", "framework",
    "eu ai act", "responsible ai", "ethics",
    # Força de trabalho e produtividade
    "workforce", "employees", "jobs", "productivity", "efficiency",
    "automation", "deployment", "adoption", "transformation",
    # Sinais de inovação (apropriados para executivos)
    "breakthrough", "new research", "announces", "launches", "first",
]

# Valor de insight e produtividade no corpo do artigo
INSIGHT_KEYWORDS = [
    "productivity", "workflow", "efficiency", "saves time", "automates",
    "enterprise", "business", "workplace", "workforce", "teams", "employees",
    "roi", "revenue", "profit", "cost", "strategy", "competitive advantage",
    "implementation", "deployment", "adoption",
]

PLATFORMS = ["linkedin", "instagram", "tiktok", "youtube", "medium"]

PLATFORM_IMAGE_SPECS = {
    "linkedin":  {"width": 1200, "height": 628,  "ratio": "1.91:1"},
    "instagram": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "tiktok":    {"width": 1080, "height": 1920, "ratio": "9:16"},
    "youtube":   {"width": 1280, "height": 720,  "ratio": "16:9"},
    "medium":    {"width": 1200, "height": 630,  "ratio": "1.91:1"},
}
