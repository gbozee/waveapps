from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings, Secret

config = Config(".env")

WAVEAPPS_API_KEY = config("WAVEAPPS_API_KEY", cast=Secret, default="")
WAVEAPPS_CLIENT_ID = config("WAVEAPPS_CLIENT_ID", cast=Secret, default="")
WAVEAPPS_CLIENT_SECRET = config("WAVEAPPS_CLIENT_SECRET", cast=Secret, default="")
WAVEAPPS_STATE = config("WAVEAPPS_STATE", default="starlette-server")
WAVE_BUSINESS_ID = config("WAVEAPPS_BUSINESS_ID", default="")
WEBHOOK_CALLBACK = config("WAVEAPPS_WEBHOOK_CALLBACK", default="")
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", cast=CommaSeparatedStrings, default="localhost,127.0.0.1"
)
