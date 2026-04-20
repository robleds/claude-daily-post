from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

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
]

NEWS_RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.technologyreview.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
]

PT_NEWS_RSS_FEEDS = [
    "https://canaltech.com.br/rss/",
    "https://www.tecmundo.com.br/rss",
    "https://olhardigital.com.br/feed/",
]

PLATFORMS = ["linkedin", "instagram", "tiktok", "youtube", "medium"]

PLATFORM_IMAGE_SPECS = {
    "linkedin":  {"width": 1200, "height": 628,  "ratio": "1.91:1"},
    "instagram": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "tiktok":    {"width": 1080, "height": 1920, "ratio": "9:16"},
    "youtube":   {"width": 1280, "height": 720,  "ratio": "16:9"},
    "medium":    {"width": 1200, "height": 630,  "ratio": "1.91:1"},
}
