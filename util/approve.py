import json
import os
import yaml
import boto3
import requests
from boto3.dynamodb.conditions import Key, Attr

from util.options import Options
from util.horsepass import HorsePass

options = Options.fetch()

"""
This function will ensure a member meets all requirements to be a member, and if so, creates an
Infra account + whitelist them to the Hack@UCF Minecraft server.

If approval fails, dispatch a Discord message saying that something went wrong and how to fix it.
"""
class Approve:
    def __init__(self):
        super(Approve, self).__init__

    # !TODO finish the post-sign-up stuff + testing
    def approve_member(member_id):
        print(f"Re-running approval for {member_id}")
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

        user_data = table.get_item(
            Key={
                'id': member_id
            }
        ).get("Item", None)

        # If a member was already approved, kill process.
        if user_data.get("is_full_member", False):
            print("\tAlready full member.")
            return True

        # Make user join the Hack@UCF Discord
        discord_id = str(user_data.get("discord_id"))
        headers = {
            "Authorization": f"Bot {options.get('discord', {}).get('bot_token')}",
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": "Hack@UCF OnboardLite Bot"
        }
        requests.put(f"http://discordapp.com/api/guilds/{options.get('discord', {}).get('guild_id')}/members/{discord_id}", headers=headers)

        # Get DM channel ID to send later...
        get_channel_id_body = {
            'recipient_id': discord_id
        }
        req = requests.post(f"https://discord.com/api/users/@me/channels", headers=headers, data=json.dumps(get_channel_id_body))
        resp = req.json()

        # Sorry for the long if statement. But we consider someone a "member" iff:
        # - They have a name
        # - We have their Discord snowflake
        # - We have their NID
        # - They paid dues
        # - They signed their ethics form
        if user_data.get("first_name") and user_data.get("nid") and user_data.get("discord_id") and user_data.get("did_pay_dues") and user_data.get("ethics_form", {}).get("signtime", 0) != 0:
            print("\tNewly-promoted full member!")
            # Create an Infra account.
            username = user_data.get("discord", {}).get("username") + "@infra.hackucf.org"
            password = HorsePass.gen()

            # # Add username to Onboard database
            # table.update_item(
            #     Key={
            #         'id': member_id
            #     },
            #     UpdateExpression='SET infra_email = :val',
            #     ExpressionAttributeValues={
            #         ':val': username
            #     }
            # )
            
            # Push account to OpenStack via Terraform magics
            # <TODO!!>
            
            # Minecraft server
            if user_data.get("minecraft", False):
                pass
                # <whitelist logic>
            
            # Assign the Dues-Paying Member role
            req_dues = requests.put(f"https://discord.com/api/guilds/{options.get('discord', {}).get('guild_id')}/members/{discord_id}/roles/{options.get('discord', {}).get('member_role')}", headers=headers)
            print(req_dues)
            
            # Send Discord message saying they are a member 
            welcome_msg = f"""Hello {user_data.get('first_name')}, and welcome to Hack@UCF!

This message is to confirm that your membership has processed successfully. You can access and edit your membership ID at https://{options.get('http', {}).get('domain')}/profile.

These credentials can be used to the Hack@UCF Private Cloud, one of our many benefits of paying dues. This can be accessed at {options.get('infra', {}).get('horizon')}.

```yaml
Username: {username}
Password: {password}
```

The password for the `Cyberlab` WiFi is currently `{options.get('infra', {}).get('wifi')}`, but this is subject to change (and we'll let you know when that happens).

Happy Hacking,
  - Hack@UCF Bot
            """

#             welcome_msg = f"""Hello {user_data.get('first_name')}, and welcome to Hack@UCF!

# This message is to confirm that your membership has processed successfully, and to give you your temporary Hack@UCF credentials.

# These credentials can be used to the Hack@UCF Private Cloud, one of our many benefits of paying dues.

# ```yaml
# Username: {username}
# Password: {password}
# ```

# When connected to the `Cyberlab` WiFi, you can access the Hack@UCF Private Cloud at {config_option}.

# The password for the `Cyberlab` WiFi is currently `cyberlab`, but this is subject to change (and we'll let you know when that happens).

# Happy Hacking,
#   - Hack@UCF Bot
# """

            send_message_body = {
                "content": welcome_msg
            }
            requests.post(f"https://discord.com/api/channels/{resp.get('id')}/messages", headers=headers, data=json.dumps(send_message_body))

            # Set member as a "full" member.
            table.update_item(
                Key={
                    'id': member_id
                },
                UpdateExpression='SET is_full_member = :val',
                ExpressionAttributeValues={
                    ':val': True
                }
            )

        elif user_data.get('did_pay_dues'):
            print("\tPaid dues but did not do other step!")
            # Send a message on why this check failed.
            fail_msg = f"""Hello {user_data.get('first_name')},

We wanted to let you know that you did not complete all of the steps for being able to become a full-fledged Hack@UCF member.

- Provided a name: {'✅' if user_data.get('first_name') else '❌'}
- Provided a UCF NID: {'✅' if user_data.get('nid') else '❌'}
- Signed Ethics Form: {'✅' if user_data.get('ethics_form', {}).get('signtime', 0) != 0 else '❌'}
- Paid $10 dues: ✅

Please complete all of these to become a full member. Once you do, visit https://{options.get('http', {}).get('domain')}/profile to re-run this check.

If you think you have completed all of these, please reach out to an Exec on the Hack@UCF Discord.

We hope to see you soon,
  - Hack@UCF Bot
"""
            send_message_body = {
                "content": fail_msg
            }
            requests.post(f"https://discord.com/api/channels/{resp.get('id')}/messages", headers=headers, data=json.dumps(send_message_body))

        else:
            print("\tDid not pay dues yet.")
        # is_dues_paying

        return False