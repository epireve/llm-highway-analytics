from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime


class CCTVCamera(BaseModel):
    """Model for individual CCTV camera"""

    camera_id: str
    location_id: str
    name: str
    url: HttpUrl


class CCTVImage(BaseModel):
    """Model for CCTV image data"""

    url: HttpUrl
    location_id: str
    camera_id: str
    name: str
    timestamp: datetime
    status: str
    retry_count: int = 0
    error_message: Optional[str] = None


class CCTVLocation(BaseModel):
    """Model for CCTV location configuration"""

    location_id: str
    name: str
    base_url: HttpUrl
    cameras: List[CCTVCamera]
    refresh_interval: int = 300  # default 5 minutes in seconds
