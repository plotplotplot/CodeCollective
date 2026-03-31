import os
from pathlib import Path
import sys

here = Path(os.path.abspath(os.path.dirname(__file__)))
root = here.parent
sys.path.append(str(root))

import docker_utils
import editme


def ensure_ubi_image(force_rebuild: bool = False) -> None:
    images = docker_utils.DOCKER_CLIENT.images.list(name="ubi")
    if not force_rebuild:
        for image in images:
            if "ubi" in image.tags:
                return
    print("Building ubi image from ubi/Dockerfile...")
    docker_utils.DOCKER_CLIENT.images.build(
        path=str(here),
        tag="ubi",
        forcerm=True,
    )


def run(network_name: str = "PORTAL", prefix: str = "") -> None:
    ensure_ubi_image()
    ubi = dict(
        image="ubi",
        name=prefix + "ubi",
        detach=True,
        network=network_name,
        restart_policy={"Name": "always"},
        ports={"8000/tcp": 8000},
        volumes={
            str(here): {"bind": "/app", "mode": "rw"},
        },
        environment={
            "COCKROACH_ASYNC_URL": (
                f"postgresql://{editme.COCKROACH_USER}@{prefix}cockroach:"
                f"{editme.COCKROACH_SQL_PORT}/{editme.COCKROACH_DB}"
                f"?sslmode={'disable' if editme.COCKROACH_INSECURE else 'require'}"
            ),
            "UBI_INTERVAL_SECONDS": os.getenv("UBI_INTERVAL_SECONDS", "60"),
            "DENA_ANNUAL": os.getenv("DENA_ANNUAL", "1"),
            "DENA_PRECISION": os.getenv("DENA_PRECISION", "6"),
            "UBI_ENTITY_TYPES": os.getenv("UBI_ENTITY_TYPES", "individual"),
            "UBI_API_KEY": os.getenv("UBI_API_KEY", ""),
            "PIDP_BASE_URL": os.getenv("PIDP_BASE_URL", f"http://{prefix}pidp:8000"),
        },
    )
    docker_utils.run_container(ubi)
