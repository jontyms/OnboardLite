import json
import os
import datetime

import boto3
import requests
from python_terraform import *
from boto3.dynamodb.conditions import Key, Attr
import yaml

from util.horsepass import HorsePass
from util.options import Options

options = Options.fetch()
tf = Terraform(working_dir=options.get("infra", {}).get("tf_directory", "./"))

"""
This function will ensure a member meets all requirements to be a member, and if so, creates an
Infra account + whitelist them to the Hack@UCF Minecraft server.

If approval fails, dispatch a Discord message saying that something went wrong and how to fix it.
"""
class Approve:
    def __init__(self):
        super(Approve, self).__init__

    def provision_infra(member_id, user_data=None):
        try:
            os.remove("terraform.tfstate")
        except Exception as e:
            pass

        try:
            os.remove("terraform.tfstate.backup")
        except Exception as e:
            pass

        try:
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
            if not user_data:

                user_data = table.get_item(
                    Key={
                        'id': member_id
                    }
                ).get("Item", None)

            username = user_data.get("discord", {}).get("username") + "@infra.hackucf.org"
            password = HorsePass.gen()

            # Add username to Onboard database
            table.update_item(
                Key={
                    'id': member_id
                },
                UpdateExpression='SET infra_email = :val',
                ExpressionAttributeValues={
                    ':val': username
                }
            )
            
            # Push account to OpenStack via Terraform magics
            tf_vars = {'os_password': options.get('infra', {}).get('ad', {}).get('password'), 'tenant_name': member_id + "-" + datetime.date.today().strftime("%Y"), 'handle': username, 'password': password}
            tf.apply(var=tf_vars, skip_plan=True)

            return {
                "username": username,
                "password": password
            }
        except Exception as e:
            print(e)
            return None


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

        # Get DM channel ID to send later...
        discord_id = str(user_data.get("discord_id"))
        headers = {
            "Authorization": f"Bot {options.get('discord', {}).get('bot_token')}",
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": "Hack@UCF OnboardLite Bot"
        }
        get_channel_id_body = {
            'recipient_id': discord_id
        }
        req = requests.post(f"https://discord.com/api/users/@me/channels", headers=headers, data=json.dumps(get_channel_id_body))
        resp = req.json()

        # Sorry for the long if statement. But we consider someone a "member" iff:
        # - They have a name
        # - We have their Discord snowflake
        # - They paid dues
        # - They signed their ethics form
        if user_data.get("first_name") and user_data.get("discord_id") and user_data.get("did_pay_dues") and user_data.get("ethics_form", {}).get("signtime", 0) != 0:
            print("\tNewly-promoted full member!")

            # Create an Infra account.
            creds = Approve.provision_infra(member_id, user_data=user_data)
            
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

These credentials can be used to the Hack@UCF Private Cloud, one of our many benefits of paying dues. This can be accessed at {options.get('infra', {}).get('horizon')} while on the CyberLab WiFi.

```yaml
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', 'Please email ops@hackucf.org for credentials.')}
```

The password for the `Cyberlab` WiFi is currently `{options.get('infra', {}).get('wifi')}`, but this is subject to change (and we'll let you know when that happens).

Happy Hacking,
  - Hack@UCF Bot
            """

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

We wanted to let you know that you **did not** complete all of the steps for being able to become an Hack@UCF member.

- Provided a name: {'✅' if user_data.get('first_name') else '❌'}
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
