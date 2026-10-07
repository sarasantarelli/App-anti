@echo off
chcp 65001 >nul
cd /d "%~dp0"
set AUTO=0
if /i "%~1"=="/auto" set AUTO=1
if not exist ".venv\Scripts\pythonw.exe" ( echo Esegui prima INSTALLA.bat & if "%AUTO%"=="0" pause & exit /b 1 )
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%~dp0'; $s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\App-anti VRI.lnk'); $s.TargetPath=$p+'.venv\Scripts\pythonw.exe'; $s.Arguments='\"'+$p+'GESTIONALE.pyw\"'; $s.WorkingDirectory=$p; if (Test-Path ($p+'icona.ico')) { $s.IconLocation=$p+'icona.ico' }; $s.Description='Valutazione rischio incendio - gestionale'; $s.Save()"
if errorlevel 1 ( echo Impossibile creare il collegamento. & if "%AUTO%"=="0" pause & exit /b 1 )
echo Collegamento "App-anti VRI" creato sul Desktop: un clic apre il gestionale (nessuna finestra nera).
if "%AUTO%"=="0" (
  choice /m "Avviare l'app in automatico all'accensione del PC (resta in background, i dati sono sempre pronti)?"
  if errorlevel 2 goto fine
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%~dp0'; $s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup')+'\App-anti VRI (avvio).lnk'); $s.TargetPath=$p+'.venv\Scripts\pythonw.exe'; $s.Arguments='\"'+$p+'GESTIONALE.pyw\" --silenzioso'; $s.WorkingDirectory=$p; $s.WindowStyle=7; $s.Save()"
echo Avvio automatico attivato.
:fine
if "%AUTO%"=="0" pause
