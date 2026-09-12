# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import os
import subprocess
import sys


# Define the default command to run uvicorn with environment variables
def run_uvicorn():
    host = os.getenv("ONBOARD_HOST", "0.0.0.0")
    port = os.getenv("ONBOARD_PORT", "8000")
    forwarded_allow_ips = os.getenv("ONBOARD_FORWARDED_ALLOW_IPS")

    command = [
        "uv",
        "run",
        "--no-dev",
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        port,
        "--workers",
        "2",
    ]

    if forwarded_allow_ips is not None:
        command.extend(["--forwarded-allow-ips", forwarded_allow_ips])
        command.append("--proxy-headers")

    subprocess.run(command)


def run_dev():
    host = os.getenv("ONBOARD_HOST", "0.0.0.0")
    port = os.getenv("ONBOARD_PORT", "8000")
    command = ["uv", "run", "-m", "uvicorn", "app.main:app", "--host", host, "--port", port, "--reload"]
    subprocess.run(command)


# Define the migrate command
def run_migrate():
    os.chdir("./app")
    command = ["uv", "run", "-m", "alembic", "upgrade", "head"]
    subprocess.run(command)


# Register the slash commands (/onboard-qr) with the Discord guild. Runs inside
# the container so it sees the same config and Bitwarden secrets as the app:
#   docker compose run --rm onboardlite register-discord-commands
def run_register_discord_commands():
    # Run as a script, this file's directory is on sys.path, not the project root.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.routes.discord_bot import COMMANDS
    from app.util.discord import Discord

    for command in Discord.register_commands(COMMANDS):
        print(f"registered /{command['name']} (id {command['id']})")


# Entry point
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        run_migrate()
    elif len(sys.argv) > 1 and sys.argv[1] == "register-discord-commands":
        run_register_discord_commands()
    elif len(sys.argv) > 1 and sys.argv[1] == "dev":
        run_dev()
    else:
        run_uvicorn()
