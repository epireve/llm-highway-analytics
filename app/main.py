from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
import httpx
import asyncio
import os
from datetime import datetime
from pathlib import Path
from .models import CCTVImage, CCTVLocation, CCTVCamera
import aiofiles
from typing import Dict, List
import json
from starlette.responses import Response
from starlette.background import BackgroundTask
import time

# Configure logging
logger.add("scraper.log", rotation="500 MB")

app = FastAPI(title="JalanOw Analytics API")

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
STORAGE_DIR = Path(__file__).parent.parent / "storage" / "images"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Storage directory: {STORAGE_DIR}")


# Custom static files handler with CORS headers
class CORSStaticFiles(StaticFiles):
    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            response = await super().__call__(scope, receive, send)
            if isinstance(response, Response):
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Cache-Control"] = "no-cache"
                return response
        return await super().__call__(scope, receive, send)


# Mount static directory for serving images with CORS
app.mount("/static", CORSStaticFiles(directory=str(STORAGE_DIR)), name="static")

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Store active locations
active_locations: Dict[str, CCTVLocation] = {}


async def fetch_image_with_retry(
    client: httpx.AsyncClient, camera: CCTVCamera, max_retries: int = 3
) -> CCTVImage:
    """Fetch a single CCTV image with retries"""
    last_error = None

    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.jalanow.com/",
                "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }

            url = str(camera.url)
            logger.info(
                f"Fetching image from {url} (attempt {attempt + 1}/{max_retries})"
            )

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                if len(response.content) < 1000:  # Basic check for valid image
                    raise ValueError("Response too small to be a valid image")

                # Generate filename with timestamp
                timestamp = datetime.now()
                filename = f"{camera.location_id}_{camera.camera_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
                file_path = STORAGE_DIR / filename

                # Save image
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(response.content)

                logger.info(f"Successfully saved image to {file_path}")

                return CCTVImage(
                    url=camera.url,
                    location_id=camera.location_id,
                    camera_id=camera.camera_id,
                    name=camera.name,
                    timestamp=timestamp,
                    status="success",
                )

        except Exception as e:
            last_error = e
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed for {url}: {str(e)}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
            continue

    logger.error(f"All attempts failed for {url}: {str(last_error)}")
    return CCTVImage(
        url=camera.url,
        location_id=camera.location_id,
        camera_id=camera.camera_id,
        name=camera.name,
        timestamp=datetime.now(),
        status="error",
        error_message=str(last_error),
    )


async def fetch_location_images(location: CCTVLocation):
    """Fetch all images for a location"""
    try:
        tasks = []
        for camera in location.cameras:
            task = fetch_image_with_retry(None, camera)  # client is created per retry
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Log results
        success_count = sum(1 for r in results if r.status == "success")
        logger.info(
            f"Fetched {success_count}/{len(tasks)} images for {location.location_id}"
        )

        # Schedule immediate retry for failed cameras
        if success_count < len(tasks):
            failed_cameras = [
                camera
                for camera, result in zip(location.cameras, results)
                if result.status == "error"
            ]
            logger.warning(
                f"Scheduling immediate retry for {len(failed_cameras)} failed cameras"
            )
            for camera in failed_cameras:
                asyncio.create_task(fetch_image_with_retry(None, camera))

    except Exception as e:
        logger.error(f"Error in fetch_location_images: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    try:
        # Add initial location
        nkve_location = CCTVLocation(
            location_id="NKVE",
            name="New Klang Valley Expressway",
            base_url="https://www.jalanow.com/malaysia-highway-E1-NKVE-New-Klang-Valley-Expressway-live-traffic-cam.php",
            cameras=[
                CCTVCamera(
                    camera_id="NKVE-11",
                    location_id="NKVE",
                    name="NKVE DAMANSARA KM17.95 NB",
                    url="https://w6.fgies.com//sd-nkve/NKVE-11.jpg",
                ),
                CCTVCamera(
                    camera_id="NKVE-12",
                    location_id="NKVE",
                    name="NKVE DAMANSARA KM17.95 SB",
                    url="https://w6.fgies.com//sd-nkve/NKVE-12.jpg",
                ),
                CCTVCamera(
                    camera_id="NKVE-21",
                    location_id="NKVE",
                    name="NKVE JALAN DUTA KM14.7 NB",
                    url="https://w6.fgies.com//sd-nkve/NKVE-21.jpg",
                ),
                CCTVCamera(
                    camera_id="NKVE-22",
                    location_id="NKVE",
                    name="NKVE JALAN DUTA KM14.7 SB",
                    url="https://w6.fgies.com//sd-nkve/NKVE-22.jpg",
                ),
                CCTVCamera(
                    camera_id="NKVE-31",
                    location_id="NKVE",
                    name="NKVE SEGAMBUT KM12.6 NB",
                    url="https://w6.fgies.com//sd-nkve/NKVE-31.jpg",
                ),
                CCTVCamera(
                    camera_id="NKVE-32",
                    location_id="NKVE",
                    name="NKVE SEGAMBUT KM12.6 SB",
                    url="https://w6.fgies.com//sd-nkve/NKVE-32.jpg",
                ),
                CCTVCamera(
                    camera_id="NKVE-41",
                    location_id="NKVE",
                    name="NKVE JALAN IPOH KM10.5 NB",
                    url="https://w6.fgies.com//sd-nkve/NKVE-41.jpg",
                ),
                CCTVCamera(
                    camera_id="NKVE-42",
                    location_id="NKVE",
                    name="NKVE JALAN IPOH KM10.5 SB",
                    url="https://w6.fgies.com//sd-nkve/NKVE-42.jpg",
                ),
            ],
        )
        active_locations[nkve_location.location_id] = nkve_location

        # Fetch images immediately
        await fetch_location_images(nkve_location)

        # Start scheduler
        scheduler.add_job(
            fetch_location_images,
            trigger=IntervalTrigger(minutes=3),
            args=[nkve_location],
            id=f"fetch_{nkve_location.location_id}",
        )
        scheduler.start()

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error in startup: {str(e)}")
        raise


@app.get("/images/{location_id}")
async def get_location_images(location_id: str, limit: int = 10):
    """Get recent images for a location"""
    try:
        if location_id not in active_locations:
            raise HTTPException(status_code=404, detail="Location not found")

        # Get list of image files for location
        image_files = sorted(
            [f for f in STORAGE_DIR.glob(f"{location_id}_*.jpg")],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )[:limit]

        if not image_files:
            # Try to fetch images immediately if none found
            await fetch_location_images(active_locations[location_id])
            await asyncio.sleep(2)  # Give time for images to be saved
            # Check again
            image_files = sorted(
                [f for f in STORAGE_DIR.glob(f"{location_id}_*.jpg")],
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )[:limit]

        base_url = str(httpx.URL(os.getenv("BASE_URL", "http://localhost:8000")))

        return {
            "location": active_locations[location_id],
            "images": [
                {
                    "filename": f.name,
                    "camera_id": f.name.split("_")[1],
                    "camera_name": next(
                        (
                            cam.name
                            for cam in active_locations[location_id].cameras
                            if cam.camera_id == f.name.split("_")[1]
                        ),
                        "Unknown Camera",
                    ),
                    "timestamp": datetime.fromtimestamp(f.stat().st_mtime),
                    "url": f"{base_url}/static/{f.name}",
                    "size": f.stat().st_size,
                }
                for f in image_files
            ],
        }

    except Exception as e:
        logger.error(f"Error in get_location_images: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations")
async def get_locations():
    """Get list of active locations"""
    return list(active_locations.values())


@app.get("/images/latest/{location_id}/{camera_id}")
async def get_latest_image(location_id: str, camera_id: str):
    """Get the latest image for a specific camera"""
    try:
        if location_id not in active_locations:
            raise HTTPException(status_code=404, detail="Location not found")

        # Find the latest image for this camera
        image_files = sorted(
            [f for f in STORAGE_DIR.glob(f"{location_id}_{camera_id}_*.jpg")],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        if not image_files:
            # Try to fetch new images
            camera = next(
                (
                    cam
                    for cam in active_locations[location_id].cameras
                    if cam.camera_id == camera_id
                ),
                None,
            )
            if camera:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await fetch_image_with_retry(client, camera)
                # Check again
                image_files = sorted(
                    [f for f in STORAGE_DIR.glob(f"{location_id}_{camera_id}_*.jpg")],
                    key=lambda x: x.stat().st_mtime,
                    reverse=True,
                )

        if not image_files:
            raise HTTPException(
                status_code=404, detail="No images found for this camera"
            )

        return FileResponse(
            str(image_files[0]), media_type="image/jpeg", filename=image_files[0].name
        )
    except Exception as e:
        logger.error(f"Error in get_latest_image: {str(e)}")
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
        "active_locations": len(active_locations),
        "image_count": len(list(STORAGE_DIR.glob("*.jpg"))),
    }
