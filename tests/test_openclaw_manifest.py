"""
Tests for OpenClaw manifest completeness (#125).
"""

from __future__ import annotations

from web.openclaw import MANIFEST


REQUIRED_SKILL_FIELDS = {
    "name",
    "path",
    "method",
    "description",
    "input_schema",
    "output_description",
}

# All skills that should be present (name field matches)
EXPECTED_SKILLS = {
    # Pre-existing
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
    # Newly added (#125)
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
}


class TestManifestStructure:
    def test_manifest_has_required_top_level_keys(self):
        assert "name" in MANIFEST
        assert "description" in MANIFEST
        assert "version" in MANIFEST
        assert "skills" in MANIFEST

    def test_skills_is_list(self):
        assert isinstance(MANIFEST["skills"], list)

    def test_each_skill_has_required_fields(self):
        for skill in MANIFEST["skills"]:
            missing = REQUIRED_SKILL_FIELDS - set(skill.keys())
            assert missing == set(), f"Skill '{skill.get('name', '?')}' missing fields: {missing}"

    def test_each_skill_method_is_post(self):
        for skill in MANIFEST["skills"]:
            assert skill["method"] == "POST", (
                f"Skill '{skill['name']}' has method {skill['method']}"
            )

    def test_each_skill_path_starts_with_slash(self):
        for skill in MANIFEST["skills"]:
            assert skill["path"].startswith("/"), f"Path for '{skill['name']}' doesn't start with /"

    def test_each_skill_input_schema_has_type(self):
        for skill in MANIFEST["skills"]:
            schema = skill["input_schema"]
            assert "type" in schema, f"Skill '{skill['name']}' input_schema missing 'type'"
            assert "properties" in schema, (
                f"Skill '{skill['name']}' input_schema missing 'properties'"
            )


class TestMissingSkillsAdded:
    def _skill_names(self) -> set[str]:
        return {s["name"] for s in MANIFEST["skills"]}

    def test_iv_smile_present(self):
        assert "iv_smile" in self._skill_names()

    def test_gex_present(self):
        assert "gex" in self._skill_names()

    def test_risk_report_present(self):
        assert "risk_report" in self._skill_names()

    def test_strategy_present(self):
        assert "strategy" in self._skill_names()

    def test_whatif_present(self):
        assert "whatif" in self._skill_names()

    def test_greeks_present(self):
        assert "greeks" in self._skill_names()

    def test_oi_present(self):
        assert "oi" in self._skill_names()

    def test_scan_present(self):
        assert "scan" in self._skill_names()

    def test_patterns_present(self):
        assert "patterns" in self._skill_names()

    def test_delta_hedge_present(self):
        assert "delta_hedge" in self._skill_names()

    def test_drift_present(self):
        assert "drift" in self._skill_names()

    def test_memory_present(self):
        assert "memory" in self._skill_names()

    def test_memory_query_present(self):
        assert "memory_query" in self._skill_names()

    def test_all_expected_skills_present(self):
        present = self._skill_names()
        missing = EXPECTED_SKILLS - present
        assert missing == set(), f"Missing skills in manifest: {missing}"

    def test_no_duplicate_names(self):
        names = [s["name"] for s in MANIFEST["skills"]]
        assert len(names) == len(set(names)), (
            f"Duplicate skill names: {set(n for n in names if names.count(n) > 1)}"
        )
