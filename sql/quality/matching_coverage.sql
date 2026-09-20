SELECT
    COUNT(*) AS total_accidents,

    COUNTIF(station_id IS NOT NULL) AS matched_accidents,
    COUNTIF(station_id IS NULL) AS unmatched_accidents,

    ROUND(
        SAFE_DIVIDE(
            COUNTIF(station_id IS NOT NULL),
            COUNT(*)
        ) * 100,
        2
    ) AS matching_rate_pct,

    ROUND(AVG(distance_to_station_m), 1) AS avg_distance_m,
    ROUND(MAX(distance_to_station_m), 1) AS max_distance_m,
    ROUND(AVG(weather_time_difference_minutes), 1)
        AS avg_time_difference_min,
    MAX(weather_time_difference_minutes)
        AS max_time_difference_min

FROM
    `{project_id}.{gold_dataset}.accident_weather`;