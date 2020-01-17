import os
from django.conf import settings

DEBUG = getattr(settings, "DEBUG", True)

WAVEAPPS_CLIENT_ID = getattr(
    settings, "WAVEAPPS_CLIENT_ID", os.getenv("WAVEAPPS_CLIENT_ID")
)
WAVEAPPS_CLIENT_SECRET = getattr(
    settings, "WAVEAPPS_CLIENT_SECRET", os.getenv("WAVEAPPS_CLIENT_SECRET")
)

WAVEAPPS_SCOPES = getattr(
    settings,
    "WAVEAPPS_SCOPES",
    ["account:*", "business:*", "sales_tax:*", "transaction:*"],
)
WAVEAPPS_STATE = getattr(settings, "WAVEAPPS_STATE", "from-django-server")
WAVEAPPS_STORAGE_CLASS = getattr(settings, "WAVEAPPS_STORAGE_CLASS", lambda: None)
WAVEAPPS_BUSINESS_ID = getattr(
    settings, "WAVEAPPS_BUSINESS_ID", os.getenv("WAVEAPPS_BUSINESS_ID")
)

