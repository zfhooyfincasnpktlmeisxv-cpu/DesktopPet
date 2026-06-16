# Desktop Pet — transparent animated desktop companion for Windows

[![tests](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/actions/workflows/tests.yml/badge.svg)](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases/latest)](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases/latest)
[![Windows](https://img.shields.io/badge/platform-Windows_10%2F11-0078D4?logo=windows&logoColor=white)](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases/latest)
[![Languages](https://img.shields.io/badge/i18n-18_languages-5c6bc0)](docs/LANGUAGES.md)

**DesktopPet** is a transparent, always-on-top desktop companion with idle animations, a shop economy, and minigames (**Monopoly**, **chess**, arcade).

> **End users:** download the [Release installer or portable exe](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases/latest) — **Python is not required**.  
> **Developers:** see [Quick start (from source)](#quick-start-from-source) — requires Python 3.10+.

Fan-made project · **Not** affiliated with DeepSeek or any official brand · [MIT](LICENSE) source

**[Download for Windows](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases/latest)** · [中文说明](README.zh-CN.md) · [Release notes & SHA-256](docs/RELEASE_NOTES.md)

---

## Why Desktop Pet?

| | |
|---|---|
| **Lives on your desktop** | Transparent window — drag, click, speech bubbles, sleep & walk |
| **More than a mascot** | Shop, hunger/mood stats, intimacy — progress auto-saves |
| **Real games inside** | **Monopoly** (24 Chinese cities) + **chess** vs AI + 4 arcade games |
| **18 UI languages** | English default — full list in [docs/LANGUAGES.md](docs/LANGUAGES.md) |
| **Ready to use** | Installer + portable exe on [Releases](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases/latest) |

---

## Demo

<!-- Replace with docs/demo.gif when you record a 10–20s screen capture -->
<!-- ![Desktop Pet demo](docs/demo.gif) -->

Static previews below. A short demo GIF can be added at `docs/demo.gif` (recommended: pet idle + game hub + Monopoly).

| Desktop pet | Mini-game hub | Monopoly board |
|:---:|:---:|:---:|
| ![Desktop pet](docs/screenshots/desktop-pet.png) | ![Game hub](docs/screenshots/game-hub.png) | ![Monopoly](docs/screenshots/richman-board.png) |

| Chess | Arcade games |
|:---:|:---:|
| ![Chess](docs/screenshots/chess.png) | ![Arcade games](docs/screenshots/mini-games.png) |

---

## Download (Windows) — no Python required

Release builds are **self-contained** Windows executables. You do **not** need Python installed.

| File | Best for |
|------|----------|
| **`DesktopPet-Setup-1.0.0.exe`** | Most users — installer, optional desktop shortcut |
| **`DesktopPet.exe`** | Portable — run without installing |

| | |
|---|---|
| **OS** | Windows 10/11 (64-bit) |
| **Saves** | `%APPDATA%\DesktopPet\` |
| **SHA-256 & AV notes** | [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md) |
| **Build yourself** | [docs/BUILD.md](docs/BUILD.md) |

Unsigned indie builds may trigger SmartScreen — see Release notes for verification steps.

---

## Features

| Module | Highlights |
|--------|------------|
| **Pet** | Frameless transparent window, tray icon, multi-pet |
| **Stats** | Hunger, mood, intimacy |
| **Economy** | Shop, backpack, daily gold cap |
| **Arcade** | Snake, catch burgers, meteor dodge, memory match |
| **Monopoly** | 24-tile board, property, cards, jail, SFX |
| **Chess** | vs AI or local two-player |

**Languages (18):** English (default), 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Italiano, Português, Русский, العربية, हिन्दी, ไทย, Tiếng Việt, Türkçe, Polski, Nederlands — [full table](docs/LANGUAGES.md). Switch in **Settings → Language**.

---

## Quick start (from source)

**Requires Python 3.10+** (3.11 recommended) and Windows 10/11. This path is for developers; end users should use [Downloads](#download-windows--no-python-required) instead.

```powershell
git clone https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet.git
cd DesktopPet
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\main.py
```

### Launcher scripts (repo root)

| English | Chinese | Action |
|---------|---------|--------|
| `start.bat` | `启动宠物.bat` | Start the app |
| `stop-desktop-pet.bat` | `停止桌宠.bat` | Quit all instances |
| `rebuild-skins.bat` | `重建皮肤.bat` | Rebuild `skins/default/` from local sprites |

If `skins/default/` is missing, run `rebuild-skins.bat` when you have source art locally.

---

## Controls

- **Left-click** — speech bubble  
- **Drag** — grab / fall  
- **Right-click** — feed, pet, shop, mini-games, Settings  
- **Tray** — left-click show/hide  

Closing the window hides to tray; use tray **Quit** to exit completely.

---

## Development

```powershell
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

[CONTRIBUTING.md](CONTRIBUTING.md) · [docs/QA.md](docs/QA.md) · [SECURITY.md](SECURITY.md)

---

## Third-party assets

- Monopoly SFX: [Kenney](https://kenney.nl/) **CC0**
- City images: [assets/richman/cities/SOURCES.md](assets/richman/cities/SOURCES.md)
- Chess: [python-chess](https://github.com/niklasf/python-chess)

---

## License

[MIT License](LICENSE) for source code. Game assets follow their directory licenses. Do not use Hasbro Monopoly trademarks commercially.
