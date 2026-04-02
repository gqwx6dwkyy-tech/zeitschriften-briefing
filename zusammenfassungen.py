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
        "Börse": "#5c6b73",
        "Internationale Politik": "#7a6855",
        "Finanzen": "#4a6259",
        "Künstliche Intelligenz": "#6b5c73",
        "Sonstiges": "#78756f",
    }

    # Nach Thema gruppieren
    gruppen: dict[str, list[BewerteterArtikel]] = {}
    for ba in artikel:
        gruppen.setdefault(ba.thema, []).append(ba)

    # --- Teil 1: Übersicht mit klickbaren Überschriften ---
    uebersicht_html = ""
    for thema, liste in gruppen.items():
        farbe = thema_farben.get(thema, "#78756f")
        uebersicht_html += f"""
    <div style="margin-top:28px; margin-bottom:10px;">
        <span style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:{farbe}; font-weight:600;">{thema}</span>
    </div>"""

        for ba in liste:
            a = ba.artikel
            aid = _artikel_id(a)
            relevanz_marker = '<span style="color:#b8a07a; margin-left:4px;" title="Hohe Relevanz">&#9679;</span>' if ba.relevanz == "hoch" else ""
            datum_str = a.datum.strftime("%d.%m. %H:%M")
            uebersicht_html += f"""
    <div style="padding:9px 0; border-bottom:1px solid #edecea;">
        <a href="#{aid}" style="font-size:14px; color:#1a1a1a; text-decoration:none; font-weight:500; line-height:1.4;">{a.titel}</a>{relevanz_marker}
        <div style="font-size:11px; color:#a09a93; margin-top:2px;">{a.quelle} &middot; {datum_str}</div>
    </div>"""

    # --- Teil 2: Ausführliche Zusammenfassungen ---
    details_html = ""
    for thema, liste in gruppen.items():
        farbe = thema_farben.get(thema, "#78756f")

        for ba in liste:
            a = ba.artikel
            aid = _artikel_id(a)
            zf = zusammenfassungen.get(aid, a.zusammenfassung)
            datum_str = a.datum.strftime("%d.%m.%Y %H:%M")

            details_html += f"""
    <article id="{aid}" class="artikel" style="margin:16px 0; padding:24px; background:#fff; border-radius:6px;">
        <div style="font-size:11px; color:#a09a93; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">{a.quelle} &middot; {datum_str}</div>
        <h3 style="margin:0 0 16px 0; font-size:17px; color:#1a1a1a; font-weight:600; line-height:1.3;">{a.titel}</h3>
        <p style="margin:0 0 20px 0; font-size:14px; color:#3d3d3d; line-height:1.75;">{zf}</p>
        <div style="display:flex; justify-content:space-between; align-items:center; padding-top:16px; border-top:1px solid #edecea;">
            <a href="{a.link}" style="font-size:12px; color:{farbe}; text-decoration:none; font-weight:500; letter-spacing:0.3px;">Originalartikel &rarr;</a>
            <a href="#top" style="font-size:11px; color:#b0aba5; text-decoration:none;">&uarr; Übersicht</a>
        </div>
    </article>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Briefing — {datum}</title>
    <style>
        body {{ margin:0; padding:0; background:#eae8e4; font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif; color:#1a1a1a; }}
        .container {{ max-width:680px; margin:0 auto; padding:0 16px 24px; }}
        .header {{ background:#2c2c2c; color:#fff; padding:28px 28px 24px; border-radius:0 0 6px 6px; margin-bottom:16px; }}
        .header h1 {{ margin:0; font-size:22px; font-weight:600; color:#fff; letter-spacing:-0.3px; }}
        .header .datum {{ color:#9a9590; font-size:13px; margin-top:6px; }}
        .uebersicht {{ background:#fff; border-radius:6px; padding:20px 24px; margin-bottom:16px; }}
        .trennlinie {{ border:0; border-top:1px solid #d5d0cb; margin:24px 0; }}
        .footer {{ text-align:center; padding:28px; font-size:11px; color:#a09a93; letter-spacing:0.3px; }}
        a:hover {{ opacity:0.7; }}
        .artikel:target {{ box-shadow:0 0 0 2px #b8a07a; }}
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
    <div class="footer">Zeitschriften-Briefing</div>
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
