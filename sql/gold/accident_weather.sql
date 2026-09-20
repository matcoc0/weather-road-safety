CREATE OR REPLACE TABLE
  `{project_id}.{gold_dataset}.accident_weather`
AS

WITH stations AS (

    SELECT DISTINCT
        station_id,
        station_name,
        latitude,
        longitude
    FROM
        `{project_id}.{silver_dataset}.weather`
    WHERE
        latitude IS NOT NULL
        AND longitude IS NOT NULL

),

nearest_station AS (

    SELECT
        a.*,

        s.station_id,
        s.station_name,

        ST_DISTANCE(
            ST_GEOGPOINT(
                a.longitude,
                a.latitude
            ),
            ST_GEOGPOINT(
                s.longitude,
                s.latitude
            )
        ) AS distance_to_station_m

    FROM
        `{project_id}.{silver_dataset}.accidents` AS a

    CROSS JOIN stations AS s

    WHERE
        a.latitude IS NOT NULL
        AND a.longitude IS NOT NULL

    QUALIFY
        ROW_NUMBER() OVER (
            PARTITION BY a.accident_id
            ORDER BY
                ST_DISTANCE(
                    ST_GEOGPOINT(
                        a.longitude,
                        a.latitude
                    ),
                    ST_GEOGPOINT(
                        s.longitude,
                        s.latitude
                    )
                ),
                s.station_id
        ) = 1

),

weather_match AS (

    SELECT
        a.accident_id,
        a.accident_timestamp,
        a.department,
        a.city,
        a.latitude,
        a.longitude,
        a.atmospheric_condition,
        a.luminosity,
        a.collision_type,

        a.station_id,
        a.station_name,
        a.distance_to_station_m,

        w.observation_timestamp
            AS weather_timestamp,

        w.temperature,
        w.rainfall_1h,
        w.wind_speed,
        w.wind_direction,

        ABS(
            TIMESTAMP_DIFF(
                w.observation_timestamp,
                a.accident_timestamp,
                MINUTE
            )
        ) AS weather_time_difference_minutes

    FROM nearest_station AS a

    LEFT JOIN
        `{project_id}.{silver_dataset}.weather` AS w

        ON
            w.station_id = a.station_id

            AND w.observation_timestamp
                BETWEEN
                    TIMESTAMP_SUB(
                        a.accident_timestamp,
                        INTERVAL 2 HOUR
                    )
                    AND
                    TIMESTAMP_ADD(
                        a.accident_timestamp,
                        INTERVAL 2 HOUR
                    )

    QUALIFY
        ROW_NUMBER() OVER (
            PARTITION BY a.accident_id
            ORDER BY
                ABS(
                    TIMESTAMP_DIFF(
                        w.observation_timestamp,
                        a.accident_timestamp,
                        MINUTE
                    )
                )
        ) = 1
)

SELECT *
FROM weather_match;