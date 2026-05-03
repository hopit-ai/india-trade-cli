"""
Tests for OpenClaw manifest completeness and validity (#125).

Validates:
- All skills have valid endpoint (path) field
- No duplicate skill names
- persona and debate skills are present (added in #166)
"""

from __future__ import annotations

from web.openclaw import MANIFEST


REQUIRED_FIELDS = {"name", "path", "method", "description", "input_schema", "output_description"}


class TestAllSkillsHaveValidEndpoint:
    def test_all_skills_have_path_field(self):
        for skill in MANIFEST["skills"]:
            assert "path" in skill, f"Skill '{skill.get('name', '?')}' missing 'path'"

    def test_all_paths_are_non_empty_strings(self):
        for skill in MANIFEST["skills"]:
            path = skill.get("path", "")
            assert isinstance(path, str) and len(path) > 0, (
                f"Skill '{skill['name']}' has invalid path: {path!r}"
            )

    def test_all_paths_start_with_slash(self):
        for skill in MANIFEST["skills"]:
            path = skill.get("path", "")
            assert path.startswith("/"), (
                f"Skill '{skill['name']}' path '{path}' does not start with '/'"
            )

    def test_all_paths_contain_skills(self):
        """All skill paths should contain /skills/ prefix."""
        for skill in MANIFEST["skills"]:
            path = skill.get("path", "")
            assert "/skills/" in path, (
                f"Skill '{skill['name']}' path '{path}' should contain '/skills/'"
            )

    def test_all_skills_have_required_fields(self):
        for skill in MANIFEST["skills"]:
            missing = REQUIRED_FIELDS - set(skill.keys())
            assert missing == set(), f"Skill '{skill.get('name', '?')}' missing: {missing}"


class TestNoDuplicateSkillNames:
    def test_no_duplicate_names(self):
        names = [s["name"] for s in MANIFEST["skills"]]
        duplicates = {n for n in names if names.count(n) > 1}
        assert duplicates == set(), f"Duplicate skill names found: {duplicates}"

    def test_no_duplicate_paths(self):
        paths = [s["path"] for s in MANIFEST["skills"]]
        duplicates = {p for p in paths if paths.count(p) > 1}
        assert duplicates == set(), f"Duplicate skill paths found: {duplicates}"


class TestPersonaAndDebateSkillsAdded:
    """New skills from #166 should be in the manifest."""

    def _skill_names(self) -> set[str]:
        return {s["name"] for s in MANIFEST["skills"]}

    def test_persona_skill_present(self):
        assert "persona" in self._skill_names(), "persona skill missing from manifest"

    def test_debate_skill_present(self):
        assert "debate" in self._skill_names(), "debate skill missing from manifest"

    def test_persona_skill_has_valid_path(self):
        skill = next(s for s in MANIFEST["skills"] if s["name"] == "persona")
        assert skill["path"] == "/skills/persona"

    def test_debate_skill_has_valid_path(self):
        skill = next(s for s in MANIFEST["skills"] if s["name"] == "debate")
        assert skill["path"] == "/skills/debate"

    def test_persona_skill_requires_persona_id_and_symbol(self):
        skill = next(s for s in MANIFEST["skills"] if s["name"] == "persona")
        required = skill["input_schema"].get("required", [])
        assert "persona_id" in required
        assert "symbol" in required

    def test_debate_skill_requires_symbol(self):
        skill = next(s for s in MANIFEST["skills"] if s["name"] == "debate")
        required = skill["input_schema"].get("required", [])
        assert "symbol" in required


class TestAllExpectedSkillsPresent:
    """Regression test — all known skills must be in manifest."""

    EXPECTED_SKILLS = {
        # Original
        "quote",
        "options_chain",
        "flows",
        "earnings",
        "macro",
        "deals",
        "backtest",
        "pairs",
        "analyze",
        "deep_analyze",
        "chat",
        "alerts_add",
        "alerts_list",
        "alerts_remove",
        "alerts_check",
        "chat_reset",
        "morning_brief",
        # Added in earlier pass (#125)
        "iv_smile",
        "gex",
        "risk_report",
        "strategy",
        "whatif",
        "greeks",
        "oi",
        "scan",
        "patterns",
        "delta_hedge",
        "drift",
        "memory",
        "memory_query",
        # Added in #166
        "persona",
        "debate",
    }

    def test_all_expected_skills_present(self):
        present = {s["name"] for s in MANIFEST["skills"]}
        missing = self.EXPECTED_SKILLS - present
        assert missing == set(), f"Expected skills missing from manifest: {missing}"

    def test_skill_count_at_least_expected(self):
        assert len(MANIFEST["skills"]) >= len(self.EXPECTED_SKILLS), (
            f"Expected at least {len(self.EXPECTED_SKILLS)} skills, got {len(MANIFEST['skills'])}"
        )
