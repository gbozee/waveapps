import pytest
import os
import asyncio
from waveapps import WaveAPI
import httpx
from starlette.config import environ

environ[
    "WAVEAPPS_BUSINESS_ID"
] = "QnVzaW5lc3M6YzVlNWQxZWItNTVjMi00NjE4LTg4M2MtODMxNWU5OWNkZTM4"
environ["WAVEAPPS_WEBHOOK_CALLBACK"] = "http://the-main-site.com/hooks"
environ["ALLOWED_HOSTS"] = "test-server,localhost"

from waveapps.frameworks.starlette import build_app


@pytest.fixture
def client():
    api_key = os.getenv("WAVEAPPS_API_KEY")
    return WaveAPI(api_key)


@pytest.fixture
def app():
    _app = build_app(api_key=os.getenv("WAVEAPPS_API_KEY"))
    return httpx.AsyncClient(app=_app, base_url="http://test-server")


@pytest.fixture
def create_future():
    def _create_future(value):
        dd = asyncio.Future()
        dd.set_result(value)
        return dd

    return _create_future
