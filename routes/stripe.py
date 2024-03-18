import logging
from typing import Optional

import boto3
import stripe
from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from util.approve import Approve
from util.authentication import Authentication
from util.errors import Errors
from util.options import Settings

templates = Jinja2Templates(directory="templates")


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pay", tags=["API"], responses=Errors.basic_http())

# Set Stripe API key.
stripe.api_key = Settings().stripe.api_key.get_secret_value()


"""
Get API information.
"""


@router.get("/")
@Authentication.member
async def get_root(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
):
    # AWS dependencies
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(Settings().aws.table)

    # Get data from DynamoDB
    user_data = table.get_item(Key={"id": user_jwt.get("id")}).get("Item", None)

    did_pay_dues = user_data.get("did_pay_dues", False)

    is_nid = True if user_data.get("nid", False) else False

    return templates.TemplateResponse(
        "pay.html",
        {
            "request": request,
            "icon": user_jwt["pfp"],
            "name": user_jwt["name"],
            "id": user_jwt["id"],
            "did_pay_dues": did_pay_dues,
            "is_nid": is_nid,
        },
    )


@router.post("/checkout")
@Authentication.member
async def create_checkout_session(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
):
    # AWS dependencies
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(Settings().aws.table)

    # Get data from DynamoDB
    user_data = table.get_item(Key={"id": user_jwt.get("id")}).get("Item", None)

    try:
        stripe_email = user_data.get("email")
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
        return str(e)

    return RedirectResponse(checkout_session.url, status_code=303)


@router.post("/webhook/validate")
async def webhook(request: Request):
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
        session = event["data"]["object"]

        if session.payment_status == "paid":
            # Mark as paid.
            pay_dues(session)

    elif event["type"] == "checkout.session.async_payment_succeeded":
        session = event["data"]["object"]
        pay_dues(session)

    # Passed signature verification
    return HTTPException(status_code=200, detail="Success.")


def pay_dues(session):
    customer_email = session.get("customer_email")

    # AWS dependencies
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(Settings().aws.table)

    # Get data from DynamoDB
    response = table.scan(FilterExpression=Attr("email").eq(customer_email)).get(
        "Items", None
    )[0]

    member_id = response.get("id")

    # Set PAID.
    table.update_item(
        Key={"id": member_id},
        UpdateExpression="SET did_pay_dues = :val",
        ExpressionAttributeValues={":val": True},
    )

    # Do checks to approve membership status.
    Approve.approve_member(member_id)
