# Spec: Skill Auto-discovery (#187)

## Problem
Adding new analysis tools requires editing `agent/tools.py` and rebuilding.
Power users and developers want to drop a Python file into a `skills/` directory
and have it automatically available in the CLI — no core-code changes.

## Solution
`engine/skill_loader.py` with three public functions:

- `discover_skills(extra_dirs=None) -> list[Path]`
  — scans `skills/` (project-level) and `~/.trading_platform/skills/` (user-level)
  — excludes files starting with `_` or `example_` (templates)

- `load_skill(path) -> dict | None`
  — imports the Python file, reads the `SKILL` dict
  — validates required keys: `name`, `description`, `parameters`, `fn`
  — returns None (with stderr warning) on any error

- `auto_register_skills(registry, extra_dirs=None) -> list[str]`
  — calls discover + load + ToolRegistry.register for each valid skill
  — returns list of successfully registered skill names

### Skill file convention
Each skill file exports a `SKILL` dict with keys:
`name`, `description`, `parameters` (JSON Schema), `fn`, optional flags.

### `skills/example_skill.py`
Documented example showing the expected structure. Prefixed with `example_`
so it is excluded from auto-loading.

### Startup integration
`auto_register_skills()` called in `run_repl()` after prompt setup.
Failures are silently swallowed — skill loading never blocks startup.

## Tests
`tests/test_skill_discovery.py`
