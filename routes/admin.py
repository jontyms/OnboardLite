import boto3, json
from boto3.dynamodb.conditions import Key, Attr

from jose import JWTError, jwt

from fastapi import APIRouter, Cookie, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from pydantic import validator, error_wrappers

from typing import Optional
from models.user import PublicContact
from models.info import InfoModel

from util.authentication import Authentication
from util.errors import Errors
from util.options import Options
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
    return {
        "data": data
    }


# <TODO!>
# """
# API endpoint that modifies a given user's data
# """
# @router.post("/get/")
# @Authentication.admin
# async def admin_edit(request: Request, token: Optional[str] = Cookie(None), member_id: Optional[str] = "FAIL"):
#     if member_id == "FAIL":
#         return {
#             "data": {},
#             "error": "Missing ?member_id"
#         }

#     dynamodb = boto3.resource('dynamodb')
#     table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
#     data = table.get_item(
#         Key={
#             'id': member_id
#         }
#     ).get("Item", None)
#     return {
#         "data": data
#     }


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
