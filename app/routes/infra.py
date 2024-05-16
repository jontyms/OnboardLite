import asyncio
import json
import logging
import os
from typing import Optional

import openstack
from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from python_terraform import Terraform
from sqlmodel import Session, select

from app.models.info import InfoModel
from app.models.user import PublicContact, UserModel
from app.util.approve import Approve
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.discord import Discord
from app.util.email import Email
from app.util.errors import Errors
from app.util.limiter import RateLimiter
from app.util.settings import Settings

logger = logging.getLogger(__name__)


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/infra", tags=["Infra"], responses=Errors.basic_http())

tf = Terraform(working_dir="./")

rate_limiter = RateLimiter(
    Settings().redis.host, Settings().redis.port, Settings().redis.db
)

rate_limiter.get_redis()


def get_shitty_database():
    """
    Dump contents of the file that stores infra options.
    I lovingly call this the "shitty database."
    """
    data = {}
    opts_path = "infra_options.json"
    try:
        with open(opts_path, "r") as f:
            data = json.loads(f.read())
    except Exception as e:
        logger.exception(f"Invalid config file at {opts_path}", e)
        data = {"gbmName": None, "imageId": None}

    return data


async def create_resource(project, callback_discord_id=None):
    shitty_database = get_shitty_database()
    proj_name = project.name

    logger.info(f"Creating resources for {proj_name}...")

    tf_vars = {
        "application_credential_id": Settings().infra.application_credential_id,
        "application_credential_secret": Settings().infra.application_credential_secret.get_secret_value(),
        "tenant_name": proj_name,
        "gbmname": shitty_database.get("gbmName"),
        "imageid": shitty_database.get("imageId"),
        "member_username": project.id,
    }
    return_code, stdout, stderr = tf.apply(var=tf_vars, skip_plan=True)
    if return_code != 0:
        logger.exception("Terraform failed!")
        logger.debug(f"\treturn: {return_code}")
        logger.debug(f"\tstderr: {stderr}\n")

    # clean up
    try:
        os.remove("terraform.tfstate")
    except Exception:
        pass

    try:
        os.remove("terraform.tfstate.backup")
    except Exception:
        pass

    if callback_discord_id:
        resource_create_msg = f"""Hello!

Your requested virtual machine has been created! You can now view it at {Settings().infra.horizon}.

Enjoy,
    - Hack@UCF Bot
"""
        Discord.send_message(callback_discord_id, resource_create_msg)

    logger.info("\tDone!")


async def teardown():
    logger.debug("Initializing post-GBM teardown...")
    death_word = "gbm"

    conn = openstack.connect(cloud="hackucf_infra")

    logger.debug("\tServers...")
    for resource in conn.compute.servers(all_projects=True):
        # logger.debug("\t" + resource.name)
        if death_word in resource.name.lower():
            logger.debug(f"\t\tdelete {resource.name}")
            conn.compute.delete_server(resource)

    logger("\tSec Groups...")
    for resource in conn.network.security_groups():
        # logger.debug("\t" + resource.name)
        if death_word in resource.name.lower():
            logger.debug(f"\t\tdelete {resource.name}")
            conn.network.delete_security_group(resource)

    logger.debug("\tRouters...")
    for resource in conn.network.routers():
        # logger.debug("\t" + resource.name)
        if death_word in resource.name.lower():
            logger.debug(f"\t\tdelete {resource.name}")
            try:
                conn.network.delete_router(resource)
            except openstack.exceptions.ConflictException as e:
                port_id_list = str(e).split(": ")[-1].split(",")
                for port_id in port_id_list:
                    logger.debug(f"\t\t\tdelete/abandon port: {port_id}")
                    conn.network.remove_interface_from_router(resource, port_id=port_id)
                    conn.network.delete_port(port_id)
                try:
                    conn.network.delete_router(resource)
                except:  # noqa
                    logger.debug("\t\t\t\tFailed and gave up.")

    logger.debug("\tNetworks...")
    for resource in conn.network.networks():
        # logger.debug("\t" + resource.name)
        if death_word in resource.name.lower():
            logger.debug(f"\t\tdelete {resource.name}")
            try:
                conn.network.delete_network(resource)
            except openstack.exceptions.ConflictException as e:
                port_id_list = str(e).split(": ")[-1][:-1].split(",")
                for port_id in port_id_list:
                    logger.debug(f"\t\t\tdelete port: {port_id}")
                    try:
                        conn.network.delete_port(port_id)
                    except:  # noqa
                        pass
                try:
                    conn.network.delete_network(resource)
                except:  # noqa
                    logger.debug("\t\t\t\tFailed and gave up.")
    logger.debug("\tDone!")


"""
Get API information.
"""


@router.get("/")
async def get_root():
    return InfoModel(
        name="Onboard Infra",
        description="Infrastructure Management via Onboard.",
        credits=[
            PublicContact(
                first_name="Jeffrey",
                surname="DiVincent",
                ops_email="jdivincent@hackucf.org",
            ),
            PublicContact(
                first_name="Caleb",
                surname="Sjostedt",
                ops_email="csjostedt@hackucf.org",
            ),
        ],
    )


"""
API endpoint to self-service create a GBM environment.
"""


@router.get("/provision/")
@Authentication.member
async def get_provision(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
):
    conn = openstack.connect(cloud="hackucf_infra")

    # Get single user
    user = conn.identity.find_user(user_jwt.get("infra_email"))

    # Get project
    project = conn.identity.get_project(user.default_project_id)

    # Provision everything
    asyncio.create_task(
        create_resource(project, user_jwt.get("discord_id"))
    )  # runs teardown async
    return {"msg": "Queued."}


"""
API endpoint to trigger tear-down of GBM-provisioned stuff.
"""


@router.get("/teardown/")
@Authentication.admin
async def get_teardown(request: Request, token: Optional[str] = Cookie(None)):
    asyncio.create_task(teardown())  # runs teardown async
    return {"msg": "Queued."}


"""
API endpoint to SET the one-click deploy Settings().
"""


@router.get("/options/get")
@Authentication.member
async def get_options(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
):
    return get_shitty_database()


"""
API endpoint to SET the one-click deploy Settings().
"""


@router.get("/options/set")
@Authentication.admin
async def set_options(
    request: Request,
    token: Optional[str] = Cookie(None),
    gbmName: Optional[str] = None,
    imageId: Optional[str] = None,
):
    shitty_database = {"gbmName": gbmName, "imageId": imageId}

    with open("infra_options.json", "w") as f:
        f.write(json.dumps(shitty_database))

    return shitty_database


"""
API endpoint to self-service reset Infra credentials (membership-validating)
"""


@router.get("/reset/")
@Authentication.member
@rate_limiter.rate_limit(1, 604800, "reset")
async def get_infra(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session: Session = Depends(get_session),
):
    member_id = user_jwt.get("id")

    if not (user_jwt.get("is_full_member") or user_jwt.get("infra_email")):
        return Errors.generate(
            request, 403, "This API endpoint is restricted to Dues-Paying Members."
        )

    # This also reprovisions Infra access if an account already exists.
    # This is useful for cleaning up things + nuking in case of an error.
    creds = Approve.provision_infra(member_id)

    if not creds:
        creds = {}

    # Get user data
    user_data = session.exec(
        select(UserModel).where(UserModel.id == user_jwt.get("id"))
    ).one_or_none()

    # Send DM...
    new_creds_msg = f"""Hello {user_data.get('first_name')},

You have requested to reset your Hack@UCF Infrastructure credentials. This change comes with new credentials.

A reminder that you can use these credentials at {Settings().infra.horizon} while on the CyberLab WiFi.

```
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', f"Please visit https://{Settings().http.domain}/profile and under Danger Zone, reset your Infra creds.")}
```

The password for the `Cyberlab` WiFi is currently `{Settings().infra.wifi}`, but this is subject to change (and we'll let you know when that happens).

By using the Hack@UCF Infrastructure, you agree to the following EULA located at https://help.hackucf.org/misc/eula

Happy Hacking,

 - Hack@UCF Bot
            """

    # Send Discord message
    # Discord.send_message(user_data.get("discord_id"), new_creds_msg)
    # Send Email
    Email.send_email("Reset Infra Credentials", new_creds_msg, user_data.get("email"))

    return {"username": creds.get("username"), "password": creds.get("password")}


"""
An endpoint to Download OpenVPN profile
"""


@router.get("/openvpn")
@Authentication.member
@rate_limiter.rate_limit(5, 60, "ovpn")
async def download_file(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
):
    # Replace 'path/to/your/file.txt' with the actual path to your file
    file_path = "../HackUCF.ovpn"
    return FileResponse(
        file_path, filename="HackUCF.ovpn", media_type="application/octet-stream"
    )
