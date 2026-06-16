# Supported UI languages

Desktop Pet ships **18 locales**. Default is **English** (`en`).

Change anytime: **right-click pet → Settings → Language**, or tray menu → Settings.

| Code | Language |
|------|----------|
| `en` | English |
| `zh_CN` | 简体中文 |
| `zh_TW` | 繁體中文 |
| `ja` | 日本語 |
| `ko` | 한국어 |
| `es` | Español |
| `fr` | Français |
| `de` | Deutsch |
| `it` | Italiano |
| `pt` | Português |
| `ru` | Русский |
| `ar` | العربية |
| `hi` | हिन्दी |
| `th` | ไทย |
| `vi` | Tiếng Việt |
| `tr` | Türkçe |
| `pl` | Polski |
| `nl` | Nederlands |

Locale files: `src/i18n/locales/*.json`

Regenerate merged strings: `python tools/build_locales.py`
