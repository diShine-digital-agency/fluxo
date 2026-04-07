# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Fluxo, please report it responsibly:

1. **Do not** open a public issue
2. Email security concerns to the project maintainers
3. Include a description of the vulnerability and steps to reproduce
4. Allow reasonable time for a fix before public disclosure

## Security Design

Fluxo is designed with security in mind:

- **Local-first**: All data processing happens locally on your machine
- **No telemetry**: No data is sent to external servers
- **No bundled streams**: Fluxo does not include any media content
- **Safe defaults**: Network features are opt-in
- **Input validation**: All imported files are parsed with strict validation
- **No code execution**: Playlist files are treated as data, never executed

### Sharing & Server Security

When the optional local playlist server is enabled:

- **Localhost by default**: `PlaylistServer` binds to `127.0.0.1` unless the caller explicitly opts in to `0.0.0.0` (LAN sharing)
- **PBKDF2-HMAC-SHA256 passwords**: Shared links support password protection using 100 000 iterations of PBKDF2 with a random 16-byte salt
- **Constant-time comparison**: Password verification uses `secrets.compare_digest` to prevent timing attacks
- **Cryptographic tokens**: Link tokens are generated with `secrets.token_urlsafe(24)`
- **Link expiration**: Shared links support optional expiry timestamps
- **Revocation**: Links can be permanently deactivated at any time

## Dependencies

We regularly review and update dependencies to address known vulnerabilities.
