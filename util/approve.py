import os

import boto3
import openstack
from python_terraform import Terraform

from util.discord import Discord
from util.email import Email
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
        pass

    def provision_infra(member_id, user_data=None):
        # Log into OpenStack
        conn = openstack.connect(cloud="hackucf_infra")

        try:
            os.remove("terraform.tfstate")
        except Exception:
            pass

        try:
            os.remove("terraform.tfstate.backup")
        except Exception:
            pass

        try:
            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
            if not user_data:
                user_data = table.get_item(Key={"id": member_id}).get("Item", None)

            # See if existing email.
            username = user_data.get("infra_email", False)
            if username:
                user = conn.identity.find_user(username)
                if user:
                    # Delete user's default project
                    print(f"user // {user.default_project_id}")
                    proj = conn.identity.get_project(user.default_project_id)
                    proj = conn.identity.delete_project(proj)

                    # Delete user
                    conn.identity.delete_user(user)
                    print(f"{username}: User deleted.")
                else:
                    print(f"{username}: No user.")

            else:
                username = (
                    user_data.get("discord", {}).get("username").replace(" ", "_")
                    + "@infra.hackucf.org"
                )
                # Add username to Onboard database
                table.update_item(
                    Key={"id": member_id},
                    UpdateExpression="SET infra_email = :val",
                    ExpressionAttributeValues={":val": username},
                )

            password = HorsePass.gen()

            ###
            # Let's create a new OpenStack user with the SDK!
            ###

            # Create a project for the new users
            try:
                new_proj = conn.identity.create_project(
                    name=member_id,
                    description="Automatically provisioning with Hack@UCF Onboard",
                )
            except openstack.exceptions.ConflictException:
                # This happens sometimes.
                new_proj = conn.identity.find_project("member_id")

            # Create account and important resources via Terraform magics.
            new_user = conn.identity.create_user(
                default_project_id=new_proj.id,
                name=username,
                description="Hack@UCF Dues Paying Member",
                password=password,
            )

            # Find member role + assign it to user and project
            member_role = conn.identity.find_role("member")
            conn.identity.assign_project_role_to_user(
                project=new_proj, user=new_user, role=member_role
            )

            # Find admin role + assign it to Onboard user + user project
            admin_role = conn.identity.find_role("admin")
            conn.identity.assign_project_role_to_user(
                project=new_proj,
                user=conn.identity.find_user("onboard-service"),
                role=admin_role,
            )

            ## Push account to OpenStack via Terraform magics (not used rn)
            # tf_vars = {'os_password': options.get('infra', {}).get('ad', {}).get('password'), 'tenant_name': member_id, 'handle': username, 'password': password}
            # tf.apply(var=tf_vars, skip_plan=True)

            return {"username": username, "password": password}
        except Exception as e:
            print(e)
            return None

    # !TODO finish the post-sign-up stuff + testing
    def approve_member(member_id):
        print(f"Re-running approval for {member_id}")
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

        user_data = table.get_item(Key={"id": member_id}).get("Item", None)

        # If a member was already approved, kill process.
        if user_data.get("is_full_member", False):
            print("\tAlready full member.")
            return True

        # Sorry for the long if statement. But we consider someone a "member" iff:
        # - They have a name
        # - We have their Discord snowflake
        # - They paid dues
        # - They signed their ethics form
        if (
            user_data.get("first_name")
            and user_data.get("discord_id")
            and user_data.get("did_pay_dues")
            and user_data.get("ethics_form", {}).get("signtime", 0) != 0
        ):
            print("\tNewly-promoted full member!")

            discord_id = user_data.get("discord_id")

            # Create an Infra account.
            creds = Approve.provision_infra(
                member_id, user_data=user_data
            )  # TODO(err): sometimes this is None
            if creds is None:
                creds = {}

            # Minecraft server
            if user_data.get("minecraft", False):
                pass
                # <whitelist logic>

            # Assign the Dues-Paying Member role
            Discord.assign_role(
                discord_id, options.get("discord", {}).get("member_role")
            )

            # Send Discord message saying they are a member
            welcome_msg = f"""Hello {user_data.get('first_name')}, and welcome to Hack@UCF!

This message is to confirm that your membership has processed successfully. You can access and edit your membership ID at https://{options.get('http', {}).get('domain')}/profile.

These credentials can be used to the Hack@UCF Private Cloud, one of our many benefits of paying dues. This can be accessed at {options.get('infra', {}).get('horizon')} while on the CyberLab WiFi.

```yaml
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', f"Please visit https://{options.get('http', {}).get('domain')}/profile and under Danger Zone, reset your Infra creds.")}
```

The password for the `Cyberlab` WiFi is currently `{options.get('infra', {}).get('wifi')}`, but this is subject to change (and we'll let you know when that happens).

By using the Hack@UCF Infrastructure, you agree to the following EULA located at https://help.hackucf.org/misc/eula

Happy Hacking,
  - Hack@UCF Bot
            """

            Discord.send_message(discord_id, welcome_msg)
            Email.send_email("Welcome to Hack@UCF", welcome_msg, user_data.get("email"))
            # Set member as a "full" member.
            table.update_item(
                Key={"id": member_id},
                UpdateExpression="SET is_full_member = :val",
                ExpressionAttributeValues={":val": True},
            )

        elif user_data.get("did_pay_dues"):
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
            Discord.send_message(discord_id, fail_msg)

        else:
            print("\tDid not pay dues yet.")

        return False
