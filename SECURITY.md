# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email the maintainers with:
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

This project stores credentials in the OS keychain (macOS Keychain / Linux Secret Service / Windows Credential Locker) via the `keyring` library. Secrets should never be logged, printed, or written to disk in plain text.
