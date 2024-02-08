import json
import requests

from util.secrets import Secrets

secrets = Secrets.fetch()

discord_id = Secrets.get("discord_id")
bad = Secrets.get("bad")
print(bad)
print(discord_id)
