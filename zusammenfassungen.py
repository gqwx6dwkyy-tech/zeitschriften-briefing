"""Tägliche Zusammenfassungsseite generieren — deutsche Artikelzusammenfassungen."""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from config import GEMINI_MODELL, ENV_PFAD, PROJEKT_PFAD
from artikel_filter import BewerteterArtikel

load_dotenv(ENV_PFAD)

SEITEN_PFAD = PROJEKT_PFAD / "docs" / "zusammenfassungen"

_WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
_MONATE = ["Jänner", "Februar", "März", "April", "Mai", "Juni",
           "Juli", "August", "September", "Oktober", "November", "Dezember"]


def _datum_deutsch(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now()
    return f"{_WOCHENTAGE[dt.weekday()]}, {dt.strftime('%d')}. {_MONATE[dt.month - 1]} {dt.year}"


def _artikel_id(artikel) -> str:
    """Stabile kurze ID aus Titel generieren."""
    return hashlib.md5(artikel.titel.encode("utf-8")).hexdigest()[:8]


def _ki_zusammenfassungen(artikel: list[BewerteterArtikel]) -> dict[str, str]:
    """Per Gemini API ausführliche deutsche Zusammenfassungen generieren."""
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    artikel_texte = []
    ids = []
    for ba in artikel:
        a = ba.artikel
        aid = _artikel_id(a)
        ids.append(aid)
        artikel_texte.append(
            f'[{aid}] {a.quelle}: {a.titel}\n{a.zusammenfassung[:500]}'
        )

    prompt = f"""Erstelle für jeden der folgenden Nachrichtenartikel eine ausführliche,
gut verständliche Zusammenfassung auf Deutsch. Die Zusammenfassung soll:
- Mindestens 8-12 Sätze umfassen und alle relevanten Punkte des Artikels abdecken
- Die Kernaussage, wichtigsten Fakten, Zahlen und Hintergründe erfassen
- Den Kontext, Ursachen und mögliche Auswirkungen erklären
- Für einen Investor/Finanzexperten relevant aufbereitet sein
- Auch englische Artikel vollständig auf Deutsch zusammenfassen
- So geschrieben sein, dass man den Originalartikel nicht mehr lesen muss,
  um die wesentlichen Informationen zu kennen

Antworte als JSON-Object mit der Artikel-ID als Key und der Zusammenfassung als Value:
{{"{ids[0]}": "Zusammenfassung...", ...}}

Artikel:
{chr(10).join(artikel_texte)}"""

    antwort = client.models.generate_content(model=GEMINI_MODELL, contents=prompt)

    antwort_text = antwort.text.strip()
    if antwort_text.startswith("```"):
        zeilen = antwort_text.split("\n")
        antwort_text = "\n".join(zeilen[1:-1])

    return json.loads(antwort_text)


def _generiere_html(artikel: list[BewerteterArtikel],
                    zusammenfassungen: dict[str, str],
                    datum: str) -> str:
    """HTML-Zusammenfassungsseite generieren — Übersicht oben, Zusammenfassungen unten."""

    thema_farben = {
        "Börse": "#1a73e8",
        "Internationale Politik": "#d93025",
        "Finanzen": "#188038",
        "Künstliche Intelligenz": "#9334e6",
        "Sonstiges": "#5f6368",
    }

    # Nach Thema gruppieren
    gruppen: dict[str, list[BewerteterArtikel]] = {}
    for ba in artikel:
        gruppen.setdefault(ba.thema, []).append(ba)

    # --- Teil 1: Übersicht mit klickbaren Überschriften ---
    uebersicht_html = ""
    for thema, liste in gruppen.items():
        farbe = thema_farben.get(thema, "#5f6368")
        uebersicht_html += f"""
    <div style="border-left:4px solid {farbe}; padding-left:12px; margin-top:24px;">
        <h2 style="margin:0;color:{farbe};font-size:18px;">{thema}</h2>
    </div>
    <ul style="margin:8px 0 0 0; padding-left:20px; list-style:none;">"""

        for ba in liste:
            a = ba.artikel
            aid = _artikel_id(a)
            relevanz_marker = " &#9733;" if ba.relevanz == "hoch" else ""
            datum_str = a.datum.strftime("%d.%m. %H:%M")
            uebersicht_html += f"""
        <li style="margin:6px 0; line-height:1.4;">
            <a href="#{aid}" style="font-size:15px; color:#1a1a1a; text-decoration:none; font-weight:600;">{a.titel}</a>{relevanz_marker}
            <span style="font-size:11px; color:#888; margin-left:6px;">{a.quelle} &middot; {datum_str}</span>
        </li>"""

        uebersicht_html += "\n    </ul>"

    # --- Teil 2: Ausführliche Zusammenfassungen ---
    details_html = ""
    for thema, liste in gruppen.items():
        farbe = thema_farben.get(thema, "#5f6368")

        for ba in liste:
            a = ba.artikel
            aid = _artikel_id(a)
            zf = zusammenfassungen.get(aid, a.zusammenfassung)
            datum_str = a.datum.strftime("%d.%m.%Y %H:%M")

            details_html += f"""
    <div id="{aid}" class="artikel" style="margin:24px 0; padding:20px; background:#fff; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <div style="font-size:11px; color:#888; margin-bottom:4px;">{a.quelle} &middot; {datum_str}</div>
        <h3 style="margin:0 0 12px 0; font-size:17px; color:#1a1a1a; border-bottom:2px solid {farbe}; padding-bottom:8px;">{a.titel}</h3>
        <p style="margin:0 0 16px 0; font-size:14px; color:#333; line-height:1.7;">{zf}</p>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <a href="{a.link}" style="font-size:13px; color:{farbe}; text-decoration:none; font-weight:600;">Originalartikel &rarr;</a>
            <a href="#top" style="font-size:11px; color:#999; text-decoration:none;">&uarr; Zur Übersicht</a>
        </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Briefing — {datum}</title>
    <style>
        body {{ margin:0; padding:0; background:#f0f2f5; font-family:Arial,Helvetica,sans-serif; }}
        .container {{ max-width:700px; margin:0 auto; padding:20px 16px; }}
        .header {{ background:linear-gradient(135deg,#1a237e,#283593); color:#fff; padding:24px; border-radius:8px; margin-bottom:8px; }}
        .header h1 {{ margin:0; font-size:22px; }}
        .header .datum {{ color:#b0bec5; font-size:13px; margin-top:4px; }}
        .uebersicht {{ background:#fff; border-radius:8px; padding:16px 20px; margin-bottom:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
        .trennlinie {{ border:0; border-top:2px solid #e0e0e0; margin:32px 0; }}
        .footer {{ text-align:center; padding:24px; font-size:11px; color:#999; }}
        a:hover {{ text-decoration:underline !important; }}
        .artikel:target {{ outline:3px solid #1a73e8; outline-offset:4px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header" id="top">
        <h1>Tages-Briefing</h1>
        <div class="datum">{datum} &middot; {len(artikel)} Artikel</div>
    </div>
    <div class="uebersicht">
        {uebersicht_html}
    </div>
    <hr class="trennlinie">
    {details_html}
    <div class="footer">Automatisch erstellt &middot; Zeitschriften-Briefing</div>
</div>
</body>
</html>"""


def erstelle_zusammenfassungsseite(artikel: list[BewerteterArtikel],
                                   github_pages_url: str | None = None) -> tuple[Path, str]:
    """Zusammenfassungsseite generieren und speichern.

    Args:
        artikel: Liste der bewerteten Artikel.
        github_pages_url: Basis-URL für GitHub Pages (z.B. "https://user.github.io/repo").

    Returns:
        Tuple aus (Pfad zur HTML-Datei, URL zur Seite).
    """
    if not artikel:
        return SEITEN_PFAD / "leer.html", ""

    # Zusammenfassungen generieren
    zusammenfassungen: dict[str, str] = {}
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            print("Erstelle deutsche KI-Zusammenfassungen...")
            zusammenfassungen = _ki_zusammenfassungen(artikel)
        except Exception as e:
            print(f"KI-Zusammenfassung fehlgeschlagen ({e}), verwende Feed-Texte.")

    datum = _datum_deutsch()
    datum_kurz = datetime.now().strftime("%Y-%m-%d")
    html = _generiere_html(artikel, zusammenfassungen, datum)

    # Seite speichern
    SEITEN_PFAD.mkdir(parents=True, exist_ok=True)
    datei = SEITEN_PFAD / f"{datum_kurz}.html"
    datei.write_text(html, encoding="utf-8")
    print(f"Zusammenfassungsseite gespeichert: {datei}")

    # URL zur Seite
    if github_pages_url:
        seiten_url = f"{github_pages_url.rstrip('/')}/zusammenfassungen/{datum_kurz}.html"
    else:
        seiten_url = f"file:///{datei.as_posix()}"

    return datei, seiten_url


if __name__ == "__main__":
    from feed_sammler import sammle_feeds
    from artikel_filter import filtere_artikel

    artikel = sammle_feeds()
    bewertete = filtere_artikel(artikel)
    datei, links = erstelle_zusammenfassungsseite(bewertete)
    print(f"\n{len(links)} Artikel-Links generiert.")
    print(f"Seite: {datei}")
