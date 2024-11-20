# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import uuid
from typing import Optional
import csv
from io import StringIO

from fastapi import APIRouter, Body, Cookie, Depends, Request, Response
from fastapi.templating import Jinja2Templates
from jose import jwt
from sqlalchemy.orm import selectinload
from sqlalchemy.types import UUID
from sqlmodel import Session, select

from app.models.user import (
    UserModel,
    UserModelMutable,
    user_to_dict,
    user_update_instance,
)
from app.util.approve import Approve
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.discord import Discord
from app.util.email import Email
from app.util.errors import Errors
from app.util.settings import Settings

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/admin", tags=["Admin"], responses=Errors.basic_http())


@router.get("/")
@Authentication.admin
async def admin(request: Request, token: Optional[str] = Cookie(None)):
    """
    Renders the Admin home page.
    """
    payload = jwt.decode(
        token,
        Settings().jwt.secret.get_secret_value(),
        algorithms=Settings().jwt.algorithm,
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
    member_id: Optional[uuid.UUID] = None,
    session: Session = Depends(get_session),
):
    """
    API endpoint to FORCE-provision Infra credentials (even without membership!!!)
    """

    if member_id == None:
        return {"username": "", "password": "", "error": "Missing ?member_id"}

    user_data = session.exec(select(UserModel).where(UserModel.id == member_id)).one_or_none()

    creds = Approve.provision_infra(member_id, user_data)
    if creds is None:
        creds = {}

    if not creds:
        return Errors.generate(request, 404, "User Not Found")

    # Get user data

    # Send DM...
    new_creds_msg = f"""Hello {user_data.first_name},

We are happy to grant you Hack@UCF Private Cloud access!

These credentials can be used to the Hack@UCF Private Cloud. This can be accessed at {Settings().infra.horizon} while on the CyberLab WiFi.

```
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', f"Please visit https://{Settings().http.domain}/profile and under Danger Zone, reset your Infra creds.")}
```

By using the Hack@UCF Infrastructure, you agree to the following Acceptable Use Policy located at https://help.hackucf.org/misc/aup

The password for the `Cyberlab` WiFi is currently `{Settings().infra.wifi}`, but this is subject to change (and we'll let you know when that happens).

Happy Hacking,
  - Hack@UCF Bot
            """

    # Send Discord message
    # Discord.send_message(user_data.get("discord_id"), new_creds_msg)
    Email.send_email("Hack@UCF Private Cloud Credentials", new_creds_msg, user_data.email)
    return {"username": creds.get("username"), "password": creds.get("password")}


@router.get("/refresh/")
@Authentication.admin
async def get_refresh(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[uuid.UUID] = None,
    session: Session = Depends(get_session),
):
    """
    API endpoint that re-runs the member verification workflow
    """
    if member_id == None:
        return {"data": {}, "error": "Missing ?member_id"}

    Approve.approve_member(member_id)

    user_data = session.exec(select(UserModel).where(UserModel.id == member_id)).one_or_none()

    if not user_data:
        return Errors.generate(request, 404, "User Not Found")

    return {"data": user_data}


@router.get("/get/")
@Authentication.admin
async def admin_get_single(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[uuid.UUID] = None,
    session: Session = Depends(get_session),
):
    """
    API endpoint that gets a specific user's data as JSON
    """
    if member_id == None:
        return {"data": {}, "error": "Missing ?member_id"}

    statement = select(UserModel).where(UserModel.id == member_id).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    user_data = user_to_dict(session.exec(statement).one_or_none())

    if not user_data:
        return Errors.generate(request, 404, "User Not Found")

    return {"data": user_data}


@router.get("/get_by_snowflake/")
@Authentication.admin
async def admin_get_snowflake(
    request: Request,
    token: Optional[str] = Cookie(None),
    discord_id: Optional[str] = "FAIL",
    session: Session = Depends(get_session),
):
    """
    API endpoint that gets a specific user's data as JSON, given a Discord snowflake.
    Designed for trusted federated systems to exchange data.
    """
    if discord_id == "FAIL":
        return {"data": {}, "error": "Missing ?discord_id"}

    statement = select(UserModel).where(UserModel.discord_id == discord_id).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    data = user_to_dict(session.exec(statement).one_or_none())
    # if not data:
    #    # Try a legacy-user-ID search (deprecated, but still neccesary)
    #    data = table.scan(FilterExpression=Attr("discord_id").eq(int(discord_id))).get(
    #        "Items"
    #    )
    #
    if not data:
        return Errors.generate(request, 404, "User Not Found")

    # data = data[0]

    return {"data": data}


@router.post("/message/")
@Authentication.admin
async def admin_post_discord_message(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[uuid.UUID] = None,
    user_jwt: dict = Body(None),
    session: Session = Depends(get_session),
):
    """
    API endpoint that gets a specific user's data as JSON
    """
    if member_id == "FAIL":
        return {"data": {}, "error": "Missing ?member_id"}

    data = session.exec(select(UserModel).where(UserModel.id == member_id)).one_or_none()

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    message_text = user_jwt.get("msg")

    res = Discord.send_message(data.discord_id, message_text)

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
    session: Session = Depends(get_session),
):
    """
    API endpoint that modifies a given user's data
    """
    member_id = input_data.id

    statement = select(UserModel).where(UserModel.id == member_id).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    member_data = session.exec(statement).one_or_none()

    if not member_data:
        return Errors.generate(request, 404, "User Not Found")
    input_data = user_to_dict(input_data)
    user_update_instance(member_data, input_data)

    session.add(member_data)
    session.commit()
    return {"data": user_to_dict(member_data), "msg": "Updated successfully!"}


@router.get("/list")
@Authentication.admin
async def admin_list(
    request: Request,
    token: Optional[str] = Cookie(None),
    session: Session = Depends(get_session),
):
    """
    API endpoint that dumps all users as JSON.
    """
    statement = select(UserModel).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    users = session.exec(statement)
    data = []
    for user in users:
        user = user_to_dict(user)
        data.append(user)

    return {"data": data}

@router.get("/csv")
@Authentication.admin
async def admin_list_csv(
    request: Request,
    token: Optional[str] = Cookie(None),
    session: Session = Depends(get_session),
):
    """
    API endpoint that dumps all users as CSV.
    """
    statement = select(UserModel).options(
        selectinload(UserModel.discord), selectinload(UserModel.ethics_form)
    )
    data = session.exec(statement)

    # Initialize a StringIO object to write CSV data into memory
    output = StringIO()
    csv_writer = csv.writer(output)

    # Write the header row
    headers = [
        "Membership ID",
        "First Name",
        "Last Name",
        "NID",
        "Email",
        "Is Returning",
        "Gender",
        "Major",
        "Class Standing",
        "Shirt Size",
        "Discord Username",
        "Experience",
        "Cyber Interests",
        "Event Interest",
        "Is C3 Interest",
        "Comments",
        "Ethics Form Timestamp",
        "Minecraft",
    ]
    csv_writer.writerow(headers)

    # Write user data rows
    for user in data:
        user_dict = user_to_dict(user)
        row = [
            user_dict.get("id"),
            user_dict.get("first_name"),
            user_dict.get("surname"),
            user_dict.get("nid"),
            user_dict.get("email"),
            user_dict.get("is_returning"),
            user_dict.get("gender"),
            user_dict.get("major"),
            user_dict.get("class_standing"),
            user_dict.get("shirt_size"),
            user_dict.get("discord", {}).get("username"),
            user_dict.get("experience"),
            user_dict.get("curiosity"),
            user_dict.get("attending"),
            user_dict.get("c3_interest"),
            user_dict.get("comments"),
            user_dict.get("ethics_form", {}).get("signtime"),
            user_dict.get("minecraft"),
        ]
        csv_writer.writerow(row)

    # Retrieve CSV content from StringIO and return as response
    csv_content = output.getvalue()
    output.close()

    return Response(content=csv_content, headers={"Content-Type": "text/csv"})
