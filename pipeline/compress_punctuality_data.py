# The compression of the dataset is done by converting most of the string by
# int using maps, in order to decrease the size of the dataset.
# The column relation-direction is also split into start and end in order to
# facilitate later analysis.

import csv
import os
from pathlib import Path

import pandas as pd

# Every path is resolved from the project root, so the script can be run from
# anywhere.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"

RELATION_FILE = REFERENCE_DIR / "RELATION.csv"
STATION_FILE = REFERENCE_DIR / "UNIQUE_STATION.csv"
TRAIN_SERV_FILE = REFERENCE_DIR / "TRAIN_SERV.csv"

DATASET_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"
DATASET_FILES = sorted(
    dataset_filename
    for dataset_filename in os.listdir(DATASET_DIR)
    if dataset_filename.endswith(".csv")
)

# Columns that contain dates to be converted to datetime
DATE_COLUMNS = ["DATDEP"]

# Columns in common across all datasets
COMMON_COLUMNS = [
    "DATDEP",
    "TRAIN_NO",
    "RELATION",
    "TRAIN_SERV",
    "PTCAR_NO",
    "LINE_NO_DEP",
    "REAL_TIME_ARR",
    "REAL_TIME_DEP",
    "PLANNED_TIME_ARR",
    "PLANNED_TIME_DEP",
    "DELAY_ARR",
    "DELAY_DEP",
    "PTCAR_LG_NM_NL",
    "LINE_NO_ARR",
    "RELATION_DIRECTION",
]

# Mapping to rename columns to match the database
COLUMN_NAMES = {
    "DATDEP": "departure_date",
    "TRAIN_NO": "train_number",
    "RELATION": "relation",
    "TRAIN_SERV": "train_service",
    "PTCAR_NO": "ptcar_number",
    "LINE_NO_DEP": "line_number_departure",
    "REAL_TIME_ARR": "real_time_arrival",
    "REAL_TIME_DEP": "real_time_departure",
    "PLANNED_TIME_ARR": "planned_time_arrival",
    "PLANNED_TIME_DEP": "planned_time_departure",
    "DELAY_ARR": "delay_arrival",
    "DELAY_DEP": "delay_departure",
    "PTCAR_LG_NM_NL": "ptcar_name",
    "LINE_NO_ARR": "line_number_arrival",
    "START": "station_departure",
    "END": "station_arrival",
}

if (
    not os.path.exists(RELATION_FILE)
    or not os.path.exists(STATION_FILE)
    or not os.path.exists(TRAIN_SERV_FILE)
):
    relation_names = set()
    station_names = set()
    service_names = set()

    for dataset_file in DATASET_FILES:
        punctuality_data = pd.read_csv(
            DATASET_DIR / dataset_file, low_memory=False
        )
        # Relation
        unique_values = set(punctuality_data["RELATION"].unique())
        relation_names.update(unique_values)

        # PTCAR_LG_NM_NL and RELATION_DIRECTION
        punctuality_data["RELATION_DIRECTION"] = punctuality_data[
            "RELATION_DIRECTION"
        ].fillna("")  # Fill NaN with an empty string
        punctuality_data["RELATION_DIRECTION"] = punctuality_data[
            "RELATION_DIRECTION"
        ].str.replace(r"^[^:]+:\s*", "", regex=True)
        route_endpoints = punctuality_data["RELATION_DIRECTION"].str.split(
            " -> ", expand=True, n=1
        )

        punctuality_data["START"] = route_endpoints[0].fillna("")
        punctuality_data["END"] = (
            route_endpoints[1].fillna("") if 1 in route_endpoints else ""
        )

        punctuality_data.drop("RELATION_DIRECTION", axis=1, inplace=True)
        unique_values = set(
            punctuality_data[["PTCAR_LG_NM_NL", "START", "END"]].values.ravel()
        )  # transform numpy into (ravel)1d array
        station_names.update(unique_values)

        # TRAIN_SERV
        unique_values = set(punctuality_data["TRAIN_SERV"].unique())
        service_names.update(unique_values)

    relation_names = sorted(
        [item for item in relation_names if isinstance(item, str)]
    )
    relation_ids = {
        name: identifier for identifier, name in enumerate(relation_names)
    }

    station_names = sorted(
        [item for item in station_names if isinstance(item, str)]
    )
    station_ids = {
        name: identifier for identifier, name in enumerate(station_names)
    }

    service_names = sorted(
        [item for item in service_names if isinstance(item, str)]
    )
    service_ids = {
        name: identifier for identifier, name in enumerate(service_names)
    }

    if not RELATION_FILE.exists():
        with open(RELATION_FILE, mode="w", newline="") as dataset_file:
            writer = csv.writer(dataset_file)
            writer.writerow(["ID", "RELATION"])
            for label, identifier in relation_ids.items():
                writer.writerow([identifier, label])

    if not STATION_FILE.exists():
        with open(STATION_FILE, mode="w", newline="") as dataset_file:
            writer = csv.writer(dataset_file)
            writer.writerow(["ID", "STATION"])
            for label, identifier in station_ids.items():
                writer.writerow([identifier, label])

    if not TRAIN_SERV_FILE.exists():
        with open(TRAIN_SERV_FILE, mode="w", newline="") as dataset_file:
            writer = csv.writer(dataset_file)
            writer.writerow(["ID", "TRAIN_SERV"])
            for label, identifier in service_ids.items():
                writer.writerow([identifier, label])

relation_df = pd.read_csv(RELATION_FILE, index_col=1, keep_default_na=False)
relation_df = relation_df.rename(columns={"id": "ID"})
relation_ids = relation_df["ID"].to_dict()

stations_df = pd.read_csv(STATION_FILE, index_col=1, keep_default_na=False)
stations_df = stations_df.rename(columns={"id": "ID"})
station_ids = stations_df["ID"].to_dict()

services_df = pd.read_csv(TRAIN_SERV_FILE, index_col=1, keep_default_na=False)
services_df = services_df.rename(columns={"id": "ID"})
service_ids = services_df["ID"].to_dict()

if not os.path.exists(CLEANED_DIR):
    os.mkdir(CLEANED_DIR)

for dataset_file in DATASET_FILES:
    punctuality_data = pd.read_csv(
        DATASET_DIR / dataset_file, low_memory=False, usecols=COMMON_COLUMNS
    )

    # We transform the date column to datetime
    for date_column in DATE_COLUMNS:
        punctuality_data[date_column] = pd.to_datetime(
            punctuality_data[date_column], format="%d%b%Y", errors="coerce"
        )

    # We transform the categorical columns to integers which is a mapping of
    # the unique values
    punctuality_data["RELATION"] = punctuality_data["RELATION"].map(
        relation_ids
    )

    punctuality_data["TRAIN_SERV"] = punctuality_data["TRAIN_SERV"].map(
        service_ids
    )

    punctuality_data["PTCAR_LG_NM_NL"] = punctuality_data[
        "PTCAR_LG_NM_NL"
    ].map(station_ids)

    # We split the RELATION_DIRECTION column into START and END columns
    punctuality_data["RELATION_DIRECTION"] = punctuality_data[
        "RELATION_DIRECTION"
    ].fillna("")  # Fill NaN with an empty string
    punctuality_data["RELATION_DIRECTION"] = punctuality_data[
        "RELATION_DIRECTION"
    ].str.replace(r"^[^:]+:\s*", "", regex=True)
    route_endpoints = punctuality_data["RELATION_DIRECTION"].str.split(
        " -> ", expand=True, n=1
    )
    punctuality_data["START"] = route_endpoints[0].fillna("")
    punctuality_data["END"] = (
        route_endpoints[1].fillna("") if 1 in route_endpoints else ""
    )

    # We map them to integers which is a mapping of the unique values
    punctuality_data["START"] = punctuality_data["START"].map(station_ids)
    punctuality_data["END"] = punctuality_data["END"].map(station_ids)

    # Since RELATION_DIRECTION is now useless, we drop it
    punctuality_data.drop("RELATION_DIRECTION", axis=1, inplace=True)

    punctuality_data = punctuality_data.rename(columns=COLUMN_NAMES)

    # we ensure that all columns has their type
    for column in [
        "relation",
        "train_service",
        "ptcar_name",
        "station_departure",
        "station_arrival",
    ]:
        punctuality_data[column] = punctuality_data[column].astype("Int64")

    punctuality_data["delay_arrival"] = punctuality_data[
        "delay_arrival"
    ].astype("float64")

    punctuality_data["delay_departure"] = punctuality_data[
        "delay_departure"
    ].astype("float64")

    punctuality_data.to_csv(CLEANED_DIR / dataset_file, index=False)
    print(f"Finished cleaning {dataset_file}")
