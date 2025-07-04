import os
from dotenv import load_dotenv

load_dotenv()

from google.cloud import secretmanager

def access_secret_version(project_id, secret_id, version_id):
    """
    Access the payload for the given secret version if one exists.
    """
    client = secretmanager.SecretManagerServiceClient()

    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    response = client.access_secret_version(request={"name": name})

    payload = response.payload.data.decode("UTF-8")
    return payload
SIMPLENOTE_USER=None
SIMPLENOTE_PASS=None

if os.getenv("USEGCP")=='YES':
    SIMPLENOTE_USER = access_secret_version("qmulclub", "SIMPLENOTE_USER", "latest")
    SIMPLENOTE_PASS = access_secret_version("qmulclub", "SIMPLENOTE_PASS", "latest")
    PPLX_API_KEY =   access_secret_version("qmulclub", "PPLX_API_KEY", "latest")
    GOOGLE_API_KEY =   access_secret_version("qmulclub", "GOOGLE_API_KEY", "latest")
    MISTRAL_API_KEY = access_secret_version("qmulclub", "MISTRAL_API_KEY", "latest")
else:
    SIMPLENOTE_USER = os.getenv("SIMPLENOTE_USER")
    SIMPLENOTE_PASS = os.getenv("SIMPLENOTE_PASS")

os.environ['LANGSMITH_TRACING'] = "true"
os.environ['LANGSMITH_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGSMITH_PROJECT'] = 'pr-large-abnormality-8'
os.environ['LANGSMITH_API_KEY'] =  access_secret_version("qmulclub", "LANGSMITH_API_KEY", "latest")
if not SIMPLENOTE_USER or not SIMPLENOTE_PASS:
    raise ValueError("SIMPLENOTE_USER and SIMPLENOTE_PASS must be set in the .env file")