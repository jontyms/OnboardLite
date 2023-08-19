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
from util.approve import Approve

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

    # AWS dependencies
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    # Get data from DynamoDB
    user_data = table.get_item(
        Key={
            'id': payload.get('id')
        }
    ).get("Item", None)

    did_pay_dues = user_data.get('did_pay_dues', False)

    return templates.TemplateResponse("pay.html", {"request": request, "icon": payload['pfp'], "name": payload['name'], "id": payload['id'], "did_pay_dues": did_pay_dues})

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
        stripe_email = user_data.get('nid') + "@ucf.edu" if user_data.get('nid', False), else user_data.get('email')
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': email,
                    'quantity': 1,
                },
            ],
            customer_email=stripe_email,
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
    nid = customer_email.replace("@ucf.edu", "")

    print(customer_email)

    # AWS dependencies
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    # Get data from DynamoDB
    response = table.scan(
        FilterExpression=Attr('nid').eq(nid)
    ).get("Items", None)[0]

    member_id = response.get('id')

    # Set PAID.
    table.update_item(
        Key={
            'id': member_id
        },
        UpdateExpression='SET did_pay_dues = :val',
        ExpressionAttributeValues={
            ':val': True
        }
    )

    # Do checks to approve membership status.
    Approve.approve_member(member_id)