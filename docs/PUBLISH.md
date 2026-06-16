# Publish to GitHub

## Before you push

- [ ] `skins/default/` includes idle / walk frames
- [ ] `DEV_MODE = False` in `src/utils/constants.py`
- [ ] No debug PNGs in repo root (see `.gitignore`)
- [ ] Do **not** commit `.venv/`, `build/`, `docs/dev/`, `tools/dev/`
- [ ] Confirm **character art** redistribution rights
- [ ] Screenshots in `docs/screenshots/`

Default UI language is **English** (18 locales in Settings).

Windows installer / exe: see [docs/BUILD.md](BUILD.md).

GitHub About, Topics, Release copy: [docs/GITHUB_PROMO.md](GITHUB_PROMO.md).

---

## GitHub Desktop

1. Open **GitHub Desktop** → **File → Add local repository** → select `DesktopPet`
2. Review changed files (`.gitignore` excludes venv, dev notes, GPU tools)
3. Commit message example: **`Initial release: desktop pet with minigames`**
4. **Publish repository** or **Push origin**

---

## Command line

```powershell
cd DesktopPet
git add .
git status
git commit -m "Initial release: desktop pet with minigames"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

---

## Suggested About / Topics

**Desktop pet for Windows · Monopoly · Chess · mini-games (PyQt6)**

Topics: `desktop-pet` `pyqt6` `python` `monopoly` `chess`
