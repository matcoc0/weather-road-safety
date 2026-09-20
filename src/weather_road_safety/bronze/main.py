def main(
    source: str,
    year: int,
    department: str | None = None,
    resource_type: str | None = None,
) -> None:
    print(
        f"Bronze pipeline: "
        f"source={source}, "
        f"year={year}, "
        f"department={department}, "
        f"resource_type={resource_type}"
    )