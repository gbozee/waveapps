import datetime
import typing
from waveapps import models, WaveBusiness, TransactionAccounts, request_helper
from . import settings


class WaveResult:
    def __init__(
        self,
        errors: dict = None,
        data: dict = None,
        tasks: typing.List[typing.Any] = None,
    ):
        self.errors = errors
        self.tasks = tasks
        self.data = data


async def create_account(data, business: WaveBusiness, **kwargs) -> WaveResult:
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
        return WaveResult(errors={"msg": "Could not create account"})
    return WaveResult(
        data={
            "name": result.name,
            "id": result.id,
            "currency": result.currency.code,
            "type": result.subtype.value,
        }
    )


async def get_accounts(**kwargs) -> WaveResult:
    business: WaveBusiness = kwargs.get("business")
    await business.get_accounts()
    return WaveResult(data=business.accounts)


async def create_transaction(data, business, **kwargs):
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
        if settings.WEBHOOK_CALLBACK:
            result = await request_helper(
                settings.WEBHOOK_CALLBACK,
                "POST",
                json={"order": data["order"], "created": created, "id": _id},
            )

    return WaveResult(
        data={
            "msg": "creating transaction. listen to {} to update".format(
                settings.WEBHOOK_CALLBACK
            )
        },
        tasks=[_create_transaction],
    )
    tasks.add_task(_create_transaction)


service = {
    "/create-transaction": {"func": create_transaction, "methods": ["POST"]},
    "/create-account": {"func": create_account, "methods": ["POST"]},
    "/accounts": {"func": get_accounts, "methods": ["GET"]},
}
