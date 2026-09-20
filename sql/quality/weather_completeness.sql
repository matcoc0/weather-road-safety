SELECT
    COUNT(*) AS total_accidents,

    COUNTIF(temperature IS NULL) AS missing_temperature,
    COUNTIF(rainfall_1h IS NULL) AS missing_rainfall,
    COUNTIF(wind_speed IS NULL) AS missing_wind_speed,
    COUNTIF(wind_direction IS NULL)AS missing_wind_direction,

    ROUND(100 * SAFE_DIVIDE(COUNTIF(temperature IS NULL), COUNT(*)), 2) AS temperature_null_pct,
    ROUND(100 * SAFE_DIVIDE(COUNTIF(rainfall_1h IS NULL),COUNT(*)), 2) AS rainfall_null_pct,
    ROUND(100 * SAFE_DIVIDE(COUNTIF(wind_speed IS NULL), COUNT(*)), 2) AS wind_speed_null_pct

FROM
    `{project_id}.{gold_dataset}.accident_weather`;