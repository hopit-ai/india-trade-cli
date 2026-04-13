"""
Tests for Docker deployment configuration (#162).
Validates that docker-compose files and Dockerfile are well-formed.
"""

from __future__ import annotations

import os
import pytest
from pathlib import Path

DOCKER_DIR = Path(__file__).parent.parent / "docker"


class TestDockerComposeConfig:
    def test_docker_compose_exists(self):
        assert (DOCKER_DIR / "docker-compose.yml").exists()

    def test_docker_compose_is_valid_yaml(self):
        import yaml

        content = (DOCKER_DIR / "docker-compose.yml").read_text()
        parsed = yaml.safe_load(content)
        assert parsed is not None

    def test_docker_compose_has_services(self):
        import yaml

        content = (DOCKER_DIR / "docker-compose.yml").read_text()
        parsed = yaml.safe_load(content)
        assert "services" in parsed

    def test_docker_compose_has_app_service(self):
        import yaml

        content = (DOCKER_DIR / "docker-compose.yml").read_text()
        parsed = yaml.safe_load(content)
        assert "app" in parsed["services"]

    def test_docker_compose_has_healthcheck(self):
        import yaml

        content = (DOCKER_DIR / "docker-compose.yml").read_text()
        parsed = yaml.safe_load(content)
        app_svc = parsed["services"]["app"]
        assert "healthcheck" in app_svc, "app service should have a healthcheck"

    def test_docker_compose_has_volumes(self):
        import yaml

        content = (DOCKER_DIR / "docker-compose.yml").read_text()
        parsed = yaml.safe_load(content)
        # Either top-level volumes or service-level volumes
        has_volumes = "volumes" in parsed or "volumes" in parsed["services"].get("app", {})
        assert has_volumes

    def test_docker_compose_exposes_port_8765(self):
        import yaml

        content = (DOCKER_DIR / "docker-compose.yml").read_text()
        parsed = yaml.safe_load(content)
        ports = parsed["services"]["app"].get("ports", [])
        port_strings = [str(p) for p in ports]
        assert any("8765" in p for p in port_strings)

    def test_dockerfile_exists(self):
        assert (DOCKER_DIR / "Dockerfile").exists()

    def test_dockerfile_has_healthcheck(self):
        content = (DOCKER_DIR / "Dockerfile").read_text()
        assert "HEALTHCHECK" in content

    def test_dockerfile_has_non_root_user(self):
        content = (DOCKER_DIR / "Dockerfile").read_text()
        assert "USER" in content

    def test_env_example_exists(self):
        assert (DOCKER_DIR / ".env.example").exists()

    def test_env_example_has_key_vars(self):
        content = (DOCKER_DIR / ".env.example").read_text()
        assert "AI_PROVIDER" in content
        assert "DEPLOY_MODE" in content
        assert "SESSION_SECRET" in content


class TestDockerProdConfig:
    def test_prod_compose_exists(self):
        assert (DOCKER_DIR / "docker-compose.prod.yml").exists()

    def test_prod_compose_is_valid_yaml(self):
        import yaml

        content = (DOCKER_DIR / "docker-compose.prod.yml").read_text()
        parsed = yaml.safe_load(content)
        assert parsed is not None


class TestDeployScript:
    def test_deploy_script_exists(self):
        scripts_dir = Path(__file__).parent.parent / "scripts"
        assert (scripts_dir / "deploy.sh").exists()

    def test_deploy_script_is_executable_or_has_shebang(self):
        scripts_dir = Path(__file__).parent.parent / "scripts"
        content = (scripts_dir / "deploy.sh").read_text()
        assert content.startswith("#!")
