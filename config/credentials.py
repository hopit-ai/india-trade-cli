"""
config/credentials.py
─────────────────────
Secure credential management for india-trade-cli.

Priority order for every credential:
  1. OS keychain  (keyring) — set once via `credentials setup`, never in files
  2. Environment variable / .env — fallback for CI/CD, Docker, or headless use
  3. Interactive prompt — asks once, offers to save to keychain

Usage:
    from config.credentials import get_credential, load_all

    # At app startup — pulls all stored keys into os.environ
    load_all()

    # Anywhere else — smart getter (keychain → env → prompt)
    api_key = get_credential("ANTHROPIC_API_KEY", "Anthropic API Key", secret=True)

Keychain service name: "india-trade-cli"
Keys are stored as:   keyring.get_password("india-trade-cli", "KITE_API_KEY")
"""

from __future__ import annotations

import os
from typing import Optional

from rich.console import Console
from rich.prompt  import Prompt, Confirm
from rich.table   import Table
from rich.text    import Text

console = Console()

SERVICE = "india-trade-cli"

# ── Known credentials (key, display label, is_secret) ────────
#   is_secret=True  → masked input + stored in keychain
#   is_secret=False → plain input, still stored in keychain

KNOWN_CREDENTIALS: list[tuple[str, str, bool]] = [
    # ── Zerodha ──────────────────────────────────────────────
    ("KITE_API_KEY",        "Zerodha API Key",                     False),
    ("KITE_API_SECRET",     "Zerodha API Secret",                  True),
    # ── Groww ────────────────────────────────────────────────
    ("GROWW_CLIENT_ID",     "Groww Client ID",                     False),
    ("GROWW_CLIENT_SECRET", "Groww Client Secret",                 True),
    # ── Angel One ────────────────────────────────────────────
    ("ANGEL_API_KEY",       "Angel One API Key",                   False),
    ("ANGEL_CLIENT_CODE",   "Angel One Client Code (Login ID)",    False),
    ("ANGEL_PASSWORD",      "Angel One Trading Password",          True),
    ("ANGEL_TOTP_SECRET",   "Angel One TOTP Secret",               True),
    # ── Upstox ───────────────────────────────────────────────
    ("UPSTOX_API_KEY",      "Upstox API Key",                      False),
    ("UPSTOX_API_SECRET",   "Upstox API Secret",                   True),
    # ── Fyers ────────────────────────────────────────────────
    ("FYERS_APP_ID",        "Fyers App ID",                        False),
    ("FYERS_SECRET_KEY",    "Fyers Secret Key",                    True),
    # ── AI Provider selection ─────────────────────────────────
    ("AI_PROVIDER",         "AI Provider (anthropic / claude_subscription / openai / gemini / …)", False),
    # ── AI API Keys ──────────────────────────────────────────
    ("ANTHROPIC_API_KEY",   "Anthropic API Key",                   True),
    ("OPENAI_API_KEY",      "OpenAI API Key",                      True),
    ("GEMINI_API_KEY",      "Google Gemini API Key",               True),
    ("OPENAI_SESSION_TOKEN","OpenAI Session Token (ChatGPT Plus)", True),
    ("GOOGLE_CLOUD_PROJECT","Google Cloud Project ID",             False),
    # ── Data / News ───────────────────────────────────────────
    ("NEWSAPI_KEY",         "NewsAPI.org Key",                     True),
]

_KNOWN_KEYS = {k for k, _, _ in KNOWN_CREDENTIALS}


# ── Keyring helper (graceful fallback if keyring unavailable) ─

def _kr_get(key: str) -> Optional[str]:
    try:
        import keyring
        return keyring.get_password(SERVICE, key) or None
    except Exception:
        return None


def _kr_set(key: str, value: str) -> bool:
    try:
        import keyring
        keyring.set_password(SERVICE, key, value)
        return True
    except Exception:
        return False


def _kr_delete(key: str) -> bool:
    try:
        import keyring
        keyring.delete_password(SERVICE, key)
        return True
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────

def load_all() -> None:
    """
    Load all stored keychain credentials into os.environ at startup.

    Keychain values only set env vars that are not already set — so an
    explicit value in .env or the shell always wins over the keychain.
    This lets load_all() run early without trampling manual overrides.
    """
    loaded = 0
    for key, _, _ in KNOWN_CREDENTIALS:
        if os.environ.get(key):
            continue            # .env / shell already set this — leave it
        value = _kr_get(key)
        if value:
            os.environ[key] = value
            loaded += 1

    if loaded:
        console.print(
            f"[dim]🔑 Loaded {loaded} credential(s) from OS keychain.[/dim]"
        )


def get_credential(
    key: str,
    label: Optional[str] = None,
    *,
    secret: bool = True,
    required: bool = True,
) -> str:
    """
    Retrieve a credential using the priority chain:
      keychain → env var → interactive prompt (+ offer to save).

    Args:
        key:      Environment variable name, e.g. "KITE_API_KEY".
        label:    Human-readable name shown in prompts.
        secret:   If True, input is masked (password mode).
        required: If True and nothing found, raises RuntimeError.

    Returns:
        The credential value, or "" if not found and not required.
    """
    display = label or key

    # 1. Keychain
    value = _kr_get(key)
    if value:
        os.environ[key] = value   # inject so rest of code sees it via os.environ
        return value

    # 2. Environment variable / .env (already loaded by dotenv)
    value = os.environ.get(key, "").strip()
    if value:
        return value

    # 3. Interactive prompt
    console.print(f"\n[yellow]⚠  Missing credential:[/yellow] [bold]{display}[/bold]")

    if secret:
        value = Prompt.ask(f"  Enter {display}", password=True)
    else:
        value = Prompt.ask(f"  Enter {display}")

    value = (value or "").strip()

    if not value:
        if required:
            raise RuntimeError(
                f"Credential '{key}' is required but was not provided. "
                f"Run `credentials setup` or add {key} to your .env file."
            )
        return ""

    # Offer to save to keychain
    if _kr_set.__module__:   # keyring available
        try:
            save = Confirm.ask("  Save to OS keychain for future sessions?", default=True)
            if save:
                if _kr_set(key, value):
                    os.environ[key] = value
                    console.print(f"  [green]✓ Saved to keychain[/green]\n")
                else:
                    console.print("  [yellow]Could not save to keychain — keyring unavailable.[/yellow]\n")
        except Exception:
            pass

    os.environ[key] = value
    return value


def set_credential(key: str, value: str) -> None:
    """Save a credential to both the keychain and os.environ."""
    os.environ[key] = value
    if not _kr_set(key, value):
        console.print("[yellow]keyring unavailable — credential set only for this session.[/yellow]")


def delete_credential(key: str) -> None:
    """Remove a credential from the keychain (env var is not touched)."""
    if _kr_delete(key):
        console.print(f"[yellow]Deleted '{key}' from keychain.[/yellow]")
    else:
        console.print(f"[dim]'{key}' was not in the keychain.[/dim]")


def list_credentials() -> None:
    """Print a table showing the status of all known credentials."""
    t = Table(
        title="Credentials",
        show_header=True,
        header_style="bold cyan",
    )
    t.add_column("Key",            style="bold")
    t.add_column("Label",          style="dim")
    t.add_column("Keychain",       justify="center")
    t.add_column("Env / .env",     justify="center")
    t.add_column("Status",         justify="center")

    for key, label, is_secret in KNOWN_CREDENTIALS:
        in_keychain = bool(_kr_get(key))
        in_env      = bool(os.environ.get(key, "").strip())
        available   = in_keychain or in_env

        kc_icon  = "[green]●[/green]" if in_keychain else "[dim]○[/dim]"
        env_icon = "[green]●[/green]" if in_env      else "[dim]○[/dim]"
        status   = "[green]✓  Set[/green]" if available else "[red]✗  Missing[/red]"

        t.add_row(key, label, kc_icon, env_icon, status)

    console.print()
    console.print(t)
    console.print(
        "\n[dim]● = present  ○ = not set[/dim]  |  "
        "[dim]Keychain: OS keyring (macOS Keychain / Linux Secret Service / Windows Credential Manager)[/dim]\n"
    )


def run_setup_wizard(keys: Optional[list[str]] = None) -> None:
    """
    Interactive wizard to configure credentials.

    Args:
        keys: List of credential keys to configure. If None, runs all.
    """
    targets = (
        [(k, l, s) for k, l, s in KNOWN_CREDENTIALS if k in keys]
        if keys
        else KNOWN_CREDENTIALS
    )

    console.print("\n[bold cyan]Credential Setup Wizard[/bold cyan]")
    console.print(
        "[dim]Credentials are stored securely in your OS keychain.\n"
        "Press Enter to skip a credential you don't need.[/dim]\n"
    )

    # Group by section
    _ZERODHA_KEYS   = {"KITE_API_KEY", "KITE_API_SECRET"}
    _GROWW_KEYS     = {"GROWW_CLIENT_ID", "GROWW_CLIENT_SECRET"}
    _ANGEL_KEYS     = {"ANGEL_API_KEY", "ANGEL_CLIENT_CODE", "ANGEL_PASSWORD", "ANGEL_TOTP_SECRET"}
    _UPSTOX_KEYS    = {"UPSTOX_API_KEY", "UPSTOX_API_SECRET"}
    _FYERS_KEYS     = {"FYERS_APP_ID", "FYERS_SECRET_KEY"}
    _AI_KEYS        = {"AI_PROVIDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                       "OPENAI_SESSION_TOKEN", "GOOGLE_CLOUD_PROJECT"}

    sections: dict[str, list] = {
        "Zerodha (Kite Connect)": [
            (k, l, s) for k, l, s in targets if k in _ZERODHA_KEYS
        ],
        "Groww": [
            (k, l, s) for k, l, s in targets if k in _GROWW_KEYS
        ],
        "Angel One (SmartAPI — free)": [
            (k, l, s) for k, l, s in targets if k in _ANGEL_KEYS
        ],
        "Upstox": [
            (k, l, s) for k, l, s in targets if k in _UPSTOX_KEYS
        ],
        "Fyers": [
            (k, l, s) for k, l, s in targets if k in _FYERS_KEYS
        ],
        "AI Provider": [
            (k, l, s) for k, l, s in targets if k in _AI_KEYS
        ],
        "Market Data": [
            (k, l, s) for k, l, s in targets if "NEWSAPI" in k
        ],
    }

    saved = 0
    for section, items in sections.items():
        if not items:
            continue

        console.print(f"[bold]{section}[/bold]")

        # Special interactive flow for the AI Provider section
        if section == "AI Provider" and any(k == "AI_PROVIDER" for k, _, _ in items):
            _wizard_ai_provider(items)
            saved += sum(1 for k, _, _ in items if _kr_get(k))
            console.print()
            continue

        for key, label, is_secret in items:
            current = _kr_get(key) or os.environ.get(key, "")
            hint    = " [dim](already set — press Enter to keep)[/dim]" if current else ""
            console.print(f"  {label}{hint}")

            if is_secret:
                value = Prompt.ask("  Value", password=True, default="")
            else:
                value = Prompt.ask("  Value", default=current or "")

            value = value.strip()
            if not value:
                continue

            if _kr_set(key, value):
                os.environ[key] = value
                saved += 1
                console.print("  [green]✓ Saved[/green]")
            else:
                console.print("  [yellow]⚠ Could not reach keychain — set in .env instead[/yellow]")
        console.print()

    console.print(
        f"[bold green]✓  Setup complete.[/bold green]  "
        f"{saved} credential(s) saved to keychain.\n"
    )


def _wizard_ai_provider(items: list[tuple[str, str, bool]]) -> None:
    """
    Interactive AI provider wizard with subscription vs API-key choice.
    Called from run_setup_wizard for the AI Provider section.
    """
    console.print(
        "\n  How do you want to use AI?\n\n"
        "  [cyan][1][/cyan] [bold]Claude (Anthropic)[/bold] — API key  [dim](pay per token)[/dim]\n"
        "  [cyan][2][/cyan] [bold]Claude Pro / Max subscription[/bold]  [dim](use `claude` CLI, no key needed)[/dim]\n"
        "  [cyan][3][/cyan] [bold]OpenAI (GPT-4o)[/bold]  — API key  [dim](pay per token)[/dim]\n"
        "  [cyan][4][/cyan] [bold]ChatGPT Plus / Team subscription[/bold]  [dim](session token, unofficial)[/dim]\n"
        "  [cyan][5][/cyan] [bold]Google Gemini[/bold] — API key  [dim](free tier at aistudio.google.com)[/dim]\n"
        "  [cyan][6][/cyan] [bold]Gemini Advanced subscription[/bold]  [dim](Vertex AI via gcloud, GCP project needed)[/dim]\n"
        "  [cyan][7][/cyan] Skip / keep existing\n"
    )
    choice = Prompt.ask("  Choice", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")

    if choice == "1":
        _save_cred("AI_PROVIDER", "anthropic")
        _prompt_and_save("ANTHROPIC_API_KEY", "Anthropic API Key", secret=True)

    elif choice == "2":
        _save_cred("AI_PROVIDER", "claude_subscription")
        console.print(
            "\n  [green]✓ Set to Claude subscription mode.[/green]\n"
            "  Make sure you have the [bold]claude[/bold] CLI installed and logged in:\n"
            "    [dim]npm install -g @anthropic-ai/claude-code[/dim]\n"
            "    [dim]claude login[/dim]\n"
        )

    elif choice == "3":
        _save_cred("AI_PROVIDER", "openai")
        _prompt_and_save("OPENAI_API_KEY", "OpenAI API Key", secret=True)

    elif choice == "4":
        _save_cred("AI_PROVIDER", "openai_subscription")
        console.print(
            "\n  [yellow]ChatGPT session token (unofficial — may break on updates).[/yellow]\n"
            "  Get it: chatgpt.com → F12 DevTools → Application → Cookies\n"
            "          → [bold]__Secure-next-auth.session-token[/bold]\n"
        )
        _prompt_and_save("OPENAI_SESSION_TOKEN", "ChatGPT Session Token", secret=True)

    elif choice == "5":
        _save_cred("AI_PROVIDER", "gemini")
        console.print("  [dim]Get a free key at: aistudio.google.com[/dim]")
        _prompt_and_save("GEMINI_API_KEY", "Google Gemini API Key", secret=True)

    elif choice == "6":
        _save_cred("AI_PROVIDER", "gemini_subscription")
        console.print(
            "\n  [green]Gemini Advanced via Vertex AI (gcloud ADC).[/green]\n"
            "  Make sure you have run: [dim]gcloud auth application-default login[/dim]\n"
        )
        _prompt_and_save("GOOGLE_CLOUD_PROJECT", "Google Cloud Project ID", secret=False)


def _save_cred(key: str, value: str) -> None:
    """Save a credential to keychain + os.environ silently."""
    if _kr_set(key, value):
        os.environ[key] = value
        console.print(f"  [green]✓ AI_PROVIDER → {value}[/green]")


def _prompt_and_save(key: str, label: str, *, secret: bool) -> None:
    """Prompt for a single credential and save it."""
    current = _kr_get(key) or os.environ.get(key, "")
    hint    = " [dim](already set — press Enter to keep)[/dim]" if current else ""
    console.print(f"  {label}{hint}")
    if secret:
        value = Prompt.ask("  Value", password=True, default="")
    else:
        value = Prompt.ask("  Value", default=current or "")
    value = value.strip()
    if value:
        if _kr_set(key, value):
            os.environ[key] = value
            console.print("  [green]✓ Saved[/green]")


def cmd_credentials(args: list[str]) -> None:
    """
    REPL handler for the `credentials` command.

    Sub-commands:
      credentials            → list all credentials and their status
      credentials list       → same as above
      credentials setup      → run the interactive setup wizard
      credentials setup KEY  → set one specific key
      credentials set KEY    → prompt for and save one key
      credentials delete KEY → remove a key from the keychain
      credentials clear      → remove ALL keys from keychain (asks for confirm)
    """
    sub = args[0].lower() if args else "list"

    if sub in ("list", "ls"):
        list_credentials()

    elif sub == "setup":
        if len(args) > 1:
            run_setup_wizard(keys=[args[1].upper()])
        else:
            run_setup_wizard()

    elif sub == "set":
        if len(args) < 2:
            console.print("[red]Usage: credentials set <KEY>[/red]")
            return
        key  = args[1].upper()
        _, _, is_secret = next(
            ((k, l, s) for k, l, s in KNOWN_CREDENTIALS if k == key),
            (key, key, True),
        )
        label = next(
            (l for k, l, _ in KNOWN_CREDENTIALS if k == key), key
        )
        console.print(f"\n[bold]Set credential:[/bold] {label}")
        value = Prompt.ask("  New value", password=is_secret)
        if value.strip():
            set_credential(key, value.strip())
            console.print(f"[green]✓ {key} updated.[/green]\n")

    elif sub == "delete":
        if len(args) < 2:
            console.print("[red]Usage: credentials delete <KEY>[/red]")
            return
        delete_credential(args[1].upper())

    elif sub == "clear":
        confirmed = Confirm.ask(
            "[red]Remove ALL credentials from keychain?[/red]", default=False
        )
        if confirmed:
            for key, _, _ in KNOWN_CREDENTIALS:
                _kr_delete(key)
            console.print("[yellow]All credentials cleared from keychain.[/yellow]")

    else:
        # Treat as `list` if unknown sub-command
        list_credentials()
