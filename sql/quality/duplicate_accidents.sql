SELECT
    accident_id,
    COUNT(*) AS row_count
FROM
    `{project_id}.{gold_dataset}.accident_weather`
GROUP BY accident_id
HAVING COUNT(*) > 1;