# Release notes — v1.0.0

Build date: **2026-06-16**

## Downloads

Attach these files to the GitHub Release for tag `v1.0.0`:

| File | Size | SHA-256 |
|------|------|---------|
| `DesktopPet-Setup-1.0.0.exe` | ~64 MB | `0BA78B148BEE719F9ADFE817A86BA0727EA1AB0184894E2B6C9208BC6492B11F` |
| `DesktopPet.exe` (portable) | ~65 MB | `73760B4D433B0A48C8D4094BD92F5B3162138866B6C270D6F556AE6D63F0D05C` |

Verify locally (PowerShell):

```powershell
Get-FileHash DesktopPet-Setup-1.0.0.exe -Algorithm SHA256
```

Recompute after rebuilding — hashes change when the binary changes.

## Requirements

- Windows **10/11** 64-bit
- **No Python** required for Release builds (self-contained PyInstaller exe)

## Antivirus / SmartScreen

Release builds are **unsigned** (no code-signing certificate). Windows Defender or other AV may show:

- “Windows protected your PC” (SmartScreen)
- Generic “unknown publisher” warnings

This is common for indie open-source exes. You can:

1. Click **More info → Run anyway** if you trust this repository
2. Compare the **SHA-256** above with your downloaded file
3. Upload the file to [VirusTotal](https://www.virustotal.com/) for a multi-engine scan

We do not bundle installers, toolbars, or crypto miners. Source is MIT-licensed on GitHub.

## Known issues (v1.0.0)

- First launch may take a few seconds while the one-file exe unpacks
- Monopoly / chess in-game UI is partly Chinese even when UI language is English
- No auto-update channel yet — check [Releases](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/releases) for new versions

See [CHANGELOG.md](../CHANGELOG.md) for full history.
