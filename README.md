# Weather & Road Safety - Cloud Data Platform

Personal Data Engineering project combining French road accident data
(BAAC) with hourly weather observations from Météo-France.

The project implements an end-to-end GCP data pipeline based on a
Bronze / Silver / Gold architecture, with Parquet storage, BigQuery,
incremental loading and Data Quality controls.

> **Status:** GCP implementation operational.  
> AWS transposition is planned as the next step of the project.

---

## Architecture

```text
BAAC / Météo-France
        │
        ▼
   data.gouv.fr APIs
        │
        ▼
┌───────────────────┐
│    GCS Bronze     │
│   Raw datasets    │
└─────────┬─────────┘
          │
          │ Python / Polars
          ▼
┌───────────────────┐
│    GCS Silver     │
│ Parquet datasets  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ BigQuery Staging  │
└─────────┬─────────┘
          │
          │ SQL MERGE
          ▼
┌───────────────────┐
│ BigQuery Silver   │
└─────────┬─────────┘
          │
          │ Spatial + temporal matching
          ▼
┌───────────────────┐
│  BigQuery Gold    │
│ accident_weather  │
└─────────┬─────────┘
          │
          ▼
    Data Quality
```

---

## Data sources

### BAAC

French road accident data published on data.gouv.fr.

The pipeline dynamically discovers the requested yearly resource instead
of relying on a hardcoded file URL.

Currently used accident attributes include:

- accident identifier
- date and time
- department
- commune
- latitude / longitude
- atmospheric conditions
- luminosity
- collision type

### Météo-France

Hourly weather observations published by Météo-France through data.gouv.fr.

Currently used variables include:

- weather station identifier
- observation timestamp
- station coordinates
- temperature
- hourly rainfall
- wind speed
- wind direction

---

## Repository structure

```text
.
├── GDtool.py
├── README.md
├── config/
│   ├── project.example.json
│   └── sources.json
├── pyproject.toml
├── scripts/
│   ├── explore_sources.py
│   └── inspect_resource.py
├── sql/
│   ├── gold/
│   │   └── accident_weather.sql
│   ├── incremental/
│   │   ├── merge_accidents.sql
│   │   └── merge_weather.sql
│   └── quality/
│       ├── duplicate_accidents.sql
│       ├── invalid_coordinates.sql
│       ├── matching_coverage.sql
│       ├── missing_timestamps.sql
│       └── weather_completeness.sql
└── src/
    └── weather_road_safety/
        ├── config.py
        ├── bronze/
        │   ├── main.py
        │   └── sources.py
        ├── silver/
        │   └── main.py
        ├── bigquery/
        │   └── main.py
        └── quality/
            └── main.py
```

### Main components

| Component | Purpose |
|---|---|
| `GDtool.py` | Central CLI used to execute each pipeline stage |
| `config/` | Project and source configuration |
| `scripts/` | Utilities used to explore and inspect source datasets |
| `bronze/` | Raw ingestion from public sources to Google Cloud Storage |
| `silver/` | Cleaning and transformation with Polars |
| `bigquery/` | BigQuery staging, incremental loading and Gold execution |
| `quality/` | Execution of SQL Data Quality controls |
| `sql/incremental/` | BigQuery `MERGE` statements |
| `sql/gold/` | Analytical Gold transformations |
| `sql/quality/` | Data Quality checks and monitoring metrics |

---

## Configuration

### Project configuration

Copy the example configuration:

```bash
cp config/project.example.json config/project.local.json
```

Then configure your local GCP environment:

```json
{
  "gcp": {
    "project_id": "YOUR_GCP_PROJECT_ID",
    "region": "europe-west9",
    "bucket": "YOUR_GCS_BUCKET"
  },
  "bigquery": {
    "silver_dataset": "road_safety_silver",
    "gold_dataset": "road_safety_gold",
    "control_dataset": "road_safety_control"
  }
}
```

`config/project.local.json` is excluded from Git and stores
environment-specific configuration.

### Source configuration

`config/sources.json` contains the public data.gouv.fr dataset API
endpoints used by the pipeline.

The source discovery logic queries these APIs to find the appropriate
BAAC and Météo-France resources dynamically.

---

## Installation

The project uses Python 3.12 and `uv` for dependency management.

```bash
uv sync
```

Authenticate locally with Google Cloud Application Default Credentials:

```bash
gcloud auth application-default login
```

The configured GCS bucket and GCP project must already exist.

---

# Running the pipeline

All main pipeline stages are executed through `GDtool.py`.

The pipeline is parameterized by year and department.

Example below:

```text
year       = 2024
department = 75
```

---

## 1. Bronze - BAAC ingestion

```bash
uv run python GDtool.py bronze --source baac --year 2024 --resource-type caract
```

The command:

1. queries the official BAAC dataset metadata;
2. discovers the resource corresponding to the requested year;
3. downloads the raw file;
4. uploads it unchanged to GCS Bronze.

Example object:

```text
bronze/
└── baac/
    └── year=2024/
        └── caract/
            └── caract-2024.csv
```

---

## 2. Bronze - Weather ingestion

```bash
uv run python GDtool.py bronze --source weather --year 2024 --department 75
```

The weather resource is dynamically selected according to the requested
department and the period containing the requested year.

Example:

```text
bronze/
└── weather/
    └── department=75/
        └── period=2020-2024/
            └── H_75_previous-2020-2024.csv.gz
```

---

## 3. Silver - Accidents

```bash
uv run python GDtool.py silver --dataset accidents --year 2024 --department 75
```

The Silver transformation:

- filters the requested department;
- standardizes timestamps;
- converts coordinates;
- selects useful accident attributes;
- writes the cleaned dataset as compressed Parquet.

Output:

```text
silver/
└── accidents/
    └── year=2024/
        └── department=75/
            └── accidents.parquet
```

---

## 4. Silver - Weather

```bash
uv run python GDtool.py silver --dataset weather --year 2024 --department 75
```

The transformation:

- parses weather timestamps;
- filters the requested year;
- standardizes station metadata;
- selects the required weather variables;
- writes the result as Parquet.

Output:

```text
silver/
└── weather/
    └── year=2024/
        └── department=75/
            └── weather.parquet
```

---

## 5. BigQuery loading

```bash
uv run python GDtool.py bigquery --year 2024 --department 75
```

This stage performs:

```text
GCS Silver Parquet
        │
        ▼
BigQuery staging tables
        │
        ▼
SQL MERGE
        │
        ▼
BigQuery Silver
        │
        ▼
Gold reconstruction
```

Temporary staging tables:

```text
road_safety_silver.stg_accidents
road_safety_silver.stg_weather
```

Persistent Silver tables:

```text
road_safety_silver.accidents
road_safety_silver.weather
```

---

## Incremental loading

The BigQuery Silver layer uses a staging + `MERGE` pattern.

### Accidents

Business key:

```text
accident_id
```

`merge_accidents.sql`:

- inserts new accidents;
- updates existing accidents only when their attributes changed;
- leaves identical rows untouched.

### Weather

Business key:

```text
(station_id, observation_timestamp)
```

`merge_weather.sql` applies the same upsert strategy to weather
observations.

This makes the BigQuery Silver loading process idempotent.

### Incremental loading validation

The pipeline was tested by loading Paris 2024 first and then Paris 2023.

New 2023 data produced:

```text
4,763 new accident rows
52,560 new weather observations
```

Reprocessing exactly the same 2023 partition produced:

```text
MERGE accidents → 0 affected rows
MERGE weather   → 0 affected rows
```

This demonstrates that replaying an already processed partition does not
create duplicates or unnecessary updates.

---

## Gold layer

The Gold table is generated by:

```text
sql/gold/accident_weather.sql
```

Target table:

```text
road_safety_gold.accident_weather
```

Its analytical grain is:

> **1 row = 1 road accident**

For every accident, BigQuery:

1. identifies the geographically nearest weather station;
2. calculates the distance with BigQuery GIS functions;
3. searches for the closest hourly weather observation;
4. enriches the accident with weather attributes.

Main BigQuery features used include:

```sql
ST_GEOGPOINT
ST_DISTANCE
ROW_NUMBER()
QUALIFY
TIMESTAMP_DIFF
```

The Gold table also keeps:

```text
station_id
station_name
distance_to_station_m
weather_timestamp
weather_time_difference_minutes
```

to make the matching process auditable.

---

## Data Quality

Run the Data Quality layer with:

```bash
uv run python GDtool.py quality --year 2024 --department 75
```

The checks are stored independently as SQL files.

### `duplicate_accidents.sql`

Checks the Gold grain:

```text
1 accident_id = 1 row
```

Any duplicate accident is considered a violation.

### `invalid_coordinates.sql`

Detects:

- missing coordinates;
- latitude outside `[-90, 90]`;
- longitude outside `[-180, 180]`.

### `missing_timestamps.sql`

Checks that both the accident timestamp and matched weather timestamp
are available.

### `matching_coverage.sql`

Produces matching metrics including:

- total accidents;
- matched accidents;
- unmatched accidents;
- matching rate;
- average / maximum station distance;
- average / maximum temporal difference.

### `weather_completeness.sql`

Measures missing values for:

- temperature;
- hourly rainfall;
- wind speed;
- wind direction.

These metrics distinguish pipeline correctness from source-data
completeness.

---

## Validation results

The pipeline has been tested on Paris accident and weather data for
2023 and 2024.

```text
Gold accidents                 8,954
Weather matching rate          100 %
Duplicate accidents            0
Invalid coordinates            0
Missing matching timestamps    0

Average station distance       ~2.28 km
Maximum station distance       ~9.39 km

Average temporal difference    ~15 min
Maximum temporal difference    30 min
```

Weather attribute completeness is not uniform across the source data.

For the current 2023-2024 Gold dataset:

```text
Missing temperature     0.45 %
Missing rainfall       24.61 %
Missing wind speed     58.53 %
```

A successful weather match therefore does not necessarily mean that
every meteorological variable is available.

---

## Utility scripts

### Explore source datasets

```bash
uv run python scripts/explore_sources.py baac
```

or:

```bash
uv run python scripts/explore_sources.py meteo-hourly
```

This utility lists available resources from the official metadata API.

### Inspect a resource

```bash
uv run python scripts/inspect_resource.py "<RESOURCE_URL>"
```

It can be used to inspect:

- schema;
- row count;
- station metadata;
- date range;
- null rates for candidate weather variables.

These scripts were primarily used during the initial source exploration
and Data Quality analysis.

---

## Current limitations

The current implementation intentionally keeps several topics for future
iterations:

- BigQuery Silver loading is incremental, while the Gold table is
  currently fully rebuilt.
- CLI commands currently process one year and one department per
  execution.
- Weather and BAAC timestamp timezone semantics require additional
  validation before advanced analytical interpretation.
- Weather-source missing values are currently monitored but not imputed.
- BigQuery partitioning and clustering are not introduced artificially
  at the current small dataset size.
- AWS implementation is not yet completed.

---

## Roadmap

Planned improvements include:

- deeper Data Quality profiling and quality thresholds;
- timezone normalization;
- automated tests;
- richer BAAC datasets (`lieux`, `vehicules`, `usagers`);
- additional geographic and administrative enrichment;
- orchestration;
- AWS implementation using equivalent cloud Data Engineering patterns.

The AWS target architecture will reproduce the same main concepts using
services such as S3 and an AWS analytical query / warehouse layer.

---

## Tech stack

```text
Python
SQL
Polars
Parquet
Google Cloud Storage
BigQuery
BigQuery GIS
Git / GitHub
uv
```

---

## Author
ls

**Mathieu Cowan**

Feel free to contact me on [LinkedIn](https://www.linkedin.com/in/mathieu-cowan/) !