@echo off
chcp 65001 >nul
cd /d "%~dp0"
set AUTO=0
if /i "%~1"=="/auto" set AUTO=1
echo ============================================================
echo  App-anti - installazione / aggiornamento (richiede internet)
echo ============================================================
set PY=
where py >nul 2>&1 && set PY=py -3
if not defined PY where python >nul 2>&1 && set PY=python
if not defined PY (
  echo Python non trovato: lo installo con winget...
  winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PY (
  echo Python non disponibile. Installalo da python.org (spunta "Add to PATH") e riesegui questo file.
  if "%AUTO%"=="0" pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if errorlevel 1 ( echo Errore nella creazione dell'ambiente Python. & if "%AUTO%"=="0" pause & exit /b 1 )
call .venv\Scripts\python -m pip install --upgrade pip -q
call .venv\Scripts\python -m pip install -r requirements.txt -q
if errorlevel 1 ( echo Errore nell'installazione dei componenti. & if "%AUTO%"=="0" pause & exit /b 1 )
if "%AUTO%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('MyDocuments')+'\App-anti-dati'; New-Item -ItemType Directory -Force $d | Out-Null; if(-not (Test-Path 'config.json')){ @{dati=$d+'\pratiche'; backup=$d+'\backup'; norme=$d+'\norme'} | ConvertTo-Json | Set-Content -Encoding UTF8 config.json }"
)
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE" >nul 2>&1
if errorlevel 1 (
  echo.
  echo ATTENZIONE: Microsoft Word non risulta installato: i PDF richiedono Word. I documenti .docx si generano comunque.
)
echo.
call .venv\Scripts\python -m antincendio_app diagnostica
echo.
if "%AUTO%"=="1" (
  call CREA_COLLEGAMENTO.bat /auto
  start "" ".venv\Scripts\pythonw.exe" "GESTIONALE.pyw"
  echo Fatto: l'app e' avviata. Trovi il collegamento "App-anti VRI" sul Desktop.
  timeout /t 6 >nul
  exit /b 0
)
call CREA_COLLEGAMENTO.bat
echo Installazione terminata. Apri l'app dal collegamento sul Desktop.
pause
