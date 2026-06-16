@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Building skins (may take 1-2 minutes)...
python tools\build_skins.py
if errorlevel 1 (
    echo Skin build failed.
    pause
    exit /b 1
)
echo Done.
pause
