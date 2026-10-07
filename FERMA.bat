@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'antincendio_app|GESTIONALE.pyw' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo App-anti fermata. (Per riavviarla usa il collegamento sul Desktop.)
pause
