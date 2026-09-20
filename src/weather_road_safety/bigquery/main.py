from pathlib import Path
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from weather_road_safety.config import (SQL_DIR, load_project_config)

def table_exists(
    client: bigquery.Client,
    table_id: str,
) -> bool:
    try:
        client.get_table(table_id)
        return True
    except NotFound:
        return False


def initialize_target(
    client: bigquery.Client,
    staging_table: str,
    target_table: str,
) -> None:
    print(f"Initializing target: {target_table}")

    job = client.copy_table(staging_table, target_table)
    job.result()
    table = client.get_table(target_table)

    print(f"Initialized {table.num_rows:,} rows into {target_table}")


def merge_target(
    client: bigquery.Client,
    sql_path: Path,
    parameters: dict[str, str],
) -> None:
    sql = sql_path.read_text(encoding="utf-8").format(**parameters)

    print(f"Merging: {sql_path.name}")

    job = client.query(sql)
    job.result()

    print(f"MERGE completed - {job.num_dml_affected_rows or 0:,} row(s) affected")

def get_client() -> tuple[bigquery.Client, dict]:
    config = load_project_config()
    client = bigquery.Client(project=config["gcp"]["project_id"])
    return client, config

def create_dataset(
    client: bigquery.Client,
    dataset_name: str,
    location: str,
) -> None:
    dataset_id = f"{client.project}.{dataset_name}"

    dataset = bigquery.Dataset(dataset_id)
    dataset.location = location

    client.create_dataset(dataset, exists_ok=True)

    print(f"Dataset ready: {dataset_id}")


def load_parquet(
    client: bigquery.Client,
    source_uri: str,
    table_id: str,
) -> None:
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=(bigquery.WriteDisposition.WRITE_TRUNCATE)
    )

    print(f"Loading {source_uri}")
    print(f"Target {table_id}")

    job = client.load_table_from_uri(source_uri, table_id, job_config=job_config)

    job.result()

    table = client.get_table(table_id)

    print(f"Loaded {table.num_rows:,} rows into {table_id}")


def execute_sql_file(
    client: bigquery.Client,
    sql_path: Path,
    parameters: dict[str, str],
) -> None:
    sql = sql_path.read_text(encoding="utf-8")

    sql = sql.format(**parameters)

    print(f"Executing: {sql_path.name}")

    job = client.query(sql)
    job.result()

    print(f"SQL completed: {sql_path.name}")


def main(year: int, department: str) -> None:
    department = department.zfill(2)

    client, config = get_client()

    project_id = config["gcp"]["project_id"]
    location = config["gcp"]["region"]
    bucket = config["gcp"]["bucket"]

    silver_dataset = (config["bigquery"]["silver_dataset"])
    gold_dataset = (config["bigquery"]["gold_dataset"])
    control_dataset = (config["bigquery"]["control_dataset"])

    for dataset_name in [
        silver_dataset,
        gold_dataset,
        control_dataset,
    ]:
        create_dataset(client=client, dataset_name=dataset_name, location=location)

    # load Silver accidents
    parameters = {
        "project_id": project_id,
        "silver_dataset": silver_dataset,
        "gold_dataset": gold_dataset,
    }

    accidents_uri = (f"gs://{bucket}/silver/accidents/year={year}/department={department}/accidents.parquet")
    accidents_staging_table = (f"{project_id}.{silver_dataset}.stg_accidents")
    accidents_target_table = (f"{project_id}.{silver_dataset}.accidents")

    load_parquet(client=client, source_uri=accidents_uri, table_id=accidents_staging_table)

    if table_exists(client,accidents_target_table,):
        merge_target(client=client, sql_path=(SQL_DIR / "incremental" / "merge_accidents.sql"),
            parameters=parameters,
        )
    else:
        initialize_target(client=client, staging_table=accidents_staging_table,
            target_table=accidents_target_table,
        )

    # load Silver weather
    weather_uri = (f"gs://{bucket}/silver/weather/year={year}/department={department}/weather.parquet")
    weather_staging_table = (f"{project_id}.{silver_dataset}.stg_weather")
    weather_target_table = (f"{project_id}.{silver_dataset}.weather")

    load_parquet(client=client, source_uri=weather_uri, table_id=weather_staging_table)

    # build Gold
    if table_exists(client, weather_target_table):
        merge_target(client=client, sql_path=(SQL_DIR / "incremental" / "merge_weather.sql"),
            parameters=parameters
        )
    else:
        initialize_target(client=client, staging_table=weather_staging_table,
            target_table=weather_target_table
        )

    execute_sql_file(client=client,sql_path=(SQL_DIR / "gold"/ "accident_weather.sql"),
        parameters=parameters
    )