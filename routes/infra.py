import boto3, json, requests
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
from models.user import PublicContact

from util.authentication import Authentication
from util.errors import Errors
from util.options import Options
from util.approve import Approve
from util.discord import Discord
from util.kennelish import Kennelish, Transformer

from python_terraform import *
import openstack
import asyncio

options = Options.fetch()

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/infra", tags=["Infra"], responses=Errors.basic_http())

tf = Terraform(working_dir="./")


shitty_database = {"gbmName": None, "imageId": None}


async def create_resource(project):
    global shitty_database
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
    except Exception as e:
        pass

    try:
        os.remove("terraform.tfstate.backup")
    except Exception as e:
        pass

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
                except:
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
                    except:
                        pass
                try:
                    conn.network.delete_network(resource)
                except:
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
    asyncio.create_task(create_resource(project))  # runs teardown async
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
    gbmName: Optional[str] = None,
    imageId: Optional[str] = None,
):
    global shitty_database

    return shitty_database


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
    global shitty_database
    shitty_database = {"gbmName": gbmName, "imageId": imageId}

    return shitty_database


"""
API endpoint to self-service reset Infra credentials (membership-validating)
"""


@router.get("/reset/")
@Authentication.member
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

```yaml
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', f"Please visit https://{options.get('http', {}).get('domain')}/profile and under Danger Zone, reset your Infra creds.")}
```

The password for the `Cyberlab` WiFi is currently `{options.get('infra', {}).get('wifi')}`, but this is subject to change (and we'll let you know when that happens).

Happy Hacking,
  - Hack@UCF Bot
            """

    # Send Discord message
    Discord.send_message(discord_id, new_creds_msg)

    return {"username": creds.get("username"), "password": creds.get("password")}


"""
API endpoint that re-runs the member verification workflow
"""


@router.get("/refresh/")
@Authentication.admin
async def get_refresh(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
):
    if member_id == "FAIL":
        return {"data": {}, "error": "Missing ?member_id"}

    Approve.approve_member(member_id)

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.get_item(Key={"id": member_id}).get("Item", None)

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    return {"data": data}


"""
API endpoint that gets a specific user's data as JSON
"""


@router.get("/get/")
@Authentication.admin
async def admin_get_single(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
):
    if member_id == "FAIL":
        return {"data": {}, "error": "Missing ?member_id"}

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.get_item(Key={"id": member_id}).get("Item", None)

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    return {"data": data}


"""
API endpoint that modifies a given user's data
"""


@router.post("/get/")
@Authentication.admin
async def admin_edit(
    request: Request,
    token: Optional[str] = Cookie(None),
    input_data: Optional[UserModelMutable] = {},
):
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


"""
API endpoint that dumps all users as JSON.
"""


@router.get("/list")
@Authentication.admin
async def admin_list(request: Request, token: Optional[str] = Cookie(None)):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.scan().get("Items", None)
    return {"data": data}


"""
API endpoint that dumps all users as CSV.
"""


@router.get("/csv")
@Authentication.admin
async def admin_list(request: Request, token: Optional[str] = Cookie(None)):
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
