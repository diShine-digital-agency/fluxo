# Security Policy

Fluxo is a local-first desktop application. All playlist data is processed on your machine. The optional local playlist server runs on your LAN and is not exposed to the internet by default.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability in Fluxo, please report it responsibly:

1. **Email**: Send a description to kevin@dishine.it with the subject line `[Fluxo Security]`.
2. **Do not** open a public GitHub issue for security vulnerabilities.
3. Include:
   - A description of the vulnerability and its potential impact.
   - Steps to reproduce the issue.
   - The affected file(s) and, if possible, a suggested fix.

We will acknowledge your report within 48 hours and aim to release a fix within 7 days for critical issues.

---

## Security Design

Fluxo is designed with security in mind:

- **Local-first**: All data processing happens locally on your machine
- **No telemetry**: No data is sent to external servers
- **No bundled streams**: Fluxo does not include any media content
- **Safe defaults**: Network features are opt-in
- **Input validation**: All imported files are parsed with strict validation
- **No code execution**: Playlist files are treated as data, never executed

---

### Sharing & Server Security

When the optional local playlist server is enabled:

- **Localhost by default**: `PlaylistServer` binds to `127.0.0.1` unless the caller explicitly opts in to `0.0.0.0` (LAN sharing)
- **PBKDF2-HMAC-SHA256 passwords**: Shared links support password protection using 100 000 iterations of PBKDF2 with a random 16-byte salt
- **Constant-time comparison**: Password verification uses `secrets.compare_digest` to prevent timing attacks
- **Cryptographic tokens**: Link tokens are generated with `secrets.token_urlsafe(24)`
- **Link expiration**: Shared links support optional expiry timestamps
- **Revocation**: Links can be permanently deactivated at any time

---

## Dependencies

We regularly review and update dependencies to address known vulnerabilities.

---

## Disclosure

We follow a coordinated disclosure approach. Once a fix has been merged, we will credit the reporter in the changelog unless they prefer to remain anonymous.
