import re

import requests

from weather_road_safety.config import load_sources_config


def fetch_dataset(source: str) -> dict:
    config = load_sources_config()

    try:
        url = config[source]["dataset_api"]
    except KeyError as exc:
        raise ValueError(f"Unknown source: {source}") from exc

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    return response.json()


def get_resource_title(resource: dict) -> str:
    return (resource.get("title") or resource.get("name") or "")


def find_baac_resource(year: int, resource_type: str) -> dict:
    dataset = fetch_dataset("baac")

    aliases = {
        "caract": ("caract", "caracteristiques"),
        "lieux": ("lieux",),
        "vehicules": ("vehicules",),
        "usagers": ("usagers",),
    }

    if resource_type not in aliases:
        raise ValueError(f"Unsupported BAAC resource type: {resource_type}")

    candidates = []

    for resource in dataset.get("resources", []):
        title = get_resource_title(resource).lower()

        if str(year) not in title:
            continue

        if not any(alias in title for alias in aliases[resource_type]):
            continue

        # exclude the additional vehicle registration dataset.
        if (resource_type == "vehicules" and "immatricul" in title):
            continue

        candidates.append(resource)

    if not candidates:
        raise ValueError(f"No BAAC resource found for type={resource_type}, year={year}")

    if len(candidates) > 1:
        titles = [get_resource_title(resource)for resource in candidates]

        raise ValueError("Multiple BAAC resources found:\n"+ "\n".join(titles))

    return candidates[0]


def find_weather_resource(
    year: int,
    department: str,
) -> dict:
    dataset = fetch_dataset("weather")

    department = department.zfill(2)

    pattern = re.compile(rf"hor_departement_{re.escape(department)}_periode_(\d{{4}})-(\d{{4}})",re.IGNORECASE)

    candidates = []

    for resource in dataset.get("resources", []):
        title = get_resource_title(resource)

        match = pattern.search(title)

        if not match:
            continue

        start_year = int(match.group(1))
        end_year = int(match.group(2))

        if start_year <= year <= end_year:
            candidates.append(resource)

    if not candidates:
        raise ValueError(f"No weather resource found for "f"department={department}, year={year}")

    if len(candidates) > 1:
        titles = [get_resource_title(resource)for resource in candidates]

        raise ValueError("Multiple weather resources found:\n" + "\n".join(titles))

    return candidates[0]


def extract_weather_period(resource: dict) -> str:
    title = get_resource_title(resource)

    match = re.search(r"periode_(\d{4}-\d{4})", title, re.IGNORECASE)

    if not match:
        raise ValueError(f"Cannot extract weather period from: {title}")

    return match.group(1)