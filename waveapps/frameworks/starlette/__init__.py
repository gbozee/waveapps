import asyncio
import datetime

from starlette import requests
from starlette.applications import Starlette
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
    requires,
)
from starlette.background import BackgroundTasks
from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings, Secret
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from waveapps import WaveAPI, WaveBusiness, models, request_helper
from waveapps.business import TransactionAccounts

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


def on_auth_error(request: Request, exc: Exception):
    return JSONResponse({"status": False, "msg": str(exc)}, status_code=403)


def build_token_backend(api_key):
    class TokenBackend(AuthenticationBackend):
        async def authenticate(self, request: HTTPConnection):
            if "Authorization" not in request.headers:
                bearer_token = api_key
            else:
                auth = request.headers["Authorization"]
                bearer_token = auth.replace("Bearer", "").strip()
            if not bearer_token:
                raise AuthenticationError("Missing WAVEAPPS_API_KEY or OAUTH_TOKEN ")
            return AuthCredentials(["authenticated"]), SimpleUser(bearer_token)

    return TokenBackend


def get_business(state, data, token) -> WaveBusiness:
    if hasattr(state, "WAVE_BUSINESS"):
        business = state.WAVE_BUSINESS
    else:
        business = WaveBusiness(data["business"], WaveAPI(token))
    return business


async def create_transaction(request: Request):
    data = await request.json()
    business = get_business(request.app.state, data, request.user.username)
    tasks = BackgroundTasks()

    async def _create_transaction():
        kwargs = dict(
            orderId=data["order"],
            date=datetime.datetime.strptime(data["date"], "%Y-%m-%d"),
            description=data["description"],
            amount=data["amount"],
            kind=models.MoneyFlow.INFlOW
            if data["kind"].lower() == "income"
            else models.MoneyFlow.OUTFLOW,
            accounts=TransactionAccounts(**data["accounts"]),
            currency=models.CurrencyCode(data["currency"].upper()),
        )
        if data.get("service_fee"):
            kwargs["charge_amount"] = data["service_fee"]
            kwargs["charge_description"] = data["service_fee_description"]
        if data.get("additional_items"):
            kwargs["additional_line_item"] = [
                {
                    "accountId": x["account"],
                    "amount": "%.2f" % x["amount"],
                    "balance": models.BalanceType.CREDIT.value
                    if x["kind"] == "expense"
                    else models.BalanceType.DEBIT.value,
                    "description": x["description"],
                    "taxes": x.get("taxes") or [],
                }
                for x in data["additional_items"]
            ]
        result = await business.create_transaction(**kwargs)
        created = bool(result.transaction)
        _id = None
        if created:
            _id = result.transaction.id
        if WEBHOOK_CALLBACK:
            result = await request_helper(
                WEBHOOK_CALLBACK,
                "POST",
                json={"order": data["order"], "created": created, "id": _id},
            )

    tasks.add_task(_create_transaction)
    return JSONResponse(
        {
            "status": True,
            "msg": "creating transaction. listen to {} to update".format(
                WEBHOOK_CALLBACK
            ),
        },
        background=tasks,
    )


async def get_accounts(request: Request):
    business = get_business(
        request.app.state, request.query_params, request.user.username
    )
    await business.get_accounts()
    return JSONResponse({"status": True, "data": business.accounts})


async def create_account(request: Request):
    data = await request.json()
    business = get_business(request.app.state, data, request.user.username)
    mapping = {
        "asset": models.AccountSubTypeValue.OTHER_CURRENT_ASSETS,
        "liability": models.AccountSubTypeValue.OTHER_CURRENT_LIABILITY,
        "expense": models.AccountSubTypeValue.EXPENSE,
        "fee": models.AccountSubTypeValue.PAYMENT_PROCESSING_FEES,
    }
    result = await business.create_new_account(
        data["name"],
        data.get("description"),
        currency=data["currency"].lower(),
        accountType=mapping[data["type"]],
    )
    if not result:
        return JSONResponse(
            {"status": False, "msg": "Could not create account"}, status_code=400
        )
    return JSONResponse(
        {
            "status": True,
            "data": {
                "name": result.name,
                "id": result.id,
                "currency": result.currency.code,
                "type": result.subtype.value,
            },
        }
    )


def build_app(api_key=None, business_id=None):
    key = api_key or str(WAVEAPPS_API_KEY)
    client = WaveAPI(key)

    routes = [
        Route(
            "/create-transaction",
            requires("authenticated")(create_transaction),
            methods=["POST"],
        ),
        Route(
            "/create-account",
            requires("authenticated")(create_account),
            methods=["POST"],
        ),
        Route("/accounts", requires("authenticated")(get_accounts), methods=["GET"]),
    ]
    token_backend = build_token_backend(key)
    app = Starlette(
        routes=routes,
        middleware=[
            Middleware(
                AuthenticationMiddleware,
                backend=token_backend(),
                on_error=on_auth_error,
            ),
            Middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS),
        ],
    )
    _business_id = business_id or WAVE_BUSINESS_ID
    app.state.WAVE_BUSINESS = WaveBusiness(_business_id, client)
    return app
