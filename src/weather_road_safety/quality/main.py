from pathlib import Path

from google.cloud import bigquery

from weather_road_safety.config import (
    SQL_DIR,
    load_project_config,
)

CHECKS = {
    "duplicate_accidents.sql": "violations",
    "invalid_coordinates.sql": "violations",
    "missing_timestamps.sql": "violations",
    "matching_coverage.sql": "metrics",
    "weather_completeness.sql": "metrics",
}

def execute_check(
    client: bigquery.Client,
    sql_path: Path,
    parameters: dict[str, str],
    check_type: str,
) -> bool:
    sql = sql_path.read_text(encoding="utf-8").format(**parameters)

    print()
    print(f"CHECK: {sql_path.name}")

    rows = list(client.query(sql).result())

    if check_type == "violations":
        if not rows:
            print("PASS - 0 violation")
            return True

        print(f"FAIL - {len(rows)} violation(s)")

        for row in rows[:10]:
            print(dict(row))

        return False

    if check_type == "metrics":
        for row in rows:
            for key, value in dict(row).items():
                print(f"{key}: {value}")

        return True

    raise ValueError(f"Unknown check type: {check_type}")


def main(
    year: int,
    department: str,
) -> None:
    config = load_project_config()

    project_id = config["gcp"]["project_id"]

    silver_dataset = (config["bigquery"]["silver_dataset"])

    gold_dataset = (config["bigquery"]["gold_dataset"])

    control_dataset = (config["bigquery"]["control_dataset"])

    client = bigquery.Client(project=project_id)

    parameters = {
        "project_id": project_id,
        "silver_dataset": silver_dataset,
        "gold_dataset": gold_dataset,
        "control_dataset": control_dataset,
        "year": str(year),
        "department": department.zfill(2),
    }

    results = []

    for filename, check_type in CHECKS.items():
        sql_path = (SQL_DIR / "quality" / filename)

        passed = execute_check(client=client, sql_path=sql_path,
                               parameters=parameters, check_type=check_type)

        results.append((filename, passed))

    failed_checks = [
        filename
        for filename, passed in results
        if not passed
    ]

    print()
    print("DATA QUALITY SUMMARY")

    if failed_checks:
        print(f"FAIL - {len(failed_checks)} check(s) failed")

        for filename in failed_checks:
            print(f"- {filename}")
    else:
        print("PASS - all violation checks passed")