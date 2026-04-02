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
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">
<tr><td align="center" style="padding:20px 10px;">
<table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;">
    <tr><td style="background:linear-gradient(135deg,#1a237e,#283593);padding:24px;">
        <h1 style="margin:0;color:#ffffff;font-size:22px;">Tages-Briefing</h1>
        <div style="color:#b0bec5;font-size:13px;margin-top:4px;">{datum}</div>
    </td></tr>
    <tr><td style="padding:32px 24px;text-align:center;">
        <p style="font-size:15px;color:#333;margin:0 0 24px 0;line-height:1.5;">
            {anzahl_artikel} relevante Artikel aus WSJ, Handelsblatt, WiWo und Barron's warten auf dich.
        </p>
        <a href="{seiten_url}" style="display:inline-block;background:#1a237e;color:#ffffff;font-size:16px;font-weight:600;padding:14px 32px;border-radius:6px;text-decoration:none;">
            Briefing lesen &rarr;
        </a>
    </td></tr>
    <tr><td style="padding:16px 24px;background:#f5f5f5;text-align:center;">
        <div style="font-size:11px;color:#999;">Automatisch erstellt &middot; Zeitschriften-Briefing</div>
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
