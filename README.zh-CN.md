# Desktop Pet · 桌宠（中文说明）

[English README](README.md)

[![tests](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/actions/workflows/tests.yml/badge.svg)](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

一只住在 Windows 桌面上的桌宠：待机、走路、冒气泡；喂食、刷好感，还能陪你玩 **大富翁** 和 **国际象棋**。

> 同人桌宠项目，与 DeepSeek 或任何官方品牌无关。发布前请确认角色素材的分发权。

## 下载（免 Python）

到 [GitHub Releases](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases) 下载：

- **DesktopPet-Setup-1.0.0.exe** — 安装版（推荐）
- **DesktopPet.exe** — 绿色单文件版

系统要求：Windows 10/11 64 位。存档在 `%APPDATA%\DesktopPet\`。

自己打包见 [docs/BUILD.md](docs/BUILD.md)。

## 语言

默认 **English**。支持 **18 种语言**（英/简中/繁中/日/韩/西/法/德/意/葡/俄/阿/印/泰/越/土/波/荷）。  
右键或托盘 → **Settings** → **Language** 切换。

完整自测清单：[docs/QA.md](docs/QA.md)

## 从源码运行

```powershell
cd DesktopPet
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

双击 **`启动宠物.bat`** 或 **`start.bat`** 运行。

详细功能见 [docs/zh-CN/FEATURES.md](docs/zh-CN/FEATURES.md)。

## 截图

见 [README.md#screenshots](README.md#screenshots) 中的 `docs/screenshots/`。

## 参与贡献

- [CONTRIBUTING.md](CONTRIBUTING.md) — 开发说明
- [CHANGELOG.md](CHANGELOG.md) — 更新记录
- [SECURITY.md](SECURITY.md) — 安全问题反馈

## 许可

源代码 [MIT](LICENSE)。角色素材请自行确认分发权。
