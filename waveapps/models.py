import typing
import enum
from graphql_client_utils import (
    GQLKlass,
    create_connection_class,
    GQLQuery,
    GQLMutation,
)


class MoneyFlow(enum.Enum):
    INFlOW = "INFLOW"
    OUTFLOW = "OUTFLOW"


class BalanceType(enum.Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class TransactionDirection(enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class CurrencyCode(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"


class AccountTypeValue(enum.Enum):
    ASSET = "ASSET"
    EQUITY = "EQUITY"
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    LIABILITY = "LIABILITY"


class AccountSubTypeValue(enum.Enum):
    CASH_AND_BANK = "CASH_AND_BANK"
    COST_OF_GOODS_SOLD = "COST_OF_GOODS_SOLD"
    CREDIT_CARD = "CREDIT_CARD"
    CUSTOMER_PREPAYMENTS_AND_CREDITS = "CUSTOMER_PREPAYMENTS_AND_CREDITS"
    DEPRECIATION_AND_AMORTIZATION = "DEPRECIATION_AND_AMORTIZATION"
    DISCOUNTS = "DISCOUNTS"
    DUE_FOR_PAYROLL = "DUE_FOR_PAYROLL"
    DUE_TO_YOU_AND_OTHER_OWNERS = "DUE_TO_YOU_AND_OTHER_OWNERS"
    EXPENSE = "EXPENSE"
    GAIN_ON_FOREIGN_EXCHANGE = "GAIN_ON_FOREIGN_EXCHANGE"
    INCOME = "INCOME"
    INVENTORY = "INVENTORY"
    LOANS = "LOANS"
    LOSS_ON_FOREIGN_EXCHANGE = "LOSS_ON_FOREIGN_EXCHANGE"
    MONEY_IN_TRANSIT = "MONEY_IN_TRANSIT"
    NON_RETAINED_EARNINGS = "NON_RETAINED_EARNINGS"
    OTHER_CURRENT_ASSETS = "OTHER_CURRENT_ASSETS"
    OTHER_CURRENT_LIABILITY = "OTHER_CURRENT_LIABILITY"
    OTHER_INCOME = "OTHER_INCOME"
    OTHER_LONG_TERM_ASSETS = "OTHER_LONG_TERM_ASSETS"
    OTHER_LONG_TERM_LIABILITY = "OTHER_LONG_TERM_LIABILITY"
    PAYABLE = "PAYABLE"
    PAYABLE_BILLS = "PAYABLE_BILLS"
    PAYABLE_OTHER = "PAYABLE_OTHER"
    PAYMENT_PROCESSING_FEES = "PAYMENT_PROCESSING_FEES"
    PAYROLL_EXPENSES = "PAYROLL_EXPENSES"
    PROPERTY_PLANT_EQUIPMENT = "PROPERTY_PLANT_EQUIPMENT"
    RECEIVABLE = "RECEIVABLE"
    RECEIVABLE_INVOICES = "RECEIVABLE_INVOICES"
    RECEIVABLE_OTHER = "RECEIVABLE_OTHER"
    RETAINED_EARNINGS = "RETAINED_EARNINGS"
    SALES_TAX = "SALES_TAX"
    TRANSFERS = "TRANSFERS"
    UNCATEGORIZED_EXPENSE = "UNCATEGORIZED_EXPENSE"
    UNCATEGORIZED_INCOME = "UNCATEGORIZED_INCOME"
    VENDOR_PREPAYMENTS_AND_CREDITS = "VENDOR_PREPAYMENTS_AND_CREDITS"


class InputError(GQLKlass):
    path: typing.List[str]
    message: str
    code: str


def create_output_class(Name, **kwargs) -> type:
    return type(
        Name,
        (GQLKlass,),
        {
            "__annotations__": {
                **kwargs,
                "didSucceed": bool,
                "inputErrors": typing.List[InputError],
            }
        },
    )


class PageInfo(GQLKlass):
    currentPage: int
    totalPages: int
    totalCount: int


class SalesTax(GQLKlass):
    id: str
    name: str
    abbreviation: str
    description: str
    taxNumber: str
    rate: float
    isCompound: bool
    isRecoverable: bool
    isArchived: bool


class Currency(GQLKlass):
    code: str
    symbol: str
    name: str
    plural: str
    exponent: int


class AccountType(GQLKlass):
    name: str
    normalBalanceType: str
    value: str


class AccountSubType(GQLKlass):
    name: str
    value: str
    type: AccountType


class Account(GQLKlass):
    id: str
    name: str
    description: str
    subtype: AccountSubType
    currency: Currency
    type: AccountType
    normalBalanceType: str
    isArchived: bool


class Invoice(GQLKlass):
    pass


class Transaction(GQLKlass):
    id: str


class Province(GQLKlass):
    code: str
    name: str
    slug: str


class Country(GQLKlass):
    code: str
    name: str
    currency: Currency
    nameWithArticle: str
    provinces: typing.List[Province]


class Address(GQLKlass):
    addressLine1: str
    addressLine2: str
    city: str
    province: Province
    country: Country
    postalCode: str


class Customer(GQLKlass):
    id: str
    name: str
    address: Address
    firstName: str
    lastName: str
    displayId: str
    email: str
    mobile: str
    phone: str
    fax: str
    currency: Currency


class BusinessType(GQLKlass):
    name: str
    value: str


class BusinessSubtype(GQLKlass):
    name: str
    value: str


class Business(GQLKlass):
    name: str
    id: str
    accounts: create_connection_class(Account, pageInfo=PageInfo)

    class Input:
        accounts = {
            "params": {"subtypes": "$subtypes", "pageSize": 100, "isArchived": "false"},
            "useQuote": False,
        }


# class MoneyTransactionCreateOutput(GQLKlass):
#     transaction: Transaction
#     didSucceed: bool
#     inputErrors: typing.List[InputError]


# class AccountCreateOutput(GQLKlass):
#     account: Account
#     didSucceed: bool
#     inputErrors: typing.List[InputError]


# class SalesTaxCreateOutput(GQLKlass):
#     salesTax: SalesTax
#     didSucceed: bool
#     inputErrors: typing.List[InputError]
MoneyTransactionCreateOutput = create_output_class(
    "MoneyTransactionCreateOutput", transaction=Transaction
)
AccountCreateOutput = create_output_class("AccountCreateOutput", salesTax=AccountType)
SalesTaxCreateOutput = create_output_class("SalesTaxCreateOutput", salesTax=SalesTax)
CustomerCreateOutput = create_output_class("CustomerCreateOutput", customer=Customer)
# class CustomerCreateOutput(GQLKlass):
#     customer: Customer
#     didSucceed: bool
#     inputErrors: typing.List[InputError]

