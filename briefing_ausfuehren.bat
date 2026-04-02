@echo off
REM Zeitschriften-Briefing ausfuehren
REM Fuer Windows Aufgabenplanung: taeglich um 07:00

cd /d "C:\Claude Code\Privat\Zeitschriften-Briefing"

REM Python ausfuehren
python hauptprogramm.py %*

REM Exit-Code weiterreichen
exit /b %errorlevel%
