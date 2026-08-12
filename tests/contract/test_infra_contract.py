import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
NGINX_CONFIG = ROOT / "infra" / "nginx" / "app.conf"
COMPOSE_CONFIG = ROOT / "infra" / "compose.local.yml"
TEST_API_SYSTEMD_CONFIG = ROOT / "infra" / "systemd" / "fateradar-test-api.service"


def nginx_location(path: str) -> str:
    config = NGINX_CONFIG.read_text(encoding="utf-8")
    match = re.search(rf"location {re.escape(path)} \{{(?P<body>.*?)\n    \}}", config, re.DOTALL)
    assert match is not None
    return match.group("body")


def test_nginx_keeps_web_and_api_on_one_origin() -> None:
    assert "proxy_pass http://api:8000;" in nginx_location("/api/")
    assert "proxy_pass http://web:3000;" in nginx_location("/")


def test_api_location_preserves_security_headers_with_no_store() -> None:
    api_location = nginx_location("/api/")

    # Nginx stops inheriting parent add_header directives as soon as a location
    # declares one, so the API block must repeat the baseline header set.
    for header in (
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Cache-Control",
    ):
        assert f"add_header {header} " in api_location


def test_nginx_overwrites_the_client_forwarding_header_at_ingress() -> None:
    for path in ("/api/", "/"):
        assert "proxy_set_header X-Forwarded-For $remote_addr;" in nginx_location(path)


def test_compose_declares_the_phase_one_process_boundaries() -> None:
    with COMPOSE_CONFIG.open(encoding="utf-8") as stream:
        compose: dict[str, Any] = yaml.safe_load(stream)

    assert set(compose["services"]) == {
        "postgres",
        "redis",
        "api",
        "worker",
        "web",
        "edge",
    }
    assert "MINGLI_TRUSTED_PROXY_CIDRS" in compose["services"]["api"]["environment"]


def test_test_api_can_lock_runtime_without_writing_the_runtime_tree() -> None:
    config = TEST_API_SYSTEMD_CONFIG.read_text(encoding="utf-8")

    assert "ProtectSystem=strict" in config
    assert (
        "ReadWritePaths=/opt/fateradar/shared/mingli-runtime/.venv.runtime.lock"
        in config
    )
    assert "ReadWritePaths=/opt/fateradar/shared/mingli-runtime\n" not in config
