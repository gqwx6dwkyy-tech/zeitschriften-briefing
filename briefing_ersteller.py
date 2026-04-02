"""Briefing-E-Mail erstellen — schlanke Mail mit Link zur Zusammenfassungsseite."""

from datetime import datetime

_WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
_MONATE = ["Jänner", "Februar", "März", "April", "Mai", "Juni",
           "Juli", "August", "September", "Oktober", "November", "Dezember"]


def _datum_deutsch(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now()
    return f"{_WOCHENTAGE[dt.weekday()]}, {dt.strftime('%d')}. {_MONATE[dt.month - 1]} {dt.year}"


def erstelle_briefing(anzahl_artikel: int, seiten_url: str) -> tuple[str, str]:
    """Schlanke Briefing-E-Mail mit Link zur Zusammenfassungsseite.

    Args:
        anzahl_artikel: Anzahl der relevanten Artikel.
        seiten_url: URL zur HTML-Zusammenfassungsseite.

    Returns:
        Tuple aus (HTML-Mail, Plaintext-Mail).
    """
    datum = _datum_deutsch()

    if anzahl_artikel == 0:
        html = f"<html><body><p>Keine relevanten Artikel für {datum} gefunden.</p></body></html>"
        text = f"Keine relevanten Artikel für {datum} gefunden."
        return html, text

    html = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f8f8f7;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f8f7;">
<tr><td align="center" style="padding:32px 10px;">
<table width="500" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:4px;border:1px solid #e8e6e3;">
    <tr><td style="padding:32px 32px 24px;border-bottom:1px solid #e8e6e3;">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#8a8580;margin-bottom:8px;">Tages-Briefing</div>
        <h1 style="margin:0;color:#1a1a1a;font-size:20px;font-weight:600;">{datum}</h1>
    </td></tr>
    <tr><td style="padding:32px;text-align:center;">
        <p style="font-size:15px;color:#4a4a4a;margin:0 0 28px 0;line-height:1.6;">
            {anzahl_artikel} relevante Artikel aus WSJ, Handelsblatt, WiWo und Barron's.
        </p>
        <a href="{seiten_url}" style="display:inline-block;background:#2c2c2c;color:#ffffff;font-size:14px;font-weight:500;padding:12px 28px;border-radius:4px;text-decoration:none;letter-spacing:0.3px;">
            Briefing lesen &rarr;
        </a>
    </td></tr>
    <tr><td style="padding:16px 32px;border-top:1px solid #e8e6e3;text-align:center;">
        <div style="font-size:11px;color:#b0aba5;">Zeitschriften-Briefing</div>
    </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

    text = (
        f"=== TAGES-BRIEFING — {datum} ===\n\n"
        f"{anzahl_artikel} relevante Artikel warten auf dich:\n"
        f"{seiten_url}\n\n"
        f"---\nAutomatisch erstellt — Zeitschriften-Briefing"
    )

    return html, text
