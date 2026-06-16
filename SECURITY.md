# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a vulnerability

If you find a security issue, **please do not open a public issue** with exploit details.

Instead:

1. Open a [GitHub Security Advisory](https://github.com/zfhooyfincasnpktlmeisxv-cpu/DesktopPet/security/advisories/new) (preferred), **or**
2. Email the repository owner via GitHub profile contact

Include:

- Description of the issue
- Steps to reproduce
- Impact (local-only vs remote)
- Desktop Pet version / commit hash if known

We will acknowledge within a reasonable time and coordinate a fix before public disclosure when appropriate.

## Scope notes

Desktop Pet is a **local desktop application**. It does not expose a network service. Typical reports we care about:

- Unsafe file path handling leading to arbitrary writes outside `%APPDATA%\DesktopPet\`
- Code execution via malicious save files or asset packs
- Dependency vulnerabilities with a practical local attack path

Out of scope: social engineering, issues requiring already-compromised admin access, or third-party game asset licensing disputes.
