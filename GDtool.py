import argparse

from weather_road_safety.bronze.main import main as bronze_main
from weather_road_safety.silver.main import main as silver_main
from weather_road_safety.bigquery.main import main as bigquery_main
from weather_road_safety.quality.main import main as quality_main


class CustomHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter,
):
    pass


def sub_command_bronze(subparsers):
    parser = subparsers.add_parser(
        "bronze",
        help="Ingest raw source data into GCS Bronze.",
        formatter_class=CustomHelpFormatter,
    )

    parser.add_argument(
        "--source",
        "-s",
        choices=["baac", "weather"],
        required=True,
        help="Source dataset to ingest.",
    )

    parser.add_argument(
        "--year",
        "-y",
        type=int,
        required=True,
        help="Target year. Example: 2024",
    )

    parser.add_argument(
        "--department",
        "-d",
        default=None,
        help="Department code. Required for weather. Example: 75",
    )

    parser.add_argument(
        "--resource-type",
        "-t",
        choices=["caract", "lieux", "vehicules", "usagers"],
        default=None,
        help="BAAC resource type.",
    )

    parser.set_defaults(func=bronze_main)


def sub_command_silver(subparsers):
    parser = subparsers.add_parser(
        "silver",
        help="Transform Bronze raw data into cleaned Parquet datasets.",
        formatter_class=CustomHelpFormatter,
    )

    parser.add_argument(
        "--dataset",
        choices=["accidents", "weather"],
        required=True,
        help="Silver dataset to build.",
    )

    parser.add_argument(
        "--year",
        "-y",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--department",
        "-d",
        required=True,
    )

    parser.set_defaults(func=silver_main)


def sub_command_bigquery(subparsers):
    parser = subparsers.add_parser(
        "bigquery",
        help="Load Silver data and build BigQuery Gold datasets.",
        formatter_class=CustomHelpFormatter,
    )

    parser.add_argument(
        "--year",
        "-y",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--department",
        "-d",
        required=True,
    )

    parser.set_defaults(func=bigquery_main)


def sub_command_quality(subparsers):
    parser = subparsers.add_parser(
        "quality",
        help="Run data quality controls.",
        formatter_class=CustomHelpFormatter,
    )

    parser.add_argument(
        "--year",
        "-y",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--department",
        "-d",
        required=True,
    )

    parser.set_defaults(func=quality_main)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "GCP Data Tool - Weather & Road Safety Data Platform"
        ),
        formatter_class=CustomHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="module",
        required=True,
        help="Pipeline module to execute.",
    )

    sub_command_bronze(subparsers)
    sub_command_silver(subparsers)
    sub_command_bigquery(subparsers)
    sub_command_quality(subparsers)

    return parser


def main():
    parser = parse_arguments()
    args = parser.parse_args()

    arguments = vars(args).copy()

    func = arguments.pop("func")
    arguments.pop("module")

    func(**arguments)


if __name__ == "__main__":
    main()