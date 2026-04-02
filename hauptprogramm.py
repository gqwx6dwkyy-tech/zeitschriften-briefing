"""Hauptprogramm — Orchestriert den gesamten Briefing-Ablauf."""

import os
import sys
import io
import json
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from config import VERLAUF_PFAD, PROJEKT_PFAD
from feed_sammler import sammle_feeds
from artikel_filter import filtere_artikel
from zusammenfassungen import erstelle_zusammenfassungsseite
from briefing_ersteller import erstelle_briefing
from mail_versand import sende_briefing

# GitHub Pages URL — wird gesetzt sobald das Repo eingerichtet ist
GITHUB_PAGES_URL = os.getenv(
    "GITHUB_PAGES_URL",
    "https://gqwx6dwkyy-tech.github.io/zeitschriften-briefing"
)


def _speichere_verlauf(artikel_daten: list[dict], versendet: bool) -> Path:
    """Briefing-Verlauf als JSON speichern."""
    VERLAUF_PFAD.mkdir(parents=True, exist_ok=True)
    zeitstempel = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    datei = VERLAUF_PFAD / f"briefing_{zeitstempel}.json"

    verlauf = {
        "zeitstempel": datetime.now(timezone.utc).isoformat(),
        "anzahl_artikel": len(artikel_daten),
        "versendet": versendet,
        "artikel": artikel_daten,
    }

    datei.write_text(json.dumps(verlauf, ensure_ascii=False, indent=2), encoding="utf-8")
    return datei


def hauptprogramm(nur_lokal: bool = False) -> int:
    """Gesamten Briefing-Ablauf ausführen.

    Args:
        nur_lokal: Wenn True, wird das Briefing nur lokal gespeichert (kein Mailversand).

    Returns:
        Exit-Code: 0 = Erfolg, 1 = Fehler, 2 = Keine Artikel gefunden.
    """
    print("=" * 50)
    print(f"Zeitschriften-Briefing — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("=" * 50)

    # 1. Feeds sammeln
    print("\n[1/5] Sammle Artikel aus RSS-Feeds...")
    try:
        artikel = sammle_feeds()
    except Exception as e:
        print(f"FEHLER beim Feed-Abruf: {e}")
        return 1

    if not artikel:
        print("Keine Artikel in den letzten 24 Stunden gefunden.")
        return 2

    print(f"  {len(artikel)} Artikel gesammelt.")

    # 2. Filtern
    print("\n[2/5] Filtere nach Relevanz...")
    try:
        bewertete = filtere_artikel(artikel)
    except Exception as e:
        print(f"FEHLER beim Filtern: {e}")
        return 1

    if not bewertete:
        print("Keine relevanten Artikel gefunden.")
        _speichere_verlauf([], False)
        return 2

    print(f"  {len(bewertete)} relevante Artikel.")

    # 3. Zusammenfassungsseite erstellen
    print("\n[3/5] Erstelle Zusammenfassungsseite...")
    try:
        seiten_datei, link_map = erstelle_zusammenfassungsseite(
            bewertete, github_pages_url=GITHUB_PAGES_URL
        )
    except Exception as e:
        print(f"FEHLER bei Zusammenfassungsseite ({e}), Links zeigen auf Originalartikel.")
        link_map = {}

    # 4. Briefing-E-Mail erstellen
    print("\n[4/5] Erstelle Briefing-E-Mail...")
    try:
        html, plaintext = erstelle_briefing(bewertete, link_map=link_map)
    except Exception as e:
        print(f"FEHLER beim Erstellen des Briefings: {e}")
        return 1

    # 5. Versenden oder lokal speichern
    versendet = False
    if nur_lokal:
        print("\n[5/5] Speichere Briefing lokal...")
        html_datei = PROJEKT_PFAD / "letztes_briefing.html"
        html_datei.write_text(html, encoding="utf-8")
        print(f"  Gespeichert: {html_datei}")
        versendet = True
    else:
        print("\n[5/5] Versende Briefing per E-Mail...")
        versendet = sende_briefing(html, plaintext)

    # Verlauf speichern
    artikel_daten = [ba.als_dict() for ba in bewertete]
    verlauf_datei = _speichere_verlauf(artikel_daten, versendet)
    print(f"\nVerlauf gespeichert: {verlauf_datei}")

    if versendet:
        print("\nBriefing erfolgreich abgeschlossen.")
        return 0
    else:
        print("\nBriefing erstellt, aber Versand fehlgeschlagen.")
        return 1


if __name__ == "__main__":
    nur_lokal = "--lokal" in sys.argv
    exit_code = hauptprogramm(nur_lokal=nur_lokal)
    sys.exit(exit_code)
