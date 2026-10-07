@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%~dp0'; $s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\App-anti VRI.lnk'); $s.TargetPath=$p+'AVVIA.bat'; $s.WorkingDirectory=$p; if (Test-Path ($p+'icona.ico')) { $s.IconLocation=$p+'icona.ico' }; $s.Description='Valutazione rischio incendio'; $s.Save()"
if errorlevel 1 ( echo Impossibile creare il collegamento. & pause & exit /b 1 )
echo Collegamento "App-anti VRI" creato sul Desktop.
pause
