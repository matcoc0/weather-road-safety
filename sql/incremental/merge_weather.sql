MERGE
    `{project_id}.{silver_dataset}.weather` AS target
USING
    `{project_id}.{silver_dataset}.stg_weather` AS source
ON
       target.station_id = source.station_id
   AND target.observation_timestamp = source.observation_timestamp

WHEN MATCHED AND (
       target.station_name IS DISTINCT FROM source.station_name
    OR target.department IS DISTINCT FROM source.department
    OR target.latitude IS DISTINCT FROM source.latitude
    OR target.longitude IS DISTINCT FROM source.longitude
    OR target.temperature IS DISTINCT FROM source.temperature
    OR target.rainfall_1h IS DISTINCT FROM source.rainfall_1h
    OR target.wind_speed IS DISTINCT FROM source.wind_speed
    OR target.wind_direction IS DISTINCT FROM source.wind_direction
)
THEN UPDATE SET
    station_name = source.station_name,
    department = source.department,
    latitude = source.latitude,
    longitude = source.longitude,
    temperature = source.temperature,
    rainfall_1h = source.rainfall_1h,
    wind_speed = source.wind_speed,
    wind_direction = source.wind_direction

WHEN NOT MATCHED THEN
INSERT (
    station_id,
    station_name,
    department,
    observation_timestamp,
    latitude,
    longitude,
    temperature,
    rainfall_1h,
    wind_speed,
    wind_direction
)
VALUES (
    source.station_id,
    source.station_name,
    source.department,
    source.observation_timestamp,
    source.latitude,
    source.longitude,
    source.temperature,
    source.rainfall_1h,
    source.wind_speed,
    source.wind_direction
);