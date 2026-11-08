from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.purchase import Purchase
from app.models.user import User


def fulfill_checkout_session(db: Session, session: dict) -> Purchase | None:
    """Credit tokens for a paid Checkout Session exactly once.

    Safe to call from both the webhook and the success-page verify endpoint:
    the purchase row is locked, so concurrent calls can't credit twice.
    """
    purchase_id = (session.get("metadata") or {}).get("purchase_id")
    query = db.query(Purchase)
    query = (
        query.filter(Purchase.id == int(purchase_id))
        if purchase_id
        else query.filter(Purchase.stripe_checkout_session_id == session.get("id"))
    )
    purchase = query.with_for_update().first()

    if not purchase:
        db.rollback()
        return None

    if purchase.status == "completed" or session.get("payment_status") != "paid":
        db.rollback()
        return purchase

    db.query(User).filter(User.id == purchase.user_id).update(
        {User.token_balance: User.token_balance + purchase.tokens},
        synchronize_session=False,
    )
    purchase.status = "completed"
    purchase.stripe_payment_intent_id = session.get("payment_intent")
    purchase.completed_at = datetime.now(timezone.utc)
    db.commit()
    return purchase
