"""
engine/skill_loader.py
──────────────────────
Auto-discovery of external skill plugins (#187).

Drop a Python file in the `skills/` directory at the project root (or in
~/.trading_platform/skills/ for user-level skills) and it will be auto-loaded
and registered in the ToolRegistry at startup.

Convention: each skill file must export a top-level `SKILL` dict:

    SKILL = {
        "name":        "my_custom_tool",         # tool name (snake_case)
        "description": "One-line what this does",
        "parameters":  {                          # JSON Schema
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE ticker"}
            },
            "required": ["symbol"],
        },
        "fn": my_function,                        # callable
        # Optional flags
        "is_read_only": True,
        "is_destructive": False,
    }

All other module-level code is executed when the file is imported (use sparingly).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional

# ── Search paths ────────────────────────────────���─────────────

_PROJECT_SKILLS_DIR = Path(__file__).parent.parent / "skills"
_USER_SKILLS_DIR = Path.home() / ".trading_platform" / "skills"


def discover_skills(extra_dirs: Optional[list[Path]] = None) -> list[Path]:
    """
    Return all Python skill files found in the search paths.

    Search order:
    1. Project-level  `skills/` (next to this repo)
    2. User-level     `~/.trading_platform/skills/`
    3. Any extra directories passed in

    Files starting with `_` or `example_` are excluded from auto-registration
    (they are treated as templates/documentation).
    """
    dirs = [_PROJECT_SKILLS_DIR, _USER_SKILLS_DIR]
    if extra_dirs:
        dirs.extend(extra_dirs)

    found: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for py_file in sorted(d.glob("*.py")):
            name = py_file.stem
            if name.startswith("_") or name.startswith("example_"):
                continue
            found.append(py_file)

    return found


def load_skill(path: Path) -> Optional[dict]:
    """
    Import a skill file and return its SKILL dict.

    Returns None (and prints a warning) if:
    - The file cannot be imported
    - The SKILL dict is missing or malformed
    - Required keys ('name', 'description', 'parameters', 'fn') are absent
    """
    module_name = f"_skill_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            _warn(f"Could not create module spec for {path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]

    except Exception as exc:
        _warn(f"Error importing skill {path.name}: {exc}")
        return None

    skill: Any = getattr(module, "SKILL", None)
    if skill is None:
        _warn(f"Skill file {path.name} has no SKILL dict — skipping")
        return None

    if not isinstance(skill, dict):
        _warn(f"Skill file {path.name}: SKILL must be a dict — skipping")
        return None

    required = {"name", "description", "parameters", "fn"}
    missing = required - set(skill.keys())
    if missing:
        _warn(f"Skill {path.name} missing required keys: {missing} — skipping")
        return None

    if not callable(skill["fn"]):
        _warn(f"Skill {path.name}: SKILL['fn'] is not callable — skipping")
        return None

    return skill


def auto_register_skills(registry: Any, extra_dirs: Optional[list[Path]] = None) -> list[str]:
    """
    Discover all skills and register them in the ToolRegistry.

    Returns the list of successfully registered skill names.
    """
    paths = discover_skills(extra_dirs=extra_dirs)
    registered: list[str] = []

    for path in paths:
        skill = load_skill(path)
        if skill is None:
            continue

        name = skill["name"]
        try:
            registry.register(
                name=name,
                description=skill["description"],
                parameters=skill["parameters"],
                fn=skill["fn"],
                is_read_only=skill.get("is_read_only", False),
                is_destructive=skill.get("is_destructive", False),
                is_concurrency_safe=skill.get("is_concurrency_safe", False),
            )
            registered.append(name)
        except Exception as exc:
            _warn(f"Failed to register skill '{name}': {exc}")

    return registered


# ── Internal helpers ───────────────────────��──────────────────


def _warn(msg: str) -> None:
    """Print a non-fatal warning to stderr."""
    import sys

    print(f"[skill-loader] WARNING: {msg}", file=sys.stderr)
