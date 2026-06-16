# Contributing

Thanks for your interest in Desktop Pet!

## Quick start for developers

```powershell
git clone https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet.git
cd DesktopPet
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python src\main.py
```

See [docs/QA.md](docs/QA.md) before opening a release-related PR.

## Pull requests

1. Fork the repo and create a branch from `master`
2. Keep changes focused — one feature or fix per PR
3. Run the full test suite locally
4. Update [CHANGELOG.md](CHANGELOG.md) under **Unreleased** (or the next version section)
5. If you change UI strings, update `src/i18n/locales/en.json` and run `python tools/build_locales.py` when other locales need syncing

## Translations

- Default / source of truth: `src/i18n/locales/en.json`
- Add or edit keys in English first, then regenerate or hand-edit other locale files
- Supported language list: `SUPPORTED_LANGUAGES` in `src/i18n/translator.py`

## Version bumps

When preparing a release, update **both**:

- `APP_VERSION` in `src/utils/constants.py`
- `MyAppVersion` in `installer/DesktopPet.iss`

Then tag `vX.Y.Z` and publish a GitHub Release (see [docs/BUILD.md](docs/BUILD.md)).

## Character art & assets

This is a fan-made project. Do not commit copyrighted character sheets you do not have rights to redistribute. `人物序列图/` and GPU matte tooling stay local (gitignored).

## Questions

Open a [GitHub Issue](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/issues) for bugs or feature ideas.
