import json
import logging
import time
import uuid
from typing import Optional
from urllib.parse import urlparse

import requests
# FastAPI
from fastapi import Cookie, Depends, FastAPI, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import jwt
from requests_oauthlib import OAuth2Session
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

# Import data types
from app.models.user import (DiscordModel, EthicsFormModel, UserModel,
                             user_to_dict)
# Import routes
from app.routes import admin, api, infra, stripe, wallet
from app.util.approve import Approve
# Import middleware
from app.util.authentication import Authentication
from app.util.database import get_session, init_db
# Import error handling
from app.util.errors import Errors
from app.util.forms import Forms
# Import the page rendering library
from app.util.kennelish import Kennelish
# Import options
from app.util.settings import Settings

if Settings().telemetry.enable:
    import sentry_sdk
### TODO: TEMP
# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"
###


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Initiate FastAPI.
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

if Settings().telemetry.enable:
    sentry_sdk.init(
        dsn=Settings().telemetry.url,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )

# Import endpoints from ./routes
app.include_router(api.router)
app.include_router(stripe.router)
app.include_router(admin.router)
app.include_router(wallet.router)
app.include_router(infra.router)

# Create the OpenStack SDK config.
with open("clouds.yaml", "w", encoding="utf-8") as f:
    f.write(
        f"""clouds:
  hackucf_infra:
    auth:
      auth_url: {Settings().infra.horizon}:5000
      application_credential_id: {Settings().infra.application_credential_id}
      application_credential_secret: {Settings().infra.application_credential_secret.get_secret_value()}
    region_name: "hack-ucf-0"
    interface: "public"
    identity_api_version: 3
    auth_type: "v3applicationcredential"
"""
    )


"""
Render the Onboard home page.
"""


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
async def index(request: Request, token: Optional[str] = Cookie(None)):
    is_full_member = False
    is_admin = False
    user_id = None
    infra_email = None

    if token is not None:
        try:
            user_jwt = jwt.decode(
                token,
                Settings().jwt.secret.get_secret_value(),
                algorithms=Settings().jwt.algorithm,
            )
            is_full_member: bool = user_jwt.get("is_full_member", False)
            is_admin: bool = user_jwt.get("sudo", False)
            user_id: bool = user_jwt.get("id", None)
            infra_email: bool = user_jwt.get("infra_email", None)
        except Exception as e:
            logger.exception(e)
            pass

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "is_full_member": is_full_member,
            "is_admin": is_admin,
            "user_id": user_id,
            "infra_email": infra_email,
        },
    )


"""
Redirects to Discord for OAuth.
This is what is linked to by Onboard.
"""


@app.get("/discord/new/")
async def oauth_transformer(redir: str = "/join/2"):
    # Open redirect check
    hostname = urlparse(redir).netloc
    if hostname != "" and hostname != Settings().http.domain:
        redir = "/join/2"

    oauth = OAuth2Session(
        Settings().discord.client_id,
        redirect_uri=Settings().discord.redirect_base + "_redir",
        scope=Settings().discord.scope,
    )
    authorization_url, state = oauth.authorization_url(
        "https://discord.com/api/oauth2/authorize"
    )

    rr = RedirectResponse(authorization_url, status_code=302)

    rr.set_cookie(key="redir_endpoint", value=redir)

    return rr


"""
Logs the user into Onboard via Discord OAuth and updates their Discord metadata.
This is what Discord will redirect to.
"""


@app.get("/api/oauth/")
async def oauth_transformer_new(
    request: Request,
    response: Response,
    code: str = None,
    redir: str = "/join/2",
    redir_endpoint: Optional[str] = Cookie(None),
    session: Session = Depends(get_session),
):
    # Open redirect check
    if redir == "_redir":
        redir = redir_endpoint

    hostname = urlparse(redir).netloc

    if hostname != "" and hostname != Settings().http.domain:
        redir = "/join/2"

    if code is None:
        return Errors.generate(
            request,
            401,
            "You declined Discord log-in",
            essay="We need your Discord account to log into myHack@UCF.",
        )

    # Get data from Discord
    oauth = OAuth2Session(
        Settings().discord.client_id,
        redirect_uri=Settings().discord.redirect_base + "_redir",
        scope=Settings().discord.scope,
    )

    token = oauth.fetch_token(
        "https://discord.com/api/oauth2/token",
        client_id=Settings().discord.client_id,
        client_secret=Settings().discord.secret.get_secret_value(),
        # authorization_response=code
        code=code,
    )

    r = oauth.get("https://discord.com/api/users/@me")
    discordData = r.json()

    # Generate a new user ID or reuse an existing one.
    statement = select(UserModel).where(UserModel.discord_id == discordData["id"])
    user = session.exec(statement).one_or_none()
    # TODO: Discuss removing
    # BACKPORT: I didn't realize that Snowflakes were strings because of an integer overflow bug.
    # So this will do a query for the "mistaken" value and then fix its data.
    # if not query_for_id:
    #    logger.info("Beginning Discord ID attribute migration...")
    #    query_for_id = table.scan(
    #        FilterExpression=Attr("discord_id").eq(int(discordData["id"]))
    #    )
    #    query_for_id = query_for_id.get("Items")
    #
    #    if query_for_id:
    #        table.update_item(
    #            Key={"id": query_for_id[0].get("id")},
    #            UpdateExpression="SET discord_id = :discord_id",
    #            ExpressionAttributeValues={":discord_id": str(discordData["id"])},
    #        )

    is_new = False

    if not user:
        is_full_member = False
        member_id = str(uuid.uuid4())
        do_sudo = False
        is_new = True
        infra_email = ""

        # Make user join the Hack@UCF Discord, if it's their first rodeo.
        discord_id = str(discordData["id"])
        headers = {
            "Authorization": f"Bot {Settings().discord.bot_token.get_secret_value()}",
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": "Hack@UCF OnboardLite Bot",
        }
        put_join_guild = {"access_token": token["access_token"]}
        requests.put(
            f"https://discordapp.com/api/guilds/{Settings().discord.guild_id}/members/{discord_id}",
            headers=headers,
            data=json.dumps(put_join_guild),
        )
        user = UserModel(discord_id=discord_id, id=member_id, infra_email=infra_email)
        discord_data = {
            "email": discordData.get("email"),
            "mfa": discordData.get("mfa_enabled"),
            "avatar": f"https://cdn.discordapp.com/avatars/{discordData['id']}/{discordData['avatar']}.png?size=512",
            "banner": f"https://cdn.discordapp.com/banners/{discordData['id']}/{discordData['banner']}.png?size=1536",
            "color": discordData.get("accent_color"),
            "nitro": discordData.get("premium_type"),
            "locale": discordData.get("locale"),
            "username": discordData.get("username"),
            "user_id": user.id,
        }
        discord_model = DiscordModel(**discord_data)
        ethics_form = EthicsFormModel()
        user.discord = discord_model
        user.ethics_form = ethics_form
        session.add(user)
        session.commit()
        session.refresh(user)

    # Create JWT. This should be the only way to issue JWTs.
    bearer = Authentication.create_jwt(user)
    rr = RedirectResponse(redir, status_code=status.HTTP_302_FOUND)
    rr.set_cookie(key="token", value=bearer)

    # Clear redirect cookie.
    rr.delete_cookie("redir_endpoint")

    return rr


"""
Renders the landing page for the sign-up flow.
"""


@app.get("/join/")
async def join(request: Request, token: Optional[str] = Cookie(None)):
    if token is None:
        return templates.TemplateResponse("signup.html", {"request": request})
    else:
        return RedirectResponse("/join/2/", status_code=status.HTTP_302_FOUND)


"""
Renders a basic "my membership" page
"""


@app.get("/profile/")
@Authentication.member
async def profile(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session: Session = Depends(get_session),
):
    statement = (
        select(UserModel)
        .where(UserModel.id == user_jwt["id"])
        .options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    )
    user_data = user_to_dict(session.exec(statement).one_or_none())

    # Re-run approval workflow.
    Approve.approve_member(user_jwt.get("id"))

    return templates.TemplateResponse(
        "profile.html", {"request": request, "user_data": user_data}
    )


"""
Renders a Kennelish form page, complete with stylings and UI controls.
"""


@app.get("/join/{num}/")
@Authentication.member
async def forms(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    num: str = 1,
    session: Session = Depends(get_session),
):
    if num == "1":
        return RedirectResponse("/join/", status_code=status.HTTP_302_FOUND)
    try:
        data = Forms.get_form_body(num)
    except Exception:
        return Errors.generate(
            request,
            404,
            "Form not found",
            essay="This form does not exist.",
        )

    # Get data from SqlModel

    statement = (
        select(UserModel)
        .where(UserModel.id == user_jwt.get("id"))
        .options(selectinload(UserModel.discord))
    )
    user_data = session.exec(statement).one_or_none()
    # Have Kennelish parse the data.
    user_data = user_to_dict(user_data)
    logger.info("Parsing form data" + str(user_data))
    body = Kennelish.parse(data, user_data)

    # return num
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "icon": user_jwt["pfp"],
            "name": user_jwt["name"],
            "id": user_jwt["id"],
            "body": body,
        },
    )


@app.get("/final")
async def final(request: Request):
    return templates.TemplateResponse("done.html", {"request": request})


@app.get("/logout")
async def logout(request: Request):
    rr = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    rr.delete_cookie(key="token")
    return rr


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("./app/static/favicon.ico")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
