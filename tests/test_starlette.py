import datetime

import httpx
import pytest

from waveapps import models
from waveapps.business import TransactionAccounts, WaveBusiness


@pytest.fixture
def create_and_test_transaction(app: httpx.Client):
    async def _create_transaction(data):
        response = await app.post("/create-transaction", json=data)
        assert response.status_code == 200
        assert response.json() == {
            "status": True,
            "data": {
                "msg": "creating transaction. listen to http://the-main-site.com/hooks to update"
            },
        }

    return _create_transaction


@pytest.mark.asyncio
async def test_create_transaction(create_and_test_transaction, mocker, create_future):
    mocked = mocker.patch(
        "waveapps.frameworks.starlette.service_layer.WaveBusiness.create_transaction"
    )
    mocked_http = mocker.patch(
        "waveapps.frameworks.starlette.service_layer.request_helper"
    )
    mocked_http.return_value = create_future(None)
    mocked.return_value = create_future(
        models.MoneyTransactionCreateOutput(transaction={"id": 23})
    )
    await create_and_test_transaction(
        {
            "order": "sample-order",
            "date": "2020-01-17",
            "description": "Payment of james novak",
            "amount": 20000,
            "kind": "expense",
            "accounts": {
                "from": "AccountFrom",
                "to": "AccountTo",
                "charges": "AccountCharges",
            },
            "currency": "usd",
        }
    )
    mocked.assert_called_with(
        orderId="sample-order",
        date=datetime.datetime(2020, 1, 17),
        description="Payment of james novak",
        kind=models.MoneyFlow.OUTFLOW,
        amount=20000,
        currency=models.CurrencyCode.USD,
        accounts=TransactionAccounts(
            **{"from": "AccountFrom", "to": "AccountTo", "charges": "AccountCharges"}
        ),
    )
    mocked_http.assert_called_with(
        "http://the-main-site.com/hooks",
        "POST",
        json={"order": "sample-order", "created": True, "id": 23},
    )
    await create_and_test_transaction(
        {
            "order": "sample-order",
            "date": "2020-01-17",
            "description": "Payment of lessons",
            "amount": 20000,
            "kind": "income",
            "accounts": {
                "from": "AccountFrom",
                "to": "AccountTo",
                "charges": "AccountCharges",
            },
            "currency": "ngn",
            "additional_items": [
                {
                    "account": "AccountCharges",
                    "amount": 4000,
                    "kind": "expense",
                    "description": "Service fee",
                }
            ],
        }
    )
    mocked.assert_called_with(
        orderId="sample-order",
        date=datetime.datetime(2020, 1, 17),
        description="Payment of lessons",
        kind=models.MoneyFlow.INFlOW,
        amount=20000,
        currency=models.CurrencyCode.NGN,
        accounts=TransactionAccounts(
            **{"from": "AccountFrom", "to": "AccountTo", "charges": "AccountCharges"}
        ),
        additional_line_item=[
            {
                "accountId": "AccountCharges",
                "amount": "4000.00",
                "balance": models.BalanceType.CREDIT.value,
                "description": "Service fee",
                "taxes": [],
            }
        ],
    )
    mocked.return_value = create_future(
        models.MoneyTransactionCreateOutput(transaction=None)
    )
    await create_and_test_transaction(
        {
            "order": "sample-order",
            "date": "2020-01-17",
            "description": "Payment of lessons",
            "amount": 20000,
            "kind": "income",
            "accounts": {
                "from": "AccountFrom",
                "to": "AccountTo",
                "charges": "AccountCharges",
            },
            "currency": "ngn",
            "service_fee": 400,
            "service_fee_description": "Service Fee",
        }
    )
    mocked.assert_called_with(
        orderId="sample-order",
        date=datetime.datetime(2020, 1, 17),
        description="Payment of lessons",
        kind=models.MoneyFlow.INFlOW,
        amount=20000,
        currency=models.CurrencyCode.NGN,
        accounts=TransactionAccounts(
            **{"from": "AccountFrom", "to": "AccountTo", "charges": "AccountCharges"}
        ),
        charge_amount=400,
        charge_description="Service Fee",
    )
    mocked_http.assert_called_with(
        "http://the-main-site.com/hooks",
        "POST",
        json={"order": "sample-order", "created": False, "id": None},
    )


@pytest.mark.asyncio
async def test_create_account(app: httpx.Client, mocker, create_future):
    Mutation = WaveBusiness("eweww", None).build_create_account_query(
        "hello", models.AccountSubTypeValue.CASH_AND_BANK
    )
    mocked = mocker.patch("waveapps.WaveAPI.query_helper")
    mocked.return_value = create_future(
        Mutation(
            accountCreate={
                "account": {
                    "name": "New Account",
                    "id": "IOOI",
                    "currency": {"code": "EUR"},
                    "subtype": {"value": "ASSET"},
                }
            }
        )
    )
    response = await app.post(
        "/create-account",
        json={
            "name": "New Account",
            "description": "Keeping track of the bad boys",
            "currency": "eur",
            "type": "asset",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": True,
        "data": {
            "name": "New Account",
            "id": "IOOI",
            "currency": "EUR",
            "type": "ASSET",
        },
    }


@pytest.mark.asyncio
async def test_get_accounts(app: httpx.Client, mocker, create_future):
    Query = WaveBusiness("eweww", None).build_accounts_query()
    mocked = mocker.patch("waveapps.WaveAPI.query_helper")
    mocked.return_value = create_future(
        Query(
            business={
                "accounts": {
                    "edges": [
                        {
                            "node": {
                                "name": "Account1",
                                "id": "ABESD",
                                "currency": {"code": "NGN"},
                                "subtype": {"value": "Expense"},
                            }
                        }
                    ]
                }
            }
        )
    )
    response = await app.get("/accounts")
    assert response.status_code == 200
    assert response.json() == {
        "status": True,
        "data": [
            {"name": "Account1", "id": "ABESD", "currency": "NGN", "type": "Expense"}
        ],
    }
