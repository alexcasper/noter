import os
from dotenv import load_dotenv

load_dotenv()

SIMPLENOTE_USER = os.getenv("SIMPLENOTE_USER")
SIMPLENOTE_PASS = os.getenv("SIMPLENOTE_PASS")

if not SIMPLENOTE_USER or not SIMPLENOTE_PASS:
    raise ValueError("SIMPLENOTE_USER and SIMPLENOTE_PASS must be set in the .env file")