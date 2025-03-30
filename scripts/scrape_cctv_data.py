#!/usr/bin/env python3

import requests
import pandas as pd
from datetime import datetime
import logging
from pathlib import Path
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fetch_cctv_data():
    """Fetch CCTV data from LLM API."""
    url = "https://gis02.llm.gov.my/llmsmpt/rest/services/TMC/Highway_CCTV_Image/FeatureServer/0/query"

    geometry = {
        "xmin": 11271098.442803863,
        "ymin": 313086.0678654611,
        "xmax": 11427641.47673183,
        "ymax": 469629.1017934233,
        "spatialReference": {"wkid": 102100},
    }

    params = {
        "f": "json",
        "returnGeometry": "true",
        "spatialRel": "esriSpatialRelIntersects",
        "geometry": json.dumps(geometry),
        "geometryType": "esriGeometryEnvelope",
        "inSR": 102100,
        "outFields": "*",
        "outSR": 102100,
        "resultType": "tile",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response data: {json.dumps(data, indent=2)}")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data: {e}")
        logger.error(
            f"Response content: {response.text if 'response' in locals() else 'No response'}"
        )
        raise


def parse_date(date_str):
    """Parse date string to standard format."""
    if not date_str:
        return None

    # Try different date formats
    formats = [
        "%m/%d/%Y %H:%M",  # 7/13/2017 15:39
        "%d/%m/%Y %H:%M",  # 26/8/2022 13:17
        "%d/%m/%Y",  # 7/6/2022
        "%m/%d/%Y",  # Fallback format
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None


def process_cctv_data(data):
    """Process CCTV data into a pandas DataFrame."""
    records = []

    features = data.get("features", [])
    logger.info(f"Found {len(features)} features in the response")

    for feature in features:
        attrs = feature.get("attributes", {})
        geom = feature.get("geometry", {})

        record = {
            "object_id": attrs.get("OBJECTID"),
            "id": attrs.get("ID"),
            "camera": attrs.get("Camera"),
            "plaza_code": attrs.get("Plaza_Code"),
            "highway_code": attrs.get("Highway_Co"),
            "cctv_url": attrs.get("CCTV_URL"),
            "date_modified": parse_date(attrs.get("Date_Modif")),
            "latitude": attrs.get("Y"),
            "longitude": attrs.get("X"),
            "highway_name": attrs.get("Highway"),
            "geom_x": geom.get("x"),
            "geom_y": geom.get("y"),
        }
        records.append(record)

    df = pd.DataFrame(records)
    logger.info(f"Processed {len(df)} records")
    return df


def main():
    """Main function to fetch and save CCTV data."""
    try:
        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # Fetch and process data
        logger.info("Fetching CCTV data...")
        raw_data = fetch_cctv_data()

        logger.info("Processing data...")
        df = process_cctv_data(raw_data)

        if len(df) == 0:
            logger.warning("No data was retrieved. Check the API response.")
            return

        # Save to CSV
        output_file = (
            data_dir / f"cctv_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        df.to_csv(output_file, index=False)
        logger.info(f"Data saved to {output_file}")

        # Print summary
        logger.info(f"Total records processed: {len(df)}")
        logger.info(f"Columns: {', '.join(df.columns)}")

        # Print first few records
        logger.info("\nFirst few records:")
        print(df.head().to_string())

    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise


if __name__ == "__main__":
    main()
