@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call INSTALLA.bat
if not exist ".venv\Scripts\python.exe" exit /b 1
echo Avvio App-anti... (si apre il browser; chiudi questa finestra per fermare l'app)
call .venv\Scripts\python -m antincendio_app serve
pause
