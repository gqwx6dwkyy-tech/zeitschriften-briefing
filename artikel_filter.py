"""Artikel nach Themenrelevanz filtern — KI-gestützt oder per Keyword-Fallback."""

import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv

from config import THEMEN, THEMEN_KEYWORDS, GEMINI_MODELL, ENV_PFAD
from feed_sammler import Artikel

load_dotenv(ENV_PFAD)


@dataclass
class BewerteterArtikel:
    """Artikel mit Relevanzbewertung."""
    artikel: Artikel
    thema: str
    relevanz: str  # "hoch", "mittel", "niedrig"

    def als_dict(self) -> dict:
        return {
            **self.artikel.als_dict(),
            "thema": self.thema,
            "relevanz": self.relevanz,
        }


def _keyword_filter(artikel_liste: list[Artikel]) -> list[BewerteterArtikel]:
    """Fallback: Artikel per Keyword-Matching filtern."""
    ergebnisse: list[BewerteterArtikel] = []

    for artikel in artikel_liste:
        text = f"{artikel.titel} {artikel.zusammenfassung}".lower()
        bestes_thema = ""
        beste_treffer = 0

        for thema, keywords in THEMEN_KEYWORDS.items():
            treffer = sum(1 for kw in keywords if kw in text)
            if treffer > beste_treffer:
                beste_treffer = treffer
                bestes_thema = thema

        if beste_treffer >= 2:
            relevanz = "hoch" if beste_treffer >= 4 else "mittel"
            ergebnisse.append(BewerteterArtikel(artikel, bestes_thema, relevanz))

    return ergebnisse


def _ki_filter(artikel_liste: list[Artikel]) -> list[BewerteterArtikel]:
    """Artikel per Gemini API nach Relevanz bewerten."""
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Artikelliste für den Prompt aufbereiten
    artikel_texte = []
    for i, a in enumerate(artikel_liste):
        artikel_texte.append(
            f"[{i}] Quelle: {a.quelle}\n"
            f"    Titel: {a.titel}\n"
            f"    Zusammenfassung: {a.zusammenfassung[:300]}"
        )

    prompt = f"""Bewerte die folgenden Nachrichtenartikel nach ihrer Relevanz für diese Themen: {', '.join(THEMEN)}.

Für jeden relevanten Artikel gib zurück:
- index: die Nummer des Artikels
- thema: das passendste Thema ({', '.join(THEMEN)})
- relevanz: "hoch" oder "mittel"

Ignoriere Artikel die keinem Thema zuzuordnen sind oder nur geringe Relevanz haben.

Antworte ausschließlich als JSON-Array, z.B.:
[{{"index": 0, "thema": "Börse", "relevanz": "hoch"}}, ...]

Artikel:
{chr(10).join(artikel_texte)}"""

    antwort = client.models.generate_content(model=GEMINI_MODELL, contents=prompt)

    # JSON aus der Antwort extrahieren
    antwort_text = antwort.text.strip()
    # Falls die Antwort in Markdown-Codeblock verpackt ist
    if antwort_text.startswith("```"):
        zeilen = antwort_text.split("\n")
        antwort_text = "\n".join(zeilen[1:-1])

    bewertungen = json.loads(antwort_text)

    ergebnisse: list[BewerteterArtikel] = []
    for b in bewertungen:
        idx = b.get("index")
        if idx is not None and 0 <= idx < len(artikel_liste):
            ergebnisse.append(BewerteterArtikel(
                artikel=artikel_liste[idx],
                thema=b.get("thema", "Sonstiges"),
                relevanz=b.get("relevanz", "mittel"),
            ))

    return ergebnisse


def filtere_artikel(artikel_liste: list[Artikel]) -> list[BewerteterArtikel]:
    """Artikel nach Themenrelevanz filtern.

    Verwendet die Claude API falls ein API-Key konfiguriert ist,
    sonst Keyword-basiertes Matching als Fallback.

    Args:
        artikel_liste: Liste der zu bewertenden Artikel.

    Returns:
        Liste der als relevant bewerteten Artikel mit Thema und Relevanz.
    """
    if not artikel_liste:
        return []

    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        try:
            print(f"Filtere {len(artikel_liste)} Artikel per KI...")
            ergebnisse = _ki_filter(artikel_liste)
            print(f"  {len(ergebnisse)} relevante Artikel gefunden.")
            return ergebnisse
        except Exception as e:
            print(f"KI-Filter fehlgeschlagen ({e}), verwende Keyword-Fallback.")

    print(f"Filtere {len(artikel_liste)} Artikel per Keywords...")
    ergebnisse = _keyword_filter(artikel_liste)
    print(f"  {len(ergebnisse)} relevante Artikel gefunden.")
    return ergebnisse


if __name__ == "__main__":
    from feed_sammler import sammle_feeds
    artikel = sammle_feeds()
    print(f"{len(artikel)} Artikel gesammelt.\n")
    bewertete = filtere_artikel(artikel)
    for b in bewertete[:10]:
        print(f"[{b.relevanz.upper()}] [{b.thema}] {b.artikel.titel}")
