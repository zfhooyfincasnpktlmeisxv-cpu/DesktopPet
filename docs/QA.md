# Release QA checklist

Run automated tests first:

```powershell
cd DesktopPet
python -m unittest discover -s tests -v
```

All tests should pass (193+). Then spot-check manually:

## Startup & tray

- [ ] First launch (no `%APPDATA%\DesktopPet\`): pet visible, **80 gold**, empty backpack
- [ ] Tray icon appears; left-click toggles show/hide
- [ ] Quit from tray fully exits (not just hide)

## Pet UI

- [ ] Right-click menu: Feed, Pet, Shop, Mini-games, **Settings**, Hide, Quit
- [ ] Drag pet; click for speech bubble
- [ ] Stat bar toggle works (if enabled in settings)

## Settings (18 languages)

- [ ] Settings opens without crash
- [ ] Switch **English → 简体中文 → 日本語 → 한국어** — menu text updates
- [ ] Save persists after restart (`settings.json` → `"language"`)

## Economy

- [ ] Shop: buy burger, gold decreases
- [ ] Feed consumes burger, hunger rises
- [ ] Mini-game awards gold; daily cap message after limit

## Games (smoke)

- [ ] Game hub opens; each arcade game starts and closes
- [ ] Monopoly: board visible, one full turn
- [ ] Chess: move piece, AI responds without freeze

## Skins

- [ ] `skins/default/idle/001.png` exists; pet body visible
- [ ] After hide + restart, pet remembers position (not gold reset)

## Known non-bugs

- Save data is **per machine** in `%APPDATA%\DesktopPet\` — not in git
- Minor languages may show English for some game feedback strings (fallback)
- Regenerate locale JSON: `python tools/build_locales.py`
