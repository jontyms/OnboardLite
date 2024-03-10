from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Body, Cookie, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.templating import Jinja2Templates
from jose import jwt

from models.user import UserModelMutable
from util.approve import Approve
from util.authentication import Authentication
from util.discord import Discord
from util.email import Email
from util.errors import Errors
from util.options import Options

options = Options.fetch()

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/admin", tags=["Admin"], responses=Errors.basic_http())


@router.get("/")
@Authentication.admin
async def admin(request: Request, token: Optional[str] = Cookie(None)):
    """
    Renders the Admin home page.
    """
    payload = jwt.decode(
        token,
        options.get("jwt").get("secret"),
        algorithms=options.get("jwt").get("algorithm"),
    )
    return templates.TemplateResponse(
        "admin_searcher.html",
        {
            "request": request,
            "icon": payload["pfp"],
            "name": payload["name"],
            "id": payload["id"],
        },
    )


@router.get("/infra/")
@Authentication.admin
async def get_infra(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
):
    """
    API endpoint to FORCE-provision Infra credentials (even without membership!!!)
    """
    if member_id == "FAIL":
        return {"username": "", "password": "", "error": "Missing ?member_id"}

    creds = Approve.provision_infra(member_id)
    if creds is None:
        creds = {}

    if not creds:
        return Errors.generate(request, 404, "User Not Found")

    # Get user data
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    user_data = table.get_item(Key={"id": member_id}).get("Item", None)

    # Send DM...
    new_creds_msg = f"""Hello {user_data.get('first_name')},

We are happy to grant you Hack@UCF Private Cloud access!

These credentials can be used to the Hack@UCF Private Cloud. This can be accessed at {options.get('infra', {}).get('horizon')} while on the CyberLab WiFi.

```
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', f"Please visit https://{options.get('http', {}).get('domain')}/profile and under Danger Zone, reset your Infra creds.")}
```

By using the Hack@UCF Infrastructure, you agree to the following EULA located at https://help.hackucf.org/misc/eula

The password for the `Cyberlab` WiFi is currently `{options.get('infra', {}).get('wifi')}`, but this is subject to change (and we'll let you know when that happens).

Happy Hacking,
  - Hack@UCF Bot
            """

    # Send Discord message
    #Discord.send_message(user_data.get("discord_id"), new_creds_msg)
    Email.send_email("Hack@UCF Private Cloud Credentials", new_creds_msg, user_data.get("email"))
    return {"username": creds.get("username"), "password": creds.get("password")}


@router.get("/refresh/")
@Authentication.admin
async def get_refresh(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
):
    """
    API endpoint that re-runs the member verification workflow
    """
    if member_id == "FAIL":
        return {"data": {}, "error": "Missing ?member_id"}

    Approve.approve_member(member_id)

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.get_item(Key={"id": member_id}).get("Item", None)

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    return {"data": data}


@router.get("/get/")
@Authentication.admin
async def admin_get_single(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
):
    """
    API endpoint that gets a specific user's data as JSON
    """
    if member_id == "FAIL":
        return {"data": {}, "error": "Missing ?member_id"}

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.get_item(Key={"id": member_id}).get("Item", None)

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    return {"data": data}


@router.get("/get_by_snowflake/")
@Authentication.admin
async def admin_get_snowflake(
    request: Request,
    token: Optional[str] = Cookie(None),
    discord_id: Optional[str] = "FAIL",
):
    """
    API endpoint that gets a specific user's data as JSON, given a Discord snowflake.
    Designed for trusted federated systems to exchange data.
    """
    if discord_id == "FAIL":
        return {"data": {}, "error": "Missing ?discord_id"}

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.scan(FilterExpression=Attr("discord_id").eq(str(discord_id))).get(
        "Items"
    )

    print(data)

    if not data:
        # Try a legacy-user-ID search (deprecated, but still neccesary)
        data = table.scan(FilterExpression=Attr("discord_id").eq(int(discord_id))).get(
            "Items"
        )
        print(data)

        if not data:
            return Errors.generate(request, 404, "User Not Found")

    data = data[0]

    return {"data": data}


@router.post("/message/")
@Authentication.admin
async def admin_post_discord_message(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
    payload: dict = Body(None),
):
    """
    API endpoint that gets a specific user's data as JSON
    """
    if member_id == "FAIL":
        return {"data": {}, "error": "Missing ?member_id"}

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.get_item(Key={"id": member_id}).get("Item", None)

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    message_text = payload.get("msg")

    res = Discord.send_message(data.get("discord_id"), message_text)

    if res:
        return {"msg": "Message sent."}
    else:
        return {"msg": "An error occured!"}


@router.post("/get/")
@Authentication.admin
async def admin_edit(
    request: Request,
    token: Optional[str] = Cookie(None),
    input_data: Optional[UserModelMutable] = {},
):
    """
    API endpoint that modifies a given user's data
    """
    member_id = input_data.id

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    old_data = table.get_item(Key={"id": member_id}).get("Item", None)

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

    return {"data": union, "msg": "Updated successfully!"}


@router.get("/list")
@Authentication.admin
async def admin_list(request: Request, token: Optional[str] = Cookie(None)):
    """
    API endpoint that dumps all users as JSON.
    """
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.scan().get("Items", None)
    return {"data": data}


@router.get("/csv")
@Authentication.admin
async def admin_list_csv(request: Request, token: Optional[str] = Cookie(None)):
    """
    API endpoint that dumps all users as CSV.
    """
    dynamodb = boto3.resource("dynamodb")
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

    return Response(content=output, headers={"Content-Type": "text/csv"})
