import typing
import pytest
import datetime
from waveapps import models, WaveAPI, WaveBusiness, TransactionAccounts


@pytest.fixture
def business(client):
    return WaveBusiness(
        "QnVzaW5lc3M6YzVlNWQxZWItNTVjMi00NjE4LTg4M2MtODMxNWU5OWNkZTM4", client
    )


@pytest.mark.asyncio
async def test_sample_graphql_query(business: WaveBusiness):
    await business.get_accounts()
    _business = business.instance
    assert _business.name == "Tuteria Limited"
    assert (
        _business.id == "QnVzaW5lc3M6YzVlNWQxZWItNTVjMi00NjE4LTg4M2MtODMxNWU5OWNkZTM4"
    )
    accounts = _business.accounts.get_node_values()
    assert accounts[0].name == "Admin-Business Meetings"


@pytest.mark.asyncio
async def test_create_new_account(business: WaveBusiness):
    account = await business.create_new_account(
        "Temp Account",
        accountType=models.AccountSubTypeValue.OTHER_CURRENT_ASSETS,
        description="Temp account creation",
    )
    assert account.name == "Temp Account"
    assert account.subtype.name == "Other Short-Term Asset"


@pytest.mark.asyncio
async def test_get_working_accounts(client: WaveAPI, business: WaveBusiness):
    await business.get_accounts()
    accounts = business.get_accounts_for_transaction(
        _from="GTBank NGN (Collecting)",
        _to="Tuteria Client Income Account",
        kind=models.TransactionDirection.DEPOSIT,
        currency=models.CurrencyCode.NGN,
    )
    assert accounts["to"][0]["name"] == "Tuteria Client Income Account"
    assert accounts["from"][0]["name"] == "GTBank NGN (Collecting)"

    accounts = business.get_accounts_for_transaction(
        _from="Tuteria Client Income Account",
        _to="Tuteria Expense Account",
        kind=models.TransactionDirection.WITHDRAWAL,
        currency=models.CurrencyCode.NGN,
    )
    assert accounts["to"][0]["name"] == "Tuteria Expense Account"
    assert accounts["from"][0]["name"] == "Tuteria Client Income Account"


@pytest.mark.asyncio
async def test_income_transaction(client: WaveAPI, business: WaveBusiness):
    await business.get_accounts()
    tutor_payment_fee_account = business.get_account("Transfer Fee")
    collecting_account = business.get_account("GTBank NGN (Collecting)")
    client_payment_account = business.get_account("Tuteria Client Income Account")
    tutor_payout_account = business.get_account("Tuteria Expense Account")

    # clients makes payment
    result = await business.create_transaction(
        "AFIRSTORDERID1DDS",
        datetime.datetime(2020, 1, 16),
        "This is a demo income transaction",
        40000,
        models.MoneyFlow.INFlOW,
        accounts=TransactionAccounts(
            _from=collecting_account["id"],
            to=client_payment_account["id"],
            charges=tutor_payment_fee_account["id"],
        ),
    )
    assert result.transaction is not None
    # payment of tutors
    result = await business.create_transaction(
        "FIRSTORDERID223",
        datetime.datetime(2020, 1, 16),
        "This is a demo payment to tutor",
        40000 * 0.75,
        models.MoneyFlow.OUTFLOW,
        accounts=TransactionAccounts(
            _from=client_payment_account["id"],
            to=tutor_payout_account["id"],
            charges=tutor_payment_fee_account["id"],
        ),
        charge_amount=(40000 * 0.75) * 0.05,
        charge_description="Transfer Fee",
    )
    assert result.transaction is not None
    # transaction =

