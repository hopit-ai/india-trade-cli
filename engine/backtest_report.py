"""
engine/backtest_report.py
─────────────────────────
Self-contained HTML backtest comparison report generator (#156).

Produces a single HTML file with:
  - Strategy ranking table (Return, CAGR, Sharpe, Max DD, Win Rate, Profit Factor)
  - Equity curve overlay chart (Chart.js embedded)
  - Benchmark (buy & hold) row

No external server dependency — pure client-side rendering.

Usage:
    from engine.backtest import run_backtest
    from engine.backtest_report import generate_html_report

    r1 = run_backtest("INFY", "rsi")
    r2 = run_backtest("INFY", "macd")
    path = generate_html_report([r1, r2])
    # → ~/Desktop/backtest_INFY_20260411_123456.html
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.backtest import BacktestResult

# ── Output directory ─────────────────────────────────────────
REPORT_OUTPUT_DIR = Path.home() / "Desktop"

# Distinct colours for up to 10 strategies
_CHART_COLORS = [
    "#60a5fa",  # blue
    "#34d399",  # green
    "#f59e0b",  # amber
    "#f87171",  # red
    "#a78bfa",  # violet
    "#fb923c",  # orange
    "#22d3ee",  # cyan
    "#e879f9",  # fuchsia
    "#86efac",  # light-green
    "#fde68a",  # light-amber
]


def generate_html_report(
    results: list["BacktestResult"],
    output_path: str | None = None,
) -> str:
    """
    Generate a self-contained HTML backtest comparison report.

    Args:
        results: One or more BacktestResult objects.
        output_path: Where to save the HTML. Defaults to Desktop.

    Returns:
        Absolute path to the saved HTML file.
    """
    if not results:
        raise ValueError("At least one BacktestResult is required")

    html = _build_html(results)

    if output_path:
        path = Path(output_path)
    else:
        symbol = results[0].symbol
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_OUTPUT_DIR / f"backtest_{symbol}_{ts}.html"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return str(path)


# ── HTML builder ─────────────────────────────────────────────


def _build_html(results: list["BacktestResult"]) -> str:
    symbol = results[0].symbol
    title = f"Backtest Report — {symbol}"

    # ── Ranking table rows ──────────────────────────────
    table_rows = ""
    for i, r in enumerate(results):
        ret_color = "#34d399" if r.total_return >= 0 else "#f87171"
        alpha = r.total_return - r.buy_hold_return
        alpha_color = "#34d399" if alpha >= 0 else "#f87171"
        table_rows += f"""
        <tr>
          <td><span class="dot" style="background:{_CHART_COLORS[i % len(_CHART_COLORS)]}"></span>
              {r.strategy_name}</td>
          <td style="color:{ret_color}">{r.total_return:+.2f}%</td>
          <td style="color:{ret_color}">{r.cagr:+.2f}%</td>
          <td style="color:{alpha_color}">{alpha:+.2f}%</td>
          <td>{r.sharpe_ratio:.2f}</td>
          <td style="color:#f87171">{r.max_drawdown:.2f}%</td>
          <td>{r.win_rate:.1f}%</td>
          <td>{r.profit_factor:.2f}</td>
          <td>{r.total_trades}</td>
        </tr>"""

    # Buy & hold row
    bh = results[0].buy_hold_return
    bh_color = "#34d399" if bh >= 0 else "#f87171"
    table_rows += f"""
        <tr class="bh-row">
          <td><span class="dot" style="background:#6b7280"></span> Buy &amp; Hold</td>
          <td style="color:{bh_color}">{bh:+.2f}%</td>
          <td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td>
        </tr>"""

    # ── Chart.js datasets ────────────────────────────────
    datasets = []
    for i, r in enumerate(results):
        color = _CHART_COLORS[i % len(_CHART_COLORS)]
        # Normalise equity curve to start at 100
        curve = r.equity_curve or [100.0]
        base = curve[0] if curve[0] != 0 else 100.0
        normalised = [round(v / base * 100, 2) for v in curve]
        datasets.append(
            {
                "label": r.strategy_name,
                "data": normalised,
                "borderColor": color,
                "backgroundColor": color + "22",
                "borderWidth": 2,
                "pointRadius": 0,
                "tension": 0.2,
                "fill": False,
            }
        )

    # Buy & hold flat line
    if results[0].equity_curve:
        n = len(results[0].equity_curve)
        bh_end = 100 * (1 + results[0].buy_hold_return / 100)
        bh_curve = [round(100 + (bh_end - 100) * k / max(n - 1, 1), 2) for k in range(n)]
        datasets.append(
            {
                "label": "Buy & Hold",
                "data": bh_curve,
                "borderColor": "#6b7280",
                "borderDash": [6, 3],
                "borderWidth": 1.5,
                "pointRadius": 0,
                "tension": 0,
                "fill": False,
            }
        )

    labels = list(range(len(results[0].equity_curve or [0])))
    chart_json = json.dumps({"labels": labels, "datasets": datasets})

    # ── Individual strategy details ───────────────────────
    detail_sections = ""
    for i, r in enumerate(results):
        color = _CHART_COLORS[i % len(_CHART_COLORS)]
        detail_sections += f"""
        <details class="detail-card">
          <summary style="color:{color}">{r.strategy_name}</summary>
          <table class="detail-table">
            <tr><td>Period</td><td>{r.start_date} → {r.end_date}</td></tr>
            <tr><td>Total Return</td><td>{r.total_return:+.2f}%</td></tr>
            <tr><td>CAGR</td><td>{r.cagr:+.2f}%</td></tr>
            <tr><td>Sharpe Ratio</td><td>{r.sharpe_ratio:.2f}</td></tr>
            <tr><td>Max Drawdown</td><td>{r.max_drawdown:.2f}%</td></tr>
            <tr><td>Win Rate</td><td>{r.win_rate:.1f}%</td></tr>
            <tr><td>Profit Factor</td><td>{r.profit_factor:.2f}</td></tr>
            <tr><td>Total Trades</td><td>{r.total_trades}</td></tr>
            <tr><td>Avg Win</td><td>{r.avg_win:+.2f}%</td></tr>
            <tr><td>Avg Loss</td><td>{r.avg_loss:+.2f}%</td></tr>
            <tr><td>Avg Hold Days</td><td>{r.avg_hold_days:.1f}</td></tr>
            <tr><td>Buy &amp; Hold</td><td>{r.buy_hold_return:+.2f}%</td></tr>
          </table>
        </details>"""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      background: #0f1117; color: #e2e8f0; margin: 0; padding: 24px;
    }}
    h1 {{ font-size: 1.4rem; margin: 0 0 4px; color: #f8fafc; }}
    .meta {{ color: #64748b; font-size: .82rem; margin-bottom: 24px; }}
    .card {{
      background: #1e2330; border: 1px solid #2d3748;
      border-radius: 10px; padding: 20px; margin-bottom: 20px;
    }}
    h2 {{ font-size: 1rem; color: #94a3b8; margin: 0 0 12px; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .84rem; }}
    th {{ text-align: left; color: #64748b; font-weight: 500;
          padding: 6px 10px; border-bottom: 1px solid #2d3748; }}
    td {{ padding: 7px 10px; border-bottom: 1px solid #1e293b; }}
    tr:hover td {{ background: #263044; }}
    .bh-row td {{ color: #94a3b8; font-style: italic; }}
    .dot {{ display: inline-block; width: 10px; height: 10px;
            border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
    canvas {{ max-height: 320px; }}
    details.detail-card {{
      background: #151b27; border: 1px solid #2d3748;
      border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;
    }}
    details.detail-card summary {{
      cursor: pointer; font-weight: 600; font-size: .9rem; outline: none;
    }}
    .detail-table {{ margin-top: 10px; width: 100%; font-size: .82rem; }}
    .detail-table td:first-child {{ color: #64748b; width: 40%; }}
    footer {{ color: #475569; font-size: .76rem; text-align: center; margin-top: 24px; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p class="meta">Generated {generated_at} &nbsp;·&nbsp; {len(results)} strateg{"y" if len(results) == 1 else "ies"}</p>

  <div class="card">
    <h2>Strategy Ranking</h2>
    <table>
      <thead>
        <tr>
          <th>Strategy</th><th>Return</th><th>CAGR</th><th>Alpha</th>
          <th>Sharpe</th><th>Max DD</th><th>Win Rate</th>
          <th>Profit Factor</th><th>Trades</th>
        </tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Equity Curves (normalised to 100)</h2>
    <canvas id="equityChart"></canvas>
  </div>

  <div class="card">
    <h2>Strategy Details</h2>
    {detail_sections}
  </div>

  <footer>India Trade CLI — backtest report</footer>

  <script>
    const cfg = {chart_json};
    new Chart(document.getElementById('equityChart'), {{
      type: 'line',
      data: cfg,
      options: {{
        responsive: true,
        plugins: {{
          legend: {{ labels: {{ color: '#94a3b8', boxWidth: 12 }} }},
          tooltip: {{ mode: 'index', intersect: false }},
        }},
        scales: {{
          x: {{ ticks: {{ color: '#64748b', maxTicksLimit: 8 }},
               grid: {{ color: '#1e293b' }} }},
          y: {{ ticks: {{ color: '#64748b', callback: v => v.toFixed(1) }},
               grid: {{ color: '#1e293b' }} }},
        }},
      }},
    }});
  </script>
</body>
</html>"""
