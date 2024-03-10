import asyncio
import json
import os
from typing import Optional

import boto3
import openstack
from fastapi import APIRouter, Cookie, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from python_terraform import Terraform

from models.info import InfoModel
from models.user import PublicContact
from util.approve import Approve
from util.authentication import Authentication
from util.discord import Discord
from util.email import Email
from util.errors import Errors
from util.limiter import RateLimiter
from util.options import Options

options = Options.fetch()

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/infra", tags=["Infra"], responses=Errors.basic_http())

tf = Terraform(working_dir="./")

rate_limiter = RateLimiter(
    options.get("redis").get("host"),
    options.get("redis").get("port"),
    options.get("redis").get("db"),
)

rate_limiter.get_redis()


def get_shitty_database():
    """
    Dump contents of the file that stores infra options.
    I lovingly call this the "shitty database."
    """
    data = {}
    try:
        with open("infra_options.json", "r") as f:
            data = json.loads(f.read())
    except Exception as e:
        print(e)
        data = {"gbmName": None, "imageId": None}

    return data


async def create_resource(project, callback_discord_id=None):
    shitty_database = get_shitty_database()
    proj_name = project.name

    print(f"Creating resources for {proj_name}...")

    tf_vars = {
        "username": options.get("infra", {}).get("ad", {}).get("username"),
        "password": options.get("infra", {}).get("ad", {}).get("password"),
        "tenant_name": proj_name,
        "gbmname": shitty_database.get("gbmName"),
        "imageid": shitty_database.get("imageId"),
        "member_username": project.id,
    }
    return_code, stdout, stderr = tf.apply(var=tf_vars, skip_plan=True)
    if return_code != 0:
        print("Terraform failed!")
        print(f"\treturn: {return_code}")
        print(f"\tstderr: {stderr}\n")

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

Your requested virtual machine has been created! You can now view it at {options.get('infra', {}).get('horizon')}.

Enjoy,
    - Hack@UCF Bot
"""
        Discord.send_message(callback_discord_id, resource_create_msg)

    print("\tDone!")


async def teardown():
    print("Initializing post-GBM teardown...")
    death_word = "gbm"

    conn = openstack.connect(cloud="hackucf_infra")

    print("\tServers...")
    for resource in conn.compute.servers(all_projects=True):
        # print("\t" + resource.name)
        if death_word in resource.name.lower():
            print(f"\t\tdelete {resource.name}")
            conn.compute.delete_server(resource)

    print("\tSec Groups...")
    for resource in conn.network.security_groups():
        # print("\t" + resource.name)
        if death_word in resource.name.lower():
            print(f"\t\tdelete {resource.name}")
            conn.network.delete_security_group(resource)

    print("\tRouters...")
    for resource in conn.network.routers():
        # print("\t" + resource.name)
        if death_word in resource.name.lower():
            print(f"\t\tdelete {resource.name}")
            try:
                conn.network.delete_router(resource)
            except openstack.exceptions.ConflictException as e:
                port_id_list = str(e).split(": ")[-1].split(",")
                for port_id in port_id_list:
                    print(f"\t\t\tdelete/abandon port: {port_id}")
                    conn.network.remove_interface_from_router(resource, port_id=port_id)
                    conn.network.delete_port(port_id)
                try:
                    conn.network.delete_router(resource)
                except: # noqa
                    print("\t\t\t\tFailed and gave up.")

    print("\tNetworks...")
    for resource in conn.network.networks():
        # print("\t" + resource.name)
        if death_word in resource.name.lower():
            print(f"\t\tdelete {resource.name}")
            try:
                conn.network.delete_network(resource)
            except openstack.exceptions.ConflictException as e:
                port_id_list = str(e).split(": ")[-1][:-1].split(",")
                for port_id in port_id_list:
                    print(f"\t\t\tdelete port: {port_id}")
                    try:
                        conn.network.delete_port(port_id)
                    except: # noqa
                        pass
                try:
                    conn.network.delete_network(resource)
                except: #noqa
                    print("\t\t\t\tFailed and gave up.")
    print("\tDone!")


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
    payload: Optional[object] = {},
):
    conn = openstack.connect(cloud="hackucf_infra")

    # Get single user
    user = conn.identity.find_user(payload.get("infra_email"))

    # Get project
    project = conn.identity.get_project(user.default_project_id)

    # Provision everything
    asyncio.create_task(
        create_resource(project, payload.get("discord_id"))
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
API endpoint to SET the one-click deploy settings.
"""


@router.get("/options/get")
@Authentication.member
async def get_options(
    request: Request,
    token: Optional[str] = Cookie(None),
    payload: Optional[object] = {},
):
    return get_shitty_database()


"""
API endpoint to SET the one-click deploy settings.
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
    payload: Optional[object] = {},
):
    member_id = payload.get("id")

    if not (payload.get("is_full_member") or payload.get("infra_email")):
        return Errors.generate(
            request, 403, "This API endpoint is restricted to Dues-Paying Members."
        )

    # This also reprovisions Infra access if an account already exists.
    # This is useful for cleaning up things + nuking in case of an error.
    creds = Approve.provision_infra(member_id)

    if not creds:
        creds = {}

    # Get user data
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    user_data = table.get_item(Key={"id": member_id}).get("Item", None)

    # Send DM...
    new_creds_msg = f"""Hello {user_data.get('first_name')},

You have requested to reset your Hack@UCF Infrastructure credentials. This change comes with new credentials.

A reminder that you can use these credentials at {options.get('infra', {}).get('horizon')} while on the CyberLab WiFi.

```
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', f"Please visit https://{options.get('http', {}).get('domain')}/profile and under Danger Zone, reset your Infra creds.")}
```

The password for the `Cyberlab` WiFi is currently `{options.get('infra', {}).get('wifi')}`, but this is subject to change (and we'll let you know when that happens).

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
    payload: Optional[object] = {},
):
    # Replace 'path/to/your/file.txt' with the actual path to your file
    file_path = "./HackUCF.ovpn"
    return FileResponse(
        file_path, filename="HackUCF.ovpn", media_type="application/octet-stream"
    )
