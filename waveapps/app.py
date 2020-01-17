import typing
from urllib.parse import quote

import httpx

from accounting_oauth import AccountingOauth, StorageInterface, request_helper
from graphql_client_utils import GQLKlass, GQLMutation, GQLQuery

U = typing.TypeVar("U", bound=GQLKlass)


class WaveStorageInterface(StorageInterface):
    def __init__(
        self,
        userId: str = None,
        businessId: str = None,
        expires_in: int = None,
        **kwargs,
    ):
        self.userId = userId
        self.businessId = businessId
        self.expires_in = expires_in
        super().__init__(**kwargs)

    def expiry_config(self):
        in_hours = 1
        if self.expires_in:
            in_hours = self.expires_in / 3600
        return {"access_token": in_hours, "refresh_token": 100 * 24}

    async def get_token(self, view_url):
        return await super().get_token(view_url)

    async def save_token(self, **token):
        self.userId = token.get("userId")
        self.businessId = token.get("businessId")
        self.expires_in = token.get("expires_in")
        return await super().save_token(**token)


class WaveOauth(AccountingOauth):
    def __init__(
        self,
        redirect_uri: str,
        client_id: str,
        client_secret: str,
        state="app-server",
        scopes: typing.Optional[typing.List[str]] = None,
        storage_interface=WaveStorageInterface,
        businessId: str = "",
    ):
        _scope = scopes
        if not _scope:
            _scope = ["account:*", "business:*", "sales_tax:*", "transaction:*"]
        super().__init__(
            redirect_uri,
            client_id,
            client_secret,
            _scope,
            "https://api.waveapps.com/oauth2/token/",
            "https://api.waveapps.com/oauth2/authorize/",
            storage_interface=storage_interface,
            businessId=businessId,
        )

    def auth_params(self) -> typing.Dict[str, typing.Any]:
        result = super().auth_params()
        if not result.get("businessId"):
            result.pop("businessId", None)
        return result

    def token_params(self, key):
        """Different post params for either authorize or refresh"""
        result = {"client_id": self.client_id, "client_secret": self.client_secret}
        if key == "refresh_token":
            result.update(scope=quote(" ".join(self.scopes)))
        return result


class WaveAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://gql.waveapps.com/graphql/public"

    async def call_api(self, query: str, variables=None, operationName: str = None):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        return await request_helper(
            self.base_url,
            "POST",
            data={
                "query": query,
                "variables": variables or {},
                "operationName": operationName,
            },
            headers=headers,
        )

    async def query_helper(
        self, query_klass: typing.Type[typing.Union[GQLQuery, GQLMutation]]
    ) -> typing.Union[GQLQuery, GQLMutation]:
        query = query_klass.as_gql()
        operationName = query_klass.get_operation_name()
        variables = query_klass.get_variables()
        result = await self.call_api(
            query, variables=variables, operationName=operationName
        )
        if result.status_code >= 400:
            raise result.raise_for_status()
        data = result.json()
        return query_klass(**data["data"])
