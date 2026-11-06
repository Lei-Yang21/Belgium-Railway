# Simple file that will scrape the dataset using every link found in
# monthly_punctuality_urls.csv

import os
from pathlib import Path

import pandas as pd
import requests

# Every path is resolved from the project root, so the script can be run from
# anywhere.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

monthly_download_links = pd.read_csv(
    PROJECT_ROOT / "data" / "reference" / "monthly_punctuality_urls.csv",
    sep=";",
)

# Create a folder to store the dataset
DOWNLOAD_FOLDER = PROJECT_ROOT / "data" / "raw"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

for index, row in monthly_download_links.iterrows():
    url = row["Lien vers les données"]
    download_path = os.path.join(DOWNLOAD_FOLDER, url.split("/")[-1])
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(download_path, "wb") as file_handle:
            for chunk in response.iter_content(1024):
                file_handle.write(chunk)
        print(f"Downloaded {download_path}")
    else:
        print(f"Failed to download {download_path}")
