import typing

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
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from waveapps import WaveAPI, WaveBusiness

from . import service_layer, settings


def on_auth_error(request: Request, exc: Exception):
    return JSONResponse({"status": False, "msg": str(exc)}, status_code=403)


def get_business(state, data, token) -> WaveBusiness:
    if hasattr(state, "WAVE_BUSINESS"):
        business = state.WAVE_BUSINESS
    else:
        business = WaveBusiness(data["business"], WaveAPI(token))
    return business


class ViewMixin:
    def __init__(
        self,
        service: typing.Dict[str, typing.Dict[str, typing.Any]],
        api_key: typing.Optional[str] = None,
        business_id: typing.Optional[str] = None,
        serverless_function: typing.Callable = None,
    ):
        self.api_key = api_key
        self.business_id = business_id
        self.client = WaveAPI(self.api_key)
        self.serverless_function = serverless_function
        self.routes: typing.List[Route] = [
            self.build_routes(key, **value) for key, value in service.items()
        ]

    @property
    def business(self) -> typing.Optional[WaveBusiness]:
        if self.business_id:
            return WaveBusiness(self.business_id, self.client)
        return None

    def build_token_backend(_self):
        class TokenBackend(AuthenticationBackend):
            async def authenticate(self, request: HTTPConnection):
                if "Authorization" not in request.headers:
                    bearer_token = _self.api_key
                else:
                    auth = request.headers["Authorization"]
                    bearer_token = auth.replace("Bearer", "").strip()
                if not bearer_token:
                    raise AuthenticationError(
                        "Missing WAVEAPPS_API_KEY or OAUTH_TOKEN "
                    )
                return AuthCredentials(["authenticated"]), SimpleUser(bearer_token)

        return TokenBackend

    def json_response(
        self, data, status_code: int = 200, tasks: BackgroundTasks = None
    ) -> typing.Union[JSONResponse]:
        return JSONResponse(data, status_code=status_code, background=tasks)

    async def build_response(
        self, coroutine: typing.Awaitable, status_code: int = 400
    ) -> typing.Union[JSONResponse]:
        result: service_layer.WaveResult = await coroutine
        tasks = BackgroundTasks()
        if result.errors:
            return self.json_response(
                {"status": False, **result.errors}, status_code=400, tasks=tasks
            )
        if result.tasks:
            for i in result.tasks:
                if type(i) in [list, tuple]:
                    try:
                        dict_index = [type(o) for o in i].index(dict)
                        kwarg_props = i[dict_index]
                        args_props = i[0:dict_index]
                        tasks.add_task(*args_props, **kwarg_props)
                    except ValueError:
                        tasks.add_task(*i)
                else:
                    tasks.add_task(i)
        _result: typing.Dict[str, typing.Any] = {"status": True}
        if result.data:
            _result.update(data=result.data)
        return self.json_response(_result, tasks=tasks)

    def build_view(
        self,
        func: typing.Callable,
        methods: typing.List[str] = ["POST"],
        auth: str = "authenticated",
    ) -> typing.Callable:
        async def f(request: Request):
            post_data = None
            business = None
            if "POST" in methods:
                post_data = await request.json()
                business = get_business(
                    request.app.state, post_data, request.user.username
                )
            if "GET" in methods:
                business = get_business(
                    request.app.state, request.query_params, request.user.username
                )
            return await self.build_response(
                func(
                    data=post_data,
                    business=business,
                    query_params=request.query_params,
                    headers=request.headers,
                    path_params=request.path_params,
                )
            )

        function = f
        if auth:
            function = requires(auth)(f)
        if self.serverless_function:
            function = self.serverless_function(function)
        return function

    def build_routes(
        self, path: str, func: typing.Callable, methods: typing.List[str] = ["POST"]
    ) -> Route:
        function = self.build_view(func, methods)
        return Route(path, function, methods=methods)


def build_app(api_key=None, business_id=None, serverless_function=None):
    app_views = ViewMixin(
        service_layer.service,
        api_key=api_key or str(settings.WAVEAPPS_API_KEY),
        business_id=business_id or settings.WAVE_BUSINESS_ID,
        serverless_function=serverless_function,
    )
    token_backend = app_views.build_token_backend()
    app = Starlette(
        routes=app_views.routes,
        middleware=[
            Middleware(
                AuthenticationMiddleware,
                backend=token_backend(),
                on_error=on_auth_error,
            ),
            Middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS),
        ],
    )
    app.state.WAVE_BUSINESS = app_views.business
    return app
