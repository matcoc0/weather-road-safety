import argparse
from io import BytesIO

import polars as pl
import requests


CANDIDATE_WEATHER_COLUMNS = [
    "RR1",
    "FF",
    "DD",
    "T",
    "U",
    "VV",
    "WW",
]


def download_resource(url: str) -> bytes:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def inspect_csv(content: bytes) -> pl.DataFrame:
    df = pl.read_csv(BytesIO(content),separator=";",infer_schema_length=10_000,)

    print(f"\nRows: {df.height:,}")
    print(f"Columns: {df.width}")

    print("\nSchema:")
    for name, dtype in df.schema.items():
        print(f"- {name}: {dtype}")

    print("\nSample:")
    print(df.head())

    if {
        "NUM_POSTE",
        "NOM_USUEL",
        "LAT",
        "LON",
    }.issubset(df.columns):
        print("\nStations:")
        print(df.select("NUM_POSTE","NOM_USUEL","LAT","LON",).unique().sort("NUM_POSTE"))

    if "AAAAMMJJHH" in df.columns:
        print("\nDate range:")
        print(df.select(pl.col("AAAAMMJJHH").min().alias("min_date"), pl.col("AAAAMMJJHH").max().alias("max_date"),))

    existing_candidate_columns = [
        col
        for col in CANDIDATE_WEATHER_COLUMNS
        if col in df.columns
    ]

    if existing_candidate_columns:
        print("\nCandidate weather variables - non null counts:")
        print(
            df.select(
                [
                    pl.col(col).is_not_null().sum().alias(col)
                    for col in existing_candidate_columns
                ]
            )
        )

        print("\nCandidate weather variables - null percentage:")
        print(
            df.select(
                [
                    (pl.col(col).is_null().mean() * 100).round(2).alias(col)
                    for col in existing_candidate_columns
                ]
            )
        )

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and inspect a CSV resource with Polars.")

    parser.add_argument(
        "url",
        help="URL of the CSV or CSV.GZ resource to inspect.",
    )

    args = parser.parse_args()

    print(f"Downloading:\n{args.url}")

    content = download_resource(args.url)

    print(f"\nDownloaded size: {len(content) / 1024 / 1024:.2f} MB")

    inspect_csv(content)


if __name__ == "__main__":
    main()