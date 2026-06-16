@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist "dist\DesktopPet.exe" (
    echo DesktopPet.exe not found. Run build-exe.bat first.
    pause
    exit /b 1
)

set ISCC=
for %%P in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) do if exist %%P set ISCC=%%~P

if "%ISCC%"=="" (
    echo Inno Setup 6 not found.
    echo Install from: https://jrsoftware.org/isdl.php
    echo You can still distribute dist\DesktopPet.exe directly.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat 2>nul
python tools\prepare_brand_assets.py

echo === Building installer ===
"%ISCC%" installer\DesktopPet.iss
if errorlevel 1 exit /b 1

echo.
echo Done: dist\DesktopPet-Setup-1.0.0.exe
pause
