SELECT
    accident_id,
    latitude,
    longitude
FROM
    `{project_id}.{gold_dataset}.accident_weather`
WHERE
    latitude IS NULL
    OR longitude IS NULL
    OR latitude NOT BETWEEN -90 AND 90
    OR longitude NOT BETWEEN -180 AND 180;