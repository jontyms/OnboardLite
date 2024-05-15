from typing import Optional

from util.database import get_session
from sqlmodel import select, Session
from sqlalchemy.orm import selectinload
from models.user import UserModel, to_dict

from fastapi import APIRouter, Body, Cookie, Request, Response, Depends
from fastapi.templating import Jinja2Templates
from jose import jwt

from models.user import UserModelMutable
from util.approve import Approve
from util.authentication import Authentication
from util.discord import Discord
from util.email import Email
from util.errors import Errors
from util.settings import Settings

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
    user_jwt: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
    session: Session = Depends(get_session)
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
    user_data = session.exec(select(UserModel).where(UserModel.id == member_id)).one_or_none()

    # Send DM...
    new_creds_msg = f"""Hello {user_data.first_name},

We are happy to grant you Hack@UCF Private Cloud access!

These credentials can be used to the Hack@UCF Private Cloud. This can be accessed at {Settings().infra.horizon} while on the CyberLab WiFi.

```
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', f"Please visit https://{Settings().http.domain}/profile and under Danger Zone, reset your Infra creds.")}
```

By using the Hack@UCF Infrastructure, you agree to the following EULA located at https://help.hackucf.org/misc/eula

The password for the `Cyberlab` WiFi is currently `{Settings().infra.wifi}`, but this is subject to change (and we'll let you know when that happens).

Happy Hacking,
  - Hack@UCF Bot
            """

    # Send Discord message
    #Discord.send_message(user_data.get("discord_id"), new_creds_msg)
    Email.send_email("Hack@UCF Private Cloud Credentials", new_creds_msg, user_data.email)
    return {"username": creds.get("username"), "password": creds.get("password")}


@router.get("/refresh/")
@Authentication.admin
async def get_refresh(
    request: Request,
    user_jwt: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
    session: Session = Depends(get_session)
):
    """
    API endpoint that re-runs the member verification workflow
    """
    if member_id == "FAIL":
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
    user_jwt: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
    session: Session = Depends(get_session)
):
    """
    API endpoint that gets a specific user's data as JSON
    """
    if member_id == "FAIL":
        return {"data": {}, "error": "Missing ?member_id"}

    statement = (
        select(UserModel)
        .where(UserModel.id == user_jwt["id"])
        .options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        )
    user_data = to_dict(session.exec(statement).one_or_none())

    if not user_data:
        return Errors.generate(request, 404, "User Not Found")

    return {"data": user_data}


@router.get("/get_by_snowflake/")
@Authentication.admin
async def admin_get_snowflake(
    request: Request,
    token: Optional[str] = Cookie(None),
    discord_id: Optional[str] = "FAIL",
    session: Session = Depends(get_session)
):
    """
    API endpoint that gets a specific user's data as JSON, given a Discord snowflake.
    Designed for trusted federated systems to exchange data.
    """
    if discord_id == "FAIL":
        return {"data": {}, "error": "Missing ?discord_id"}

    statement = (
        select(UserModel)
        .where(UserModel.discord_id == discord_id)
        .options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        )
    data = to_dict(session.exec(statement).one_or_none())
    #if not data:
    #    # Try a legacy-user-ID search (deprecated, but still neccesary)
    #    data = table.scan(FilterExpression=Attr("discord_id").eq(int(discord_id))).get(
    #        "Items"
    #    )
    #
    #    if not data:
    #        return Errors.generate(request, 404, "User Not Found")

    #data = data[0]

    return {"data": data}


@router.post("/message/")
@Authentication.admin
async def admin_post_discord_message(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
    user_jwt: dict = Body(None),
    session: Session = Depends(get_session)
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

    statement = (
        select(UserModel)
        .where(UserModel.id == member_id)
        .options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        )
    old_data = to_dict(session.exec(statement).one_or_none())

    if not old_data:
        return Errors.generate(request, 404, "User Not Found")
    input_data = input_data.model_dump(exclude_unset=True)
    for key, value in input_data:
        if value is not None:
            setattr(old_data, key, value)

    new_data=UserModel(**old_data)
    session.add(new_data)
    session.commit()
    return {"data": new_data, "msg": "Updated successfully!"}
    


@router.get("/list")
@Authentication.admin
async def admin_list(request: Request, token: Optional[str] = Cookie(None), session: Session = Depends(get_session)):
    """
    API endpoint that dumps all users as JSON.
    """
    statement = (
        select(UserModel)
        .options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        )
    data = to_dict(session.exec(statement))
    return {"data": data}


@router.get("/csv")
@Authentication.admin
async def admin_list_csv(request: Request, token: Optional[str] = Cookie(None), session: Session = Depends(get_session)):
    """
    API endpoint that dumps all users as CSV.
    """
    statement = (
        select(UserModel)
        .options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        )
    data = to_dict(session.exec(statement))

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
