#!/usr/bin/env python3
"""
Register OnboardLite's slash commands (/onboard-qr) with Discord.

Bulk-overwrites the guild's application commands with the list in
app/routes/discord_bot.py, so removing a command there and re-running this
removes it from Discord too. Guild commands show up instantly; global ones
can take up to an hour, and membership only matters in the Hack@UCF guild.

The bot must have been invited with the `applications.commands` scope, and
the "Interactions Endpoint URL" in the developer portal must point at
https://join.hackucf.org/discord/interactions for the commands to do anything.

Reads discord.client_id, discord.guild_id and discord.bot_token from config.yml.

Run with:
  uv run python scripts/register_discord_commands.py
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    from app.routes.discord_bot import COMMANDS
    from app.util.settings import Settings

    discord = Settings().discord
    if not discord.enable or discord.bot_token is None or not discord.client_id or not discord.guild_id:
        sys.exit("Discord is not configured: fill in discord.enable, client_id, guild_id and bot_token in config.yml.")

    resp = requests.put(
        f"https://discord.com/api/v10/applications/{discord.client_id}/guilds/{discord.guild_id}/commands",
        headers={"Authorization": f"Bot {discord.bot_token.get_secret_value()}"},
        json=COMMANDS,
    )
    if resp.status_code >= 400:
        sys.exit(f"Discord refused the commands: {resp.status_code} {resp.text[:500]}")

    for command in resp.json():
        print(f"registered /{command['name']} (id {command['id']})")


if __name__ == "__main__":
    main()
