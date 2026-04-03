"""Tägliche Zusammenfassungsseite generieren — deutsche Artikelzusammenfassungen."""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from config import GEMINI_MODELL, ENV_PFAD, PROJEKT_PFAD, THEMEN
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
        "Börse": "#1a6b6a",
        "Internationale Politik": "#7a6855",
        "Künstliche Intelligenz": "#6b5c73",
        "Sonstiges": "#7f8c8d",
    }

    # Nach Thema gruppieren
    gruppen: dict[str, list[BewerteterArtikel]] = {}
    for ba in artikel:
        gruppen.setdefault(ba.thema, []).append(ba)

    # Feste Themen-Reihenfolge aus config, Sonstiges am Ende
    themen_reihenfolge = [t for t in THEMEN if t in gruppen]
    for t in gruppen:
        if t not in themen_reihenfolge:
            themen_reihenfolge.append(t)

    # --- Teil 1: Übersicht mit klickbaren Überschriften ---
    uebersicht_html = ""
    for thema in themen_reihenfolge:
        liste = gruppen[thema]
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
    <div style="padding:9px 0; border-bottom:1px solid #edecea; display:flex; justify-content:space-between; align-items:center;">
        <div style="flex:1;">
            <a href="#{aid}" style="font-size:14px; color:#1a1a1a; text-decoration:none; font-weight:500; line-height:1.4;">{a.titel}</a>{relevanz_marker}
            <div style="font-size:11px; color:#a09a93; margin-top:2px;">{a.quelle} &middot; {datum_str}</div>
        </div>
        <button onclick="inHubKopieren('{aid}')" class="btn-hub-klein" title="In Leseliste">&#10149;</button>
    </div>"""

    # --- Teil 2: Ausführliche Zusammenfassungen ---
    details_html = ""
    for thema in themen_reihenfolge:
        liste = gruppen[thema]
        farbe = thema_farben.get(thema, "#78756f")

        for ba in liste:
            a = ba.artikel
            aid = _artikel_id(a)
            zf = zusammenfassungen.get(aid, a.zusammenfassung)
            datum_str = a.datum.strftime("%d.%m.%Y %H:%M")

            # Zusammenfassung für data-Attribut escapen
            zf_escaped = zf.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            titel_escaped = a.titel.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

            details_html += f"""
    <article id="{aid}" class="artikel" data-id="{aid}" data-titel="{titel_escaped}" data-quelle="{a.quelle}" data-link="{a.link}" data-zusammenfassung="{zf_escaped}" data-datum="{datum_str}">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div style="flex:1;">
                <div style="font-size:11px; color:#7f8c8d; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">{a.quelle} &middot; {datum_str}</div>
                <h3 style="margin:0 0 16px 0; font-size:17px; color:#2c3e50; font-weight:600; line-height:1.3;">{a.titel}</h3>
            </div>
            <div style="display:flex; gap:6px; margin-left:12px; flex-shrink:0; padding-top:4px;">
                <button onclick="toggleLesen('{aid}')" class="btn-lesen" id="btn-lesen-{aid}" title="Später lesen">&#9733;</button>
                <button onclick="inHubKopieren('{aid}')" class="btn-hub" title="In Leseliste kopieren">&#10149;</button>
            </div>
        </div>
        <p style="margin:0 0 20px 0; font-size:14px; color:#2c3e50; line-height:1.75;">{zf}</p>
        <div style="display:flex; justify-content:space-between; align-items:center; padding-top:16px; border-top:1px solid #e8dcc8;">
            <a href="{a.link}" style="font-size:12px; color:{farbe}; text-decoration:none; font-weight:500; letter-spacing:0.3px;">Originalartikel &rarr;</a>
            <a href="#top" style="font-size:11px; color:#7f8c8d; text-decoration:none;">&uarr; Übersicht</a>
        </div>
    </article>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Briefing — {datum}</title>
    <style>
        body {{ margin:0; padding:0; background:#f5f0e8; font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif; color:#2c3e50; }}
        .container {{ max-width:680px; margin:0 auto; padding:0 16px 24px; }}
        .header {{ background:#1a6b6a; color:#fff; padding:28px 28px 24px; border-radius:0 0 6px 6px; margin-bottom:16px; }}
        .header h1 {{ margin:0; font-size:22px; font-weight:600; color:#fff; letter-spacing:-0.3px; }}
        .header .datum {{ color:#b8d8d6; font-size:13px; margin-top:6px; }}
        .header .nav-links {{ margin-top:10px; }}
        .header .nav-links a {{ color:#b8d8d6; font-size:12px; text-decoration:none; margin-right:16px; }}
        .header .nav-links a:hover {{ color:#fff; }}
        .uebersicht {{ background:#faf7f2; border-radius:6px; padding:20px 24px; margin-bottom:16px; border:1px solid #e8dcc8; }}
        .trennlinie {{ border:0; border-top:1px solid #e8dcc8; margin:24px 0; }}
        .footer {{ text-align:center; padding:28px; font-size:11px; color:#7f8c8d; letter-spacing:0.3px; }}
        a:hover {{ opacity:0.85; }}
        .artikel {{ margin:16px 0; padding:24px; background:#faf7f2; border-radius:6px; border:1px solid #e8dcc8; }}
        .artikel:target {{ box-shadow:0 0 0 2px #1a6b6a; }}
        .artikel.gepinnt {{ border-color:#1a6b6a; }}
        .btn-lesen, .btn-hub {{ border:1px solid #e8dcc8; background:#faf7f2; border-radius:4px; cursor:pointer; font-size:16px; width:32px; height:32px; display:flex; align-items:center; justify-content:center; color:#7f8c8d; transition:all 0.15s; }}
        .btn-lesen:hover {{ background:#1a6b6a; color:#fff; border-color:#1a6b6a; }}
        .btn-hub:hover {{ background:#1a6b6a; color:#fff; border-color:#1a6b6a; }}
        .btn-lesen.aktiv {{ background:#1a6b6a; color:#fff; border-color:#1a6b6a; }}
        .btn-hub-klein {{ border:1px solid #e8dcc8; background:#faf7f2; border-radius:4px; cursor:pointer; font-size:13px; width:26px; height:26px; display:flex; align-items:center; justify-content:center; color:#7f8c8d; transition:all 0.15s; flex-shrink:0; margin-left:8px; }}
        .btn-hub-klein:hover {{ background:#1a6b6a; color:#fff; border-color:#1a6b6a; }}
        .leseliste {{ background:#faf7f2; border-radius:6px; padding:20px 24px; margin-bottom:16px; border:2px solid #1a6b6a; display:none; }}
        .leseliste h2 {{ margin:0 0 12px 0; font-size:15px; color:#1a6b6a; font-weight:600; }}
        .leseliste-item {{ padding:8px 0; border-bottom:1px solid #e8dcc8; display:flex; justify-content:space-between; align-items:center; }}
        .leseliste-item:last-child {{ border-bottom:none; }}
        .leseliste-item a {{ font-size:14px; color:#2c3e50; text-decoration:none; font-weight:500; }}
        .leseliste-item .entfernen {{ cursor:pointer; color:#c0392b; font-size:12px; border:none; background:none; }}
        .hub-toast {{ position:fixed; bottom:24px; right:24px; background:#1a6b6a; color:#fff; padding:12px 20px; border-radius:6px; font-size:13px; opacity:0; transition:opacity 0.3s; pointer-events:none; z-index:100; }}
        .hub-toast.sichtbar {{ opacity:1; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header" id="top">
        <h1>Tages-Briefing</h1>
        <div class="datum">{datum} &middot; {len(artikel)} Artikel</div>
        <div class="nav-links"><a href="../leseliste.html">Leseliste &rarr;</a></div>
    </div>

    <div class="leseliste" id="leseliste">
        <h2>&#9733; Später lesen</h2>
        <div id="leseliste-inhalt"></div>
    </div>

    <div class="uebersicht">
        {uebersicht_html}
    </div>
    <hr class="trennlinie">
    {details_html}
    <div class="footer">Zeitschriften-Briefing</div>
</div>

<div class="hub-toast" id="toast"></div>

<script src="../github-sync.js"></script>
<script>
(function() {{
    let _daten = null;

    function showToast(msg, fehler) {{
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.style.background = fehler ? '#c0392b' : '#1a6b6a';
        t.classList.add('sichtbar');
        setTimeout(() => t.classList.remove('sichtbar'), 2500);
    }}

    function renderLeseliste() {{
        if (!_daten) return;
        const items = _daten.spaeter_lesen || [];
        const container = document.getElementById('leseliste-inhalt');
        const wrapper = document.getElementById('leseliste');
        if (!items.length) {{
            wrapper.style.display = 'none';
            return;
        }}
        wrapper.style.display = 'block';
        container.innerHTML = items.map(item => `
            <div class="leseliste-item">
                <a href="#${{item.id}}">${{item.titel}}</a>
                <button class="entfernen" onclick="toggleLesen('${{item.id}}')" title="Entfernen">&times;</button>
            </div>
        `).join('');

        // Gepinnte Artikel visuell nach oben sortieren
        const artikelContainer = document.querySelector('.trennlinie').parentNode;
        const ids = items.map(i => i.id);
        const alleArtikel = [...artikelContainer.querySelectorAll('.artikel')];
        const trennlinie = artikelContainer.querySelector('.trennlinie');
        const gepinnte = alleArtikel.filter(a => ids.includes(a.dataset.id));
        const rest = alleArtikel.filter(a => !ids.includes(a.dataset.id));
        const insertPoint = trennlinie.nextSibling;
        gepinnte.forEach(a => {{ a.classList.add('gepinnt'); artikelContainer.insertBefore(a, insertPoint); }});
        const footer = artikelContainer.querySelector('.footer');
        rest.forEach(a => artikelContainer.insertBefore(a, footer));

        document.querySelectorAll('.btn-lesen').forEach(btn => {{
            const aid = btn.id.replace('btn-lesen-', '');
            btn.classList.toggle('aktiv', ids.includes(aid));
        }});
    }}

    window.toggleLesen = async function(aid) {{
        if (!_daten) return;
        const items = _daten.spaeter_lesen || [];
        const idx = items.findIndex(i => i.id === aid);
        if (idx >= 0) {{
            items.splice(idx, 1);
        }} else {{
            const el = document.querySelector(`[data-id="${{aid}}"]`);
            if (el) {{
                items.unshift({{
                    id: aid,
                    titel: el.dataset.titel,
                    quelle: el.dataset.quelle,
                    link: el.dataset.link
                }});
            }}
        }}
        _daten.spaeter_lesen = items;
        renderLeseliste();
        try {{
            await GH_SYNC.speichern(_daten);
        }} catch (e) {{
            showToast('Sync-Fehler: ' + e.message, true);
        }}
    }};

    window.inHubKopieren = async function(aid) {{
        if (!_daten) return;
        const el = document.querySelector(`[data-id="${{aid}}"]`);
        if (!el) return;
        const items = _daten.leseliste || [];
        if (items.some(i => i.id === aid)) {{
            showToast('Bereits in der Leseliste');
            return;
        }}
        items.unshift({{
            id: aid,
            titel: el.dataset.titel,
            quelle: el.dataset.quelle,
            link: el.dataset.link,
            zusammenfassung: el.dataset.zusammenfassung,
            datum: el.dataset.datum,
            gespeichert: new Date().toISOString()
        }});
        _daten.leseliste = items;
        showToast('In Leseliste gespeichert');
        try {{
            await GH_SYNC.speichern(_daten);
        }} catch (e) {{
            showToast('Sync-Fehler: ' + e.message, true);
        }}
    }};

    // Init — Daten von GitHub laden
    GH_SYNC.laden()
        .then(daten => {{
            _daten = daten;
            renderLeseliste();
        }})
        .catch(e => {{
            showToast('Laden fehlgeschlagen: ' + e.message, true);
            _daten = {{ spaeter_lesen: [], leseliste: [] }};
        }});
}})();
</script>
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
