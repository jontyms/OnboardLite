import boto3, json
from boto3.dynamodb.conditions import Key, Attr

from jose import JWTError, jwt

from fastapi import APIRouter, Cookie, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.encoders import jsonable_encoder

from pydantic import validator, error_wrappers

from typing import Optional
from models.user import UserModelMutable
from models.info import InfoModel

from util.authentication import Authentication
from util.errors import Errors
from util.options import Options
from util.approve import Approve
from util.kennelish import Kennelish, Transformer

options = Options.fetch()

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses=Errors.basic_http()
)


"""
Renders the Admin home page.
"""
@router.get("/")
@Authentication.admin
async def admin(request: Request, token: Optional[str] = Cookie(None)):
    payload = jwt.decode(token, options.get("jwt").get("secret"), algorithms=options.get("jwt").get("algorithm"))
    return templates.TemplateResponse("admin_searcher.html", {"request": request, "icon": payload['pfp'], "name": payload['name'], "id": payload['id']})


"""
API endpoint that re-runs the member verification workflow
"""
@router.get("/refresh/")
@Authentication.admin
async def get_refresh(request: Request, token: Optional[str] = Cookie(None), member_id: Optional[str] = "FAIL"):
    if member_id == "FAIL":
        return {
            "data": {},
            "error": "Missing ?member_id"
        }

    Approve.approve_member(member_id)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.get_item(
        Key={
            'id': member_id
        }
    ).get("Item", None)

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    return {
        "data": data
    }


"""
API endpoint that gets a specific user's data as JSON
"""
@router.get("/get/")
@Authentication.admin
async def admin_get_single(request: Request, token: Optional[str] = Cookie(None), member_id: Optional[str] = "FAIL"):
    if member_id == "FAIL":
        return {
            "data": {},
            "error": "Missing ?member_id"
        }

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.get_item(
        Key={
            'id': member_id
        }
    ).get("Item", None)

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    return {
        "data": data
    }


"""
API endpoint that modifies a given user's data
"""
@router.post("/get/")
@Authentication.admin
async def admin_edit(request: Request, token: Optional[str] = Cookie(None), input_data: Optional[UserModelMutable] = {}):

    member_id = input_data.id

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    old_data = table.get_item(
        Key={
            'id': member_id
        }
    ).get("Item", None)

    if not old_data:
        return Errors.generate(request, 404, "User Not Found")

    # Take Pydantic data -> dict -> strip null values
    new_data = {k: v for k, v in jsonable_encoder(input_data).items() if v is not None}

    # Existing  U  Provided
    union = {**old_data, **new_data}

    # This is how this works:
    # 1. Get old data
    # 2. Get new data (pydantic-validated)
    # 3. Union the two
    # 4. Put back as one giant entry
    
    table.put_item(Item=union)

    return {
        "data": union,
        "msg": "Updated successfully!"
    }


"""
API endpoint that dumps all users as JSON.
"""
@router.get("/list")
@Authentication.admin
async def admin_list(request: Request, token: Optional[str] = Cookie(None)):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.scan().get("Items", None)
    return {
        "data": data
    }


"""
API endpoint that dumps all users as CSV.
"""
@router.get("/csv")
@Authentication.admin
async def admin_list(request: Request, token: Optional[str] = Cookie(None)):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.scan().get("Items", None)
    
    output = "Membership ID, First Name, Last Name, NID, Is Returning, Gender, Major, Class Standing, Shirt Size, Discord Username, Experience, Cyber Interests, Event Interest, Is C3 Interest, Comments, Ethics Form Timestamp, Minecraft, Infra Email\n"
    for user in data:
        output += f'"{user.get("id")}", '
        output += f'"{user.get("first_name")}", '
        output += f'"{user.get("surname")}", '
        output += f'"{user.get("nid")}", '
        output += f'"{user.get("is_returning")}", '
        output += f'"{user.get("gender")}", '
        output += f'"{user.get("major")}", '
        output += f'"{user.get("class_standing")}", '
        output += f'"{user.get("shirt_size")}", '
        output += f'"{user.get("discord", {}).get("username")}", '
        output += f'"{user.get("experience")}", '
        output += f'"{user.get("curiosity")}", '
        output += f'"{user.get("attending")}", '
        output += f'"{user.get("c3_interest")}", '
        
        output += f'"{user.get("comments")}", '

        output += f'"{user.get("ethics_form", {}).get("signtime")}", '
        output += f'"{user.get("minecraft")}", '
        output += f'"{user.get("infra_email")}"\n'

    return Response(content=output, headers={
        "Content-Type": "text/csv"
    })
