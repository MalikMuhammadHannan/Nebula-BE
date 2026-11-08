import stripe

from app.config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, FRONTEND_URL

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(user_id: int, purchase_id: int, price_id: str, idempotency_key: str):
    return stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/billing/cancel",
        client_reference_id=str(user_id),
        metadata={
            "user_id": str(user_id),
            "purchase_id": str(purchase_id),
        },
        idempotency_key=idempotency_key,
    )


def construct_webhook_event(payload: bytes, sig_header: str | None):
    return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)


def retrieve_checkout_session(session_id: str):
    return stripe.checkout.Session.retrieve(session_id)
