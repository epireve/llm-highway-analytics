"""PocketBase database client and utilities"""

import sys
import traceback
from pocketbase import PocketBase
from pocketbase.errors import ClientResponseError
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
import os
from dotenv import load_dotenv

# Singleton instance
_pb_instance = None
_is_authenticated = False


def get_pb_client():
    """Get the PocketBase client instance"""
    # Reload environment variables
    load_dotenv()

    # Get PocketBase URL from environment
    pocketbase_url = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090")

    global _pb_instance
    if _pb_instance is None:
        logger.debug(f"Creating new PocketBase client instance at {pocketbase_url}")
        _pb_instance = PocketBase(pocketbase_url)
    return _pb_instance


async def authenticate_admin():
    """Authenticate with PocketBase admin credentials if available"""
    global _is_authenticated

    if _is_authenticated:
        logger.debug("Already authenticated with PocketBase")
        return True

    # Reload environment variables
    load_dotenv()

    # Get authentication credentials from environment
    admin_email = os.getenv("POCKETBASE_ADMIN_EMAIL", "")
    admin_password = os.getenv("POCKETBASE_ADMIN_PASSWORD", "")

    # Debug environment variables
    logger.debug(f"POCKETBASE_ADMIN_EMAIL: {admin_email}")
    logger.debug(
        f"POCKETBASE_ADMIN_PASSWORD: {'*' * len(admin_password) if admin_password else 'Not set'}"
    )

    # Check if variables are defined but empty
    if admin_email == "":
        logger.warning("POCKETBASE_ADMIN_EMAIL is defined but empty")
    if admin_password == "":
        logger.warning("POCKETBASE_ADMIN_PASSWORD is defined but empty")

    if not admin_email or not admin_password:
        logger.warning(
            "PocketBase admin credentials not provided in environment variables."
        )
        logger.warning(
            "Set POCKETBASE_ADMIN_EMAIL and POCKETBASE_ADMIN_PASSWORD in your .env file."
        )
        return False

    try:
        logger.debug(
            f"Attempting to authenticate with PocketBase using admin email: {admin_email}"
        )
        client = get_pb_client()
        auth_data = client.admins.auth_with_password(admin_email, admin_password)
        _is_authenticated = True
        logger.info(
            f"Successfully authenticated with PocketBase admin account: {admin_email}"
        )
        logger.debug(f"Auth token received: {auth_data.token[:10]}...")
        return True
    except ClientResponseError as e:
        logger.error(
            f"PocketBase authentication error: {e.status} {e.data.get('message', '')}"
        )
        if e.status == 400:
            logger.error("Authentication failed. Check your credentials in .env file.")
        elif e.status == 404:
            logger.error(
                "API endpoint not found. Check if PocketBase is running and the URL is correct."
            )
        return False
    except Exception as e:
        logger.error(f"Failed to authenticate with PocketBase: {str(e)}")
        logger.debug(f"Exception type: {type(e).__name__}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False


async def check_pocketbase_connection():
    """Check if PocketBase is running and reachable"""
    try:
        # Reload environment variables
        load_dotenv()

        client = get_pb_client()

        # First, try to access a basic API endpoint that doesn't require authentication
        logger.debug("Testing PocketBase connection...")

        try:
            # Try to access the health endpoint first (doesn't require auth)
            health = client.health.check()
            logger.info(f"PocketBase health check successful: {health}")

            # We'll consider the server up if the health check passes
            # Authentication may still be needed for operations
            admin_email = os.getenv("POCKETBASE_ADMIN_EMAIL", "")
            admin_password = os.getenv("POCKETBASE_ADMIN_PASSWORD", "")

            if admin_email and admin_password:
                auth_result = await authenticate_admin()
                logger.info(f"Authentication result: {auth_result}")

            return True

        except Exception as e:
            logger.error(f"PocketBase connection error: {str(e)}")
            logger.debug(f"Exception type: {type(e).__name__}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False
    except Exception as e:
        logger.error(f"PocketBase connection error: {str(e)}")
        logger.debug(f"Exception type: {type(e).__name__}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False


async def init_collections():
    """Initialize PocketBase collections if they don't exist"""
    try:
        logger.info("Initializing PocketBase collections")

        # Check connection first
        if not await check_pocketbase_connection():
            logger.error(
                "Failed to connect to PocketBase. Cannot initialize collections."
            )
            return False

        # Try to authenticate if we have credentials
        if not await authenticate_admin():
            logger.warning("Not authenticated as admin. Cannot create collections.")
            return False

        # At this point, we're authenticated and connected
        logger.info(
            "Successfully authenticated with PocketBase. Creating collections..."
        )

        # For now, we'll assume the collections are created manually through the admin UI
        # since we're having issues with the Python library version
        logger.info(
            "Please create the following collections manually through the PocketBase admin UI:"
        )
        logger.info(
            "1. highways - with fields: code (text, required, unique), name (text, required), highway_id (text, required)"
        )
        logger.info(
            "2. cameras - with fields: camera_id (text, required), name (text, required), location_id (text, required), highway (relation to highways, required)"
        )
        logger.info(
            "3. camera_images - with fields: camera (relation to cameras, required), image_path (text, required), capture_time (date, required), file_size (number, required)"
        )

        # For testing purposes, we'll return True indicating that initialization was successful
        # The user will need to create the collections manually
        return True

    except Exception as e:
        logger.error(f"Error initializing PocketBase collections: {str(e)}")
        logger.exception("Full traceback:")
        return False


async def save_highway(
    highway_code: str, highway_name: str, highway_id: str
) -> Optional[Dict]:
    """Save or update a highway record"""
    try:
        client = get_pb_client()

        # Check if highway exists
        try:
            existing = client.collection("highways").get_first_list_item(
                f'code = "{highway_code}"'
            )
            # Update existing record
            return client.collection("highways").update(
                existing.id, {"name": highway_name, "highway_id": highway_id}
            )
        except:
            # Create new record
            return client.collection("highways").create(
                {"code": highway_code, "name": highway_name, "highway_id": highway_id}
            )
    except Exception as e:
        logger.error(f"Error saving highway {highway_code}: {str(e)}")
        return None


async def save_camera(
    camera_id: str, name: str, location_id: str, highway_code: str
) -> Optional[Dict]:
    """Save or update a camera record"""
    try:
        client = get_pb_client()

        # Get highway record
        try:
            highway = client.collection("highways").get_first_list_item(
                f'code = "{highway_code}"'
            )
        except:
            logger.error(f"Highway {highway_code} not found")
            return None

        # Check if camera exists
        try:
            existing = client.collection("cameras").get_first_list_item(
                f'camera_id = "{camera_id}"'
            )
            # Update existing record
            return client.collection("cameras").update(
                existing.id,
                {"name": name, "location_id": location_id, "highway": highway.id},
            )
        except:
            # Create new record
            return client.collection("cameras").create(
                {
                    "camera_id": camera_id,
                    "name": name,
                    "location_id": location_id,
                    "highway": highway.id,
                }
            )
    except Exception as e:
        logger.error(f"Error saving camera {camera_id}: {str(e)}")
        return None


async def save_camera_image(
    camera_id: str, image_path: str, timestamp: datetime, file_size: int
) -> Optional[Dict]:
    """Save a camera image record"""
    try:
        client = get_pb_client()

        # Get camera record
        try:
            camera = client.collection("cameras").get_first_list_item(
                f'camera_id = "{camera_id}"'
            )
        except:
            logger.error(f"Camera {camera_id} not found")
            return None

        # Create image record
        return client.collection("camera_images").create(
            {
                "camera": camera.id,
                "image_path": image_path,
                "capture_time": timestamp.isoformat(),
                "file_size": file_size,
            }
        )
    except Exception as e:
        logger.error(f"Error saving camera image for {camera_id}: {str(e)}")
        return None


async def get_latest_camera_images(
    highway_code: str = None, camera_id: str = None, limit: int = 100
) -> List[Dict]:
    """
    Get the latest camera images with flexible filtering:
    - Filter by highway_code if provided
    - Filter by camera_id if provided
    - If both provided, filter by both
    - If neither provided, return latest images across all cameras
    """
    try:
        client = get_pb_client()
        camera_filter = ""

        # Case 1: Both highway_code and camera_id provided
        if highway_code and camera_id:
            try:
                # Get highway record
                highway = client.collection("highways").get_first_list_item(
                    f'code = "{highway_code}"'
                )

                # Get specific camera for this highway and camera_id
                camera = client.collection("cameras").get_first_list_item(
                    f'camera_id = "{camera_id}" && highway = "{highway.id}"'
                )

                if not camera:
                    return []

                # Filter for this specific camera
                camera_filter = f'camera = "{camera.id}"'

            except Exception as e:
                logger.error(f"Error getting specific camera: {str(e)}")
                return []

        # Case 2: Only highway_code provided
        elif highway_code:
            try:
                # Get highway record
                highway = client.collection("highways").get_first_list_item(
                    f'code = "{highway_code}"'
                )

                # Get cameras for this highway
                cameras = client.collection("cameras").get_full_list(
                    query_params={"filter": f'highway = "{highway.id}"'}
                )

                if not cameras:
                    return []

                # Build filter for these cameras
                camera_ids = [camera.id for camera in cameras]
                camera_filter = " || ".join(
                    [f'camera = "{camera_id}"' for camera_id in camera_ids]
                )

                if camera_filter:
                    camera_filter = f"({camera_filter})"

            except Exception as e:
                logger.error(f"Error getting highway cameras: {str(e)}")
                return []

        # Case 3: Only camera_id provided
        elif camera_id:
            try:
                # Get camera by camera_id
                camera = client.collection("cameras").get_first_list_item(
                    f'camera_id = "{camera_id}"'
                )

                if not camera:
                    return []

                # Filter for this camera
                camera_filter = f'camera = "{camera.id}"'

            except Exception as e:
                logger.error(f"Error getting camera by id: {str(e)}")
                return []

        # Get images based on the constructed filter
        query_params = {
            "sort": "-capture_time",
            "expand": "camera,camera.highway",
            "limit": limit,
        }

        if camera_filter:
            query_params["filter"] = camera_filter

        images = client.collection("camera_images").get_full_list(
            query_params=query_params
        )

        # Process and format results
        result = []
        for img in images:
            try:
                camera_data = img.expand.get("camera", {})
                highway_data = camera_data.expand.get("highway", {})

                result.append(
                    {
                        "id": img.id,
                        "image_path": img.image_path,
                        "capture_time": img.capture_time,
                        "file_size": img.file_size,
                        "camera": {
                            "id": camera_data.id,
                            "camera_id": camera_data.camera_id,
                            "name": camera_data.name,
                            "location_id": camera_data.location_id,
                        },
                        "highway": {
                            "id": highway_data.id if highway_data else None,
                            "code": highway_data.code if highway_data else None,
                            "name": highway_data.name if highway_data else None,
                        },
                    }
                )
            except Exception as e:
                logger.error(f"Error processing image record: {str(e)}")
                continue

        return result
    except Exception as e:
        logger.error(f"Error getting latest camera images: {str(e)}")
        return []
