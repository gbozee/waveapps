from waveapps.frameworks.starlette import build_app
from starlette.config import Config

config = Config(".env")

WAVE_BUSINESS_ID = config(
    "WAVEAPPS_BUSINESS_ID",
    default="QnVzaW5lc3M6YzVlNWQxZWItNTVjMi00NjE4LTg4M2MtODMxNWU5OWNkZTM4",
)

app = build_app(business_id=WAVE_BUSINESS_ID)
