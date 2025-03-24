#!/opt/homebrew/bin/python3

import asyncio
import httpx
import base64
import json
from pathlib import Path
from datetime import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import re
from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to Python path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import HIGHWAYS, get_highway_codes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("image_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Get highway codes from config
HIGHWAY_CODES = get_highway_codes()
logger.info(
    f"Loaded {len(HIGHWAY_CODES)} highway codes from config: {', '.join(HIGHWAY_CODES)}"
)

# Create storage directories
STORAGE_DIR = Path(__file__).parent.parent / "storage"
IMAGES_DIR = STORAGE_DIR / "images"
METADATA_DIR = STORAGE_DIR / "metadata"

for directory in [STORAGE_DIR, IMAGES_DIR, METADATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created directory: {directory}")


async def fetch_camera_data(highway_code: str):
    """Fetch camera data from the highway"""
    try:
        if highway_code not in HIGHWAYS:
            logger.error(f"Invalid highway code: {highway_code}")
            return []

        url = f"https://www.llm.gov.my/assets/ajax.vigroot.php?h={highway_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://www.llm.gov.my/",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Cookie": "PHPSESSID=1",
        }

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()

            # Try multiple parsing approaches
            cameras = []

            # Approach 1: Try to parse as JSON
            try:
                data = response.json()
                if isinstance(data, list):
                    cameras.extend(
                        [{**cam, "image_url": cam.get("image")} for cam in data]
                    )
                elif isinstance(data, dict):
                    cameras.append({**data, "image_url": data.get("image")})

                if cameras:
                    logger.info(
                        f"Successfully parsed JSON data for {highway_code}, found {len(cameras)} cameras"
                    )
                    return cameras
            except json.JSONDecodeError:
                logger.debug(
                    f"Failed to parse JSON for {highway_code}, trying HTML parsing"
                )

            # Approach 2: Try to parse HTML and find image URLs
            text = response.text
            soup = BeautifulSoup(text, "html.parser")

            # Look for img tags
            img_tags = soup.find_all("img")
            if img_tags:
                logger.debug(f"Found {len(img_tags)} img tags for {highway_code}")
                for i, img in enumerate(img_tags):
                    src = img.get("src", "")
                    if "data:image/jpeg;base64," in src:
                        cameras.append(
                            {
                                "id": f"{highway_code}-{i+1}",
                                "image_url": src,
                                "name": f"{HIGHWAYS[highway_code]['name']} Camera {i+1}",
                            }
                        )

            # Approach 3: Try to find image URLs directly in HTML
            if not cameras:
                image_matches = re.findall(r'data:image/jpeg;base64,([^"\'}\s]+)', text)
                if image_matches:
                    logger.debug(
                        f"Found {len(image_matches)} base64 images in HTML for {highway_code}"
                    )
                    for i, img in enumerate(image_matches):
                        cameras.append(
                            {
                                "id": f"{highway_code}-{i+1}",
                                "image_url": f"data:image/jpeg;base64,{img}",
                                "name": f"{HIGHWAYS[highway_code]['name']} Camera {i+1}",
                            }
                        )

            if cameras:
                logger.info(
                    f"Successfully extracted {len(cameras)} cameras for {highway_code}"
                )
                return cameras

            logger.error(f"No valid data found in response for {highway_code}")
            return []

    except Exception as e:
        logger.error(f"Error fetching camera data for {highway_code}: {str(e)}")
        logger.exception("Full traceback:")
        return []


async def save_images(highway_code: str):
    """Save images for a highway"""
    try:
        cameras = await fetch_camera_data(highway_code)
        if not cameras:
            logger.warning(f"No cameras found for highway {highway_code}")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for camera in cameras:
            try:
                # Generate filenames
                image_filename = f"{highway_code}_{camera['id']}_{timestamp}.jpg"
                metadata_filename = f"{highway_code}_{camera['id']}_{timestamp}.json"
                image_path = IMAGES_DIR / image_filename

                # Extract and save image data in chunks
                if "image_url" in camera and camera["image_url"]:
                    image_url = camera["image_url"]
                    if image_url.startswith("data:image/jpeg;base64,"):
                        # Handle base64 data in chunks
                        base64_data = image_url.split("base64,")[1]
                        chunk_size = 1024 * 1024  # 1MB chunks

                        with open(image_path, "wb") as f:
                            for i in range(0, len(base64_data), chunk_size):
                                chunk = base64_data[i : i + chunk_size]
                                image_chunk = base64.b64decode(chunk)
                                f.write(image_chunk)

                        logger.info(f"Saved image in chunks: {image_filename}")
                    else:
                        # Handle direct URL
                        async with httpx.AsyncClient() as client:
                            async with client.stream("GET", image_url) as response:
                                response.raise_for_status()
                                with open(image_path, "wb") as f:
                                    async for chunk in response.aiter_bytes():
                                        f.write(chunk)

                        logger.info(f"Saved image from URL: {image_filename}")

                # Save metadata
                metadata = {
                    "highway_code": highway_code,
                    "highway_name": HIGHWAYS[highway_code]["name"],
                    "camera_id": camera["id"],
                    "camera_name": camera["name"],
                    "timestamp": timestamp,
                    "image_filename": image_filename,
                }

                metadata_path = METADATA_DIR / metadata_filename
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                logger.info(f"Saved metadata: {metadata_filename}")

            except Exception as e:
                logger.error(
                    f"Error saving camera {camera['id']} for highway {highway_code}: {str(e)}"
                )
                continue

    except Exception as e:
        logger.error(f"Error in save_images for highway {highway_code}: {str(e)}")
        logger.exception("Full traceback:")


async def cleanup_old_files():
    """Delete files older than 7 days"""
    try:
        current_time = datetime.now()
        for directory in [IMAGES_DIR, METADATA_DIR]:
            for file_path in directory.glob("*"):
                file_age = current_time - datetime.fromtimestamp(
                    file_path.stat().st_mtime
                )
                if file_age.days > 7:
                    file_path.unlink()
                    logger.info(f"Deleted old file: {file_path}")
    except Exception as e:
        logger.error(f"Error in cleanup_old_files: {str(e)}")


async def main():
    """Main function to run the scheduler"""
    scheduler = AsyncIOScheduler()

    # Schedule image saving every 5 minutes for each highway
    for highway_code in HIGHWAY_CODES:
        scheduler.add_job(
            lambda hc=highway_code: asyncio.create_task(
                save_images(hc)
            ),  # Use closure to capture highway_code
            trigger=IntervalTrigger(minutes=5),
            id=f"save_images_{highway_code}",
            replace_existing=True,
        )

    # Schedule cleanup every day
    scheduler.add_job(
        lambda: asyncio.create_task(cleanup_old_files()),
        trigger=IntervalTrigger(days=1),
        id="cleanup_old_files",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")

    # Run initial jobs immediately
    for highway_code in HIGHWAY_CODES:
        await save_images(highway_code)
    await cleanup_old_files()

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
