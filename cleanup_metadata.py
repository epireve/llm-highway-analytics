#!/usr/bin/env python3

import os
from pathlib import Path
import shutil
from loguru import logger

# Configure logging
logger.add("cleanup.log", rotation="100 MB")


def cleanup_metadata():
    """Clean up old metadata JSON files"""
    try:
        # Get the metadata directory
        metadata_dir = Path(__file__).parent / "storage" / "metadata"

        if not metadata_dir.exists():
            logger.info("No metadata directory found, nothing to clean up")
            return

        # Count files before deletion
        json_files = list(metadata_dir.glob("*.json"))
        file_count = len(json_files)

        if file_count == 0:
            logger.info("No metadata files found, nothing to clean up")
            return

        logger.info(f"Found {file_count} metadata files to clean up")

        # Remove the entire metadata directory
        shutil.rmtree(metadata_dir)
        logger.info(f"Successfully removed metadata directory with {file_count} files")

    except Exception as e:
        logger.error(f"Error cleaning up metadata: {str(e)}")
        logger.exception("Full error traceback:")


if __name__ == "__main__":
    cleanup_metadata()
