@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  App-anti - installazione (una sola volta, richiede internet)
echo ============================================================
set PY=
where py >nul 2>&1 && set PY=py -3
if not defined PY where python >nul 2>&1 && set PY=python
if not defined PY (
  echo Python non trovato: provo a installarlo con winget...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo Chiudi questa finestra e riesegui INSTALLA.bat per completare.
  pause
  exit /b 1
)
%PY% -m venv .venv
if errorlevel 1 ( echo Errore nella creazione dell'ambiente Python. & pause & exit /b 1 )
call .venv\Scripts\python -m pip install --upgrade pip
call .venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 ( echo Errore nell'installazione dei componenti. & pause & exit /b 1 )
if not exist "C:\Program Files\LibreOffice\program\soffice.exe" (
  echo.
  echo LibreOffice non trovato: serve per ottenere anche i PDF (i Word funzionano comunque).
  choice /m "Installare LibreOffice ora (gratuito)?"
  if not errorlevel 2 winget install -e --id TheDocumentFoundation.LibreOffice --accept-package-agreements --accept-source-agreements
)
echo.
call .venv\Scripts\python -m antincendio_app diagnostica
echo.
call CREA_COLLEGAMENTO.bat
echo Installazione terminata. Avvia l'app dal collegamento sul Desktop (o con AVVIA.bat)
pause
