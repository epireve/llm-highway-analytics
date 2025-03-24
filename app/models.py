from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime


class CCTVCamera(BaseModel):
    """Model for a CCTV camera"""

    camera_id: str
    location_id: str
    name: str
    url: str
    base64_image: Optional[str] = None
    last_updated: Optional[datetime] = None


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


class Highway(BaseModel):
    """Model for a highway"""

    id: str
    code: str
    name: str
    cameras: List[CCTVCamera]


class HighwayList(BaseModel):
    """Model for a list of highways"""

    highways: List[Highway]


# Example mapping of highway codes to their full details
HIGHWAY_MAPPING = {
    "NKVE": {"id": "E1", "name": "L/raya Baru Lembah Klang (NKVE)"},
    "PLS": {"id": "E1", "name": "L/raya Utara Selatan (PLUS Utara)"},
    "PLUS": {"id": "E2", "name": "L/raya Utara Selatan (PLUS Selatan)"},
    "LINK2": {"id": "E3", "name": "L/raya Hubungan Kedua Malaysia Singapura (LINK2)"},
    "KESAS": {"id": "E5", "name": "L/raya Shah Alam (KESAS)"},
    "ELITE": {"id": "E6", "name": "L/raya Utara Selatan Hubungan Tengah (ELITE)"},
    "GRANDSAGA": {"id": "E7", "name": "L/raya Cheras Kajang (GRANDSAGA)"},
    "KLK": {"id": "E8", "name": "L/raya KL-Karak (KLK)"},
    "LPT1": {"id": "E8", "name": "L/raya Pantai Timur Fasa 1 (LPT1)"},
    "LPT2": {"id": "E8", "name": "L/raya Pantai Timur Fasa 2 (LPT2)"},
    "BES": {"id": "E9", "name": "L/raya BESRAYA (BES)"},
    "NPE": {"id": "E10", "name": "L/raya Pantai Baharu (NPE)"},
    "LDP": {"id": "E11", "name": "L/raya Damansara Puchong (LDP)"},
    "AKLEH": {"id": "E12", "name": "L/raya Bertingkat Ampang KL (AKLEH)"},
    "LKSA": {"id": "E13", "name": "L/raya Kemuning Shah Alam (LKSA)"},
    "SILK": {"id": "E18", "name": "L/raya Lingkaran Luar Kajang (SILK)"},
    "SUKE": {"id": "E19", "name": "L/raya Sungai Besi Ulu Kelang (SUKE)"},
    "MEX": {"id": "E20", "name": "L/raya KL-Putrajaya (MEX)"},
    "LEKAS": {"id": "E21", "name": "L/raya Kajang Seremban (LEKAS)"},
    "SDE": {"id": "E22", "name": "L/raya Senai Desaru (SDE)"},
    "SPRINT": {"id": "E23", "name": "L/raya Skim Penyuraian Trafik KL-Barat (SPRINT)"},
    "LATAR": {"id": "E25", "name": "L/raya KL-Kuala Selangor (LATAR)"},
    "SKVE": {"id": "E26", "name": "L/raya Lembah Klang Selatan (SKVE)"},
    "JSAHMS": {
        "id": "E28",
        "name": "Jambatan Sultan Abdul Halim Muadzam Shah (JSAHMS)",
    },
    "NNKSB": {"id": "E30", "name": "L/raya Pintas Selat Klang Utara Baru (NNKSB)"},
    "DASH": {"id": "E31", "name": "L/raya Bertingkat Damansara Shah Alam (DASH)"},
    "WCE": {"id": "E32", "name": "L/raya Pesisiran Pantai Barat (WCE)"},
    "DUKE": {"id": "E33", "name": "L/raya Duta-Ulu Kelang (DUKE)"},
    "GCE": {"id": "E35", "name": "L/raya Koridor Gutrie (GCE)"},
    "PNB": {"id": "E36", "name": "Jambatan Pulau Pinang (PNB)"},
    "SMART": {"id": "E38", "name": "Terowong SMART"},
    "SPE": {"id": "E39", "name": "L/raya Setiawangsa Pantai (SPE)"},
}
