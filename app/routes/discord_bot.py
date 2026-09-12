# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
"""
Discord slash commands, served as an Interactions endpoint.

Discord POSTs each interaction here and expects an answer in the same
response, so there is no gateway connection or bot process. Set the
"Interactions Endpoint URL" in the developer portal to /discord/interactions
and register the commands with `app/entry.py register-discord-commands`.
"""

import json
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import select
from urllib3 import encode_multipart_formdata

from app.models.user import UserModel
from app.util.database import get_session
from app.util.qr import membership_qr_png
from app.util.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/discord",
    tags=["Discord"],
)

# https://discord.com/developers/docs/interactions/receiving-and-responding
INTERACTION_PING = 1
INTERACTION_APPLICATION_COMMAND = 2
CALLBACK_PONG = 1
CALLBACK_CHANNEL_MESSAGE = 4
FLAG_EPHEMERAL = 1 << 6
# Discord rejects an interaction response with "Missing Permissions" when the
# app lacks these in the channel the command was run from.
PERMISSION_EMBED_LINKS = 1 << 14
PERMISSION_ATTACH_FILES = 1 << 15

# Every command we register with Discord. `entry.py register-discord-commands`
# reads this so the endpoint and the portal can't drift apart.
COMMANDS = [
    {
        "name": "onboard-qr",
        "description": "Show your Hack@UCF membership QR code",
        "type": 1,
    },
]


def verify_signature(public_key: str, signature: str | None, timestamp: str | None, body: bytes) -> bool:
    """Discord signs `timestamp + body` with the application's Ed25519 key."""
    if not signature or not timestamp:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(bytes.fromhex(signature), timestamp.encode() + body)
    except (ValueError, InvalidSignature):
        return False
    return True


def ephemeral_message(content: str) -> dict:
    return {"type": CALLBACK_CHANNEL_MESSAGE, "data": {"content": content, "flags": FLAG_EPHEMERAL}}


def onboard_qr_response(user: UserModel) -> Response:
    """
    An ephemeral embed with the member's QR attached. The QR encodes the
    membership ID, so it must never be visible to anyone but the invoker.
    """
    user_id = str(user.id)
    payload = {
        "type": CALLBACK_CHANNEL_MESSAGE,
        "data": {
            "flags": FLAG_EPHEMERAL,
            "embeds": [
                {
                    "title": "Your Hack@UCF Membership QR",
                    "description": f"Membership ID: `{user_id}`\nFull member: {'Yes' if user.is_full_member else 'No'}",
                    "image": {"url": "attachment://qr.png"},
                }
            ],
            "attachments": [{"id": 0, "filename": "qr.png"}],
        },
    }
    body, content_type = encode_multipart_formdata(
        {
            "payload_json": json.dumps(payload),
            "files[0]": ("qr.png", membership_qr_png(user_id), "image/png"),
        }
    )
    return Response(content=body, media_type=content_type)


@router.post("/interactions")
async def interactions(request: Request, session=Depends(get_session)):
    """Receive a Discord interaction (PING or slash command) and answer it inline."""
    public_key = Settings().discord.public_key
    if not Settings().discord.enable or not public_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord interactions are not configured")

    body = await request.body()
    # Discord's endpoint validation sends deliberately bad signatures and
    # requires a 401 for them, otherwise the portal refuses to save the URL.
    if not verify_signature(public_key, request.headers.get("x-signature-ed25519"), request.headers.get("x-signature-timestamp"), body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid request signature")

    interaction = json.loads(body)
    if interaction.get("type") == INTERACTION_PING:
        return {"type": CALLBACK_PONG}

    if interaction.get("type") != INTERACTION_APPLICATION_COMMAND:
        return ephemeral_message("Sorry, I don't know how to handle that.")

    command = interaction.get("data", {}).get("name")
    if command != "onboard-qr":
        logger.warning("Unknown Discord command %r", command)
        return ephemeral_message("Sorry, I don't know that command.")

    # In a guild the invoker is under `member`; in a DM it's `user`.
    discord_user = interaction.get("member", {}).get("user") or interaction.get("user") or {}
    discord_id = discord_user.get("id")
    if not discord_id:
        return ephemeral_message("Sorry, I couldn't tell who you are.")

    user = session.exec(select(UserModel).where(UserModel.discord_id == str(discord_id))).one_or_none()
    if not user:
        return ephemeral_message("You haven't onboarded yet! Sign up at https://join.hackucf.org and then try again.")

    needed = PERMISSION_EMBED_LINKS | PERMISSION_ATTACH_FILES
    if int(interaction.get("app_permissions", 0)) & needed != needed:
        logger.warning("Bot lacks Embed Links / Attach Files in channel %s; cannot send the QR", interaction.get("channel_id"))
        return ephemeral_message("I can't attach images in this channel. You can find your QR code at https://join.hackucf.org/profile")

    return onboard_qr_response(user)
