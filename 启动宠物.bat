@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting DesktopPet...
python src\main.py
pause
