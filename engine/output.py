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
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

PDF_OUTPUT_DIR = Path.home() / "Desktop"


# ── PDF Export ───────────────────────────────────────────────

def export_to_pdf(
    content: str,
    title: str = "India Trade CLI Report",
    filename: Optional[str] = None,
) -> str:
    """
    Export text content to a formatted PDF.

    Args:
        content: raw text/terminal output to export
        title: PDF title
        filename: optional filename (auto-generated if not provided)

    Returns:
        Path to the saved PDF file.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        console.print("[red]fpdf2 not installed. Run: pip install fpdf2[/red]")
        return ""

    # Clean terminal formatting codes and non-ASCII characters
    clean = _strip_rich_markup(content)
    clean = clean.replace("₹", "Rs.").replace("→", "->").replace("←", "<-")
    clean = clean.replace("━", "-").replace("─", "-").replace("│", "|")
    clean = clean.replace("╔", "+").replace("╗", "+").replace("╚", "+").replace("╝", "+")
    # Remove any remaining non-latin1 characters
    clean = clean.encode("latin-1", errors="replace").decode("latin-1")

    # Generate filename
    if not filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r'[^\w\-]', '_', title)[:30]
        filename = f"trade_{safe_title}_{ts}.pdf"

    filepath = PDF_OUTPUT_DIR / filename

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pw = pdf.w - 40  # printable width (margins)

    # ── Header bar ───────────────────────────────────────────
    pdf.set_fill_color(20, 60, 120)
    pdf.rect(0, 0, pdf.w, 28, "F")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(6)
    pdf.cell(0, 10, title, align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(200, 220, 255)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p IST')}",
             align="C")
    pdf.ln(16)

    # ── Content ──────────────────────────────────────────────
    pdf.set_text_color(30, 30, 30)

    # Section header keywords
    _SECTION_KEYWORDS = {
        "VERDICT", "TRADE RECOMMENDATION", "RATIONALE", "RISKS", "RISK",
        "BULL CASE", "BEAR CASE", "FACILITATOR", "SCORECARD",
        "ANALYST REPORTS", "RESEARCH DEBATE", "SIMPLE EXPLANATION",
        "TRADE PLAN", "EXIT PLAN", "ENTRY ORDERS", "SIZING",
        "BACKTEST", "STRATEGY", "CONFIDENCE", "WINNER",
    }

    for line in clean.split("\n"):
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue

        # Detect section headers
        is_header = False
        if stripped.startswith("##"):
            is_header = True
            stripped = stripped.lstrip("#").strip()
        elif stripped.rstrip(":").upper() in _SECTION_KEYWORDS:
            is_header = True
        elif len(stripped) > 3 and stripped == stripped.upper() and not stripped[0].isdigit():
            # All caps lines (but not numbers)
            is_header = True

        if is_header:
            pdf.ln(4)
            pdf.set_fill_color(230, 240, 250)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(20, 60, 120)
            pdf.cell(0, 8, "  " + stripped, new_x="LMARGIN", new_y="NEXT", fill=True)
            pdf.set_text_color(30, 30, 30)
            pdf.ln(2)

        elif stripped.startswith("- ") or stripped.startswith("* "):
            # Bullet points with indent
            pdf.set_font("Helvetica", "", 9)
            bullet_text = stripped.lstrip("-* ").strip()
            pdf.cell(8)  # indent
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(4, 5, chr(8226))  # bullet char
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(pw - 12, 5, " " + bullet_text)

        elif ":" in stripped and len(stripped.split(":")[0]) < 20:
            # Key-value pairs (e.g. "Entry: Rs.2,360")
            parts = stripped.split(":", 1)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(8)  # indent
            pdf.cell(50, 5, parts[0].strip() + ":")
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, parts[1].strip())

        else:
            # Regular text
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, stripped)

    # ── Footer ───────────────────────────────────────────────
    pdf.ln(10)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y(), pdf.w - 20, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "India Trade CLI  |  AI-Powered Multi-Agent Stock Analysis",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 5, "github.com/ArchieIndian/india-trade-cli",
             new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.output(str(filepath))
    return str(filepath)


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
        "\n--- SIMPLE EXPLANATION ---\n"
        "Here's what the above means in plain English:\n\n"
        + result
    )


# ── Flag Parser ──────────────────────────────────────────────

def parse_output_flags(args: list[str]) -> tuple[list[str], bool, bool]:
    """
    Extract --pdf and --explain flags from command args.

    Returns:
        (clean_args, wants_pdf, wants_explain)
    """
    wants_pdf = "--pdf" in args
    wants_explain = "--explain" in args

    clean = [a for a in args if a not in ("--pdf", "--explain")]
    return clean, wants_pdf, wants_explain


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
        if wants_pdf:
            output = output + "\n\n" + _strip_rich_markup(explanation)

    if wants_pdf:
        filepath = export_to_pdf(output, title=title)
        if filepath:
            console.print(f"\n[green]PDF saved:[/green] {filepath}")


# ── Helpers ──────────────────────────────────────────────────

def _strip_rich_markup(text: str) -> str:
    """Remove Rich markup tags from text."""
    # Remove [bold], [red], [/bold], [dim], etc.
    clean = re.sub(r'\[/?[a-zA-Z_ ]+\]', '', text)
    # Remove emoji that might not render in PDF
    clean = re.sub(r'[^\x00-\x7F\u20B9]+', '', clean)
    return clean.strip()
