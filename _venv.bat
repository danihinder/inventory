@echo off
:: =============================================================================
:: _venv.bat  -  venv-Helfer fuer inventar_mail_watch.py
::
:: Prueft ob .venv vorhanden und funktionstuechtig ist.
:: Falls nicht (erster Start, oder nach Umzug): neu erstellen + Pakete installieren.
:: Setzt %PYTHON% auf den venv-Python-Pfad fuer den Aufrufer.
:: =============================================================================
cd /d "%~dp0"
set PYTHON=%~dp0.venv\Scripts\python.exe

if exist "%PYTHON%" (
    "%PYTHON%" -c "import win32com.client, openpyxl" >nul 2>&1
    if not errorlevel 1 goto :venv_ok
    echo.
    echo   Aktualisiere Pakete ^(requirements.txt^)...
    echo   --------------------------------------------------------------------------
    "%PYTHON%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo   --------------------------------------------------------------------------
        echo   Fehler: pip install fehlgeschlagen. Falls der venv defekt ist,
        echo   ".venv"-Verzeichnis loeschen und erneut starten.
        pause
        exit /b 1
    )
    echo   --------------------------------------------------------------------------
    echo   Pakete aktualisiert.
    echo.
    goto :venv_ok
)

echo.
echo   Virtuelle Umgebung wird eingerichtet...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo   +==========================================================+
    echo   ^|  Python nicht gefunden!                                  ^|
    echo   ^|                                                          ^|
    echo   ^|  Bitte installieren:  https://www.python.org/downloads/  ^|
    echo   ^|  Wichtig: Option "Add Python to PATH" aktivieren!        ^|
    echo   +==========================================================+
    echo.
    pause
    exit /b 1
)

echo   Erstelle .venv ...
python -m venv .venv
if errorlevel 1 (
    echo   Fehler: venv konnte nicht erstellt werden.
    pause
    exit /b 1
)

echo   Installiere Pakete ^(requirements.txt^)...
echo   --------------------------------------------------------------------------
"%PYTHON%" -m pip install --upgrade pip -q
"%PYTHON%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo   --------------------------------------------------------------------------
    echo   Fehler: Paketinstallation fehlgeschlagen. Fehlermeldung oben pruefen.
    pause
    exit /b 1
)
echo   --------------------------------------------------------------------------
echo   Einrichtung abgeschlossen.
echo.

:venv_ok
exit /b 0
