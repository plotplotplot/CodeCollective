"""
Governance Backend Runner

Manages the governance backend service container for motions, voting, and engagement.
"""

import os
from pathlib import Path
import sys

here = Path(os.path.abspath(os.path.dirname(__file__)))
root = here.parent
sys.path.append(str(root))

import docker_utils
import editme


def ensure_governance_backend_image() -> None:
    """Build the governance-backend Docker image if it doesn't exist."""
    images = docker_utils.DOCKER_CLIENT.images.list(name="governance-backend")
    for image in images:
        if any("governance-backend" in tag for tag in image.tags):
            return
    print("Building governance-backend image from governance-backend/Dockerfile...")
    docker_utils.DOCKER_CLIENT.images.build(
        path=str(here),
        tag="governance-backend",
    )


def run(network_name: str = "PORTAL", prefix: str = "") -> None:
    """Run the governance backend service."""
    ensure_governance_backend_image()
    
    db_host = f"{prefix}governance-db"
    database_url = os.getenv(
        "DATABASE_URL",
        (
            f"postgresql://{editme.GOVERNANCE_DB_USER}:"
            f"{editme.GOVERNANCE_DB_PASSWORD}@{db_host}:5432/"
            f"{editme.GOVERNANCE_DB_NAME}"
        ),
    )
    redis_url = os.getenv("REDIS_URL", f"redis://{prefix}redis:6379/0")
    
    backend = dict(
        image="governance-backend",
        name=prefix + "governance-backend",
        detach=True,
        network=network_name,
        restart_policy={"Name": "always"},
        ports={
            "8002/tcp": 8002,
        },
        volumes={
            str(here): {"bind": "/app", "mode": "rw"},
        },
        environment={
            "DATABASE_URL": database_url,
            "REDIS_URL": redis_url,
        },
        healthcheck={
            "test": ["CMD-SHELL", "curl -fsS http://127.0.0.1:8002/health >/dev/null"],
            "interval": 5000000000,  # 5s
            "timeout": 5000000000,   # 5s
            "retries": 10,
        },
    )
    docker_utils.run_container(backend)


if __name__ == "__main__":
    run()
