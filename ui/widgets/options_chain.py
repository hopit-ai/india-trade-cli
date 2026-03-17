"""
ui/widgets/options_chain.py
────────────────────────────
Textual widget: compact options chain viewer.
Shows ATM ±5 strikes with CE/PE LTP, OI, and IV.
"""

from __future__ import annotations

from textual.app     import ComposeResult
from textual.widgets import DataTable, Static, Label, Input
from textual         import on
from rich.text       import Text


class OptionsChainWidget(Static):
    """
    Compact options chain: shows CE | Strike | PE columns.
    User can type a symbol and it loads the nearest expiry chain.
    """

    DEFAULT_CSS = """
    OptionsChainWidget {
        height: auto;
        border: round $success;
        padding: 0 1;
    }
    OptionsChainWidget Label {
        color: $success;
        text-style: bold;
    }
    OptionsChainWidget Input {
        height: 1;
        border: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Options Chain")
        yield Input(placeholder="Symbol (e.g. NIFTY)", id="chain-symbol")
        yield DataTable(id="chain-table", show_cursor=False)

    def on_mount(self) -> None:
        t = self.query_one("#chain-table", DataTable)
        t.add_columns(
            "CE LTP", "CE OI(L)", "CE IV%",
            "Strike",
            "PE IV%", "PE OI(L)", "PE LTP",
        )
        self.load_chain("NIFTY")

    @on(Input.Submitted, "#chain-symbol")
    def on_symbol_submitted(self, event: Input.Submitted) -> None:
        self.load_chain(event.value.strip().upper())

    def load_chain(self, underlying: str) -> None:
        try:
            from market.options import get_options_chain, get_atm_strike
            from market.quotes  import get_ltp

            spot  = get_ltp(f"NSE:{underlying}")
            chain = get_options_chain(underlying)
            atm   = get_atm_strike(underlying, spot)

            strikes = sorted(set(c.strike for c in chain))
            atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - atm))
            lo      = max(0, atm_idx - 5)
            hi      = min(len(strikes), atm_idx + 6)
            visible = strikes[lo:hi]

            ce_map  = {c.strike: c for c in chain if c.option_type.upper() == "CE"}
            pe_map  = {c.strike: c for c in chain if c.option_type.upper() == "PE"}

            t = self.query_one("#chain-table", DataTable)
            t.clear()

            for strike in visible:
                ce   = ce_map.get(strike)
                pe   = pe_map.get(strike)
                is_atm = abs(strike - atm) < 1

                strike_text = Text(f"{strike:,.0f}", style="bold cyan" if is_atm else "white")

                ce_ltp  = f"₹{ce.last_price:,.0f}" if ce else "—"
                ce_oi   = f"{ce.open_interest/1e5:.1f}L" if ce and ce.open_interest else "—"
                ce_iv   = f"{ce.iv:.1f}%" if ce and ce.iv else "—"
                pe_ltp  = f"₹{pe.last_price:,.0f}" if pe else "—"
                pe_oi   = f"{pe.open_interest/1e5:.1f}L" if pe and pe.open_interest else "—"
                pe_iv   = f"{pe.iv:.1f}%" if pe and pe.iv else "—"

                t.add_row(
                    Text(ce_ltp, style="green"),
                    ce_oi, ce_iv,
                    strike_text,
                    pe_iv, pe_oi,
                    Text(pe_ltp, style="red"),
                )
        except Exception as e:
            t = self.query_one("#chain-table", DataTable)
            t.clear()
