import asyncio
import os
from dotenv import load_dotenv
from loguru import logger
from app.db import (
    get_pb_client,
    authenticate_admin,
    check_pocketbase_connection,
    init_collections,
)

# Configure logging
logger.add("debug_pocketbase.log", level="DEBUG")


async def main():
    # Load environment variables
    load_dotenv()

    logger.info(f"Using PocketBase URL: {os.getenv('POCKETBASE_URL')}")
    logger.info(f"Admin email: {os.getenv('POCKETBASE_ADMIN_EMAIL')}")

    # Try connecting to PocketBase
    logger.info("Checking PocketBase connection...")
    connection_successful = await check_pocketbase_connection()
    logger.info(f"Connection check result: {connection_successful}")

    # Try authenticating
    if connection_successful:
        logger.info("Trying to authenticate...")
        auth_successful = await authenticate_admin()
        logger.info(f"Authentication result: {auth_successful}")

        # Initialize collections
        if auth_successful:
            logger.info("Initializing collections...")
            init_result = await init_collections()
            logger.info(f"Collections initialization result: {init_result}")


if __name__ == "__main__":
    asyncio.run(main())
