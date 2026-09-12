# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
"""
Tests for the /discord/interactions endpoint that backs the /onboard-qr slash command.
"""

import io
import json
import time
from email import message_from_bytes

import pytest
import segno
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import UserModel
from app.util.settings import Settings

INTERACTIONS_URL = "/discord/interactions"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(name="signing_key")
def signing_key_fixture():
    """Stand in for Discord: configure our public key and hand back the private half."""
    key = Ed25519PrivateKey.generate()
    public_hex = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    discord = Settings().discord
    previous = (discord.enable, discord.public_key)
    discord.enable = True
    discord.public_key = public_hex
    yield key
    discord.enable, discord.public_key = previous


def signed_post(client: TestClient, key: Ed25519PrivateKey, interaction: dict, *, tamper: bool = False):
    body = json.dumps(interaction).encode()
    timestamp = str(int(time.time()))
    signature = key.sign(timestamp.encode() + body)
    if tamper:
        signature = bytes([signature[0] ^ 0xFF]) + signature[1:]
    return client.post(
        INTERACTIONS_URL,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-Ed25519": signature.hex(),
            "X-Signature-Timestamp": timestamp,
        },
    )


# Embed Links | Attach Files: what the bot needs in the channel to send the QR.
ALL_NEEDED_PERMISSIONS = str((1 << 14) | (1 << 15))


def onboard_qr_interaction(discord_id: str, *, in_guild: bool = True, app_permissions: str = ALL_NEEDED_PERMISSIONS) -> dict:
    user = {"id": discord_id, "username": "someone"}
    interaction = {"type": 2, "data": {"name": "onboard-qr", "type": 1}, "app_permissions": app_permissions}
    if in_guild:
        interaction["member"] = {"user": user}
    else:
        interaction["user"] = user
    return interaction


def parse_multipart(response) -> tuple[dict, bytes]:
    """Split Discord's multipart callback into (payload_json, qr.png bytes)."""
    raw = f"Content-Type: {response.headers['content-type']}\r\n\r\n".encode() + response.content
    parts = {part.get_param("name", header="content-disposition"): part for part in message_from_bytes(raw).get_payload()}
    payload = json.loads(parts["payload_json"].get_payload(decode=True))
    png = parts["files[0]"].get_payload(decode=True)
    assert parts["files[0]"].get_filename() == "qr.png"
    return payload, png


def test_rejects_when_not_configured(client: TestClient):
    """config.yml in tests has Discord disabled, so the endpoint must refuse outright."""
    response = client.post(INTERACTIONS_URL, json={"type": 1})
    assert response.status_code == 503


def test_rejects_missing_signature(client: TestClient, signing_key):
    response = client.post(INTERACTIONS_URL, json={"type": 1})
    assert response.status_code == 401


def test_rejects_bad_signature(client: TestClient, signing_key):
    """Discord's endpoint validation sends bad signatures and requires a 401."""
    response = signed_post(client, signing_key, {"type": 1}, tamper=True)
    assert response.status_code == 401


def test_rejects_signature_from_other_key(client: TestClient, signing_key):
    response = signed_post(client, Ed25519PrivateKey.generate(), {"type": 1})
    assert response.status_code == 401


def test_ping_pong(client: TestClient, signing_key):
    response = signed_post(client, signing_key, {"type": 1})
    assert response.status_code == 200
    assert response.json() == {"type": 1}


def test_onboard_qr_returns_ephemeral_qr(client: TestClient, signing_key, test_user: UserModel):
    response = signed_post(client, signing_key, onboard_qr_interaction(test_user.discord_id))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/form-data")

    payload, png = parse_multipart(response)
    assert payload["type"] == 4
    assert payload["data"]["flags"] & 64, "QR must be ephemeral: it encodes the membership ID"
    embed = payload["data"]["embeds"][0]
    assert embed["image"]["url"] == "attachment://qr.png"
    assert str(test_user.id) in embed["description"]
    assert "Full member: Yes" in embed["description"]
    assert png.startswith(PNG_MAGIC)


def test_onboard_qr_encodes_membership_id(client: TestClient, signing_key, test_user: UserModel):
    """The scanner reads the bare UUID, same as the profile page and wallet passes."""
    response = signed_post(client, signing_key, onboard_qr_interaction(test_user.discord_id))
    _, png = parse_multipart(response)
    # segno can't decode, but it is deterministic: the same data renders to the same bytes.
    expected = io.BytesIO()
    segno.make(str(test_user.id), error="m").save(expected, kind="png", scale=8, border=2)
    assert png == expected.getvalue()


def test_onboard_qr_works_from_dm(client: TestClient, signing_key, test_user: UserModel):
    response = signed_post(client, signing_key, onboard_qr_interaction(test_user.discord_id, in_guild=False))
    assert response.status_code == 200
    payload, _ = parse_multipart(response)
    assert str(test_user.id) in payload["data"]["embeds"][0]["description"]


def test_onboard_qr_shows_not_full_member(client: TestClient, signing_key, session: Session, test_user: UserModel):
    test_user.is_full_member = False
    session.add(test_user)
    session.commit()
    response = signed_post(client, signing_key, onboard_qr_interaction(test_user.discord_id))
    payload, _ = parse_multipart(response)
    assert "Full member: No" in payload["data"]["embeds"][0]["description"]


def test_onboard_qr_without_attach_files_permission_falls_back_to_link(client: TestClient, signing_key, test_user: UserModel):
    """Discord would reject the attachment with "Missing Permissions"; point at the profile page instead."""
    embed_links_only = str(1 << 14)
    response = signed_post(client, signing_key, onboard_qr_interaction(test_user.discord_id, app_permissions=embed_links_only))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["flags"] & 64
    assert "join.hackucf.org/profile" in body["data"]["content"]


def test_onboard_qr_unknown_user(client: TestClient, signing_key):
    response = signed_post(client, signing_key, onboard_qr_interaction("000000000000000000"))
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == 4
    assert body["data"]["flags"] & 64
    assert "join.hackucf.org" in body["data"]["content"]


def test_unknown_command_is_answered(client: TestClient, signing_key, test_user: UserModel):
    """Answer rather than 4xx, so Discord doesn't show 'The application did not respond'."""
    interaction = onboard_qr_interaction(test_user.discord_id)
    interaction["data"]["name"] = "something-else"
    response = signed_post(client, signing_key, interaction)
    assert response.status_code == 200
    assert response.json()["data"]["flags"] & 64
