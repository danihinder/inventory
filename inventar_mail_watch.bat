@echo off
call "%~dp0_venv.bat"
if errorlevel 1 exit /b 1
"%PYTHON%" "%~dp0inventar_mail_watch.py" --watch 60
