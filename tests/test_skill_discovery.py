"""
Tests for skill auto-discovery (#187).
"""

from __future__ import annotations

import pytest
from pathlib import Path


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def skills_dir(tmp_path):
    """Return a temp directory for test skill files."""
    d = tmp_path / "skills"
    d.mkdir()
    return d


def _write_skill(skills_dir: Path, filename: str, content: str) -> Path:
    """Write a skill file into the skills dir and return its path."""
    p = skills_dir / filename
    p.write_text(content, encoding="utf-8")
    return p


VALID_SKILL_CODE = """\
def _my_fn(symbol: str) -> dict:
    return {"symbol": symbol, "result": "ok"}

SKILL = {
    "name": "test_skill",
    "description": "A test skill",
    "parameters": {
        "type": "object",
        "properties": {"symbol": {"type": "string"}},
        "required": ["symbol"],
    },
    "fn": _my_fn,
    "is_read_only": True,
}
"""


# ── discover_skills tests ─────────────────────────────────────


class TestDiscoverSkills:
    def test_finds_python_files(self, skills_dir):
        from engine.skill_loader import discover_skills

        _write_skill(skills_dir, "my_skill.py", VALID_SKILL_CODE)
        found = discover_skills(extra_dirs=[skills_dir])
        assert any(p.name == "my_skill.py" for p in found)

    def test_excludes_example_prefix(self, skills_dir):
        from engine.skill_loader import discover_skills

        _write_skill(skills_dir, "example_demo.py", VALID_SKILL_CODE)
        found = discover_skills(extra_dirs=[skills_dir])
        assert not any(p.name == "example_demo.py" for p in found)

    def test_excludes_underscore_prefix(self, skills_dir):
        from engine.skill_loader import discover_skills

        _write_skill(skills_dir, "_internal.py", VALID_SKILL_CODE)
        found = discover_skills(extra_dirs=[skills_dir])
        assert not any(p.name == "_internal.py" for p in found)

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        from engine.skill_loader import discover_skills

        missing = tmp_path / "nonexistent"
        found = discover_skills(extra_dirs=[missing])
        assert found == []

    def test_multiple_files_found(self, skills_dir):
        from engine.skill_loader import discover_skills

        _write_skill(skills_dir, "skill_a.py", VALID_SKILL_CODE)
        _write_skill(skills_dir, "skill_b.py", VALID_SKILL_CODE)
        found = discover_skills(extra_dirs=[skills_dir])
        names = [p.name for p in found]
        assert "skill_a.py" in names
        assert "skill_b.py" in names


# ── load_skill tests ──────────────────────────────────────────


class TestLoadSkill:
    def test_loads_valid_skill(self, skills_dir):
        from engine.skill_loader import load_skill

        path = _write_skill(skills_dir, "valid_skill.py", VALID_SKILL_CODE)
        skill = load_skill(path)
        assert skill is not None
        assert skill["name"] == "test_skill"
        assert callable(skill["fn"])

    def test_returns_none_for_missing_skill_dict(self, skills_dir):
        from engine.skill_loader import load_skill

        path = _write_skill(skills_dir, "no_skill.py", "# no SKILL dict here\n")
        skill = load_skill(path)
        assert skill is None

    def test_returns_none_for_missing_required_key(self, skills_dir):
        from engine.skill_loader import load_skill

        code = """\
def fn(): pass
SKILL = {
    "name": "incomplete",
    "description": "Missing parameters and fn",
    # "parameters" missing
    # "fn" missing
}
"""
        path = _write_skill(skills_dir, "incomplete.py", code)
        skill = load_skill(path)
        assert skill is None

    def test_returns_none_for_non_callable_fn(self, skills_dir):
        from engine.skill_loader import load_skill

        code = """\
SKILL = {
    "name": "bad_fn",
    "description": "fn is not callable",
    "parameters": {"type": "object", "properties": {}},
    "fn": "not_a_function",
}
"""
        path = _write_skill(skills_dir, "bad_fn.py", code)
        skill = load_skill(path)
        assert skill is None

    def test_returns_none_for_syntax_error(self, skills_dir):
        from engine.skill_loader import load_skill

        path = _write_skill(skills_dir, "syntax_error.py", "def broken(: pass\n")
        skill = load_skill(path)
        assert skill is None

    def test_skill_fn_is_callable_and_works(self, skills_dir):
        from engine.skill_loader import load_skill

        path = _write_skill(skills_dir, "runnable.py", VALID_SKILL_CODE)
        skill = load_skill(path)
        assert skill is not None
        result = skill["fn"]("INFY")
        assert result["symbol"] == "INFY"


# ── auto_register_skills tests ────────────────────────────────


class TestAutoRegisterSkills:
    def _make_registry(self):
        """Create a real ToolRegistry for testing."""
        from agent.tools import ToolRegistry

        return ToolRegistry()

    def test_registers_valid_skill(self, skills_dir):
        from engine.skill_loader import auto_register_skills

        _write_skill(skills_dir, "register_me.py", VALID_SKILL_CODE)
        registry = self._make_registry()
        registered = auto_register_skills(registry, extra_dirs=[skills_dir])
        assert "test_skill" in registered

    def test_skill_appears_in_registry(self, skills_dir):
        from engine.skill_loader import auto_register_skills

        _write_skill(skills_dir, "in_registry.py", VALID_SKILL_CODE)
        registry = self._make_registry()
        auto_register_skills(registry, extra_dirs=[skills_dir])
        assert "test_skill" in registry._tools

    def test_empty_dir_returns_empty_list(self, skills_dir):
        from engine.skill_loader import auto_register_skills

        registry = self._make_registry()
        registered = auto_register_skills(registry, extra_dirs=[skills_dir])
        assert registered == []

    def test_skips_invalid_skills_gracefully(self, skills_dir):
        from engine.skill_loader import auto_register_skills

        _write_skill(skills_dir, "bad_skill.py", "SKILL = 'not a dict'")
        _write_skill(skills_dir, "good_skill.py", VALID_SKILL_CODE)
        registry = self._make_registry()
        registered = auto_register_skills(registry, extra_dirs=[skills_dir])
        # Only good_skill (test_skill) should be registered
        assert "test_skill" in registered
        assert len(registered) == 1

    def test_registered_skill_is_callable_via_registry(self, skills_dir):
        from engine.skill_loader import auto_register_skills

        _write_skill(skills_dir, "exec_skill.py", VALID_SKILL_CODE)
        registry = self._make_registry()
        auto_register_skills(registry, extra_dirs=[skills_dir])
        result = registry.execute("test_skill", {"symbol": "TCS"})
        assert result.get("symbol") == "TCS"


# ── example skill file test ───────────────────────────────────


class TestExampleSkillFile:
    def test_example_skill_is_excluded_from_discover(self):
        """The project-level example_skill.py must NOT be auto-discovered."""
        from engine.skill_loader import discover_skills

        found = discover_skills()  # default dirs only
        names = [p.name for p in found]
        assert "example_skill.py" not in names

    def test_example_skill_loads_as_valid_skill(self, tmp_path):
        """example_skill.py is a valid skill file when loaded directly."""
        from engine.skill_loader import load_skill

        example_path = Path(__file__).parent.parent / "skills" / "example_skill.py"
        if not example_path.exists():
            pytest.skip("example_skill.py not found")

        skill = load_skill(example_path)
        assert skill is not None
        assert skill["name"] == "example_sector_news"
        assert callable(skill["fn"])
