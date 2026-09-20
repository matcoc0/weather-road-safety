MERGE
    `{project_id}.{silver_dataset}.accidents` AS target
USING
    `{project_id}.{silver_dataset}.stg_accidents` AS source
ON
    target.accident_id = source.accident_id

WHEN MATCHED AND (
       target.accident_timestamp IS DISTINCT FROM source.accident_timestamp
    OR target.department IS DISTINCT FROM source.department
    OR target.city IS DISTINCT FROM source.city
    OR target.latitude IS DISTINCT FROM source.latitude
    OR target.longitude IS DISTINCT FROM source.longitude
    OR target.atmospheric_condition IS DISTINCT FROM source.atmospheric_condition
    OR target.luminosity IS DISTINCT FROM source.luminosity
    OR target.collision_type IS DISTINCT FROM source.collision_type
)
THEN UPDATE SET
    accident_timestamp = source.accident_timestamp,
    department = source.department,
    city = source.city,
    latitude = source.latitude,
    longitude = source.longitude,
    atmospheric_condition = source.atmospheric_condition,
    luminosity = source.luminosity,
    collision_type = source.collision_type

WHEN NOT MATCHED THEN
INSERT (
    accident_id,
    accident_timestamp,
    department,
    city,
    latitude,
    longitude,
    atmospheric_condition,
    luminosity,
    collision_type
)
VALUES (
    source.accident_id,
    source.accident_timestamp,
    source.department,
    source.city,
    source.latitude,
    source.longitude,
    source.atmospheric_condition,
    source.luminosity,
    source.collision_type
);