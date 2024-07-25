import logging
import uuid
from typing import Optional

import stripe
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models.user import UserModel, user_to_dict
from app.util.approve import Approve
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.errors import Errors
from app.util.settings import Settings

templates = Jinja2Templates(directory="app/templates")


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pay", tags=["API"], responses=Errors.basic_http())

if not Settings().stripe.pause_payments:
    # Set Stripe API key.
    stripe.api_key = Settings().stripe.api_key.get_secret_value()


@router.get("/")
@Authentication.member
async def get_root(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session: Session = Depends(get_session),
):
    """
    Get API information.
    """
    statement = (
        select(UserModel)
        .where(UserModel.id == uuid.UUID(user_jwt["id"]))
        .options(selectinload(UserModel.discord))
    )
    user_data = session.exec(statement).one_or_none()
    did_pay_dues = user_data.did_pay_dues

    user_data = user_to_dict(user_data)

    paused_payments = Settings().stripe.pause_payments

    return templates.TemplateResponse(
        "pay.html",
        {
            "request": request,
            "user_data": user_data,
            "did_pay_dues": did_pay_dues,
            "paused_payments": paused_payments,
        },
    )


@router.api_route("/checkout", methods=["GET", "POST"])
@Authentication.member
async def create_checkout_session(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session: Session = Depends(get_session),
):
    if Settings().stripe.pause_payments:
        return Errors.generate(request, 503, "Payments Paused")

    user_data = session.exec(
        select(UserModel).where(UserModel.id == uuid.UUID(user_jwt.get("id")))
    ).one_or_none()
    if user_data.email == None:
        return Errors.generate(request, 400, "No email associated with account")
    try:
        stripe_email = user_data.email
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    "price": Settings().stripe.price_id,
                    "quantity": 1,
                },
            ],
            customer_email=stripe_email,
            mode="payment",
            success_url=Settings().stripe.url_success,
            cancel_url=Settings().stripe.url_failure,
        )
    except Exception as e:
        logger.exeption("Error creating checkout session in stripe.py", e)
        return HTTPException(status_code=500, detail="Error creating checkout session.")

    return RedirectResponse(checkout_session.url, status_code=303)


@router.post("/webhook/validate")
async def webhook(request: Request, session: Session = Depends(get_session)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None
    endpoint_secret = Settings().stripe.webhook_secret.get_secret_value()

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        # Invalid payload
        logger.error("Malformed Stripe Payload", e)
        return HTTPException(status_code=400, detail="Malformed payload.")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error("Malformed Stripe Payload", e)
        return HTTPException(status_code=400, detail="Malformed payload.")

    # Event Handling
    if event["type"] == "checkout.session.completed":
        # Retrieve the session. If you require line items in the response, you may include them by expanding line_items.
        checkout_session = event["data"]["object"]

        if checkout_session.payment_status == "paid":
            # Mark as paid.
            pay_dues(checkout_session, session)

    elif event["type"] == "checkout.session.async_payment_succeeded":
        checkout_session = event["data"]["object"]
        pay_dues(checkout_session, session)

    # Passed signature verification
    return HTTPException(status_code=200, detail="Success.")


def pay_dues(checkout_session, db_session):
    customer_email = checkout_session.get("customer_email")

    user_data = db_session.exec(
        select(UserModel).where(UserModel.email == customer_email)
    ).one_or_none()

    member_id = user_data.id

    # Set PAID.
    user_data.did_pay_dues = True
    db_session.add(user_data)
    db_session.commit()
    db_session.refresh(user_data)

    # Do checks to approve membership status.
    Approve.approve_member(member_id)
