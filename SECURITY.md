# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

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

## Dependencies

We regularly review and update dependencies to address known vulnerabilities.
