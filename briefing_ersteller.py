"""Briefing aus bewerteten Artikeln erstellen — HTML und Plaintext."""

import json
import os
import hashlib
from datetime import datetime, timezone

from dotenv import load_dotenv

from config import THEMEN, CLAUDE_MODELL, ENV_PFAD, MAX_ARTIKEL_PRO_BRIEFING
from artikel_filter import BewerteterArtikel

load_dotenv(ENV_PFAD)

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


def _gruppiere_nach_thema(artikel: list[BewerteterArtikel]) -> dict[str, list[BewerteterArtikel]]:
    gruppen: dict[str, list[BewerteterArtikel]] = {}
    for thema in THEMEN:
        passende = [a for a in artikel if a.thema == thema]
        if passende:
            gruppen[thema] = passende
    bekannt = set(THEMEN)
    sonstige = [a for a in artikel if a.thema not in bekannt]
    if sonstige:
        gruppen["Sonstiges"] = sonstige
    return gruppen


def _ki_zusammenfassung(artikel: list[BewerteterArtikel]) -> dict[int, str]:
    """Per Claude API Kurzzusammenfassungen für die E-Mail generieren (2-3 Sätze)."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    artikel_texte = []
    for i, ba in enumerate(artikel):
        a = ba.artikel
        artikel_texte.append(
            f"[{i}] {a.quelle}: {a.titel}\n{a.zusammenfassung[:400]}"
        )

    prompt = f"""Erstelle für jeden der folgenden Nachrichtenartikel eine prägnante
Zusammenfassung in 2-3 Sätzen. Die Zusammenfassung soll die Kernaussage erfassen
und für einen Investor/Finanzexperten relevant sein.

Antworte als JSON-Object mit dem Index als Key und der Zusammenfassung als Value, z.B.:
{{"0": "Zusammenfassung...", "1": "Zusammenfassung..."}}

Artikel auf Deutsch zusammenfassen, auch wenn der Originalartikel auf Englisch ist.

Artikel:
{chr(10).join(artikel_texte)}"""

    antwort = client.messages.create(
        model=CLAUDE_MODELL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    antwort_text = antwort.content[0].text.strip()
    if antwort_text.startswith("```"):
        zeilen = antwort_text.split("\n")
        antwort_text = "\n".join(zeilen[1:-1])

    return {int(k): v for k, v in json.loads(antwort_text).items()}


def _erstelle_html(gruppen: dict[str, list[BewerteterArtikel]],
                   zusammenfassungen: dict[int, str],
                   artikel_index: dict[int, int],
                   link_map: dict[str, str],
                   datum: str) -> str:
    """HTML-Briefing generieren — Links zeigen auf Zusammenfassungsseite."""
    thema_farben = {
        "Börse": "#1a73e8",
        "Internationale Politik": "#d93025",
        "Finanzen": "#188038",
        "Künstliche Intelligenz": "#9334e6",
        "Sonstiges": "#5f6368",
    }

    artikel_html = ""
    for thema, artikel_liste in gruppen.items():
        farbe = thema_farben.get(thema, "#5f6368")
        artikel_html += f"""
        <tr><td style="padding:20px 0 8px 0;">
            <h2 style="margin:0;font-size:18px;color:{farbe};border-bottom:2px solid {farbe};padding-bottom:6px;">{thema}</h2>
        </td></tr>"""

        for ba in artikel_liste:
            a = ba.artikel
            aid = _artikel_id(a)
            zf = zusammenfassungen.get(artikel_index.get(id(ba), -1), a.zusammenfassung)
            relevanz_badge = "&#9733;" if ba.relevanz == "hoch" else ""
            datum_str = a.datum.strftime("%d.%m. %H:%M")
            # Link zur Zusammenfassungsseite, Fallback auf Originalartikel
            link = link_map.get(aid, a.link)

            artikel_html += f"""
        <tr><td style="padding:10px 0;border-bottom:1px solid #e0e0e0;">
            <div style="font-size:9px;color:#888;margin-bottom:2px;">{a.quelle} &middot; {datum_str} {relevanz_badge}</div>
            <a href="{link}" style="font-size:15px;color:#1a1a1a;text-decoration:none;font-weight:600;">{a.titel}</a>
            <div style="font-size:13px;color:#444;margin-top:4px;line-height:1.5;">{zf}</div>
        </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
<tr><td align="center" style="padding:20px 10px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;">
    <tr><td style="background:linear-gradient(135deg,#1a237e,#283593);padding:24px 24px 20px;">
        <h1 style="margin:0;color:#ffffff;font-size:22px;">Tages-Briefing</h1>
        <div style="color:#b0bec5;font-size:13px;margin-top:4px;">{datum}</div>
    </td></tr>
    <tr><td style="padding:0 24px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0">
        {artikel_html}
        </table>
    </td></tr>
    <tr><td style="padding:16px 24px;background:#f5f5f5;text-align:center;">
        <div style="font-size:11px;color:#999;">Automatisch erstellt &middot; Zeitschriften-Briefing</div>
    </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _erstelle_plaintext(gruppen: dict[str, list[BewerteterArtikel]],
                        zusammenfassungen: dict[int, str],
                        artikel_index: dict[int, int],
                        link_map: dict[str, str],
                        datum: str) -> str:
    """Plaintext-Briefing generieren."""
    zeilen = [f"=== TAGES-BRIEFING — {datum} ===", ""]

    for thema, artikel_liste in gruppen.items():
        zeilen.append(f"--- {thema.upper()} ---")
        zeilen.append("")
        for ba in artikel_liste:
            a = ba.artikel
            aid = _artikel_id(a)
            zf = zusammenfassungen.get(artikel_index.get(id(ba), -1), a.zusammenfassung)
            datum_str = a.datum.strftime("%d.%m. %H:%M")
            link = link_map.get(aid, a.link)
            zeilen.append(f"[{a.quelle} | {datum_str}] {a.titel}")
            zeilen.append(f"  {zf}")
            zeilen.append(f"  {link}")
            zeilen.append("")

    zeilen.append("---")
    zeilen.append("Automatisch erstellt — Zeitschriften-Briefing")
    return "\n".join(zeilen)


def erstelle_briefing(artikel: list[BewerteterArtikel],
                      link_map: dict[str, str] | None = None) -> tuple[str, str]:
    """Briefing aus bewerteten Artikeln erstellen.

    Args:
        artikel: Liste der bewerteten, relevanten Artikel.
        link_map: Dict mit artikel_id -> URL zur Zusammenfassungsseite.

    Returns:
        Tuple aus (HTML-Briefing, Plaintext-Briefing).
    """
    if link_map is None:
        link_map = {}

    if not artikel:
        datum = _datum_deutsch()
        return (
            f"<html><body><p>Keine relevanten Artikel für {datum} gefunden.</p></body></html>",
            f"Keine relevanten Artikel für {datum} gefunden.",
        )

    # Auf Maximum begrenzen (hoch-relevante zuerst)
    artikel_sortiert = sorted(artikel, key=lambda a: (0 if a.relevanz == "hoch" else 1))
    artikel_sortiert = artikel_sortiert[:MAX_ARTIKEL_PRO_BRIEFING]

    # Index für Zusammenfassungs-Zuordnung
    artikel_index: dict[int, int] = {}
    for i, ba in enumerate(artikel_sortiert):
        artikel_index[id(ba)] = i

    # Kurz-Zusammenfassungen für die E-Mail
    zusammenfassungen: dict[int, str] = {}
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            print("Erstelle KI-Zusammenfassungen für E-Mail...")
            zusammenfassungen = _ki_zusammenfassung(artikel_sortiert)
        except Exception as e:
            print(f"KI-Zusammenfassung fehlgeschlagen ({e}), verwende Feed-Texte.")

    gruppen = _gruppiere_nach_thema(artikel_sortiert)
    datum = _datum_deutsch()

    html = _erstelle_html(gruppen, zusammenfassungen, artikel_index, link_map, datum)
    text = _erstelle_plaintext(gruppen, zusammenfassungen, artikel_index, link_map, datum)

    return html, text
