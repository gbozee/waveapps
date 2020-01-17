import datetime
import typing

from waveapps import app, models


class WaveException(Exception):
    pass


class TransactionAccounts:
    def __init__(
        self, _from: str = None, to: str = None, charges: str = None, **kwargs
    ):
        self._from = _from or kwargs.get("from")
        self.to = to
        self.charges = charges


def build_query_class_helper(
    class_fields: typing.Dict[str, type],
    input_fields: typing.Dict[str, typing.Any],
    operation_name: str,
    query_params: typing.Dict[str, str],
    variables: typing.Dict[str, typing.Any],
    kind="query",
):
    BaseClass = models.GQLQuery if kind == "query" else models.GQLMutation
    if input_fields:
        input_keys = input_fields.keys()
        class_keys = class_fields.keys()
        for k in input_keys:
            if k not in class_keys:
                raise WaveException("missing input param for mutation field %s" % k)
    Mutation = type(
        "Mutation",
        (BaseClass,),
        {
            "__annotations__": class_fields,
            "Input": type("Input", (object,), input_fields),
            "get_operation_name": classmethod(lambda cls: operation_name),
            "get_query_params": classmethod(lambda cls: query_params),
            "get_variables": classmethod(lambda cls: variables),
        },
    )
    return Mutation


class WaveBusiness:
    def __init__(
        self,
        businessId: str,
        client: app.WaveAPI,
        accountTypes: typing.List[models.AccountSubTypeValue] = None,
    ):
        self.businessId = businessId
        self._accounts: typing.List[models.Account] = []
        self._instance: models.Business = None
        self.client = client
        self.accountTypes = accountTypes
        if not accountTypes:
            self.accountTypes = [
                models.AccountSubTypeValue.OTHER_CURRENT_ASSETS,
                models.AccountSubTypeValue.EXPENSE,
                models.AccountSubTypeValue.CASH_AND_BANK,
                models.AccountSubTypeValue.PAYMENT_PROCESSING_FEES,
            ]

    def build_create_account_query(
        self,
        name,
        subType: models.AccountSubTypeValue,
        description: str = None,
        currency: str = "NGN",
    ):
        return build_query_class_helper(
            class_fields={
                "accountCreate": models.create_output_class(
                    "AccountCreateOutput", account=models.Account
                )
            },
            input_fields={
                "accountCreate": {"params": {"input": "$input"}, "useQuote": False}
            },
            operation_name="createAccountMutation",
            query_params={"$input": "AccountCreateInput!"},
            variables={
                "input": {
                    "businessId": self.businessId,
                    "subtype": subType.value,
                    "currency": models.CurrencyCode(currency.upper()).value,
                    "name": name,
                    "description": description or name,
                }
            },
            kind="mutation",
        )

    def build_accounts_query(self):
        return build_query_class_helper(
            class_fields={"business": models.Business},
            input_fields={
                "business": {"params": {"id": "$businessId"}, "useQuote": False}
            },
            operation_name="BusinessQuery",
            query_params={"$businessId": "ID!", "$subtypes": "[AccountSubtypeValue!]!"},
            variables={
                "businessId": self.businessId,
                "subtypes": [x.value for x in self.accountTypes],
            },
        )

    @property
    def accounts(self) -> typing.List[typing.Dict[str, str]]:
        return [
            {
                "name": x.name,
                "id": x.id,
                "currency": x.currency.code,
                "type": x.subtype.value,
            }
            for x in self._accounts
        ]

    @property
    def instance(self) -> models.Business:
        return self._instance

    async def get_accounts(self):
        Query = self.build_accounts_query()
        result = await self.client.query_helper(Query)
        self._instance = result.business
        if self._instance:
            self._accounts = result.business.accounts.get_node_values()

    async def create_new_account(
        self,
        name: str,
        description: str = None,
        accountType: models.AccountSubTypeValue = models.AccountSubTypeValue.OTHER_CURRENT_ASSETS,
        currency="ngn",
    ) -> typing.Optional[models.Account]:
        results = [x for x in self._accounts if x.name == name]
        if results:
            return results[0]
        Mutation = self.build_create_account_query(
            name, accountType, description=description, currency=currency
        )
        result = await self.client.query_helper(Mutation)
        account = result.accountCreate.account
        if account:
            return account
        return None

    def get_account(self, name) -> typing.Optional[typing.Dict[str, str]]:
        result = [x for x in self.accounts if name in x["name"].strip() == name]
        if result:
            return result[0]
        return None

    def get_accounts_for_transaction(
        self,
        _from,
        _to,
        kind: models.TransactionDirection,
        currency: models.CurrencyCode = models.CurrencyCode.NGN,
    ) -> typing.Dict[str, typing.List[typing.Dict[str, typing.Any]]]:
        from_accounts: typing.List[typing.Any] = []

        to_accounts: typing.List[typing.Any] = []
        if kind == models.TransactionDirection.DEPOSIT:
            from_accounts = [
                x
                for x in self.accounts
                if x["type"] == models.AccountSubTypeValue.CASH_AND_BANK.value
                and x["currency"] == currency.value
            ]
            to_accounts = [
                x
                for x in self.accounts
                if x["type"] == models.AccountSubTypeValue.OTHER_CURRENT_ASSETS.value
                and x["currency"] == currency.value
            ]
        else:
            from_accounts = [
                x
                for x in self.accounts
                if x["type"] == models.AccountSubTypeValue.OTHER_CURRENT_ASSETS.value
                and x["currency"] == currency.value
            ]
            to_accounts = [
                x
                for x in self.accounts
                if x["type"] == models.AccountSubTypeValue.EXPENSE.value
                and x["currency"] == currency.value
            ]
        from_accounts = [x for x in from_accounts if x["name"] == _from]
        to_accounts = [x for x in to_accounts if x["name"] == _to]
        return {"from": from_accounts, "to": to_accounts}

    async def create_transaction(
        self,
        orderId: str,
        date: datetime.datetime,
        description: str,
        amount: float,
        kind: models.MoneyFlow,
        accounts: TransactionAccounts,
        currency: models.CurrencyCode = models.CurrencyCode.NGN,
        charge_amount: float = 0,
        charge_description: str = None,
        additional_line_item: typing.List[typing.Dict[str, typing.Any]] = None,
    ) -> models.MoneyTransactionCreateOutput:
        if kind == models.MoneyFlow.INFlOW:
            _kind = models.TransactionDirection.WITHDRAWAL
        else:
            _kind = models.TransactionDirection.DEPOSIT
        balance = (
            models.BalanceType.DEBIT
            if _kind == models.TransactionDirection.WITHDRAWAL
            else models.BalanceType.CREDIT
        )
        lineItems = [
            {
                "accountId": accounts.to,
                "amount": "%.2f" % (amount - charge_amount),
                "balance": balance.value,
                "description": description,
                "taxes": [],
            }
        ]
        if charge_amount > 0:
            lineItems.append(
                {
                    "accountId": accounts.charges,
                    "amount": "%.2f" % (charge_amount),
                    "balance": models.BalanceType.CREDIT.value,
                    "description": charge_description,
                    "taxes": [],
                }
            )
        if additional_line_item:
            lineItems.extend(additional_line_item)
        Mutation = build_query_class_helper(
            class_fields={
                "moneyTransactionCreate": models.MoneyTransactionCreateOutput
            },
            input_fields={
                "moneyTransactionCreate": {
                    "params": {"input": "$input"},
                    "useQuote": False,
                }
            },
            operation_name="createTransactionMutation",
            query_params={"$input": "MoneyTransactionCreateInput!"},
            kind="mutation",
            variables={
                "input": {
                    "businessId": self.businessId,
                    "externalId": orderId,
                    "date": date.strftime("%Y-%m-%d"),
                    "description": description,
                    "anchor": {
                        "accountId": accounts._from,
                        "amount": "%.2f" % amount,
                        "direction": _kind.value,
                    },
                    "lineItems": lineItems,
                }
            },
        )
        result = await self.client.query_helper(Mutation)
        return result.moneyTransactionCreate
