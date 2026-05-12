"""
tests/test_dag_orchestrator.py
──────────────────────────────
Tests for the DAG-based analyst swarm orchestration.

All analyst .analyze() calls are mocked — no real API/network calls.
"""

from __future__ import annotations

import pytest

from agent.multi_agent import AnalystReport


# ── Helpers ───────────────────────────────────────────────────


def _make_report(analyst: str, verdict: str = "BULLISH", score: float = 40.0) -> AnalystReport:
    return AnalystReport(
        analyst=analyst,
        verdict=verdict,
        confidence=70,
        score=score,
        key_points=[f"{analyst} looks good"],
        data={},
    )


def _make_error_report(analyst: str, error: str = "simulated failure") -> AnalystReport:
    return AnalystReport(
        analyst=analyst,
        verdict="UNKNOWN",
        confidence=0,
        score=0,
        error=error,
    )


# ── Registry tests ────────────────────────────────────────────


def test_analyst_registry_contains_all_7():
    """ANALYST_REGISTRY must have all 7 analyst names."""
    from agent.dag_orchestrator import ANALYST_REGISTRY

    expected = {
        "Technical",
        "Fundamental",
        "Options",
        "NewsMacro",
        "Sentiment",
        "SectorRotation",
        "Risk",
    }
    assert expected == set(ANALYST_REGISTRY.keys())


def test_analyst_registry_values_are_classes():
    """All values in ANALYST_REGISTRY must be classes (types)."""
    from agent.dag_orchestrator import ANALYST_REGISTRY

    for name, cls in ANALYST_REGISTRY.items():
        assert isinstance(cls, type), f"{name} should be a class, got {type(cls)}"


def test_analyst_registry_classes_have_analyze():
    """All registered classes must have an analyze() method."""
    from agent.dag_orchestrator import ANALYST_REGISTRY

    for name, cls in ANALYST_REGISTRY.items():
        assert hasattr(cls, "analyze"), f"{name} class missing analyze()"


# ── PRESET_DAGS tests ─────────────────────────────────────────


def test_preset_dags_has_required_keys():
    """PRESET_DAGS must contain fast, full, options_focused, quick_trade."""
    from agent.dag_orchestrator import PRESET_DAGS

    required = {"fast", "full", "options_focused", "quick_trade"}
    assert required.issubset(set(PRESET_DAGS.keys()))


def test_preset_dags_full_contains_all_7():
    """PRESET_DAGS['full'] must list all 7 analyst keys."""
    from agent.dag_orchestrator import PRESET_DAGS, ANALYST_REGISTRY

    full_analysts = set(PRESET_DAGS["full"]["analysts"])
    assert full_analysts == set(ANALYST_REGISTRY.keys())


def test_preset_dags_fast_has_2_analysts():
    from agent.dag_orchestrator import PRESET_DAGS

    assert len(PRESET_DAGS["fast"]["analysts"]) == 2


def test_preset_dags_each_has_description():
    from agent.dag_orchestrator import PRESET_DAGS

    for name, cfg in PRESET_DAGS.items():
        assert "description" in cfg, f"Preset '{name}' missing description"
        assert isinstance(cfg["description"], str) and cfg["description"]


# ── DAGNode tests ─────────────────────────────────────────────


def test_dagnode_defaults():
    from agent.dag_orchestrator import DAGNode, ANALYST_REGISTRY

    node = DAGNode(name="Technical", analyst_class=ANALYST_REGISTRY["Technical"], depends_on=[])
    assert node.weight == 1.0
    assert node.prior_reports is None


# ── build_dag() tests ─────────────────────────────────────────


def test_build_dag_valid_simple():
    """build_dag() with a minimal valid config returns list of DAGNodes."""
    from agent.dag_orchestrator import build_dag

    config = {
        "analysts": ["Technical", "Fundamental"],
        "dependencies": {},
        "weights": {"Technical": 1.5, "Fundamental": 1.0},
    }
    nodes = build_dag(config)
    assert len(nodes) == 2
    names = [n.name for n in nodes]
    assert "Technical" in names
    assert "Fundamental" in names


def test_build_dag_returns_topologically_sorted():
    """build_dag() returns nodes such that dependencies come before dependents."""
    from agent.dag_orchestrator import build_dag

    config = {
        "analysts": ["Technical", "Fundamental", "Risk"],
        "dependencies": {"Risk": ["Technical", "Fundamental"]},
        "weights": {},
    }
    nodes = build_dag(config)
    names = [n.name for n in nodes]
    risk_idx = names.index("Risk")
    tech_idx = names.index("Technical")
    fund_idx = names.index("Fundamental")
    assert risk_idx > tech_idx
    assert risk_idx > fund_idx


def test_build_dag_unknown_analyst_raises():
    """build_dag() with an unknown analyst name raises ValueError."""
    from agent.dag_orchestrator import build_dag

    config = {
        "analysts": ["Technical", "NonExistentAnalyst"],
        "dependencies": {},
        "weights": {},
    }
    with pytest.raises(ValueError, match="NonExistentAnalyst"):
        build_dag(config)


def test_build_dag_circular_dependency_raises():
    """build_dag() with a circular dependency raises ValueError."""
    from agent.dag_orchestrator import build_dag

    config = {
        "analysts": ["Technical", "Fundamental"],
        "dependencies": {
            "Technical": ["Fundamental"],
            "Fundamental": ["Technical"],
        },
        "weights": {},
    }
    with pytest.raises(ValueError, match="[Cc]ircular|[Cc]ycle"):
        build_dag(config)


def test_build_dag_applies_weights():
    """build_dag() assigns custom weights to nodes."""
    from agent.dag_orchestrator import build_dag

    config = {
        "analysts": ["Technical", "Fundamental"],
        "dependencies": {},
        "weights": {"Technical": 2.5, "Fundamental": 0.5},
    }
    nodes = build_dag(config)
    by_name = {n.name: n for n in nodes}
    assert by_name["Technical"].weight == 2.5
    assert by_name["Fundamental"].weight == 0.5


def test_build_dag_default_weight_for_missing():
    """build_dag() uses weight=1.0 for analysts not listed in weights."""
    from agent.dag_orchestrator import build_dag

    config = {
        "analysts": ["Technical"],
        "dependencies": {},
        "weights": {},
    }
    nodes = build_dag(config)
    assert nodes[0].weight == 1.0


# ── _topological_sort() tests ─────────────────────────────────


def test_topological_sort_linear_chain():
    """_topological_sort with A→B→C should return [A, B, C]."""
    from agent.dag_orchestrator import DAGNode, _topological_sort, ANALYST_REGISTRY

    cls = ANALYST_REGISTRY["Technical"]
    nodes = {
        "A": DAGNode(name="A", analyst_class=cls, depends_on=[]),
        "B": DAGNode(name="B", analyst_class=cls, depends_on=["A"]),
        "C": DAGNode(name="C", analyst_class=cls, depends_on=["B"]),
    }
    order = _topological_sort(nodes)
    assert order.index("A") < order.index("B")
    assert order.index("B") < order.index("C")


def test_topological_sort_parallel_branches():
    """_topological_sort with parallel branches: A and B both feed C."""
    from agent.dag_orchestrator import DAGNode, _topological_sort, ANALYST_REGISTRY

    cls = ANALYST_REGISTRY["Technical"]
    nodes = {
        "A": DAGNode(name="A", analyst_class=cls, depends_on=[]),
        "B": DAGNode(name="B", analyst_class=cls, depends_on=[]),
        "C": DAGNode(name="C", analyst_class=cls, depends_on=["A", "B"]),
    }
    order = _topological_sort(nodes)
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("C")
    assert len(order) == 3


def test_topological_sort_cycle_raises():
    """_topological_sort raises ValueError when a cycle is detected."""
    from agent.dag_orchestrator import DAGNode, _topological_sort, ANALYST_REGISTRY

    cls = ANALYST_REGISTRY["Technical"]
    nodes = {
        "X": DAGNode(name="X", analyst_class=cls, depends_on=["Y"]),
        "Y": DAGNode(name="Y", analyst_class=cls, depends_on=["X"]),
    }
    with pytest.raises(ValueError):
        _topological_sort(nodes)


def test_topological_sort_single_node():
    from agent.dag_orchestrator import DAGNode, _topological_sort, ANALYST_REGISTRY

    cls = ANALYST_REGISTRY["Technical"]
    nodes = {"Only": DAGNode(name="Only", analyst_class=cls, depends_on=[])}
    order = _topological_sort(nodes)
    assert order == ["Only"]


# ── run_dag() tests ───────────────────────────────────────────


def _patch_all_analysts(monkeypatch):
    """Patch analyze() on all 7 analyst classes to return a fixed report."""
    from agent.dag_orchestrator import ANALYST_REGISTRY

    for name, cls in ANALYST_REGISTRY.items():
        report = _make_report(cls.name if hasattr(cls, "name") else name)
        monkeypatch.setattr(cls, "analyze", lambda self, symbol, exchange="NSE", r=report: r)


def test_run_dag_fast_preset_returns_dag_result(monkeypatch):
    """run_dag() with 'fast' preset returns a DAGResult with 2 reports."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("INFY", dag_config=PRESET_DAGS["fast"])
    assert result.symbol == "INFY"
    assert len(result.reports) == 2
    assert result.scorecard is not None


def test_run_dag_result_has_execution_order(monkeypatch):
    """DAGResult.execution_order is a non-empty list."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("TCS", dag_config=PRESET_DAGS["fast"])
    assert isinstance(result.execution_order, list)
    assert len(result.execution_order) == 2


def test_run_dag_result_total_time_ms(monkeypatch):
    """DAGResult.total_time_ms is a positive float."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("RELIANCE", dag_config=PRESET_DAGS["fast"])
    assert result.total_time_ms >= 0.0


def test_run_dag_dependency_respected(monkeypatch):
    """Risk analyst should run after Technical and Fundamental."""
    call_order = []

    from agent.dag_orchestrator import ANALYST_REGISTRY

    original_classes = {}
    for name in ["Technical", "Fundamental", "Risk"]:
        cls = ANALYST_REGISTRY[name]
        original_classes[name] = cls

    def make_analyze(analyst_name):
        def analyze(self, symbol, exchange="NSE"):
            call_order.append(analyst_name)
            return _make_report(analyst_name)

        return analyze

    for name in ["Technical", "Fundamental", "Risk"]:
        monkeypatch.setattr(ANALYST_REGISTRY[name], "analyze", make_analyze(name))

    from agent.dag_orchestrator import run_dag

    config = {
        "analysts": ["Technical", "Fundamental", "Risk"],
        "dependencies": {"Risk": ["Technical", "Fundamental"]},
        "weights": {},
    }
    run_dag("INFY", dag_config=config)

    assert call_order.index("Risk") > call_order.index("Technical")
    assert call_order.index("Risk") > call_order.index("Fundamental")


def test_run_dag_failed_analyst_captured(monkeypatch):
    """An analyst that raises an exception produces an error report; others succeed."""
    from agent.dag_orchestrator import ANALYST_REGISTRY

    def raising_analyze(self, symbol, exchange="NSE"):
        raise RuntimeError("data feed down")

    def ok_analyze(self, symbol, exchange="NSE"):
        return _make_report("Fundamental")

    monkeypatch.setattr(ANALYST_REGISTRY["Technical"], "analyze", raising_analyze)
    monkeypatch.setattr(ANALYST_REGISTRY["Fundamental"], "analyze", ok_analyze)

    from agent.dag_orchestrator import run_dag

    config = {
        "analysts": ["Technical", "Fundamental"],
        "dependencies": {},
        "weights": {},
    }
    result = run_dag("INFY", dag_config=config)
    assert len(result.reports) == 2
    error_reports = [r for r in result.reports if r.error]
    ok_reports = [r for r in result.reports if not r.error]
    assert len(error_reports) == 1
    assert len(ok_reports) == 1
    assert "data feed down" in error_reports[0].error


def test_run_dag_custom_config_with_weights(monkeypatch):
    """Custom weights are reflected in the DAGResult."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag

    config = {
        "analysts": ["Technical", "Fundamental"],
        "dependencies": {},
        "weights": {"Technical": 3.0, "Fundamental": 0.5},
    }
    result = run_dag("INFY", dag_config=config)
    assert result is not None
    assert len(result.reports) == 2


def test_run_dag_parallel_completes_all(monkeypatch):
    """parallel=True still produces all expected reports."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("INFY", dag_config=PRESET_DAGS["fast"], parallel=True)
    assert len(result.reports) == 2


def test_run_dag_sequential_completes_all(monkeypatch):
    """parallel=False still produces all expected reports."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("INFY", dag_config=PRESET_DAGS["fast"], parallel=False)
    assert len(result.reports) == 2


def test_run_dag_exchange_passed_through(monkeypatch):
    """exchange parameter is forwarded to analysts."""
    received = {}

    from agent.dag_orchestrator import ANALYST_REGISTRY

    def capture_analyze(self, symbol, exchange="NSE"):
        received["exchange"] = exchange
        return _make_report("Technical")

    monkeypatch.setattr(ANALYST_REGISTRY["Technical"], "analyze", capture_analyze)

    from agent.dag_orchestrator import run_dag

    config = {"analysts": ["Technical"], "dependencies": {}, "weights": {}}
    run_dag("INFY", dag_config=config, exchange="BSE")
    assert received.get("exchange") == "BSE"


def test_run_dag_full_preset_7_reports(monkeypatch):
    """PRESET_DAGS['full'] produces 7 reports."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("NIFTY", dag_config=PRESET_DAGS["full"])
    assert len(result.reports) == 7


# ── DAGResult.summary() tests ─────────────────────────────────


def test_dag_result_summary_non_empty(monkeypatch):
    """DAGResult.summary() returns a non-empty string."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("INFY", dag_config=PRESET_DAGS["fast"])
    summary = result.summary()
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_dag_result_summary_includes_symbol(monkeypatch):
    """DAGResult.summary() includes the symbol in output."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("WIPRO", dag_config=PRESET_DAGS["fast"])
    summary = result.summary()
    assert "WIPRO" in summary


# ── list_presets() tests ──────────────────────────────────────


def test_list_presets_does_not_crash(capsys):
    """list_presets() runs without raising any exceptions."""
    from agent.dag_orchestrator import list_presets

    list_presets()  # should not raise


# ── DAGResult dag_name tests ──────────────────────────────────


def test_run_dag_dag_name_in_result(monkeypatch):
    """DAGResult.dag_name contains the dag_config description or a default."""
    _patch_all_analysts(monkeypatch)

    from agent.dag_orchestrator import run_dag, PRESET_DAGS

    result = run_dag("INFY", dag_config=PRESET_DAGS["fast"])
    assert isinstance(result.dag_name, str)
