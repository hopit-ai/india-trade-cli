"""
app/commands/persona.py
───────────────────────
CLI command handler for named investor persona analysis.

Commands:
  persona list                  — show all personas table
  persona <id> <SYMBOL>         — single persona analysis
  debate <SYMBOL>               — all 5 personas + consensus table

Output delegates to agent/persona_agent.py for the analysis logic
and renders results with Rich tables.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table
from rich import box

from agent.personas import get_persona, list_personas
from agent.persona_agent import run_persona_analysis, run_debate
from agent.schemas import PersonaSignal

console = Console()

# Verdict → Rich colour
_VERDICT_COLOUR = {
    "STRONG_BUY": "bold green",
    "BUY": "green",
    "HOLD": "yellow",
    "SELL": "red",
    "STRONG_SELL": "bold red",
}


def _verdict_styled(verdict: str) -> str:
    colour = _VERDICT_COLOUR.get(verdict, "white")
    return f"[{colour}]{verdict}[/{colour}]"


# ── persona list ──────────────────────────────────────────────


def _cmd_persona_list() -> None:
    table = Table(
        title="Named Investor Personas",
        show_header=True,
        header_style="bold cyan",
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("ID", style="bold", width=14)
    table.add_column("Name", width=22)
    table.add_column("Style", width=14)
    table.add_column("Top Focus", width=44)

    focus_map = {
        "buffett": "ROE >15%, FCF yield >5%, durable moat, low D/E",
        "jhunjhunwala": "India macro, earnings trajectory, promoter quality",
        "lynch": "PEG <1.0, explainable business, low institutional ownership",
        "soros": "Reflexivity, FII flows, INR trend, boom-bust regime",
        "munger": "Inversion, management incentives, accounting quality",
    }

    for persona in list_personas():
        table.add_row(
            persona.id,
            persona.name,
            persona.style,
            focus_map.get(persona.id, ""),
        )

    console.print()
    console.print(table)
    console.print(
        "[dim]Usage: persona <id> <SYMBOL>   e.g. persona buffett RELIANCE[/dim]\n"
        "[dim]       debate <SYMBOL>          e.g. debate INFY[/dim]\n"
    )


# ── persona <id> <SYMBOL> ─────────────────────────────────────


def _cmd_single_persona(
    persona_id: str,
    symbol: str,
    exchange: str,
    registry: Any,
    llm_provider: Any,
) -> None:
    try:
        persona = get_persona(persona_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return

    console.print(f"\n[dim]Analysing {exchange}:{symbol} as {persona.name}...[/dim]")

    try:
        signal = run_persona_analysis(
            persona_id=persona_id,
            symbol=symbol,
            exchange=exchange,
            registry=registry,
            llm_provider=llm_provider,
        )
    except Exception as e:
        console.print(f"[red]Persona analysis failed:[/red] {e}")
        return

    # ── Header ────────────────────────────────────────────────
    console.print()
    console.rule(
        f"[bold]{persona.name} on {exchange}:{symbol}[/bold]",
        style="cyan",
    )

    # ── Signal ────────────────────────────────────────────────
    verdict_str = _verdict_styled(signal.verdict)
    console.print(f"  Signal     : {verdict_str}  ({signal.confidence}% confidence)")

    # ── Checklist ─────────────────────────────────────────────
    if signal.rationale:
        console.print("  Checklist  :")
        for item in signal.rationale:
            console.print(f"    {item}")

    # ── Key metrics ───────────────────────────────────────────
    if signal.key_metrics:
        console.print("  Key Metrics:")
        for k, v in signal.key_metrics.items():
            console.print(f"    [dim]{k:<12}[/dim]: {v}")

    console.print()


# ── debate <SYMBOL> ───────────────────────────────────────────


def _cmd_debate(
    symbol: str,
    exchange: str,
    registry: Any,
    llm_provider: Any,
) -> None:
    console.print(f"\n[dim]Running investor debate on {exchange}:{symbol}...[/dim]")

    try:
        signals = run_debate(
            symbol=symbol,
            exchange=exchange,
            registry=registry,
            llm_provider=llm_provider,
        )
    except Exception as e:
        console.print(f"[red]Debate failed:[/red] {e}")
        return

    if not signals:
        console.print("[dim]No signals returned.[/dim]")
        return

    # ── Header ────────────────────────────────────────────────
    console.print()
    console.rule(
        f"[bold]Investor Debate: {exchange}:{symbol}[/bold]",
        style="cyan",
    )

    # ── Debate table ──────────────────────────────────────────
    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("Persona", width=18)
    table.add_column("Signal", width=12)
    table.add_column("Confidence", justify="right", width=12)
    table.add_column("Key Factor", width=36)

    name_map = {p.id: p.name for p in list_personas()}

    for signal in signals:
        persona_name = name_map.get(signal.persona, signal.persona.title())
        top_factor = ""
        if signal.key_metrics:
            # Pick first key metric as the "key factor" display
            k, v = next(iter(signal.key_metrics.items()))
            top_factor = f"{k}: {v}"
        elif signal.rationale:
            # Use first rationale item, strip leading check marks
            top_factor = signal.rationale[0].lstrip("✓✗~— ").strip()
            if len(top_factor) > 34:
                top_factor = top_factor[:31] + "..."

        table.add_row(
            persona_name,
            _verdict_styled(signal.verdict),
            f"{signal.confidence}%",
            top_factor,
        )

    console.print(table)

    # ── Consensus ─────────────────────────────────────────────
    _print_consensus(signals, name_map)
    console.print()


def _print_consensus(signals: list[PersonaSignal], name_map: dict[str, str]) -> None:
    """Compute and print the consensus verdict line."""
    # Bucket verdicts
    buy_verdicts = {"STRONG_BUY", "BUY"}
    sell_verdicts = {"STRONG_SELL", "SELL"}

    buy_camp: list[str] = []
    sell_camp: list[str] = []
    hold_camp: list[str] = []

    for sig in signals:
        name = name_map.get(sig.persona, sig.persona.title())
        if sig.verdict in buy_verdicts:
            buy_camp.append(name)
        elif sig.verdict in sell_verdicts:
            sell_camp.append(name)
        else:
            hold_camp.append(name)

    # Plurality wins
    counts = {
        "BUY": len(buy_camp),
        "HOLD": len(hold_camp),
        "SELL": len(sell_camp),
    }
    consensus = max(counts, key=lambda k: counts[k])
    count = counts[consensus]

    consensus_str = _verdict_styled(consensus)
    parts = [f"  Consensus  : {consensus_str} ({count}/{len(signals)})"]

    if consensus == "HOLD":
        if buy_camp:
            parts.append(f"  — BUY camp: {', '.join(buy_camp)}")
        if sell_camp:
            parts.append(f"  — SELL camp: {', '.join(sell_camp)}")
    elif consensus == "BUY":
        if hold_camp or sell_camp:
            dissenters = hold_camp + sell_camp
            parts.append(f"  — Cautious: {', '.join(dissenters)}")
    elif consensus == "SELL":
        if hold_camp or buy_camp:
            dissenters = hold_camp + buy_camp
            parts.append(f"  — Bullish holdouts: {', '.join(dissenters)}")

    for part in parts:
        console.print(part)


# ── Main dispatcher ───────────────────────────────────────────


def run(args: list[str], registry: Any = None, llm_provider: Any = None) -> None:
    """
    Dispatch persona commands.

    Called with:
      args = ["list"]                       → show all personas
      args = ["buffett", "RELIANCE"]        → single persona
      args = ["buffett", "NSE:RELIANCE"]    → explicit exchange
    """
    if not args or args[0].lower() == "list":
        _cmd_persona_list()
        return

    if len(args) < 2:
        console.print(
            "[red]Usage:[/red]\n"
            "  [cyan]persona list[/cyan]                   — all personas\n"
            "  [cyan]persona <id> <SYMBOL>[/cyan]          — e.g. persona buffett RELIANCE\n"
            "  [cyan]persona <id> NSE:<SYMBOL>[/cyan]      — explicit exchange\n"
        )
        return

    persona_id = args[0].lower()
    symbol_arg = args[1].upper()

    # Parse optional exchange prefix: "NSE:RELIANCE"
    if ":" in symbol_arg:
        exchange, symbol = symbol_arg.split(":", 1)
    else:
        exchange = "NSE"
        symbol = symbol_arg

    _cmd_single_persona(
        persona_id=persona_id,
        symbol=symbol,
        exchange=exchange,
        registry=registry,
        llm_provider=llm_provider,
    )


def run_debate_command(
    args: list[str],
    registry: Any = None,
    llm_provider: Any = None,
) -> None:
    """
    Dispatch the debate command.

    Called with:
      args = ["RELIANCE"]            → debate on NSE:RELIANCE
      args = ["NSE:RELIANCE"]        → explicit exchange
    """
    if not args:
        console.print(
            "[red]Usage: debate <SYMBOL>[/red]\n[dim]  debate RELIANCE\n  debate NSE:RELIANCE[/dim]"
        )
        return

    symbol_arg = args[0].upper()

    if ":" in symbol_arg:
        exchange, symbol = symbol_arg.split(":", 1)
    else:
        exchange = "NSE"
        symbol = symbol_arg

    _cmd_debate(
        symbol=symbol,
        exchange=exchange,
        registry=registry,
        llm_provider=llm_provider,
    )
