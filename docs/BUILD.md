# Build Windows release

## What you get

| Output | Path | Notes |
|--------|------|-------|
| Standalone exe | `dist/DesktopPet.exe` | ~65 MB, no Python required |
| Installer | `dist/DesktopPet-Setup-1.0.0.exe` | Needs Inno Setup 6 |

Icons and installer wizard art use the pet model from `assets/branding/pet-source.png` (your试玩图角色).

---

## Step 1 — Build exe

Double-click **`build-exe.bat`**, or:

```powershell
cd DesktopPet
pip install -r requirements.txt -r requirements-build.txt
python tools\prepare_brand_assets.py
pyinstaller --noconfirm DesktopPet.spec
```

Result: `dist\DesktopPet.exe`

---

## Step 2 — Build installer (optional)

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php)
2. Double-click **`build-installer.bat`**

Result: `dist\DesktopPet-Setup-1.0.0.exe`

---

## GitHub Release

1. Tag: `v1.0.0`
2. Upload `dist\DesktopPet-Setup-1.0.0.exe` (or `DesktopPet.exe`)
3. Release notes: Windows 10/11, English UI by default, 18 languages in Settings

User saves stay in `%APPDATA%\DesktopPet\` and are **not** removed on uninstall.

---

## Regenerate icons only

```powershell
python tools\prepare_brand_assets.py
```

Updates:

- `assets/icon.png` — tray icon
- `assets/icon.ico` — exe + installer icon
- `assets/branding/generated/wizard-*.bmp` — installer side art

Replace `assets/branding/pet-source.png` if you change the mascot.
