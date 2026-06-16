@echo off
chcp 65001 >nul
echo Stopping Desktop Pet (Python processes running main.py)...
for /f "tokens=2" %%a in ('wmic process where "commandline like '%%main.py%%'" get processid /format:list ^| find "="') do taskkill /PID %%a /F 2>nul
echo Done.
pause
