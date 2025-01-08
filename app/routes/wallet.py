# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import json
import logging
import os
import uuid
from typing import Optional

import requests
from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import RedirectResponse
from google.auth import crypt, jwt
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from neo_airpress import PKPass
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models.info import InfoModel
from app.models.user import PublicContact, UserModel, user_to_dict
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.errors import Errors
from app.util.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wallet",
    tags=["API", "MobileWallet"],
    responses=Errors.basic_http(),
)


class GoogleWallet:
    def __init__(self):
        self.auth_dict = json.loads(Settings().google_wallet.auth_json.get_secret_value())
        # Set up authenticated client
        self.auth()

    # [END setup]

    # [START auth]
    def auth(self):
        """Create authenticated HTTP client using a service account file."""
        self.credentials = Credentials.from_service_account_info(
            self.auth_dict,
            scopes=["https://www.googleapis.com/auth/wallet_object.issuer"],
        )

        self.client = build("walletobjects", "v1", credentials=self.credentials)

    # [END auth]
    def create_object(self, issuer_id: str, class_suffix: str, user_data: UserModel) -> str:
        """Create an object.

        Args:
            issuer_id (str): The issuer ID being used for this request.
            class_suffix (str): Developer-defined unique ID for the pass class.
            object_suffix (str): Developer-defined unique ID for the pass object.

        Returns:
            The pass object ID: f"{issuer_id}.{object_suffix}"
        """
        user_id = str(user_data.id)
        # Check if the object exists
        try:
            self.client.loyaltyobject().get(resourceId=f"{issuer_id}.{user_data.id}").execute()
        except HttpError as e:
            if e.status_code != 404:
                # Something else went wrong...
                logger.error("Google Wallet" + str(e.error_details))
                return f"{issuer_id}.{user_id}"
        else:
            logger.info(f"Wallet Object {issuer_id}.{user_id} already exists!")
            return f"{issuer_id}.{user_id}"

        # See link below for more information on required properties
        # https://developers.google.com/wallet/retail/loyalty-cards/rest/v1/loyaltyobject
        new_object = {
            "id": f"{issuer_id}.{user_id}",
            "classId": f"{issuer_id}.{class_suffix}",
            "state": "ACTIVE",
            "heroImage": {
                "sourceUri": {"uri": "https://cdn.hackucf.org/newsletter/banner.png"},
                "contentDescription": {
                    "defaultValue": {
                        "language": "en-US",
                        "value": "Hack@UCF Banner Logo",
                    }
                },
            },
            "hexBackgroundColor": "#231f20",
            "logo": {
                "sourceUri": {"uri": "https://cdn.hackucf.org/PFP.png"},
                "contentDescription": {
                    "defaultValue": {
                        "language": "en-US",
                        "value": "LOGO_IMAGE_DESCRIPTION",
                    }
                },
            },
            "cardTitle": {
                "defaultValue": {
                    "language": "en-US",
                    "value": "Hack@UCF Membership ID",
                }
            },
            "subheader": {"defaultValue": {"language": "en-US", "value": "Name "}},
            "header": {
                "defaultValue": {
                    "language": "en-US",
                    "value": str(user_data.first_name) + " " + str(user_data.surname),
                }
            },
            "linksModuleData": {
                "uris": [
                    {
                        "uri": "https://join.hackucf.org/profile",
                        "description": "Profile Page",
                        "id": "PROFILE",
                    },
                ]
            },
            "barcode": {
                "type": "QR_CODE",
                "value": user_id,
                "alternateText": user_data.discord.username,
            },
            "locations": [
                {
                    "latitude": 28.60183940476708,
                    "longitude": -81.19807063116282,
                },
            ],
            "accountId": user_id,
            "accountName": str(user_data.first_name) + " " + str(user_data.surname),
        }

        # Create the object
        response = self.client.genericobject().insert(body=new_object).execute()

        return f"{issuer_id}.{user_id}"

    def create_jwt_existing_objects(self, issuer_id: str, user_id, class_id) -> str:
        """Generate a signed JWT that references an existing pass object.

        When the user opens the "Add to Google Wallet" URL and saves the pass to
        their wallet, the pass objects defined in the JWT are added to the
        user's Google Wallet app. This allows the user to save multiple pass
        objects in one API call.

        The objects to add must follow the below format:

        {
            'id': 'ISSUER_ID.OBJECT_SUFFIX',
            'classId': 'ISSUER_ID.CLASS_SUFFIX'
        }

        Args:
            issuer_id (str): The issuer ID being used for this request.

        Returns:
            An "Add to Google Wallet" link
        """

        # Multiple pass types can be added at the same time
        # At least one type must be specified in the JWT claims
        # Note: Make sure to replace the placeholder class and object suffixes
        objects_to_add = {
            # Loyalty cards
            "genericObjects": [
                {
                    "id": f"{issuer_id}.{user_id}",
                    "classId": f"{issuer_id}.{class_id}",
                }
            ],
        }

        # Create the JWT claims
        claims = {
            "iss": self.credentials.service_account_email,
            "aud": "google",
            "origins": ["join.hackucf.org"],
            "typ": "savetowallet",
            "payload": objects_to_add,
        }

        # The service account credentials are used to sign the JWT
        signer = crypt.RSASigner.from_service_account_info(self.auth_dict)
        token = jwt.encode(signer, claims).decode("utf-8")

        return f"https://pay.google.com/gp/v/save/{token}"

    # [END jwtExisting]


if Settings().google_wallet.enable:
    google_wallet = GoogleWallet()


def get_img(url):
    """
    Used to get Discord image.
    """
    resp = requests.get(url, stream=True)
    status = resp.status_code
    if status < 400:
        return resp.raw.read()
    else:
        return get_img("https://cdn.hackucf.org/PFP.png")


def apple_wallet(user_data):
    """
    User data -> Apple Wallet blob
    """
    # Create empty pass package
    p = PKPass()

    is_ops = True if user_data.get("ops_email", False) else False

    # Add locally stored assets
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "static",
            "apple_wallet",
            "icon.png",
        ),
        "rb",
    ) as file:
        ico_data = file.read()
        p.add_to_pass_package(("icon.png", ico_data))

    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "static",
            "apple_wallet",
            "icon@2x.png",
        ),
        "rb",
    ) as file:
        ico_data = file.read()
        p.add_to_pass_package(("icon@2x.png", ico_data))

    pass_json = {
        "passTypeIdentifier": "pass.org.hackucf.join",
        "formatVersion": 1,
        "teamIdentifier": "VWTW9R97Q4",
        "organizationName": "Hack@UCF",
        "serialNumber": str(uuid.uuid4()),
        "description": "Hack@UCF Membership ID",
        "locations": [
            {
                "latitude": 28.601366109876327,
                "longitude": -81.19867691612126,
                "relevantText": "You're near the CyberLab!",
            }
        ],
        "foregroundColor": "#D2990B",
        "backgroundColor": "#1C1C1C",
        "labelColor": "#ffffff",
        "logoText": "",
        "barcodes": [
            {
                "format": "PKBarcodeFormatQR",
                "message": str(user_data.get("id", "Unknown_ID")),
                "messageEncoding": "iso-8859-1",
                "altText": user_data.get("discord", {}).get("username", None),
            }
        ],
        "generic": {
            "primaryFields": [
                {
                    "label": "Name",
                    "key": "name",
                    "value": user_data.get("first_name", "") + " " + user_data.get("surname", ""),
                }
            ],
            "secondaryFields": [
                {
                    "label": "Infra Email",
                    "key": "infra",
                    "value": user_data.get("infra_email", "Not Provisioned"),
                }
            ],
            "backFields": [
                {
                    "label": "View Profile",
                    "key": "view-profile",
                    "value": "You can view and edit your profile at https://join.hackucf.org/profile.",
                    "attributedValue": "You can view and edit your profile at <a href='https://join.hackucf.org/profile'>join.hackucf.org</a>.",
                },
                {
                    "label": "Check In",
                    "key": "check-in",
                    "value": "At a meeting? Visit https://hackucf.org/signin to sign in",
                    "attributedValue": "At a meeting? Visit <a href='https://hackucf.org/signin'>hackucf.org/signin</a> to sign in.",
                },
            ],
        },
    }

    # I am duplicating the file reads because it's easier than re-setting file pointers to the start of each file.
    # I think.

    # User profile image
    discord_img = user_data.get("discord", {}).get("avatar", False)
    if discord_img:
        img_data = get_img(discord_img)
        p.add_to_pass_package(("thumbnail.png", img_data))

        img_data = get_img(discord_img)
        p.add_to_pass_package(("thumbnail@2x.png", img_data))

    # Role-based logo.
    if is_ops:
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "static",
                "apple_wallet",
                "logo_ops@2x.png",
            ),
            "rb",
        ) as file:
            ico_data = file.read()
            p.add_to_pass_package(("logo@2x.png", ico_data))

        with open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "static",
                "apple_wallet",
                "logo_ops.png",
            ),
            "rb",
        ) as file:
            ico_data = file.read()
            p.add_to_pass_package(("logo.png", ico_data))
    else:
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "static",
                "apple_wallet",
                "logo_reg@2x.png",
            ),
            "rb",
        ) as file:
            ico_data = file.read()
            p.add_to_pass_package(("logo@2x.png", ico_data))

        with open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "static",
                "apple_wallet",
                "logo_reg.png",
            ),
            "rb",
        ) as file:
            ico_data = file.read()
            p.add_to_pass_package(("logo.png", ico_data))

    pass_data = json.dumps(pass_json).encode("utf8")

    p.add_to_pass_package(("pass.json", pass_data))

    # Add locally stored credentials
    key_path = Settings().apple_wallet.pki_dir / "hackucf.key"
    cert_path = Settings().apple_wallet.pki_dir / "hackucf.pem"
    wwdr_path = Settings().apple_wallet.pki_dir / "wwdr.pem"

    # Check if files exist before opening them
    if not key_path.exists():
        logger.error(f"File not found: {key_path}")
        raise FileNotFoundError(f"File not found: {key_path}")

    if not cert_path.exists():
        logger.error(f"File not found: {cert_path}")
        raise FileNotFoundError(f"File not found: {cert_path}")

    if not wwdr_path.exists():
        logger.error(f"File not found: {cert_path}")
        raise FileNotFoundError(f"File not found: {cert_path}")

    # Open the files
    with key_path.open("rb") as key, cert_path.open("rb") as cert, wwdr_path.open("rb") as wwdr:
        # Add credentials to pass package
        p.key = key.read()
        p.cert = cert.read()
        p.sign(wwdr=wwdr.read())

    # As we've added credentials to pass package earlier we don't need to supply them to `.sign()`
    # This is an alternative to calling .sign() method with credentials as arguments.

    return p


@router.get("/")
async def get_root():
    """
    Get API information.
    """
    return InfoModel(
        name="Onboard for Mobile Wallets",
        description="Apple Wallet support.",
        credits=[
            PublicContact(
                first_name="Jonathan",
                surname="Styles",
                ops_email="jstyles@hackucf.org",
            )
        ],
    )


@router.get("/apple")
@Authentication.member
async def aapl_gen(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session=Depends(get_session),
):
    statement = select(UserModel).where(UserModel.id == uuid.UUID(user_jwt["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    user_data = user_to_dict(session.exec(statement).one_or_none())

    p = apple_wallet(user_data)

    return Response(
        content=bytes(p),
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": 'attachment; filename="hackucf.pkpass"'},
    )


@router.get("/google")
@Authentication.member
async def google_gen(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session=Depends(get_session),
):
    if not Settings().google_wallet.enable:
        return Errors.generate()
    statement = select(UserModel).where(UserModel.id == uuid.UUID(user_jwt["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    issuer_id = Settings().google_wallet.issuer_id
    class_suffix = Settings().google_wallet.class_suffix
    user_data = session.exec(statement).one_or_none()
    object_id = google_wallet.create_object(issuer_id, class_suffix, user_data)
    redir_url = google_wallet.create_jwt_existing_objects(
        issuer_id,
        str(user_data.id),
        class_suffix,
    )

    return RedirectResponse(redir_url)
