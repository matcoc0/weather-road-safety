from pathlib import Path

from google.cloud import bigquery

from weather_road_safety.config import (SQL_DIR, load_project_config)

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
    accidents_uri = (f"gs://{bucket}/silver/accidents/year={year}/department={department}/accidents.parquet")
    accidents_table = (f"{project_id}.{silver_dataset}.accidents")

    load_parquet(client=client, source_uri=accidents_uri, table_id=accidents_table)

    # load Silver weather
    weather_uri = (f"gs://{bucket}/silver/weather/year={year}/department={department}/weather.parquet")
    weather_table = (f"{project_id}.{silver_dataset}.weather")

    load_parquet(client=client, source_uri=weather_uri, table_id=weather_table)

    # build Gold
    execute_sql_file(
        client=client,
        sql_path=SQL_DIR / "gold" / "accident_weather.sql",
        parameters={
            "project_id": project_id,
            "silver_dataset": silver_dataset,
            "gold_dataset": gold_dataset,
        }
    )