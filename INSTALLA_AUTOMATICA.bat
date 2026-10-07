@echo off
chcp 65001 >nul
title App-anti - installazione automatica
set "DEST=%LOCALAPPDATA%\App-anti"
set "URL=https://github.com/sarasantarelli/App-anti/archive/refs/heads/claude/fire-safety-assessment-app-0c719q.zip"
echo ============================================================
echo  App-anti: installazione automatica (ci vogliono alcuni minuti)
echo ============================================================
echo Scarico l'ultima versione...
mkdir "%DEST%" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; $z=Join-Path $env:TEMP 'app-anti.zip'; Invoke-WebRequest -UseBasicParsing '%URL%' -OutFile $z; $t=Join-Path $env:TEMP 'app-anti-x'; if(Test-Path $t){Remove-Item $t -Recurse -Force}; Expand-Archive $z $t -Force; $src=(Get-ChildItem $t | Select-Object -First 1).FullName; robocopy $src '%DEST%' /E /XD data norme backup .venv /XF config.json | Out-Null; exit 0"
if not exist "%DEST%\INSTALLA.bat" (
  echo Download non riuscito: controlla la connessione internet e riprova.
  pause
  exit /b 1
)
call "%DEST%\INSTALLA.bat" /auto
