import argparse

import polars as pl
import requests


DATASETS = {
    "baac": (
        "https://www.data.gouv.fr/api/1/datasets/"
        "bases-de-donnees-annuelles-des-accidents-corporels-"
        "de-la-circulation-routiere-annees-de-2005-a-2024/"
    ),
    "meteo-hourly": (
        "https://www.data.gouv.fr/api/1/datasets/"
        "donnees-climatologiques-de-base-horaires/"
    ),
    "meteo-stations": (
        "https://www.data.gouv.fr/api/1/datasets/"
        "informations-sur-les-stations-metadonnees/"
    ),
}


def fetch_dataset(source: str) -> dict:
    url = DATASETS[source]

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    return response.json()


def resources_to_dataframe(dataset: dict) -> pl.DataFrame:
    resources = dataset.get("resources", [])

    rows = []

    for resource in resources:
        rows.append(
            {
                "id": resource.get("id"),
                "title": resource.get("title")
                or resource.get("name")
                or "",
                "format": resource.get("format"),
                "filesize": resource.get("filesize"),
                "last_modified": resource.get("last_modified"),
                "url": resource.get("url"),
            }
        )

    return pl.DataFrame(rows)


def filter_resources(df: pl.DataFrame, contains: str | None, file_format: str | None,) -> pl.DataFrame:

    if contains:
        df = df.filter(pl.col("title").str.to_lowercase().str.contains(contains.lower(), literal=True))

    if file_format:
        df = df.filter(pl.col("format").str.to_lowercase() == file_format.lower())

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore official source datasets.")

    parser.add_argument("source", choices=DATASETS.keys())

    parser.add_argument("--contains", help="Filter resource names.",)

    parser.add_argument("--format", dest="file_format", help="Filter by file format.",)

    parser.add_argument("--limit",type=int, default=20)

    args = parser.parse_args()

    dataset = fetch_dataset(args.source)

    print(f"\nDataset: {dataset.get('title')}")
    print(f"Resources: {len(dataset.get('resources', []))}\n")

    df = resources_to_dataframe(dataset)
    df = filter_resources(df=df, contains=args.contains, file_format=args.file_format,)

    pl.Config.set_tbl_rows(args.limit)
    pl.Config.set_tbl_width_chars(180)
    pl.Config.set_fmt_str_lengths(500)

    print(df.select("id", "title", "format", "filesize", "last_modified", "url",).head(args.limit))


if __name__ == "__main__":
    main()