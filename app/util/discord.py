# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import json
import logging

import requests

from app.util.settings import Settings

logger = logging.getLogger(__name__)

headers: dict[str, str] = {}
if Settings().discord.enable:
    headers = {
        "Authorization": f"Bot {Settings().discord.bot_token.get_secret_value()}",  # type: ignore[attribute-error]
        "Content-Type": "application/json",
        "X-Audit-Log-Reason": "Hack@UCF OnboardLite Bot",
    }


def _api_error(req) -> str:
    """Discord's JSON error body, or the raw text when it isn't JSON (e.g. a proxy error page)."""
    try:
        return str(req.json())
    except ValueError:
        return req.text[:200]


class Discord:
    """
    This function handles Discord API interactions, including sending messages.
    """

    def __init__(self):
        pass

    @staticmethod
    def assign_role(discord_id, role_id):
        if not Settings().discord.enable:
            return
        logger.info(f"Assigning role {role_id} to {discord_id}, on guild {Settings().discord.guild_id}")
        discord_id = str(discord_id)

        req = requests.put(
            f"https://discord.com/api/guilds/{Settings().discord.guild_id}/members/{discord_id}/roles/{role_id}",
            headers=headers,
        )
        if req.status_code >= 400:
            # %s args rather than an f-string: Sentry groups log events on the
            # message template, so every failure lands in one issue instead of
            # a separate issue per member.
            logger.error("Failed to assign role %s to %s: %s %s", role_id, discord_id, req.status_code, _api_error(req))
            raise Exception(f"Discord api error: {_api_error(req)}")
        return req.status_code < 400

    @staticmethod
    def register_commands(commands: list[dict]) -> list[dict]:
        """
        Bulk-overwrite the guild's slash commands with `commands`, so a command
        removed from the list disappears from Discord on the next run.

        Guild-scoped rather than global: guild commands show up instantly, global
        ones take up to an hour, and membership only matters in the Hack@UCF guild.
        Registration alone does nothing until the "Interactions Endpoint URL" in
        the developer portal points at /discord/interactions.
        """
        if not Settings().discord.enable:
            raise Exception("Discord integration is disabled")
        req = requests.put(
            f"https://discord.com/api/v10/applications/{Settings().discord.client_id}/guilds/{Settings().discord.guild_id}/commands",
            headers=headers,
            data=json.dumps(commands),
        )
        if req.status_code >= 400:
            logger.error("Failed to register Discord commands: %s %s", req.status_code, _api_error(req))
            raise Exception(f"Discord api error: {_api_error(req)}")
        return req.json()

    @staticmethod
    def get_dm_channel_id(discord_id):
        discord_id = str(discord_id)

        # Get DM channel ID.
        get_channel_id_body = {"recipient_id": discord_id}
        req = requests.post(
            "https://discord.com/api/users/@me/channels",
            headers=headers,
            data=json.dumps(get_channel_id_body),
        )
        resp = req.json()

        return resp.get("id", None)

    @staticmethod
    def send_message(discord_id, message):
        if not Settings().discord.enable:
            return
        discord_id = str(discord_id)
        channel_id = Discord.get_dm_channel_id(discord_id)

        send_message_body = {"content": message}
        res = requests.post(
            f"https://discord.com/api/channels/{channel_id}/messages",
            headers=headers,
            data=json.dumps(send_message_body),
        )

        # Use res.ok()?
        return res.status_code < 400

    def join_hack_server(self, discord_id, token):
        if not Settings().discord.enable:
            return True
        # Make user join the Hack@UCF Discord, if it's their first rodeo.
        logger.info(f"Joining {discord_id} to Hack@UCF Discord")
        headers = {
            "Authorization": f"Bot {Settings().discord.bot_token.get_secret_value()}",  # type: ignore[attribute-error]
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": "Hack@UCF OnboardLite Bot",
        }
        put_join_guild = {"access_token": token["access_token"]}
        req = requests.put(
            f"https://discordapp.com/api/guilds/{Settings().discord.guild_id}/members/{discord_id}",
            headers=headers,
            data=json.dumps(put_join_guild),
        )
        # Deliberately does not raise: this runs inside the OAuth callback,
        # before the user row is committed, so a member who cannot be
        # auto-joined (guild cap, ban, missing bot permission) must still be
        # able to finish signing up. Log loudly instead — until now this
        # response was discarded, so a failure here stayed invisible until the
        # dues role assignment 404'd with Unknown Member months later.
        if req.status_code >= 400:
            logger.error("Failed to join %s to guild %s: %s %s", discord_id, Settings().discord.guild_id, req.status_code, _api_error(req))
            return False
        # 201 = joined, 204 = already a member.
        return True
