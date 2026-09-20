import gzip
from io import BytesIO

import polars as pl
from google.cloud import storage

from weather_road_safety.config import load_project_config


def get_storage_client():
    config = load_project_config()

    project_id = config["gcp"]["project_id"]
    bucket_name = config["gcp"]["bucket"]

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)

    return bucket

def download_single_object(prefix: str) -> tuple[bytes, str]:
    bucket = get_storage_client()

    blobs = [
        blob
        for blob in bucket.list_blobs(prefix=prefix)
        if not blob.name.endswith("/")
    ]

    if not blobs:
        raise ValueError(f"No Bronze object found under: {prefix}")

    if len(blobs) > 1:
        names = "\n".join(blob.name for blob in blobs)

        raise ValueError(f"Multiple objects found under {prefix}:\n{names}")

    blob = blobs[0]

    print(f"Reading: gs://{bucket.name}/{blob.name}")

    return blob.download_as_bytes(), blob.name


def read_csv_bytes(
    content: bytes,
    object_name: str,
) -> pl.DataFrame:
    if object_name.endswith(".gz"):
        content = gzip.decompress(content)

    return pl.read_csv(BytesIO(content), separator=";", infer_schema_length=10_000)


def require_columns(
    df: pl.DataFrame,
    required_columns: list[str],
    dataset: str,
) -> None:
    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing columns in {dataset}: {missing}")


def upload_parquet(
    df: pl.DataFrame,
    object_name: str,
) -> None:
    bucket = get_storage_client()
    blob = bucket.blob(object_name)

    buffer = BytesIO()

    df.write_parquet(buffer,compression="zstd",)

    blob.upload_from_string(buffer.getvalue(),content_type="application/octet-stream",)

    print(f"Written {df.height:,} rows => gs://{bucket.name}/{object_name}")


def build_accidents(
    year: int,
    department: str,
) -> None:
    department = department.zfill(2)

    content, object_name = download_single_object(
        prefix=(f"bronze/baac/year={year}/caract/")
    )

    df = read_csv_bytes(content=content, object_name=object_name)

    require_columns(
        df=df,
        required_columns=[
            "Num_Acc",
            "jour",
            "mois",
            "an",
            "hrmn",
            "lum",
            "dep",
            "com",
            "atm",
            "col",
            "lat",
            "long",
        ],
        dataset="BAAC characteristics",
    )

    clean_time = (
        pl.col("hrmn")
        .cast(pl.String)
        .str.strip_chars()
        .str.replace_all(":", "")
        .str.pad_start(4, "0")
    )

    accident_timestamp = (
        pl.concat_str(
            [
                pl.col("an").cast(pl.String),
                pl.col("mois")
                .cast(pl.String)
                .str.pad_start(2, "0"),
                pl.col("jour")
                .cast(pl.String)
                .str.pad_start(2, "0"),
                clean_time,
            ]
        )
        .str.strptime(pl.Datetime, format="%Y%m%d%H%M", strict=False,)
        .alias("accident_timestamp")
    )

    accidents = (
        df.filter(pl.col("dep").cast(pl.String) == department)
        .select(
            [
                pl.col("Num_Acc").cast(pl.String).alias("accident_id"),
                accident_timestamp,

                pl.col("dep").cast(pl.String).alias("department"),

                pl.col("com").cast(pl.String).alias("city"),

                pl.col("lat").cast(pl.String).str.strip_chars()
                .str.replace_all(",", ".").cast(pl.Float64, strict=False)
                .alias("latitude"),

                pl.col("long").cast(pl.String).str.strip_chars()
                .str.replace_all(",", ".").cast(pl.Float64, strict=False)
                .alias("longitude"),

                pl.col("atm").cast(pl.Int64, strict=False)
                .alias("atmospheric_condition"),

                pl.col("lum").cast(pl.Int64, strict=False)
                .alias("luminosity"),

                pl.col("col").cast(pl.Int64, strict=False)
                .alias("collision_type"),
            ]
        )
        .sort("accident_timestamp")
    )

    print(f"Bronze rows: {df.height:,}")
    print(f"Silver accident rows: {accidents.height:,}")
    print(accidents.head())

    upload_parquet(
        df=accidents,
        object_name=(
            f"silver/accidents/"
            f"year={year}/"
            f"department={department}/"
            f"accidents.parquet"
        ),
    )


def build_weather(
    year: int,
    department: str,
) -> None:
    department = department.zfill(2)

    content, object_name = download_single_object(
        prefix=(
            f"bronze/weather/"
            f"department={department}/"
        )
    )

    df = read_csv_bytes(
        content=content,
        object_name=object_name,
    )

    require_columns(
        df=df,
        required_columns=[
            "NUM_POSTE",
            "NOM_USUEL",
            "LAT",
            "LON",
            "AAAAMMJJHH",
            "T",
            "RR1",
            "FF",
            "DD",
        ],
        dataset="Météo-France hourly observations",
    )

    observation_timestamp = (
        pl.concat_str([pl.col("AAAAMMJJHH").cast(pl.String), pl.lit("00")])
        .str.strptime(pl.Datetime,format="%Y%m%d%H%M",strict=False)
        .alias("observation_timestamp")
    )
    weather = (
        df.with_columns(observation_timestamp).filter(pl.col("observation_timestamp").dt.year() == year)
        .select(
            [
                pl.col("NUM_POSTE").cast(pl.String).alias("station_id"),
                pl.col("NOM_USUEL").cast(pl.String).alias("station_name"),
                pl.lit(department).alias("department"),
                pl.col("observation_timestamp"),
                pl.col("LAT").cast(pl.Float64, strict=False).alias("latitude"),
                pl.col("LON").cast(pl.Float64, strict=False).alias("longitude"),
                pl.col("T").cast(pl.Float64, strict=False).alias("temperature"),
                pl.col("RR1").cast(pl.Float64, strict=False).alias("rainfall_1h"),
                pl.col("FF").cast(pl.Float64, strict=False).alias("wind_speed"),
                pl.col("DD").cast(pl.Float64, strict=False).alias("wind_direction"),
            ]
        )
        .sort(["station_id", "observation_timestamp",])
    )

    null_timestamps = weather.select(pl.col("observation_timestamp").is_null().sum()).item()
    print(f"Invalid weather timestamps: {null_timestamps:,}")

    print(f"Bronze rows: {df.height:,}")
    print(f"Silver weather rows: {weather.height:,}")
    print(weather.head())

    upload_parquet(
        df=weather,
        object_name=(f"silver/weather/year={year}/department={department}/weather.parquet")
    )


def main(
    dataset: str,
    year: int,
    department: str,
) -> None:
    if dataset == "accidents":
        build_accidents(year=year, department=department,)
        return

    if dataset == "weather":
        build_weather(year=year, department=department,)
        return

    raise ValueError(f"Unsupported Silver dataset: {dataset}")