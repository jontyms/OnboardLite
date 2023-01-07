import boto3
from boto3.dynamodb.conditions import Key, Attr

from fastapi import APIRouter, Cookie, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from pydantic import validator, error_wrappers

from typing import Optional, Union
from models.user import PublicContact
from models.info import InfoModel

from util.authentication import Authentication
from util.errors import Errors
from util.options import Options
from util.kennelish import Kennelish, Transformer

import stripe

options = Options.fetch()
templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/pay",
    tags=["API"],
    responses=Errors.basic_http()
)

# Set Stripe API key.
stripe.api_key = options.get('stripe').get('api_key')

"""
Get API information.
"""
@router.get("/")
@Authentication.member
async def get_root(request: Request, token: Optional[str] = Cookie(None), payload: Optional[object] = {}):
    return templates.TemplateResponse("pay.html", {"request": request, "icon": payload['pfp'], "name": payload['name'], "id": payload['id']})

@router.post('/checkout')
@Authentication.member
async def create_checkout_session(request: Request, token: Optional[str] = Cookie(None), payload: Optional[object] = {}):
    # AWS dependencies
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    # Get data from DynamoDB
    user_data = table.get_item(
        Key={
            'id': payload.get('id')
        }
    ).get("Item", None)

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': options.get('stripe').get('price_id'),
                    'quantity': 1,
                },
            ],
            customer_email=user_data.get('knights_email'),
            mode='payment',
            success_url=options.get('stripe').get('url').get('success'),
            cancel_url=options.get('stripe').get('url').get('failure'),
        )
    except Exception as e:
        return str(e)

    return RedirectResponse(
        checkout_session.url, 
        status_code=303
    )

@router.post("/webhook/validate")
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    event = None
    endpoint_secret = options.get('stripe').get('webhook_secret')

    try:
        event = stripe.Webhook.construct_event(
          payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        print(e)
        return HTTPException(status_code=400, detail="Malformed payload.")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(e)
        return HTTPException(status_code=400, detail="Malformed payload.")

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Retrieve the session. If you require line items in the response, you may include them by expanding line_items.

        if session.payment_status == "paid":
            # Mark as paid.
            pay_dues(session)

        print(session)

    elif event['type'] == 'checkout.session.async_payment_succeeded':
        session = event['data']['object']
        pay_dues(session)

    # Passed signature verification
    return HTTPException(status_code=200, detail="Success.")
    # print(await request.json())
    # return "yeet"
    

def pay_dues(session):
    customer_email = session.get('customer_email')

    print(customer_email)

    # AWS dependencies
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    # Get data from DynamoDB
    response = table.scan(
        FilterExpression=Attr('knights_email').eq(customer_email)
    ).get("Items", None)[0]

    print(response)

    # Set PAID.
    table.update_item(
        Key={
            'id': response.get('id')
        },
        UpdateExpression='SET did_pay_dues = :val',
        ExpressionAttributeValues={
            ':val': True
        }
    )