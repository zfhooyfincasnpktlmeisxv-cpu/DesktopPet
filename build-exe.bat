@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo === Desktop Pet: prepare icons ===
if exist ".venv\Scripts\python.exe" (
    call .venv\Scripts\activate.bat
) else (
    echo Using system Python...
)

pip install -q -r requirements.txt -r requirements-build.txt

python tools\prepare_brand_assets.py
if errorlevel 1 exit /b 1

echo.
echo === Desktop Pet: build exe ===
if exist build rmdir /s /q build
if exist dist\DesktopPet.exe del /f /q dist\DesktopPet.exe
pyinstaller --noconfirm DesktopPet.spec
if errorlevel 1 exit /b 1

echo.
echo Done: dist\DesktopPet.exe
echo Next: run build-installer.bat to create setup package
pause
