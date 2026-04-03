"""
engine/output.py
────────────────
Output formatters for CLI commands.

Two reusable flags available on any command:
  --pdf          Export output to a formatted PDF
  --explain      Append a simple explanation (like explaining to a 16-year-old)

Usage:
    analyze RELIANCE --pdf
    analyze RELIANCE --explain
    analyze RELIANCE --pdf --explain
    flows --pdf
    backtest RELIANCE rsi --explain

The framework captures command output, then:
  --pdf:     converts to a styled PDF saved to ~/Desktop/
  --explain: sends the output to LLM with "explain simply" prompt, appends result

Install for PDF: pip install fpdf2
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

PDF_OUTPUT_DIR = Path.home() / "Desktop"
EXPORTS_DIR = Path.home() / ".trading_platform" / "exports"


# ── PDF Export ───────────────────────────────────────────────


def _build_pdf(content: str, title: str) -> object:
    """Build a FPDF object from content. Returns the FPDF instance."""
    from fpdf import FPDF

    # Clean terminal formatting codes and non-ASCII characters
    clean = _strip_rich_markup(content)
    clean = clean.replace("\u20b9", "Rs.").replace("\u2192", "->").replace("\u2190", "<-")
    clean = clean.replace("\u2501", "-").replace("\u2500", "-").replace("\u2502", "|")
    clean = (
        clean.replace("\u2554", "+")
        .replace("\u2557", "+")
        .replace("\u255a", "+")
        .replace("\u255d", "+")
    )
    # Remove any remaining non-latin1 characters
    clean = clean.encode("latin-1", errors="replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    w = pdf.w - pdf.l_margin - pdf.r_margin  # printable width

    # ── Title ────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(w, 8, title)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(w, 5, f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p IST')}")
    pdf.set_x(pdf.l_margin)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # ── Content — just write everything as plain text ────────
    pdf.set_font("Courier", "", 8)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(w, 4, clean)

    # ── Footer ───────────────────────────────────────────────
    pdf.ln(5)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(
        w,
        4,
        "India Trade CLI | AI-Powered Multi-Agent Stock Analysis | github.com/hopit-ai/india-trade-cli",
    )

    return pdf


def _archive_filename(title: str) -> str:
    """
    Build a descriptive archive filename from the title.

    Examples:
        "Analysis RELIANCE"       -> "RELIANCE_analysis_2026-04-01_14-32-05.pdf"
        "Deep Analysis TCS"       -> "TCS_deep_analysis_2026-04-01_09-15-00.pdf"
        "Backtest INFY rsi"       -> "INFY_backtest_rsi_2026-04-01_11-00-42.pdf"
        "AI Chat"                 -> "ai_chat_2026-04-01_16-22-10.pdf"
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    parts = title.strip().split()

    # Try to extract symbol and report type
    symbol = ""
    report_type = ""

    if len(parts) >= 2:
        # Check common patterns: "Analysis SYMBOL", "Deep Analysis SYMBOL", etc.
        keyword_map = {
            "analysis": "analysis",
            "deep": "deep_analysis",
            "backtest": "backtest",
            "brief": "brief",
            "ai": "ai_chat",
            "risk": "risk_report",
            "portfolio": "portfolio",
        }
        first_lower = parts[0].lower()
        if first_lower in keyword_map:
            report_type = keyword_map[first_lower]
            # "Deep Analysis SYMBOL" -> symbol is last part
            if first_lower == "deep" and len(parts) >= 3:
                symbol = parts[2]
                report_type = "deep_analysis"
            else:
                symbol = parts[1]
                # Append remaining parts (e.g. "Backtest INFY rsi" -> "backtest_rsi")
                if len(parts) > 2 and first_lower == "backtest":
                    report_type = f"backtest_{'_'.join(parts[2:])}"
        else:
            # Symbol might be first: just use the whole title
            symbol = parts[0]
            report_type = "_".join(parts[1:]).lower()

    if not report_type:
        report_type = re.sub(r"[^\w]", "_", title.lower())[:30]

    # Clean up
    symbol = re.sub(r"[^\w]", "", symbol).upper()
    report_type = re.sub(r"[^\w]", "_", report_type).lower()[:30]

    if symbol:
        return f"{symbol}_{report_type}_{ts}.pdf"
    return f"{report_type}_{ts}.pdf"


def export_to_pdf(
    content: str,
    title: str = "India Trade CLI Report",
    filename: Optional[str] = None,
) -> str:
    """
    Export text content to a formatted PDF.

    Saves to ~/Desktop/ AND automatically archives a timestamped copy
    to ~/.trading_platform/exports/.

    Args:
        content: raw text/terminal output to export
        title: PDF title
        filename: optional filename (auto-generated if not provided)

    Returns:
        Path to the saved PDF file (on Desktop).
    """
    try:
        from fpdf import FPDF  # noqa: F401 — just check availability
    except ImportError:
        console.print("[red]fpdf2 not installed. Run: pip install fpdf2[/red]")
        return ""

    pdf = _build_pdf(content, title)

    # Generate desktop filename
    if not filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r"[^\w\-]", "_", title)[:30]
        filename = f"trade_{safe_title}_{ts}.pdf"

    filepath = PDF_OUTPUT_DIR / filename
    pdf.output(str(filepath))

    # ── Auto-archive a timestamped copy ──────────────────────
    try:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        archive_name = _archive_filename(title)
        archive_path = EXPORTS_DIR / archive_name
        import shutil

        shutil.copy2(str(filepath), str(archive_path))
    except Exception:
        pass  # archiving is best-effort, never fail the main export

    return str(filepath)


# ── Exports management ──────────────────────────────────────


def list_exports() -> list[dict]:
    """
    List all archived PDF exports.

    Returns list of dicts with keys: name, path, size_kb, modified.
    Sorted by modification time (newest first).
    """
    if not EXPORTS_DIR.exists():
        return []

    exports = []
    for f in EXPORTS_DIR.glob("*.pdf"):
        stat = f.stat()
        exports.append(
            {
                "name": f.name,
                "path": str(f),
                "size_kb": stat.st_size / 1024,
                "modified": datetime.fromtimestamp(stat.st_mtime),
            }
        )

    exports.sort(key=lambda x: x["modified"], reverse=True)
    return exports


def open_export(filename: str) -> bool:
    """Open an exported PDF with the system default viewer."""
    import subprocess
    import platform

    path = EXPORTS_DIR / filename
    if not path.exists():
        return False

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", str(path)])
        elif system == "Linux":
            subprocess.Popen(["xdg-open", str(path)])
        elif system == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


def clear_exports(older_than_days: int = 30) -> int:
    """
    Delete exports older than N days.

    Returns number of files deleted.
    """
    if not EXPORTS_DIR.exists():
        return 0

    cutoff = datetime.now().timestamp() - (older_than_days * 86400)
    deleted = 0
    for f in EXPORTS_DIR.glob("*.pdf"):
        if f.stat().st_mtime < cutoff:
            try:
                f.unlink()
                deleted += 1
            except Exception:
                pass
    return deleted


# ── Simple Explainer ─────────────────────────────────────────


def explain_simply(content: str, llm_provider=None) -> str:
    """
    Take complex analysis output and explain it simply.
    Uses LLM to rewrite in plain language a 16-year-old would understand.

    If no LLM provider available, uses a rule-based simplifier.
    """
    if llm_provider:
        return _llm_explain(content, llm_provider)
    return _rule_based_explain(content)


EXPLAIN_PROMPT = """You are explaining a stock market analysis to a 16-year-old who has never traded before.

Here is the analysis output:
{content}

Rewrite this in simple, everyday language. Follow these rules:
1. No jargon — replace every technical term with a simple explanation
   - "RSI 72" → "the stock has been going up a lot recently (like a rubber band stretched too far)"
   - "PCR 1.3" → "more people are betting it will go down than up"
   - "ATR-based stop" → "we'll exit if the price drops by its typical daily swing amount"
   - "BULLISH" → "looks like it could go up"
   - "VIX 18" → "the market is a bit nervous right now"
2. Use analogies and everyday comparisons
3. Explain WHY each decision matters, not just WHAT it is
4. End with a clear "So what does this mean?" summary
5. Keep it under 300 words
6. Use simple bullet points

Start with: "Here's what this analysis means in simple terms:"
"""


def _llm_explain(content: str, llm_provider) -> str:
    """Use LLM to explain simply."""
    try:
        clean = _strip_rich_markup(content)
        # Truncate to avoid huge prompts
        if len(clean) > 3000:
            clean = clean[:3000] + "\n...(truncated)"

        prompt = EXPLAIN_PROMPT.format(content=clean)
        response = llm_provider.chat(
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        return response
    except Exception as e:
        return f"(Could not generate simple explanation: {e})"


def _rule_based_explain(content: str) -> str:
    """Fallback: simple keyword-based jargon replacement."""
    clean = _strip_rich_markup(content)

    replacements = {
        "BULLISH": "likely to go UP",
        "BEARISH": "likely to go DOWN",
        "NEUTRAL": "could go either way",
        "STRONG_BUY": "strong signal to BUY",
        "STRONG_SELL": "strong signal to SELL",
        "VOLATILE": "prices are swinging wildly",
        "VaR": "maximum expected loss",
        "CVaR": "average loss in worst-case scenarios",
        "RSI": "momentum indicator (how fast price moved)",
        "MACD": "trend strength indicator",
        "ATR": "average daily price swing",
        "PCR": "put-call ratio (bearish vs bullish bets)",
        "IV Rank": "how expensive options are right now",
        "Max Pain": "price where most option buyers lose money",
        "FII": "Foreign Institutional Investors (big foreign funds)",
        "DII": "Domestic Institutional Investors (Indian mutual funds)",
        "EMA": "moving average (smoothed price trend)",
        "SMA": "simple moving average",
        "CNC": "delivery (buy and hold)",
        "MIS": "intraday (buy and sell same day)",
        "NRML": "futures/options position",
        "stop-loss": "exit price to limit losses",
        "R:R": "reward-to-risk ratio",
    }

    result = clean
    for term, simple in replacements.items():
        result = result.replace(term, f"{term} ({simple})")

    return (
        "\n--- SIMPLE EXPLANATION ---\nHere's what the above means in plain English:\n\n" + result
    )


# ── Flag Parser ──────────────────────────────────────────────


def parse_output_flags(args: list[str]) -> tuple[list[str], bool, bool, bool]:
    """
    Extract --pdf, --explain, and --explain-save flags from command args.

    Returns:
        (clean_args, wants_pdf, wants_explain, wants_explain_save)
    """
    wants_explain_save = "--explain-save" in args
    wants_pdf = "--pdf" in args or "--save-pdf" in args or wants_explain_save
    wants_explain = "--explain" in args or wants_explain_save

    clean = [a for a in args if a not in ("--pdf", "--save-pdf", "--explain", "--explain-save")]
    return clean, wants_pdf, wants_explain, wants_explain_save


def handle_output_flags(
    output: str,
    title: str,
    wants_pdf: bool,
    wants_explain: bool,
    llm_provider=None,
) -> None:
    """
    Apply output flags after a command completes.

    Args:
        output: the command's text output
        title: PDF title / context label
        wants_pdf: export to PDF?
        wants_explain: append simple explanation?
        llm_provider: LLM for explain (optional, falls back to rule-based)
    """
    if wants_explain:
        console.print()
        console.rule("[bold green]Simple Explanation[/bold green]", style="green")
        explanation = explain_simply(output, llm_provider)
        if llm_provider:
            # LLM already streamed it
            pass
        else:
            console.print(explanation, highlight=False)
        console.rule(style="green")

        # Append explanation to output for PDF
        output = output + "\n\n--- SIMPLE EXPLANATION ---\n\n" + _strip_rich_markup(explanation)

    if wants_pdf:
        filepath = export_to_pdf(output, title=title)
        if filepath:
            console.print(f"\n[green]PDF saved:[/green] {filepath}")
            # Show archive path
            archive_name = _archive_filename(title)
            console.print(f"[dim]Archived:[/dim] ~/.trading_platform/exports/{archive_name}")


# ── Helpers ──────────────────────────────────────────────────


def _strip_rich_markup(text: str) -> str:
    """Remove Rich markup tags from text."""
    # Remove [bold], [red], [/bold], [dim], etc.
    clean = re.sub(r"\[/?[a-zA-Z_ ]+\]", "", text)
    # Remove emoji that might not render in PDF
    clean = re.sub(r"[^\x00-\x7F\u20B9]+", "", clean)
    return clean.strip()
