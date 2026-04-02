"""RSS-Feeds abrufen und Artikel der letzten 24 Stunden sammeln."""

import sys
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from time import mktime

import feedparser

from config import FEEDS, ARTIKEL_MAX_ALTER_STUNDEN

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


@dataclass
class Artikel:
    """Ein einzelner Artikel aus einem RSS-Feed."""
    titel: str
    quelle: str
    datum: datetime
    zusammenfassung: str
    link: str

    def als_dict(self) -> dict:
        return {
            "titel": self.titel,
            "quelle": self.quelle,
            "datum": self.datum.isoformat(),
            "zusammenfassung": self.zusammenfassung,
            "link": self.link,
        }

    def als_text(self) -> str:
        datum_str = self.datum.strftime("%d.%m.%Y %H:%M")
        return f"[{self.quelle}] {self.titel} ({datum_str})\n{self.zusammenfassung}\n{self.link}"


def _parse_datum(eintrag) -> datetime | None:
    """Datum aus einem Feed-Eintrag extrahieren."""
    for feld in ("published_parsed", "updated_parsed"):
        parsed = getattr(eintrag, feld, None)
        if parsed:
            return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
    return None


def _bereinige_html(text: str) -> str:
    """Einfache HTML-Tags aus Text entfernen."""
    import re
    sauber = re.sub(r"<[^>]+>", "", text)
    sauber = re.sub(r"\s+", " ", sauber).strip()
    return sauber


def _ist_duplikat(artikel: Artikel, bestehende: list[Artikel]) -> bool:
    """Prüft ob ein Artikel mit sehr ähnlichem Titel bereits vorhanden ist."""
    titel_lower = artikel.titel.lower().strip()
    for bestehend in bestehende:
        if bestehend.titel.lower().strip() == titel_lower:
            return True
        # Teilstring-Prüfung für leicht abweichende Titel
        if len(titel_lower) > 20 and len(bestehend.titel) > 20:
            if titel_lower[:40] == bestehend.titel.lower().strip()[:40]:
                return True
    return False


def sammle_feeds(feeds: dict[str, list[str]] | None = None,
                 max_alter_stunden: int = ARTIKEL_MAX_ALTER_STUNDEN) -> list[Artikel]:
    """Alle konfigurierten RSS-Feeds abrufen und aktuelle Artikel sammeln.

    Args:
        feeds: Dict mit Quellname -> Liste von Feed-URLs. Standard: config.FEEDS
        max_alter_stunden: Maximales Alter der Artikel in Stunden.

    Returns:
        Liste von Artikel-Objekten, sortiert nach Datum (neueste zuerst).
    """
    if feeds is None:
        feeds = FEEDS

    grenze = datetime.now(timezone.utc) - timedelta(hours=max_alter_stunden)
    artikel_liste: list[Artikel] = []
    fehler: list[str] = []

    for quelle, urls in feeds.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
                if feed.bozo and not feed.entries:
                    fehler.append(f"Feed-Fehler bei {quelle} ({url}): {feed.bozo_exception}")
                    continue

                for eintrag in feed.entries:
                    datum = _parse_datum(eintrag)
                    if datum is None or datum < grenze:
                        continue

                    zusammenfassung = ""
                    if hasattr(eintrag, "summary"):
                        zusammenfassung = _bereinige_html(eintrag.summary)
                    elif hasattr(eintrag, "description"):
                        zusammenfassung = _bereinige_html(eintrag.description)

                    artikel = Artikel(
                        titel=eintrag.get("title", "Ohne Titel"),
                        quelle=quelle,
                        datum=datum,
                        zusammenfassung=zusammenfassung[:500],
                        link=eintrag.get("link", ""),
                    )

                    if not _ist_duplikat(artikel, artikel_liste):
                        artikel_liste.append(artikel)

            except Exception as e:
                fehler.append(f"Fehler beim Abruf von {quelle} ({url}): {e}")

    if fehler:
        print(f"--- {len(fehler)} Feed-Fehler ---")
        for f in fehler:
            print(f"  {f}")

    artikel_liste.sort(key=lambda a: a.datum, reverse=True)
    return artikel_liste


if __name__ == "__main__":
    print("Sammle Artikel aus RSS-Feeds...")
    artikel = sammle_feeds()
    print(f"\n{len(artikel)} Artikel gefunden:\n")
    for a in artikel[:10]:
        print(a.als_text())
        print()
