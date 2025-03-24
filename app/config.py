"""Static configuration for highways and cameras"""

HIGHWAYS = {
    "NKV": {
        "id": "E1",
        "code": "NKV",
        "name": "L/raya Baru Lembah Klang (NKVE)",
        "cameras": [],  # Will be populated from AJAX response
    },
    "PLS": {
        "id": "E1",
        "code": "PLS",
        "name": "L/raya Utara Selatan (PLUS Utara)",
        "cameras": [],
    },
    "SPL": {
        "id": "E2",
        "code": "SPL",
        "name": "L/raya Utara Selatan (PLUS Selatan)",
        "cameras": [],
    },
    "LINK2": {
        "id": "E3",
        "code": "LINK2",
        "name": "L/raya Hubungan Kedua Malaysia Singapura (LINK2)",
        "cameras": [],
    },
    "KSS": {
        "id": "E5",
        "code": "KSS",
        "name": "L/raya Shah Alam (KESAS)",
        "cameras": [],
    },
    "ELT": {
        "id": "E6",
        "code": "ELT",
        "name": "L/raya Utara Selatan Hubungan Tengah (ELITE)",
        "cameras": [],
    },
    "CKH": {
        "id": "E7",
        "code": "CKH",
        "name": "L/raya Cheras Kajang (GRANDSAGA)",
        "cameras": [],
    },
    "KLK": {"id": "E8", "code": "KLK", "name": "L/raya KL-Karak (KLK)", "cameras": []},
    "LPT": {
        "id": "E8",
        "code": "LPT",
        "name": "L/raya Pantai Timur Fasa 1 (LPT1)",
        "cameras": [],
    },
    "ECE2": {
        "id": "E8",
        "code": "ECE2",
        "name": "L/raya Pantai Timur Fasa 2 (LPT2)",
        "cameras": [],
    },
    "BES": {"id": "E9", "code": "BES", "name": "L/raya BESRAYA (BES)", "cameras": []},
    "NPE": {
        "id": "E10",
        "code": "NPE",
        "name": "L/raya Pantai Baharu (NPE)",
        "cameras": [],
    },
    "LDP": {
        "id": "E11",
        "code": "LDP",
        "name": "L/raya Damansara Puchong (LDP)",
        "cameras": [],
    },
    "AKL": {
        "id": "E12",
        "code": "AKL",
        "name": "L/raya Bertingkat Ampang KL (AKLEH)",
        "cameras": [],
    },
    "KSA": {
        "id": "E13",
        "code": "KSA",
        "name": "L/raya Kemuning Shah Alam (LKSA)",
        "cameras": [],
    },
    "SLK": {
        "id": "E18",
        "code": "SLK",
        "name": "L/raya Lingkaran Luar Kajang (SILK)",
        "cameras": [],
    },
    "SUKE": {
        "id": "E19",
        "code": "SUKE",
        "name": "L/raya Sungai Besi Ulu Kelang (SUKE)",
        "cameras": [],
    },
    "KLP": {
        "id": "E20",
        "code": "KLP",
        "name": "L/raya KL-Putrajaya (MEX)",
        "cameras": [],
    },
    "LKS": {
        "id": "E21",
        "code": "LKS",
        "name": "L/raya Kajang Seremban (LEKAS)",
        "cameras": [],
    },
    "SDE": {
        "id": "E22",
        "code": "SDE",
        "name": "L/raya Senai Desaru (SDE)",
        "cameras": [],
    },
    "SRT": {
        "id": "E23",
        "code": "SRT",
        "name": "L/raya Skim Penyuraian Trafik KL-Barat (SPRINT)",
        "cameras": [],
    },
    "LTR": {
        "id": "E25",
        "code": "LTR",
        "name": "L/raya KL-Kuala Selangor (LATAR)",
        "cameras": [],
    },
    "SKV": {
        "id": "E26",
        "code": "SKV",
        "name": "L/raya Lembah Klang Selatan (SKVE)",
        "cameras": [],
    },
    "JKSB": {
        "id": "E28",
        "code": "JKSB",
        "name": "Jambatan Sultan Abdul Halim Muadzam Shah (JSAHMS)",
        "cameras": [],
    },
    "NNKSB": {
        "id": "E30",
        "code": "NNKSB",
        "name": "L/raya Pintas Selat Klang Utara Baru (NNKSB)",
        "cameras": [],
    },
    "DASH": {
        "id": "E31",
        "code": "DASH",
        "name": "L/raya Bertingkat Damansara Shah Alam (DASH)",
        "cameras": [],
    },
    "WCE": {
        "id": "E32",
        "code": "WCE",
        "name": "L/raya Pesisiran Pantai Barat (WCE)",
        "cameras": [],
    },
    "DUKE": {
        "id": "E33",
        "code": "DUKE",
        "name": "L/raya Duta-Ulu Kelang (DUKE)",
        "cameras": [],
    },
    "GCE": {
        "id": "E35",
        "code": "GCE",
        "name": "L/raya Koridor Gutrie (GCE)",
        "cameras": [],
    },
    "PNB": {
        "id": "E36",
        "code": "PNB",
        "name": "Jambatan Pulau Pinang (PNB)",
        "cameras": [],
    },
    "SMT": {"id": "E38", "code": "SMT", "name": "Terowong SMART", "cameras": []},
    "SPE": {
        "id": "E39",
        "code": "SPE",
        "name": "L/raya Setiawangsa Pantai (SPE)",
        "cameras": [],
    },
}


def get_highway_list():
    """Get list of all highways with their cameras"""
    return [
        {
            "id": highway_data["id"],
            "code": code,
            "name": highway_data["name"],
            "cameras": [],  # Will be populated dynamically from AJAX response
        }
        for code, highway_data in HIGHWAYS.items()
    ]


def get_highway_codes():
    """Get list of all highway codes"""
    return list(HIGHWAYS.keys())
