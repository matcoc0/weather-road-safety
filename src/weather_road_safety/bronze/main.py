from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests
from google.cloud import storage

from weather_road_safety.bronze.sources import (
    extract_weather_period,
    find_baac_resource,
    find_weather_resource,
    get_resource_title,
)
from weather_road_safety.config import load_project_config


def download_resource(url: str) -> bytes:
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    return response.content


def get_filename(resource: dict) -> str:
    url = resource.get("url")

    if not url:
        raise ValueError("Resource has no URL.")

    filename = PurePosixPath(urlparse(url).path).name

    if not filename:
        raise ValueError(f"Cannot determine filename from URL: {url}")

    return filename


def upload_to_gcs(content: bytes, object_name: str, source_resource: dict,) -> None:
    config = load_project_config()

    project_id = config["gcp"]["project_id"]
    bucket_name = config["gcp"]["bucket"]

    if not project_id:
        raise ValueError("Missing gcp.project_id in project.local.json")

    if not bucket_name:
        raise ValueError("Missing gcp.bucket in project.local.json")

    client = storage.Client(project=project_id)

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    blob.metadata = {
        "source_url": source_resource["url"],
        "source_title": get_resource_title(
            source_resource
        ),
    }

    blob.upload_from_string(content)

    print(f"Uploaded {len(content) / 1024 / 1024:.2f} MB")
    print(f"gs://{bucket_name}/{object_name}")


def ingest_baac(year: int,resource_type: str,) -> None:
    resource = find_baac_resource(year=year,resource_type=resource_type,)
    title = get_resource_title(resource)
    print(f"Found BAAC resource: {title}")
    content = download_resource(resource["url"])
    filename = get_filename(resource)
    object_name = (f"bronze/baac/year={year}/{resource_type}/{filename}")
    upload_to_gcs(content=content, object_name=object_name, source_resource=resource,)


def ingest_weather( year: int, department: str,) -> None:
    department = department.zfill(2)
    resource = find_weather_resource(year=year, department=department)
    title = get_resource_title(resource)
    period = extract_weather_period(resource)

    print(f"Found weather resource: {title}")

    content = download_resource(resource["url"])
    filename = get_filename(resource)
    object_name = (f"bronze/weather/department={department}/period={period}/{filename}")
    upload_to_gcs(content=content, object_name=object_name, source_resource=resource,)


def main(source: str, year: int, department: str | None = None, resource_type: str | None = None) -> None:
    if source == "baac":
        if resource_type is None:
            raise ValueError("--resource-type is required when source=baac")

        ingest_baac(year=year, resource_type=resource_type,)
        return

    if source == "weather":
        if department is None:
            raise ValueError("--department is required when source=weather")

        ingest_weather(year=year, department=department,)
        return

    raise ValueError(f"Unsupported Bronze source: {source}")