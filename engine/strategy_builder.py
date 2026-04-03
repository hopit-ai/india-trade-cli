"""
engine/strategy_builder.py
──────────────────────────
Interactive strategy builder — describe a strategy in plain English,
the AI asks questions, generates code, backtests, and saves.

Components:
  StrategyStore          — persistence for user strategies
  validate_strategy_code — AST-based safety + correctness checks
  find_similar_strategies — match user description to existing strategies
  build_and_test         — validate + load + backtest in one call
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional


from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()

STRATEGIES_DIR = Path.home() / ".trading_platform" / "strategies"

# Modules that user-generated strategy code is allowed to import
IMPORT_WHITELIST = {
    "pandas",
    "pd",
    "numpy",
    "np",
    "math",
    "analysis.technical",
    "analysis",
    "engine.backtest",
    "engine",
    "market.history",
    "market",  # for pairs strategies fetching other symbols
}

# Keywords for matching user descriptions to existing strategies
STRATEGY_KEYWORDS = {
    "rsi": ["rsi", "relative strength", "oversold", "overbought", "momentum"],
    "ma": [
        "moving average",
        "ema",
        "sma",
        "crossover",
        "cross",
        "golden cross",
        "death cross",
        "trend",
    ],
    "ema": ["ema", "exponential moving average"],
    "macd": ["macd", "signal line", "histogram", "convergence", "divergence"],
    "bollinger": ["bollinger", "bb", "bands", "squeeze", "standard deviation", "mean reversion"],
    "bb": ["bollinger", "bb"],
}


# ── Strategy Store ──────────────────────────────────────────


class StrategyStore:
    """Persistence layer for user-created strategies."""

    def __init__(self, base_dir: Path = STRATEGIES_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list_strategies(self) -> list[dict]:
        """List all saved strategies with metadata."""
        strategies = []
        for meta_file in sorted(self.base_dir.glob("*.json")):
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                meta["has_code"] = (self.base_dir / f"{meta_file.stem}.py").exists()
                strategies.append(meta)
            except Exception:
                pass
        return strategies

    def load_strategy(self, name: str):
        """Dynamically import a saved strategy and return an instance."""
        py_file = self.base_dir / f"{name}.py"
        if not py_file.exists():
            raise FileNotFoundError(f"Strategy '{name}' not found at {py_file}")

        spec = importlib.util.spec_from_file_location(f"user_strategy_{name}", str(py_file))
        module = importlib.util.module_from_spec(spec)

        # Provide access to the backtest module
        sys.modules[f"user_strategy_{name}"] = module
        spec.loader.exec_module(module)

        # Find the Strategy subclass in the module
        from engine.backtest import Strategy

        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy:
                # Load parameters from metadata if available
                meta = self.get_metadata(name)
                params = meta.get("parameters", {}) if meta else {}
                try:
                    return obj(**params)
                except TypeError:
                    return obj()

        raise RuntimeError(f"No Strategy subclass found in {py_file}")

    def get_metadata(self, name: str) -> Optional[dict]:
        """Load metadata JSON for a strategy."""
        meta_file = self.base_dir / f"{name}.json"
        if not meta_file.exists():
            return None
        try:
            with open(meta_file) as f:
                return json.load(f)
        except Exception:
            return None

    def save_strategy(self, name: str, code: str, metadata: dict) -> Path:
        """Save strategy code and metadata."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

        py_file = self.base_dir / f"{name}.py"
        meta_file = self.base_dir / f"{name}.json"

        py_file.write_text(code)

        metadata.setdefault("name", name)
        metadata.setdefault("created", datetime.now().isoformat())
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        return py_file

    def update_metadata(self, name: str, updates: dict) -> None:
        """Merge updates into existing metadata."""
        meta = self.get_metadata(name) or {"name": name}
        meta.update(updates)
        meta_file = self.base_dir / f"{name}.json"
        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=2, default=str)

    def delete_strategy(self, name: str) -> bool:
        """Delete strategy files. Returns True if something was deleted."""
        deleted = False
        for ext in (".py", ".json"):
            path = self.base_dir / f"{name}{ext}"
            if path.exists():
                path.unlink()
                deleted = True
        return deleted

    def get_code(self, name: str) -> Optional[str]:
        """Return the raw Python code for a strategy."""
        py_file = self.base_dir / f"{name}.py"
        if py_file.exists():
            return py_file.read_text()
        return None


# Singleton
strategy_store = StrategyStore()


# ── Code Validation ─────────────────────────────────────────


def validate_strategy_code(code: str) -> tuple[bool, str]:
    """
    Validate LLM-generated strategy code for safety and correctness.

    Checks (all static AST analysis — code is NEVER executed here):
      1. Valid Python syntax (ast.parse)
      2. Contains a class subclassing Strategy with generate_signals method
      3. Only imports from whitelisted modules (pandas, numpy, math, analysis.*, engine.backtest)
      4. No dangerous builtins (exec, eval, open, __import__, ...) or dunder escapes

    Returns:
        (True, "") on success, (False, "error description") on failure.
    """
    # 1. Syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error on line {e.lineno}: {e.msg}"

    # 2. Find Strategy subclass with generate_signals
    found_class = False
    found_method = False
    class_name = None

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it has a base that looks like Strategy
            for base in node.bases:
                base_name = ""
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name == "Strategy":
                    found_class = True
                    class_name = node.name
                    # Check for generate_signals method
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if item.name == "generate_signals":
                                found_method = True

    if not found_class:
        return False, "No class subclassing Strategy found. Must have: class MyStrategy(Strategy):"
    if not found_method:
        return False, f"Class {class_name} is missing the generate_signals(self, df) method."

    # 3. Import whitelist check
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in IMPORT_WHITELIST:
                    return (
                        False,
                        f"Forbidden import: '{alias.name}'. Only allowed: pandas, numpy, math, analysis.technical, engine.backtest",
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root not in IMPORT_WHITELIST:
                    return (
                        False,
                        f"Forbidden import: 'from {node.module}'. Only allowed: pandas, numpy, math, analysis.technical, engine.backtest",
                    )

    # 4. Dangerous builtin / dunder access check
    _DANGEROUS_BUILTINS = {
        "exec",
        "eval",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "vars",
        "dir",
        "globals",
        "locals",
        "breakpoint",
    }
    _DANGEROUS_DUNDERS = {
        "__builtins__",
        "__globals__",
        "__locals__",
        "__class__",
        "__bases__",
        "__subclasses__",
        "__import__",
        "__code__",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_BUILTINS:
                return False, f"Forbidden call: '{node.func.id}()' is not allowed in strategy code."
        if isinstance(node, ast.Attribute) and node.attr in _DANGEROUS_DUNDERS:
            return (
                False,
                f"Forbidden attribute access: '{node.attr}' is not allowed in strategy code.",
            )
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in _DANGEROUS_DUNDERS:
                return (
                    False,
                    f"Forbidden string literal: '{node.value}' may not appear in strategy code.",
                )

    return True, ""


# ── Similar Strategy Finder ─────────────────────────────────


def find_similar_strategies(description: str) -> list[dict]:
    """
    Find strategies similar to a plain-English description.
    Matches against built-in strategies and saved user strategies.
    """
    desc_lower = description.lower()
    results = []

    # Check built-in strategies
    for name, keywords in STRATEGY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score > 0:
            results.append(
                {
                    "name": name,
                    "type": "builtin",
                    "match_score": score,
                    "description": _builtin_description(name),
                }
            )

    # Check saved user strategies
    for meta in strategy_store.list_strategies():
        user_desc = meta.get("description", "").lower()
        # Simple word overlap
        desc_words = set(desc_lower.split())
        user_words = set(user_desc.split())
        overlap = len(desc_words & user_words)
        if overlap >= 2:
            results.append(
                {
                    "name": meta["name"],
                    "type": "saved",
                    "match_score": overlap,
                    "description": meta.get("description", ""),
                }
            )

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:5]


def _builtin_description(name: str) -> str:
    """Human-readable description for built-in strategies."""
    descs = {
        "rsi": "RSI overbought/oversold: Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought). Mean reversion strategy.",
        "ma": "EMA Crossover: Buy when fast EMA crosses above slow EMA, sell on cross below. Trend following.",
        "ema": "Same as MA — EMA crossover trend following strategy.",
        "macd": "MACD Signal: Buy when MACD histogram turns positive, sell when it turns negative. Momentum strategy.",
        "bollinger": "Bollinger Bands: Buy at lower band (oversold), sell at upper band (overbought). Mean reversion.",
        "bb": "Bollinger Bands: Buy at lower band, sell at upper band.",
    }
    return descs.get(name, "")


# ── Build and Test ──────────────────────────────────────────


def build_and_test(
    code: str,
    symbol: str = "RELIANCE",
    period: str = "1y",
    capital: float = 100000,
) -> tuple:
    """
    Validate strategy code, load it, and run a backtest.

    Returns:
        (strategy_instance, backtest_result) on success.
        Raises ValueError with error message on failure.
    """
    ok, error = validate_strategy_code(code)
    if not ok:
        raise ValueError(error)

    # Write to a temp file and load
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        spec = importlib.util.spec_from_file_location("_tmp_strategy", tmp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        from engine.backtest import Strategy, Backtester

        strategy = None
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy:
                try:
                    strategy = obj()
                except TypeError:
                    strategy = obj()
                break

        if not strategy:
            raise ValueError("No Strategy subclass found in generated code.")

        bt = Backtester(symbol=symbol, period=period, capital=capital)
        result = bt.run(strategy)
        return strategy, result

    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ── Extract Strategy from LLM Response ──────────────────────

COMPLETION_MARKER = "%%%STRATEGY_COMPLETE%%%"


def extract_strategy_payload(response: str) -> Optional[dict]:
    """
    Extract strategy code and metadata from an LLM response
    containing the %%%STRATEGY_COMPLETE%%% marker.

    Returns dict with keys: code, name, description, symbol, parameters
    or None if marker not found.
    """
    if COMPLETION_MARKER not in response:
        return None

    # Find JSON after the marker
    idx = response.index(COMPLETION_MARKER) + len(COMPLETION_MARKER)
    rest = response[idx:].strip()

    # Try to parse as JSON
    try:
        # Find JSON object boundaries
        start = rest.index("{")
        depth = 0
        end = start
        for i, ch in enumerate(rest[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        payload = json.loads(rest[start:end])
        return payload
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: try to extract code from markdown code block
    code_match = re.search(r"```python\s*\n(.*?)```", rest, re.DOTALL)
    if not code_match:
        code_match = re.search(r"```\s*\n(.*?)```", rest, re.DOTALL)

    if code_match:
        return {
            "code": code_match.group(1).strip(),
            "name": "custom_strategy",
            "description": "User-defined strategy",
            "symbol": "RELIANCE",
            "parameters": {},
        }

    # Last resort: check if the rest looks like Python code directly
    if "class " in rest and "generate_signals" in rest:
        # Extract up to the end of the class
        lines = rest.split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if (
                line.strip().startswith("from ")
                or line.strip().startswith("import ")
                or line.strip().startswith("class ")
            ):
                in_code = True
            if in_code:
                code_lines.append(line)
        if code_lines:
            return {
                "code": "\n".join(code_lines),
                "name": "custom_strategy",
                "description": "User-defined strategy",
                "symbol": "RELIANCE",
                "parameters": {},
            }

    return None


# ── Display Helpers ─────────────────────────────────────────


def print_strategy_list(strategies: list[dict]) -> None:
    """Print a Rich table of saved strategies."""
    if not strategies:
        console.print(
            "[dim]No saved strategies. Use [bold]strategy new[/bold] to create one.[/dim]"
        )
        return

    table = Table(title="Saved Strategies", show_lines=False)
    table.add_column("Name", style="cyan bold")
    table.add_column("Description")
    table.add_column("Return", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Created", style="dim")

    for s in strategies:
        bt = s.get("last_backtest", {})
        ret = f"{bt.get('total_return', 0):+.1f}%" if bt else "-"
        sharpe = f"{bt.get('sharpe', 0):.2f}" if bt else "-"
        wr = f"{bt.get('win_rate', 0):.0f}%" if bt else "-"
        created = s.get("created", "")[:10]
        table.add_row(
            s.get("name", "?"),
            s.get("description", "")[:50],
            ret,
            sharpe,
            wr,
            created,
        )

    console.print(table)


def print_strategy_code(name: str, code: str, metadata: Optional[dict] = None) -> None:
    """Display strategy code with syntax highlighting."""
    if metadata:
        desc = metadata.get("description", "")
        params = metadata.get("parameters", {})
        console.print(f"\n[bold cyan]{name}[/bold cyan]")
        if desc:
            console.print(f"[dim]{desc}[/dim]")
        if params:
            console.print(f"[dim]Parameters: {params}[/dim]")
        console.print()

    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"Strategy: {name}", border_style="cyan"))
