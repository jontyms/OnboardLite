import json

import requests

from util.options import Options

options = Options.fetch()

headers = {
    "Authorization": f"Bot {options.get('discord', {}).get('bot_token')}",
    "Content-Type": "application/json",
    "X-Audit-Log-Reason": "Hack@UCF OnboardLite Bot",
}


class Discord:
    """
    This function handles Discord API interactions, including sending messages.
    """

    def __init__(self):
        pass

    def assign_role(discord_id, role_id):
        discord_id = str(discord_id)

        req = requests.put(
            f"https://discord.com/api/guilds/{options.get('discord', {}).get('guild_id')}/members/{discord_id}/roles/{role_id}",
            headers=headers,
        )

        return req.status_code < 400

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

    def send_message(discord_id, message):
        discord_id = str(discord_id)
        channel_id = Discord.get_dm_channel_id(discord_id)

        send_message_body = {"content": message}
        req = requests.post(
            f"https://discord.com/api/channels/{channel_id}/messages",
            headers=headers,
            data=json.dumps(send_message_body),
        )
        print(req.text)

        return req.status_code < 400
