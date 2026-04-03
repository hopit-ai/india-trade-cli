"""
ui/widgets/portfolio.py
────────────────────────
Textual widget: live portfolio summary panel.
Displays holdings, positions, P&L, and refreshes every 30s.
Shows a Broker column automatically when multiple brokers are connected.
"""

from __future__ import annotations

from textual.app     import ComposeResult
from textual.widgets import DataTable, Static, Label
from rich.text       import Text


class PortfolioWidget(Static):
    """
    Shows holdings + positions in a two-section DataTable.
    Refreshes automatically via the app's tick interval.
    Adds a 'Broker' column when multiple brokers are connected.
    """

    DEFAULT_CSS = """
    PortfolioWidget {
        height: auto;
        border: round $accent;
        padding: 0 1;
    }
    PortfolioWidget Label {
        color: $accent;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Portfolio")
        yield DataTable(id="holdings-table", show_cursor=False)
        yield DataTable(id="positions-table", show_cursor=False)

    def on_mount(self) -> None:
        self._setup_holdings_table(multi=False)
        self._setup_positions_table(multi=False)
        self.refresh_data()

    def _setup_holdings_table(self, multi: bool = False) -> None:
        t = self.query_one("#holdings-table", DataTable)
        t.clear(columns=True)
        cols = ["Symbol", "Qty", "Avg", "LTP", "P&L", "%"]
        if multi:
            cols.append("Broker")
        t.add_columns(*cols)

    def _setup_positions_table(self, multi: bool = False) -> None:
        t = self.query_one("#positions-table", DataTable)
        t.clear(columns=True)
        cols = ["Symbol", "Qty", "Avg", "LTP", "P&L", "Product"]
        if multi:
            cols.append("Broker")
        t.add_columns(*cols)

    def refresh_data(self) -> None:
        """Fetch fresh data from all connected brokers and redraw tables."""
        try:
            from engine.portfolio import get_multi_broker_summary
            summ  = get_multi_broker_summary()
            multi = summ.multi_broker

            # Re-setup columns if broker count changed
            self._setup_holdings_table(multi=multi)
            self._setup_positions_table(multi=multi)

            self._render_holdings(summ.holdings, multi=multi)
            self._render_positions(summ.positions, multi=multi)

            # Update label to show broker names
            label = self.query_one("Label", Label)
            if multi and summ.brokers:
                brokers_str = " + ".join(b.title() for b in summ.brokers)
                label.update(f"Portfolio  [dim]({brokers_str})[/dim]")
            else:
                label.update("Portfolio")

        except Exception:
            self.query_one("#holdings-table",  DataTable).clear()
            self.query_one("#positions-table",  DataTable).clear()

    def _render_holdings(self, holdings, multi: bool = False) -> None:
        t = self.query_one("#holdings-table", DataTable)
        t.clear()
        for h in sorted(holdings, key=lambda x: (x.broker, x.symbol)):
            color = "green" if h.pnl >= 0 else "red"
            row = [
                h.symbol,
                str(h.qty),
                f"₹{h.avg_price:,.0f}",
                f"₹{h.ltp:,.0f}",
                Text(f"₹{h.pnl:,.0f}", style=color),
                Text(f"{h.pnl_pct:+.1f}%", style=color),
            ]
            if multi:
                row.append(Text(h.broker.title(), style="dim"))
            t.add_row(*row)

    def _render_positions(self, positions, multi: bool = False) -> None:
        t = self.query_one("#positions-table", DataTable)
        t.clear()
        for p in sorted(positions, key=lambda x: (x.broker, x.symbol)):
            color = "green" if p.pnl >= 0 else "red"
            row = [
                p.symbol,
                str(p.qty),
                f"₹{p.avg_price:,.0f}",
                f"₹{p.ltp:,.0f}",
                Text(f"₹{p.pnl:,.0f}", style=color),
                p.product,
            ]
            if multi:
                row.append(Text(p.broker.title(), style="dim"))
            t.add_row(*row)
