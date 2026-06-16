@echo off
chcp 65001 >nul
echo 正在结束 Desktop Pet（python 进程）...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq DesktopPet*" 2>nul
for /f "tokens=2" %%i in ('wmic process where "commandline like '%%DesktopPet%%main.py%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do taskkill /F /PID %%i 2>nul
taskkill /F /FI "COMMANDLINE eq *DesktopPet*main.py*" 2>nul
echo 若仍有残留，请在任务管理器中结束「Python」进程。
pause
