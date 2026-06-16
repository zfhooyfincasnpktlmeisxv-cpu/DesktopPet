@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting Desktop Pet...
python src\main.py
pause
