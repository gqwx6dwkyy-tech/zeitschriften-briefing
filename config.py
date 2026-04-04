"""Konfiguration für das Zeitschriften-Briefing."""

from pathlib import Path

# --- Projektpfade ---
PROJEKT_PFAD = Path(__file__).resolve().parent
VERLAUF_PFAD = PROJEKT_PFAD / "verlauf"
ENV_PFAD = PROJEKT_PFAD / ".env"

# --- RSS-Feeds ---
FEEDS = {
    "Wall Street Journal": [
        "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
        "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",
    ],
    "Barron's": [
        "https://news.google.com/rss/search?q=site:barrons.com&hl=en-US&gl=US&ceid=US:en",
    ],
    "Handelsblatt": [
        "https://www.handelsblatt.com/contentexport/feed/finanzen",
        "https://www.handelsblatt.com/contentexport/feed/politik",
    ],
    "Wirtschaftswoche": [
        "https://www.wiwo.de/contentexport/feed/rss/finanzen",
        "https://www.wiwo.de/contentexport/feed/rss/politik",
    ],
}

# --- Themen ---
THEMEN = ["Börse", "Künstliche Intelligenz", "Internationale Politik"]

THEMEN_KEYWORDS = {
    "Börse": [
        "aktie", "börse", "dax", "s&p", "nasdaq", "dow jones", "kurs",
        "rallye", "korrektur", "bullenmarkt", "bärenmarkt", "ipo", "dividende",
        "stock", "market", "rally", "shares", "trading", "index", "etf",
        "wall street", "earnings", "bull", "bear",
    ],
    "Internationale Politik": [
        "geopolitik", "sanktion", "handelskonflikt", "zoll", "tarif",
        "nato", "eu", "china", "usa", "russland", "krieg", "wahl",
        "gipfel", "diplomat", "außenpolitik", "embargo",
        "geopolit", "sanction", "trade war", "tariff", "election",
        "summit", "diplomacy", "foreign policy",
    ],
    "Künstliche Intelligenz": [
        "künstliche intelligenz", "ki ", "maschinelles lernen", "deep learning",
        "chatgpt", "openai", "claude", "anthropic", "google gemini", "llm",
        "neuronales netz", "algorithmus", "automatisierung", "robotik",
        "artificial intelligence", " ai ", "machine learning", "neural network",
        "generative ai", "deepseek", "nvidia", "gpu", "chip",
        "transformer", "large language model", "copilot", "midjourney",
    ],
}

# --- E-Mail ---
MAIL_EMPFAENGER = "christian_aigner91@hotmail.com"
SMTP_SERVER = "mail.gmx.net"
SMTP_PORT = 587

# --- Briefing ---
MAX_ARTIKEL_PRO_BRIEFING = 30
ARTIKEL_MAX_ALTER_STUNDEN = 24

# --- Gemini API (kostenlos) ---
GEMINI_MODELL = "gemini-2.0-flash-lite"
