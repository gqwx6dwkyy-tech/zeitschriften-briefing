"""E-Mail-Versand über Outlook SMTP."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from dotenv import load_dotenv

from config import MAIL_EMPFAENGER, SMTP_SERVER, SMTP_PORT, ENV_PFAD

load_dotenv(ENV_PFAD)


def sende_briefing(html: str, plaintext: str,
                   empfaenger: str = MAIL_EMPFAENGER) -> bool:
    """Briefing per E-Mail versenden.

    Args:
        html: HTML-Version des Briefings.
        plaintext: Plaintext-Version des Briefings.
        empfaenger: E-Mail-Adresse des Empfängers.

    Returns:
        True wenn erfolgreich, False bei Fehler.
    """
    absender = os.getenv("MAIL_ABSENDER")
    passwort = os.getenv("MAIL_PASSWORT")

    if not absender or not passwort:
        print("FEHLER: MAIL_ABSENDER und MAIL_PASSWORT müssen in .env gesetzt sein.")
        return False

    datum = datetime.now().strftime("%d.%m.%Y")
    betreff = f"Tages-Briefing — {datum}"

    nachricht = MIMEMultipart("alternative")
    nachricht["From"] = absender
    nachricht["To"] = empfaenger
    nachricht["Subject"] = betreff

    nachricht.attach(MIMEText(plaintext, "plain", "utf-8"))
    nachricht.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(absender, passwort)
            server.sendmail(absender, empfaenger, nachricht.as_string())
        print(f"Briefing erfolgreich an {empfaenger} versendet.")
        return True
    except smtplib.SMTPAuthenticationError:
        print("FEHLER: SMTP-Authentifizierung fehlgeschlagen. "
              "Prüfen Sie MAIL_ABSENDER und MAIL_PASSWORT in .env.")
        return False
    except smtplib.SMTPException as e:
        print(f"FEHLER: SMTP-Fehler beim Versand: {e}")
        return False
    except Exception as e:
        print(f"FEHLER: Unerwarteter Fehler beim Mailversand: {e}")
        return False


if __name__ == "__main__":
    # Testmail versenden
    test_html = """<html><body>
    <h1>Test-Briefing</h1>
    <p>Dies ist eine Testnachricht vom Zeitschriften-Briefing.</p>
    </body></html>"""
    test_text = "Test-Briefing\n\nDies ist eine Testnachricht vom Zeitschriften-Briefing."

    erfolg = sende_briefing(test_html, test_text)
    if not erfolg:
        print("\nHinweis: Stellen Sie sicher, dass .env korrekt konfiguriert ist.")
