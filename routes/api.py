import boto3

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import HTMLResponse

from typing import Optional
from models.user import PublicContact
from models.info import InfoModel

from util.authentication import Authentication
from util.errors import Errors
from util.options import Options
from util.kennelish import Kennelish

options = Options.fetch()

router = APIRouter(
    prefix="/api",
    tags=["API"],
    responses=Errors.basic_http()
)

@router.get("/")
async def get_root():
    return InfoModel(
        name="Onboard (beta)",
        description = "Hack@UCF's in-house membership management suite.",
        credits=[
            PublicContact(
            first_name="Jeffrey",
            surname="DiVincent",
            ops_email="jdivincent@hackucf.org"
            )
        ]
    )

@router.get("/form/{num}")
async def get_form(num: str):
    return Options.get_form_body(num)


@router.get("/form/{num}/html", response_class=HTMLResponse)
@Authentication.member
async def get_form_html(request: Request, token: Optional[str] = Cookie(None), payload: Optional[object] = {}, num: str = 1):
    # AWS dependencies
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    print(payload)

    # Get form object
    data = Options.get_form_body(num)

    # Get data from DynamoDB
    user_data = table.get_item(
        Key={
            'id': payload.get('id')
        }
    ).get("Item", None)
    
    # Have Kennelish parse the data.
    body = Kennelish.parse(data, user_data)

    return body


@router.post("/form/{num}")
async def post_form(num: str, body: object):
    