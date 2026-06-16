# GitHub 推广文案（复制粘贴即可）

把仓库「打扮好」能明显提高搜索和推荐曝光。按下面清单在 GitHub 网页上操作一次即可。

---

## 1. 仓库 About（右侧齿轮 ⚙）

**Description（描述）** — 直接复制：

```
A cute Windows desktop pet with shop economy, Monopoly & chess mini-games. PyQt6 · 18 languages · one-click installer.
```

**Website**（可选）：

```
https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases/latest
```

**Topics（主题标签）** — 粘贴这些（最多 20 个）：

```
desktop-pet
pyqt6
python
windows
virtual-pet
monopoly
chess
mini-games
tamagotchi
desktop-widget
pyqt
indie-game
open-source
i18n
game
pet-simulator
windows-app
qt6
idle-game
desktop-companion
```

勾选 **Releases**、**Packages** 可留空。

---

## 2. Social preview（社交预览图）

链接被分享到 Twitter / Discord / 微信时显示的横幅。

1. 本地生成图（若尚未生成）：

   ```powershell
   python tools\prepare_brand_assets.py
   ```

2. GitHub 仓库 → **Settings** → **General** → **Social preview**
3. 上传：`docs/github-social-preview.png`（1280×640）

---

## 3. Release v1.0.0 说明（发布页正文）

**Title:** `Desktop Pet v1.0.0 — Windows desktop pet with games`

**Body:**

```markdown
## Desktop Pet v1.0.0

Your desktop companion — feed her, earn gold, play **Monopoly** and **chess** together.

### Download

| File | Notes |
|------|-------|
| **DesktopPet-Setup-1.0.0.exe** | Installer (recommended) |
| **DesktopPet.exe** | Portable, no install |

- Windows 10/11 64-bit
- No Python required
- 18 UI languages (Settings → Language)
- Saves: `%APPDATA%\DesktopPet\`

### Highlights

- Transparent always-on-top pet with animations & speech bubbles
- Shop economy + hunger / mood / intimacy stats
- Monopoly (24-tile Chinese city board) + Chess vs AI
- Arcade: snake, catch burgers, meteor dodge, memory match

### Notes

Fan-made project, not affiliated with DeepSeek or any official brand.
MIT source code — see [LICENSE](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/blob/master/LICENSE).

**Antivirus:** unsigned build — see [RELEASE_NOTES.md](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/blob/master/docs/RELEASE_NOTES.md) for SHA-256 checksums and SmartScreen guidance.

**Full readme:** https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet#readme
```

上传附件：`DesktopPet-Setup-1.0.0.exe`（和/或 `DesktopPet.exe`）

勾选 **Set as the latest release**。

---

## 4. 创建 Tag

Release 页面 → **Choose a tag** → 输入 `v1.0.0` → **Create new tag on publish**

或本地：

```powershell
git tag -a v1.0.0 -m "Desktop Pet v1.0.0"
git push origin v1.0.0
```

---

## 5. 曝光小技巧

| 做法 | 作用 |
|------|------|
| README 顶部 **Download** 链接 | 访客 3 秒内找到安装包 |
| Social preview 图 | 外链分享更醒目 |
| Topics 标签 | GitHub 搜索 `desktop-pet` `pyqt6` 等能搜到你 |
| Release 附件 | Star 的用户会直接来下 exe |
| 截图放 README | 比纯文字转化高很多 |
| 中文 + 英文 README | 覆盖更多地区搜索 |

可选：发到 V2EX / 知乎 / Reddit r/Python / r/desktops — 带上 Release 链接和一张截图。

---

## 6. Pin 仓库（个人主页）

你的 GitHub 主页 → **Customize your pins** → 把 **DesktopPet** 钉在最前面。
