SELECT
    accident_id,
    accident_timestamp,
    weather_timestamp
FROM
    `{project_id}.{gold_dataset}.accident_weather`
WHERE
    accident_timestamp IS NULL
    OR weather_timestamp IS NULL;