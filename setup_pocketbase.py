#!/usr/bin/env python

import os
import json
import httpx
import asyncio
import webbrowser
from dotenv import load_dotenv
from loguru import logger

# Configure logging
logger.add("setup_pocketbase.log", level="DEBUG")


async def check_pocketbase_running(url):
    """Check if PocketBase server is running"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/api/health")
            return response.status_code == 200
    except Exception:
        return False


async def setup_collections():
    # Load environment variables
    load_dotenv()

    # Get PocketBase config
    url = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090")
    admin_email = os.getenv("POCKETBASE_ADMIN_EMAIL", "")
    admin_password = os.getenv("POCKETBASE_ADMIN_PASSWORD", "")

    if not admin_email or not admin_password:
        logger.error(
            "Admin credentials not found. Please set POCKETBASE_ADMIN_EMAIL and POCKETBASE_ADMIN_PASSWORD in .env file"
        )
        return False

    logger.info(f"Using PocketBase URL: {url}")
    logger.info(f"Admin email: {admin_email}")

    # Check if PocketBase is running
    is_running = await check_pocketbase_running(url)
    if not is_running:
        logger.error(f"PocketBase is not running at {url}")
        logger.info(
            'Please start PocketBase with: cd pocketbase && ./pocketbase serve --http="127.0.0.1:8090"'
        )
        logger.info(
            "If this is your first time, you'll need to create an admin account through the web UI"
        )

        # Try to open the admin UI
        admin_url = f"{url}/_/"
        logger.info(f"Opening admin UI at {admin_url}")
        webbrowser.open(admin_url)
        return False

    # Create HTTP client
    async with httpx.AsyncClient(timeout=30.0, base_url=url) as client:
        # First, check if PocketBase is running
        try:
            health_response = await client.get("/api/health")
            if health_response.status_code != 200:
                logger.error(f"PocketBase health check failed: {health_response.text}")
                return False
            logger.info("PocketBase health check successful")
        except Exception as e:
            logger.error(f"Error connecting to PocketBase: {str(e)}")
            return False

        # Now try to create the tables - note that PocketBase might not allow table creation without admin access
        try:
            # First try to get a JWT token directly from the API
            login_data = {"identity": admin_email, "password": admin_password}

            # Try different auth endpoints to get a token
            token = None
            auth_endpoints = [
                "/api/admins/auth-with-password",
                "/api/collections/users/auth-with-password",
                "/api/users/auth-with-password",
            ]

            for endpoint in auth_endpoints:
                try:
                    logger.debug(f"Trying authentication endpoint: {endpoint}")
                    auth_response = await client.post(endpoint, json=login_data)
                    if auth_response.status_code == 200:
                        token_data = auth_response.json()
                        if "token" in token_data:
                            token = token_data["token"]
                            logger.info(f"Authentication successful with {endpoint}")
                            break
                except Exception as auth_err:
                    logger.debug(
                        f"Auth attempt failed with {endpoint}: {str(auth_err)}"
                    )

            # If we couldn't get a token, try using basic credentials directly
            headers = {}
            if token:
                headers["Authorization"] = token

            # First, check if we can access the collections
            try:
                collections_response = await client.get(
                    "/api/collections", headers=headers
                )
                if collections_response.status_code != 200:
                    logger.error(
                        f"Failed to access collections: {collections_response.text}"
                    )
                    logger.error(
                        "You need to create an admin account and authenticate before running this script"
                    )
                    logger.info(f"1. Go to {url}/_/ in your browser")
                    logger.info(f"2. Create an admin account with email {admin_email}")
                    logger.info("3. Run this script again")
                    return False

                existing_collections = [
                    col["name"] for col in collections_response.json()["items"]
                ]
                logger.info(f"Found existing collections: {existing_collections}")

                # Create the highways collection if it doesn't exist
                if "highways" not in existing_collections:
                    highways_schema = {
                        "name": "highways",
                        "type": "base",
                        "schema": [
                            {
                                "name": "code",
                                "type": "text",
                                "required": True,
                                "unique": True,
                            },
                            {"name": "name", "type": "text", "required": True},
                            {"name": "highway_id", "type": "text", "required": True},
                        ],
                    }

                    highways_response = await client.post(
                        "/api/collections", json=highways_schema, headers=headers
                    )
                    if highways_response.status_code not in [200, 201]:
                        logger.error(
                            f"Failed to create highways collection: {highways_response.text}"
                        )
                        return False
                    logger.info("Highways collection created successfully")
                else:
                    logger.info("Highways collection already exists")

                # Fetch the collections again to get the IDs
                collections_response = await client.get(
                    "/api/collections", headers=headers
                )
                if collections_response.status_code != 200:
                    logger.error(
                        f"Failed to fetch collections: {collections_response.text}"
                    )
                    return False

                collections = collections_response.json()["items"]
                highways_id = next(
                    (col["id"] for col in collections if col["name"] == "highways"),
                    None,
                )

                if not highways_id:
                    logger.error("Failed to find highways collection ID")
                    return False

                # Create the cameras collection if it doesn't exist
                if "cameras" not in existing_collections:
                    cameras_schema = {
                        "name": "cameras",
                        "type": "base",
                        "schema": [
                            {"name": "camera_id", "type": "text", "required": True},
                            {"name": "name", "type": "text", "required": True},
                            {"name": "location_id", "type": "text", "required": True},
                            {
                                "name": "highway",
                                "type": "relation",
                                "required": True,
                                "options": {
                                    "collectionId": highways_id,
                                    "cascadeDelete": True,
                                },
                            },
                        ],
                    }

                    cameras_response = await client.post(
                        "/api/collections", json=cameras_schema, headers=headers
                    )
                    if cameras_response.status_code not in [200, 201]:
                        logger.error(
                            f"Failed to create cameras collection: {cameras_response.text}"
                        )
                        return False
                    logger.info("Cameras collection created successfully")
                else:
                    logger.info("Cameras collection already exists")

                # Fetch the collections again to get the cameras ID
                collections_response = await client.get(
                    "/api/collections", headers=headers
                )
                if collections_response.status_code != 200:
                    logger.error(
                        f"Failed to fetch collections: {collections_response.text}"
                    )
                    return False

                collections = collections_response.json()["items"]
                cameras_id = next(
                    (col["id"] for col in collections if col["name"] == "cameras"), None
                )

                if not cameras_id:
                    logger.error("Failed to find cameras collection ID")
                    return False

                # Create the camera_images collection if it doesn't exist
                if "camera_images" not in existing_collections:
                    camera_images_schema = {
                        "name": "camera_images",
                        "type": "base",
                        "schema": [
                            {
                                "name": "camera",
                                "type": "relation",
                                "required": True,
                                "options": {
                                    "collectionId": cameras_id,
                                    "cascadeDelete": True,
                                },
                            },
                            {"name": "image_path", "type": "text", "required": True},
                            {"name": "capture_time", "type": "date", "required": True},
                            {"name": "file_size", "type": "number", "required": True},
                        ],
                    }

                    camera_images_response = await client.post(
                        "/api/collections", json=camera_images_schema, headers=headers
                    )
                    if camera_images_response.status_code not in [200, 201]:
                        logger.error(
                            f"Failed to create camera_images collection: {camera_images_response.text}"
                        )
                        return False
                    logger.info("Camera_images collection created successfully")
                else:
                    logger.info("Camera_images collection already exists")

                logger.info("All collections created successfully")
                return True

            except Exception as e:
                logger.error(f"Error setting up collections: {str(e)}")
                logger.exception("Full error traceback:")
                return False

        except Exception as e:
            logger.error(f"Error setting up collections: {str(e)}")
            logger.exception("Full error traceback:")
            return False


async def main():
    result = await setup_collections()
    if result:
        logger.info("PocketBase setup completed successfully!")
        logger.info(
            "You can now run the FastAPI application with: .venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"
        )
    else:
        logger.error("PocketBase setup failed")
        logger.info("Please fix the issues mentioned above and try again")


if __name__ == "__main__":
    asyncio.run(main())
