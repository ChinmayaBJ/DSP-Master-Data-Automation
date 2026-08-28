import requests
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

DATASPHERE_TOKEN_URL = os.environ["DSP_TOKEN_URL"]
DATASPHERE_CLIENT_ID = os.environ["DSP_CLIENT_ID"]
DATASPHERE_CLIENT_SECRET = os.environ["DSP_CLIENT_SECRET"]
DATASPHERE_BASE_URL = os.environ["DSP_BASE_URL"]


def get_bearer_token():
    response = requests.post(
        DATASPHERE_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": DATASPHERE_CLIENT_ID,
            "client_secret": DATASPHERE_CLIENT_SECRET,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]
