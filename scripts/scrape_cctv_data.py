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
    """Fetch CCTV data from LLM API for multiple regions."""
    url = "https://gis02.llm.gov.my/llmsmpt/rest/services/TMC/Highway_CCTV_Image/FeatureServer/0/query"

    # Define base geometries with different resolutions
    geometries = []

    # Resolution 1: ~78,271 units (from first working URL)
    base_width_1 = 78271.517
    base_height_1 = 78271.517

    # Resolution 2: ~156,543 units (from second working URL)
    base_width_2 = 156543.034
    base_height_2 = 156543.034

    # Define the full area to cover
    full_area = {
        "xmin": 10018754.171386987,  # Westernmost point
        "ymin": 0.0,  # Southernmost point
        "xmax": 11900000.0,  # Easternmost point
        "ymax": 800000.0,  # Northernmost point
    }

    # Generate grid cells with both resolutions
    for base_width, base_height in [
        (base_width_1, base_height_1),
        (base_width_2, base_height_2),
    ]:
        overlap_factor = 0.5
        step_x = base_width * (1 - overlap_factor)
        step_y = base_height * (1 - overlap_factor)

        current_y = full_area["ymin"]
        while current_y < full_area["ymax"]:
            current_x = full_area["xmin"]
            while current_x < full_area["xmax"]:
                cell = {
                    "xmin": current_x,
                    "ymin": current_y,
                    "xmax": min(current_x + base_width, full_area["xmax"]),
                    "ymax": min(current_y + base_height, full_area["ymax"]),
                    "spatialReference": {"wkid": 102100},
                }
                geometries.append(cell)
                current_x += step_x
            current_y += step_y

    # Add specific known working regions
    known_regions = [
        {
            # Central KL (known working)
            "xmin": 11271098.44283168,
            "ymin": 313086.06784793735,
            "xmax": 11349369.959795732,
            "ymax": 391357.5848119855,
            "spatialReference": {"wkid": 102100},
        },
        {
            # Greater KL (known working)
            "xmin": 11271098.442804527,
            "ymin": 313086.0678650439,
            "xmax": 11427641.476732496,
            "ymax": 469629.1017930098,
            "spatialReference": {"wkid": 102100},
        },
    ]
    geometries.extend(known_regions)

    # Add specific highway regions
    highway_regions = [
        # PLUS North
        {
            "xmin": 11271098.442804527,
            "ymin": 469629.1017930098,
            "xmax": 11427641.476732496,
            "ymax": 800000.0,
            "spatialReference": {"wkid": 102100},
        },
        # PLUS South
        {
            "xmin": 11271098.442810982,
            "ymin": 100000.0,
            "xmax": 11584184.510673836,
            "ymax": 313086.0678654611,
            "spatialReference": {"wkid": 102100},
        },
        # East Coast
        {
            "xmin": 11427641.47673183,
            "ymin": 100000.0,
            "xmax": 11900000.0,
            "ymax": 800000.0,
            "spatialReference": {"wkid": 102100},
        },
        # West Coast
        {
            "xmin": 10018754.171386987,
            "ymin": 313086.0678654611,
            "xmax": 11271098.442803863,
            "ymax": 800000.0,
            "spatialReference": {"wkid": 102100},
        },
    ]
    geometries.extend(highway_regions)

    all_features = []
    seen_cameras = set()
    total_features = 0

    for i, geometry in enumerate(geometries, 1):
        region_name = f"Region {i}"

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
            logger.info(f"Fetching data for {region_name}...")
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            features = data.get("features", [])
            total_features += len(features)

            # Filter out duplicates based on Camera field
            new_features = []
            for feature in features:
                camera = feature.get("attributes", {}).get("Camera")
                if camera and camera not in seen_cameras:
                    seen_cameras.add(camera)
                    new_features.append(feature)

            logger.info(
                f"Found {len(features)} features in {region_name} (unique: {len(new_features)})"
            )
            all_features.extend(new_features)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data for {region_name}: {e}")
            logger.error(
                f"Response content: {response.text if 'response' in locals() else 'No response'}"
            )
            continue

    logger.info(f"Total features found: {total_features}")
    logger.info(f"Total unique features: {len(all_features)}")
    return {"features": all_features}


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
