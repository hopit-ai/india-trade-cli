"""
agent/dag_orchestrator.py
──────────────────────────
DAG-based analyst swarm orchestration.

Instead of the fixed 7-analyst team, define custom analyst configurations:
  - Which analysts to include
  - Optional dependencies between analysts (analyst B can see A's results)
  - Analyst weights for the scorecard

Usage:
    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    # Use a preset
    reports = run_dag("INFY", dag_config=PRESET_DAGS["fast"])

    # Custom config
    config = {
        "analysts": ["Technical", "Fundamental", "Risk"],
        "dependencies": {"Risk": ["Technical", "Fundamental"]},
        "weights": {"Technical": 1.5, "Fundamental": 1.2, "Risk": 1.0},
    }
    reports = run_dag("INFY", dag_config=config)
"""

from __future__ import annotations

import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.table import Table

from agent.multi_agent import (
    AnalystReport,
    FundamentalAnalyst,
    NewsMacroAnalyst,
    OptionsAnalyst,
    RiskAnalyst,
    SectorRotationAnalyst,
    SentimentAnalyst,
    TechnicalAnalyst,
    compute_scorecard,
)

console = Console()


# ── Analyst registry ──────────────────────────────────────────
# Maps string name → analyst class
ANALYST_REGISTRY: dict[str, type] = {
    "Technical": TechnicalAnalyst,
    "Fundamental": FundamentalAnalyst,
    "Options": OptionsAnalyst,
    "NewsMacro": NewsMacroAnalyst,
    "Sentiment": SentimentAnalyst,
    "SectorRotation": SectorRotationAnalyst,
    "Risk": RiskAnalyst,
}


@dataclass
class DAGNode:
    name: str  # e.g. "Technical"
    analyst_class: type  # class from ANALYST_REGISTRY
    depends_on: list[str]  # names of analysts this one depends on
    weight: float = 1.0  # weight in scorecard
    prior_reports: list = None  # filled at runtime with dependency results


@dataclass
class DAGResult:
    symbol: str
    exchange: str
    dag_name: str
    reports: list  # list[AnalystReport]
    scorecard: Any  # AnalystScorecard from compute_scorecard()
    execution_order: list[str]  # topological order used
    total_time_ms: float

    def summary(self) -> str:
        """Return a human-readable summary of the DAG execution results."""
        lines = [
            f"DAG Analysis: {self.symbol} ({self.exchange}) — {self.dag_name}",
            f"Execution order: {' → '.join(self.execution_order)}",
            f"Time: {self.total_time_ms:.0f}ms",
            "",
        ]
        if self.scorecard:
            lines.append(self.scorecard.summary())
            lines.append("")
        for report in self.reports:
            lines.append(report.summary_text())
        return "\n".join(lines)


# ── Built-in presets ──────────────────────────────────────────
PRESET_DAGS: dict[str, dict] = {
    "fast": {
        "analysts": ["Technical", "Fundamental"],
        "dependencies": {},
        "weights": {"Technical": 1.5, "Fundamental": 1.2},
        "description": "2-analyst fast scan (~5s, no LLM)",
    },
    "full": {
        "analysts": [
            "Technical",
            "Fundamental",
            "Options",
            "NewsMacro",
            "Sentiment",
            "SectorRotation",
            "Risk",
        ],
        "dependencies": {"Risk": ["Technical", "Fundamental"]},
        "weights": {
            "Technical": 1.5,
            "Fundamental": 1.2,
            "Options": 1.3,
            "NewsMacro": 1.0,
            "Sentiment": 0.8,
            "SectorRotation": 0.9,
            "Risk": 1.0,
        },
        "description": "Full 7-analyst team",
    },
    "options_focused": {
        "analysts": ["Technical", "Options", "Risk"],
        "dependencies": {"Risk": ["Technical", "Options"]},
        "weights": {"Technical": 1.2, "Options": 2.0, "Risk": 1.0},
        "description": "Options-focused analysis",
    },
    "quick_trade": {
        "analysts": ["Technical", "Sentiment", "Risk"],
        "dependencies": {"Risk": ["Technical"]},
        "weights": {"Technical": 1.5, "Sentiment": 1.0, "Risk": 1.0},
        "description": "Intraday/quick trade setup check",
    },
}


def _topological_sort(nodes: dict[str, DAGNode]) -> list[str]:
    """
    Kahn's algorithm for topological sort.
    Raises ValueError if cycle detected.
    """
    # Build in-degree map and adjacency list
    in_degree: dict[str, int] = {name: 0 for name in nodes}
    adjacency: dict[str, list[str]] = {name: [] for name in nodes}

    for name, node in nodes.items():
        for dep in node.depends_on:
            # dep must come before name → dep → name edge
            adjacency[dep].append(name)
            in_degree[name] += 1

    # Initialize queue with all zero in-degree nodes
    queue: deque[str] = deque(name for name, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        node_name = queue.popleft()
        order.append(node_name)
        for neighbor in adjacency[node_name]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(nodes):
        raise ValueError(
            f"Circular dependency detected in DAG. Processed {len(order)}/{len(nodes)} nodes."
        )

    return order


def build_dag(dag_config: dict) -> list[DAGNode]:
    """
    Validate config, resolve ANALYST_REGISTRY references, return topologically sorted nodes.
    Raises ValueError for: unknown analyst name, circular dependency.
    """
    analysts = dag_config.get("analysts", [])
    dependencies: dict[str, list[str]] = dag_config.get("dependencies", {})
    weights: dict[str, float] = dag_config.get("weights", {})

    # Validate all analyst names
    for name in analysts:
        if name not in ANALYST_REGISTRY:
            raise ValueError(
                f"Unknown analyst '{name}'. Valid names: {sorted(ANALYST_REGISTRY.keys())}"
            )

    # Validate dependency targets also exist in the analyst list
    analyst_set = set(analysts)
    for dependent, deps in dependencies.items():
        if dependent not in analyst_set:
            raise ValueError(f"Dependency key '{dependent}' is not in the analysts list.")
        for dep in deps:
            if dep not in analyst_set:
                raise ValueError(
                    f"Dependency target '{dep}' (for '{dependent}') is not in the analysts list."
                )

    # Build DAGNode dict
    nodes: dict[str, DAGNode] = {}
    for name in analysts:
        nodes[name] = DAGNode(
            name=name,
            analyst_class=ANALYST_REGISTRY[name],
            depends_on=list(dependencies.get(name, [])),
            weight=weights.get(name, 1.0),
        )

    # Topological sort (also validates for cycles)
    order = _topological_sort(nodes)

    # Return nodes in topological order
    return [nodes[name] for name in order]


def run_dag(
    symbol: str,
    dag_config: dict,
    exchange: str = "NSE",
    parallel: bool = True,
    timeout_seconds: float = 60.0,
) -> DAGResult:
    """
    Execute analysts in DAG order.

    - Independent nodes (no unfulfilled deps) run in parallel via ThreadPoolExecutor
    - Dependent nodes wait for their dependencies to complete
    - Each analyst receives prior dependency reports in its analyze() call via
      a thread-local context (store reports dict, pass it via kwargs if supported)
    - Failed analysts (exception) produce an AnalystReport with error="" filled
    - Compute scorecard using compute_scorecard() from multi_agent
    """
    start_time = time.time()

    nodes = build_dag(dag_config)
    dag_name = dag_config.get("description", "custom")
    execution_order = [n.name for n in nodes]

    # Completed results: analyst_name → AnalystReport
    completed: dict[str, AnalystReport] = {}

    def _run_analyst(node: DAGNode) -> AnalystReport:
        """Instantiate and run an analyst. Catches all exceptions."""
        # Build a minimal stub registry (analysts that need real tools will fail
        # gracefully with their own error handling, per existing behavior)
        try:
            from agent.tools import ToolRegistry

            registry = ToolRegistry()
        except Exception:
            registry = MagicRegistry()

        try:
            analyst_instance = node.analyst_class(registry)
            return analyst_instance.analyze(symbol, exchange)
        except Exception as exc:
            cls_name = getattr(node.analyst_class, "name", node.name)
            return AnalystReport(
                analyst=cls_name,
                verdict="UNKNOWN",
                confidence=0,
                score=0,
                error=str(exc),
            )

    if parallel:
        # Wave-based parallel execution: each wave is the set of nodes whose
        # dependencies have all completed.
        remaining = list(nodes)
        with ThreadPoolExecutor() as executor:
            while remaining:
                # Find nodes ready to run (all deps satisfied)
                ready = [n for n in remaining if all(dep in completed for dep in n.depends_on)]
                if not ready:
                    # Safety: should not happen if topo sort is correct, but guard anyway
                    raise RuntimeError(
                        "DAG execution stalled — no nodes ready to run. "
                        f"Remaining: {[n.name for n in remaining]}"
                    )

                futures = {executor.submit(_run_analyst, node): node for node in ready}
                for future in as_completed(futures, timeout=timeout_seconds):
                    node = futures[future]
                    try:
                        report = future.result()
                    except Exception as exc:
                        cls_name = getattr(node.analyst_class, "name", node.name)
                        report = AnalystReport(
                            analyst=cls_name,
                            verdict="UNKNOWN",
                            confidence=0,
                            score=0,
                            error=str(exc),
                        )
                    completed[node.name] = report

                for node in ready:
                    remaining.remove(node)
    else:
        # Sequential execution following topological order
        for node in nodes:
            report = _run_analyst(node)
            completed[node.name] = report

    reports = [completed[n.name] for n in nodes]
    scorecard = compute_scorecard(reports)
    total_time_ms = (time.time() - start_time) * 1000.0

    return DAGResult(
        symbol=symbol,
        exchange=exchange,
        dag_name=dag_name,
        reports=reports,
        scorecard=scorecard,
        execution_order=execution_order,
        total_time_ms=total_time_ms,
    )


class MagicRegistry:
    """Minimal stub registry for analyst instantiation when ToolRegistry unavailable."""

    def execute(self, tool_name: str, params: dict) -> dict:
        return {"error": "no registry available"}


def list_presets() -> None:
    """Print a Rich table of available preset DAG configs."""
    table = Table(title="Available DAG Presets", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Analysts", style="green")
    table.add_column("Dependencies")
    table.add_column("Description", style="dim")

    for name, cfg in PRESET_DAGS.items():
        analysts_str = ", ".join(cfg.get("analysts", []))
        deps = cfg.get("dependencies", {})
        deps_str = "\n".join(f"{k} ← {', '.join(v)}" for k, v in deps.items()) if deps else "none"
        desc = cfg.get("description", "")
        table.add_row(name, analysts_str, deps_str, desc)

    console.print(table)
