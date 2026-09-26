from datetime import datetime, timezone
from uuid import uuid4

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.ai.token_packages import TOKEN_PACKAGES, get_package
from app.core.jwt import get_current_user
from app.database.session import get_db
from app.models.purchase import Purchase
from app.models.user import User
from app.schema.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    TokenBalanceResponse,
    TokenPackageResponse,
)
from app.services.stripe_service import construct_webhook_event, create_checkout_session

router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
)


@router.get("/packages", response_model=list[TokenPackageResponse])
def list_token_packages():
    return [
        TokenPackageResponse(key=key, tokens=pkg["tokens"], amount=pkg["amount"])
        for key, pkg in TOKEN_PACKAGES.items()
    ]


@router.get("/tokens", response_model=TokenBalanceResponse)
def get_token_balance(current_user: User = Depends(get_current_user)):
    return TokenBalanceResponse(token_balance=current_user.token_balance)


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def create_checkout(
    payload: CheckoutSessionRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    package = get_package(payload.package)
    if not package:
        raise HTTPException(status_code=400, detail="Unknown token package")

    key = idempotency_key or uuid4().hex

    existing = db.query(Purchase).filter(Purchase.idempotency_key == key).first()
    if existing:
        if not existing.stripe_checkout_session_id:
            raise HTTPException(status_code=409, detail="Checkout session for this request is still being created")
        session = stripe.checkout.Session.retrieve(existing.stripe_checkout_session_id)
        return CheckoutSessionResponse(checkout_url=session.url, session_id=session.id)

    purchase = Purchase(
        user_id=current_user.id,
        package=payload.package,
        tokens=package["tokens"],
        amount=package["amount"] * 100,
        idempotency_key=key,
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    try:
        session = create_checkout_session(
            user_id=current_user.id,
            purchase_id=purchase.id,
            price_id=package["price_id"],
            idempotency_key=key,
        )
    except stripe.error.StripeError as e:
        db.delete(purchase)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Could not start checkout: {e.user_message or str(e)}")

    purchase.stripe_checkout_session_id = session.id
    db.commit()

    return CheckoutSessionResponse(checkout_url=session.url, session_id=session.id)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    payload = await request.body()

    try:
        event = construct_webhook_event(payload, stripe_signature)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook payload or signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        purchase_id = (session.get("metadata") or {}).get("purchase_id")

        purchase = (
            db.query(Purchase).filter(Purchase.id == purchase_id).first()
            if purchase_id
            else db.query(Purchase).filter(Purchase.stripe_checkout_session_id == session.get("id")).first()
        )

        if purchase and purchase.status != "completed" and session.get("payment_status") == "paid":
            user = db.query(User).filter(User.id == purchase.user_id).first()
            if user:
                user.token_balance += purchase.tokens
            purchase.status = "completed"
            purchase.stripe_payment_intent_id = session.get("payment_intent")
            purchase.completed_at = datetime.now(timezone.utc)
            db.commit()

    return {"status": "success"}
