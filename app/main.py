from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    StreamingResponse,
    HTMLResponse,
)
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
import httpx
import asyncio
import os
from datetime import datetime
from pathlib import Path
from .models import CCTVCamera, Highway, HighwayList
from .config import HIGHWAYS, get_highway_list
import aiofiles
from typing import Dict, List, AsyncGenerator
import json
import base64
import re
from dotenv import load_dotenv
from .db import (
    init_collections,
    save_highway,
    save_camera,
    save_camera_image,
    get_latest_camera_images,
)

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "5"))

# Configure logging
logger.add("scraper.log", rotation="500 MB")

app = FastAPI(title="LLM Highway Analytics API")

# Configure CORS - More permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Create storage directory with absolute path
STORAGE_DIR = Path(__file__).parent.parent / "storage"
IMAGES_DIR = STORAGE_DIR / "images"
METADATA_DIR = STORAGE_DIR / "metadata"

# Create necessary directories
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Storage directory: {STORAGE_DIR}")
logger.info(f"Images directory: {IMAGES_DIR}")
logger.info(f"Metadata directory: {METADATA_DIR}")

# Mount static directory for serving images with CORS
app.mount("/static", StaticFiles(directory=str(IMAGES_DIR)), name="static")

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Store active highways
active_highways: Dict[str, Highway] = {}

# Configure templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


async def fetch_camera_data(highway_code: str) -> List[Dict]:
    """Fetch camera data for a specific highway"""
    try:
        url = f"https://www.llm.gov.my/assets/ajax.vigroot.php?h={highway_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://www.llm.gov.my/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Cookie": "PHPSESSID=1",
        }

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()

            # Log raw response for debugging
            logger.debug(f"Raw response for {highway_code}: {response.text[:1000]}...")

            # Try multiple parsing approaches
            cameras = []
            text = response.text

            # Try to find image and name pairs - first approach with img and div pattern
            img_tags = re.findall(
                r'<img[^>]*src=["\'](data:image/[^"\']+)["\'][^>]*>', text
            )
            name_divs = re.findall(r'<div style="width:320px;">(.*?)</div>', text)

            if img_tags and name_divs and len(img_tags) == len(name_divs):
                logger.info(
                    f"Found {len(img_tags)} image+name pairs for {highway_code}"
                )
                for i, (img_data, name) in enumerate(zip(img_tags, name_divs)):
                    cameras.append(
                        {
                            "id": f"{highway_code}-{i+1}",
                            "name": name.strip(),
                            "image": img_data,
                        }
                    )
            elif img_tags:
                logger.info(
                    f"Found {len(img_tags)} images without matching names for {highway_code}"
                )
                for i, img_data in enumerate(img_tags):
                    cameras.append(
                        {
                            "id": f"{highway_code}-{i+1}",
                            "name": f"{highway_code} Camera {i+1}",
                            "image": img_data,
                        }
                    )

            # If still no cameras found, look for base64 data directly
            if not cameras:
                base64_matches = re.findall(
                    r'data:image/(?:jpeg|png|gif);base64,([^"\'}\s]+)', text
                )
                if base64_matches:
                    logger.info(
                        f"Found {len(base64_matches)} base64 images for {highway_code}"
                    )
                    for i, img_data in enumerate(base64_matches):
                        cameras.append(
                            {
                                "id": f"{highway_code}-{i+1}",
                                "name": f"{highway_code} Camera {i+1}",
                                "image": f"data:image/jpeg;base64,{img_data}",
                            }
                        )

            if cameras:
                logger.info(
                    f"Successfully extracted {len(cameras)} cameras for {highway_code}"
                )
                return cameras

            logger.error(f"No camera data found in HTML response for {highway_code}")
            logger.debug(f"Response content: {text[:500]}...")
            return []

    except httpx.RequestError as e:
        logger.error(
            f"Network error fetching data for highway {highway_code}: {str(e)}"
        )
        return []
    except Exception as e:
        logger.error(f"Error fetching camera data for highway {highway_code}: {str(e)}")
        logger.exception("Full error traceback:")
        return []


async def update_highway_data(highway_code: str):
    """Update data for a specific highway"""
    try:
        if highway_code not in HIGHWAYS:
            logger.error(f"Unknown highway code: {highway_code}")
            return

        cameras_data = await fetch_camera_data(highway_code)

        if not cameras_data:
            logger.warning(f"No cameras found for highway {highway_code}")
            # Keep existing cameras if we have them
            if (
                highway_code in active_highways
                and active_highways[highway_code].cameras
            ):
                logger.info(
                    f"Keeping existing {len(active_highways[highway_code].cameras)} cameras for {highway_code}"
                )
                return
            return

        # Save highway to PocketBase
        await save_highway(
            highway_code=highway_code,
            highway_name=HIGHWAYS[highway_code]["name"],
            highway_id=HIGHWAYS[highway_code]["id"],
        )

        # Update highway cameras
        highway = Highway(
            code=highway_code,
            id=HIGHWAYS[highway_code]["id"],
            name=HIGHWAYS[highway_code]["name"],
            cameras=[
                CCTVCamera(
                    camera_id=str(cam.get("id", f"{highway_code}-{i}")),
                    location_id=highway_code,
                    name=cam.get("name", f"Camera {i+1}"),
                    last_updated=datetime.now(),
                )
                for i, cam in enumerate(cameras_data)
                if cam.get("image")
                or cam.get("id")  # Only include cameras with either image or ID
            ],
        )

        if not highway.cameras:
            logger.warning(f"No valid cameras found in data for highway {highway_code}")
            return

        active_highways[highway_code] = highway
        logger.info(
            f"Updated {len(highway.cameras)} cameras for highway {highway_code}"
        )

        # Save cameras to PocketBase
        for camera in highway.cameras:
            await save_camera(
                camera_id=camera.camera_id,
                name=camera.name,
                location_id=camera.location_id,
                highway_code=highway_code,
            )

        # Save images if present
        timestamp = datetime.now()
        saved_count = 0

        for camera in highway.cameras:
            try:
                # Get image data from cameras_data
                camera_data = next(
                    (
                        cam
                        for cam in cameras_data
                        if str(cam.get("id")) == camera.camera_id
                    ),
                    None,
                )

                if not camera_data or not camera_data.get("image"):
                    logger.warning(
                        f"No image data for camera {camera.camera_id} ({camera.name})"
                    )
                    continue

                # Remove data:image/jpeg;base64, prefix if present
                base64_data = camera_data["image"].split(",")[-1].strip()
                if not base64_data:
                    logger.warning(
                        f"Empty base64 data for camera {camera.camera_id} ({camera.name})"
                    )
                    continue

                try:
                    image_data = base64.b64decode(base64_data)
                except Exception as e:
                    logger.error(
                        f"Failed to decode base64 data for camera {camera.camera_id} ({camera.name}): {str(e)}"
                    )
                    continue

                # Validate image data
                if len(image_data) < 100:  # Basic size check
                    logger.warning(
                        f"Suspiciously small image data ({len(image_data)} bytes) for camera {camera.camera_id}"
                    )
                    continue

                # Create filename with camera details - use NKVE for consistency
                highway_prefix = "NKVE" if highway_code == "NKV" else highway_code
                filename = f"{highway_prefix}_{camera.camera_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
                file_path = IMAGES_DIR / filename

                # Save image
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(image_data)

                # Save to PocketBase
                await save_camera_image(
                    camera_id=camera.camera_id,
                    image_path=f"/static/{filename}",
                    timestamp=timestamp,
                    file_size=len(image_data),
                )

                saved_count += 1
                logger.info(
                    f"Saved image ({len(image_data)} bytes) for camera {camera.name} ({camera.camera_id})"
                )

            except Exception as e:
                logger.error(
                    f"Error saving image for camera {camera.camera_id} ({camera.name}): {str(e)}"
                )
                logger.exception("Full error traceback:")

        logger.info(
            f"Successfully saved {saved_count} out of {len(highway.cameras)} images for highway {highway_code}"
        )

    except Exception as e:
        logger.error(f"Error updating highway {highway_code}: {str(e)}")
        logger.exception("Full error traceback:")


@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    try:
        logger.info("Starting highway monitoring application...")
        logger.info("API endpoints available at:")
        logger.info("  - GET /highways - List all highways with camera data")
        logger.info(
            "  - GET /highways/{highway_code} - Get details for a specific highway"
        )
        logger.info(
            "  - GET /cameras?highway_code={code} - Get cameras (optionally filtered by highway)"
        )
        logger.info(
            "  - GET /images?highway_code={code}&camera_id={id}&limit={n} - Get images with flexible filtering"
        )
        logger.info("  - GET /health - API health check")
        logger.info("  - GET / - Web dashboard")

        # Initialize PocketBase collections
        try:
            logger.info("Initializing PocketBase collections...")
            pb_init_result = await init_collections()
            if pb_init_result:
                logger.info("PocketBase collections initialized successfully")
            else:
                logger.warning(
                    "PocketBase collections initialization skipped or failed"
                )
                logger.warning(
                    "You may need to create collections manually through the PocketBase admin UI"
                )
        except Exception as pb_error:
            logger.error(f"Error initializing PocketBase: {str(pb_error)}")
            logger.warning(
                "Continuing with application startup despite PocketBase initialization error"
            )

        # Initialize highways from static config
        for code, highway_data in HIGHWAYS.items():
            highway = Highway(
                id=highway_data["id"],
                code=code,
                name=highway_data["name"],
                cameras=[],  # Start with empty cameras list
            )
            active_highways[code] = highway

            # Add scheduler job for each highway
            scheduler.add_job(
                update_highway_data,
                trigger=IntervalTrigger(minutes=SCRAPE_INTERVAL_MINUTES),
                args=[code],
                id=f"update_{code}",
                replace_existing=True,
            )

            # Fetch initial data for all highways asynchronously
            asyncio.create_task(update_highway_data(code))

        scheduler.start()
        logger.info(
            f"Application startup complete. Initialized {len(HIGHWAYS)} highways for monitoring."
        )
        logger.info(f"Images will be updated every {SCRAPE_INTERVAL_MINUTES} minutes.")
    except Exception as e:
        logger.error(f"Error in startup: {str(e)}")
        logger.exception("Full startup error traceback:")
        raise


@app.get("/highways", response_model=HighwayList)
async def get_highways():
    """Get list of all highways"""
    highways = [
        Highway(
            id=data["id"],
            code=code,
            name=data["name"],
            cameras=active_highways[code].cameras if code in active_highways else [],
        )
        for code, data in HIGHWAYS.items()
    ]
    return HighwayList(highways=highways)


@app.get("/highways/{highway_code}")
async def get_highway(highway_code: str):
    """Get details for a specific highway"""
    if highway_code not in HIGHWAYS:
        raise HTTPException(status_code=404, detail="Highway not found")

    highway_data = HIGHWAYS[highway_code]
    cameras = (
        active_highways[highway_code].cameras if highway_code in active_highways else []
    )

    return Highway(
        id=highway_data["id"],
        code=highway_code,
        name=highway_data["name"],
        cameras=cameras,
    )


@app.get("/cameras")
async def get_cameras(highway_code: str = None):
    """Get all cameras, optionally filtered by highway"""
    if highway_code:
        if highway_code not in active_highways:
            raise HTTPException(status_code=404, detail="Highway not found")
        return active_highways[highway_code].cameras
    else:
        # Return all cameras from all highways
        all_cameras = []
        for code, highway in active_highways.items():
            all_cameras.extend(highway.cameras)
        return all_cameras


async def stream_image_chunks(
    image_path: Path, chunk_size: int = 8192
) -> AsyncGenerator[bytes, None]:
    """Stream image file in chunks"""
    async with aiofiles.open(image_path, "rb") as f:
        while chunk := await f.read(chunk_size):
            yield chunk


@app.get("/images")
async def get_images(highway_code: str = None, camera_id: str = None, limit: int = 20):
    """
    Get latest images with flexible filtering:
    - If both highway_code and camera_id are provided, get latest image for that camera
    - If only highway_code is provided, get latest images for that highway
    - If neither is provided, get latest images across all highways
    """
    try:
        # Get images based on the provided filters
        images = await get_latest_camera_images(
            highway_code=highway_code, camera_id=camera_id, limit=limit
        )

        if not images and highway_code:
            # Try to fetch new data if we have a highway code
            await update_highway_data(highway_code)
            # Check again
            images = await get_latest_camera_images(
                highway_code=highway_code, camera_id=camera_id, limit=limit
            )

        if not images:
            raise HTTPException(
                status_code=404, detail="No images found matching the criteria"
            )

        # Format response based on whether we're requesting a single camera or multiple
        if camera_id:
            # Single camera response (just the latest image)
            latest_image = images[0]
            return {
                "highway_code": latest_image["highway"]["code"],
                "highway_name": latest_image["highway"]["name"],
                "camera_id": latest_image["camera"]["camera_id"],
                "camera_name": latest_image["camera"]["name"],
                "timestamp": latest_image["capture_time"],
                "image_url": latest_image["image_path"],
            }
        else:
            # Format multi-camera response
            formatted_images = []
            camera_processed = (
                set()
            )  # Track processed cameras to get only latest per camera

            for image in images:
                cam_id = image["camera"]["camera_id"]
                if highway_code or cam_id not in camera_processed:
                    # If filtering by highway, include all images; otherwise just the latest per camera
                    camera_processed.add(cam_id)
                    formatted_images.append(
                        {
                            "highway_code": image["highway"]["code"],
                            "highway_name": image["highway"]["name"],
                            "camera_id": cam_id,
                            "camera_name": image["camera"]["name"],
                            "timestamp": image["capture_time"],
                            "image_url": image["image_path"],
                        }
                    )

            return {
                "count": len(formatted_images),
                "images": formatted_images,
            }

    except Exception as e:
        logger.error(f"Error getting images: {str(e)}")
        logger.exception("Full error traceback:")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "storage_dir": str(STORAGE_DIR),
        "storage_exists": STORAGE_DIR.exists(),
        "storage_is_dir": STORAGE_DIR.is_dir(),
        "active_highways": len(active_highways),
        "image_count": len(list(IMAGES_DIR.glob("*.jpg"))),
    }


@app.get("/", response_class=HTMLResponse)
async def root(request):
    """Serve the main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})
