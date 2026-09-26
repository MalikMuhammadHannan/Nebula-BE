from pydantic import BaseModel


class CheckoutSessionRequest(BaseModel):
    package: str


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class TokenBalanceResponse(BaseModel):
    token_balance: int


class TokenPackageResponse(BaseModel):
    key: str
    tokens: int
    amount: int
