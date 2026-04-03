# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email **mitra.arkid@gmail.com** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
3. You should receive a response within 72 hours.

## Scope

Security issues we care about:
- Credential leakage (API keys, broker tokens, session data)
- Injection vulnerabilities in user input handling
- Unauthorized access to broker APIs or order placement
- Dependencies with known CVEs

## Credentials Handling

This project uses two storage mechanisms for sensitive data:

- **API keys and secrets** (broker API keys, AI provider keys) are stored in the OS keychain (macOS Keychain / Linux Secret Service / Windows Credential Locker) via the `keyring` library. These are never written to plain text files.

- **Broker session tokens** (access tokens obtained after OAuth/TOTP login) are cached as JSON files under `~/.trading_platform/` to allow session resumption without re-authentication. These files:
  - Contain short-lived access tokens (not API secrets)
  - Are automatically deleted on `logout`
  - Have built-in expiry checks (6–20 hours depending on broker)
  - Are stored with default file permissions (user-only on most systems)

Secrets should never be logged, printed to console, or committed to version control.
