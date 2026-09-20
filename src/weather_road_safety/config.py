import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
SQL_DIR = PROJECT_ROOT / "sql"


def load_json(filename: str) -> dict:
    path = CONFIG_DIR / filename

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_project_config() -> dict:
    return load_json("project.local.json")


def load_sources_config() -> dict:
    return load_json("sources.json")