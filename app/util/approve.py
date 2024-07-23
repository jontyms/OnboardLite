import logging
import uuid

from keycloak import KeycloakAdmin
from sqlalchemy.orm import selectinload
from sqlalchemy.types import UUID
from sqlmodel import Session, select

from app.models.user import UserModel
from app.util.database import engine
from app.util.discord import Discord
from app.util.email import Email
from app.util.horsepass import HorsePass
from app.util.settings import Settings

logger = logging.getLogger()


class Approve:
    """
    This function will ensure a member meets all requirements to be a member, and if so, creates an
    Infra account + whitelist them to the Hack@UCF Minecraft server.

    If approval fails, dispatch a Discord message saying that something went wrong and how to fix it.
    """

    def __init__(self):
        pass

    def provision_infra(member_id: uuid.UUID, user_data):
        username = user_data.discord.username
        password = HorsePass.gen()
        admin = KeycloakAdmin(
            server_url=Settings().keycloak.url,
            username=Settings().keycloak.username,
            password=Settings().keycloak.password.get_secret_value(),
            realm_name=Settings().keycloak.relam,
            verify=True,
        )
        try:
            admin.create_user(
                {
                    "email": user_data.email,
                    "username": username,
                    "enabled": True,
                    "firstName": user_data.first_name,
                    "lastName": user_data.surname,
                    "attributes": {"onboard-membership-id": str(user_data.id)},
                    "credentials": [
                        {
                            "value": "secret",
                            "type": password,
                        }
                    ],
                },
                exist_ok=False,
            )
        except Exception:
            logger.exception("Keycloak Error")
            raise

        return {"username": username, "password": password}

    # !TODO finish the post-sign-up stuff + testing
    def approve_member(member_id: uuid.UUID):
        with Session(engine) as session:
            logger.info(f"Re-running approval for {str(member_id)}")
            statement = (
                select(UserModel)
                .where(UserModel.id == member_id)
                .options(
                    selectinload(UserModel.discord), selectinload(UserModel.ethics_form)
                )
            )

            result = session.exec(statement)
            user_data = result.one_or_none()
            if not user_data:
                raise Exception("User not found.")
            # If a member was already approved, kill process.
            if user_data.is_full_member:
                logger.info("\tAlready full member.")
                return True

            # Sorry for the long if statement. But we consider someone a "member" iff:
            # - They have a name
            # - We have their Discord snowflake
            # - They paid dues
            # - They signed their ethics form
            if (
                user_data.first_name
                and user_data.discord_id
                and user_data.did_pay_dues
                and user_data.ethics_form.signtime != 0
            ):
                logger.info("\tNewly-promoted full member!")

                discord_id = user_data.discord_id

                # Create an Infra account.
                try:
                    creds = Approve.provision_infra(member_id, user_data)
                except:
                    logger.exception("Failed to provision user account")
                    creds = {"username": None, "password": None}

                # Assign the Dues-Paying Member role
                Discord.assign_role(discord_id, Settings().discord.member_role)

                # Send Discord message saying they are a member
                welcome_msg = f"""Hello {user_data.first_name}, and welcome to Hack@UCF!

This message is to confirm that your membership has processed successfully. You can access and edit your membership ID at https://{Settings().http.domain}/profile.

These credentials can be used to the Hack@UCF Private Cloud, one of our many benefits of paying dues. This can be accessed at {Settings().infra.horizon} while on the CyberLab WiFi.

```yaml
Username: {creds.get('username', 'Not Set')}
Password: {creds.get('password', f"Please visit https://{Settings().http.domain}/profile and under Danger Zone, reset your Infra creds.")}
```

The password for the `Cyberlab` WiFi is currently `{Settings().infra.wifi}`, but this is subject to change (and we'll let you know when that happens).

By using the Hack@UCF Infrastructure, you agree to the Acceptable Use Policy located at https://help.hackucf.org/misc/aup

Happy Hacking,
  - Hack@UCF Bot
            """

                Discord.send_message(discord_id, welcome_msg)
                Email.send_email("Welcome to Hack@UCF", welcome_msg, user_data.email)
                # Set member as a "full" member.
                user_data.is_full_member = True
                session.add(user_data)
                session.commit()
                session.refresh(user_data)

            elif user_data.did_pay_dues:
                logger.info("\tPaid dues but did not do other step!")
                # Send a message on why this check failed.
                fail_msg = f"""Hello {user_data.first_name},

We wanted to let you know that you **did not** complete all of the steps for being able to become an Hack@UCF member.

- Provided a name: {'✅' if user_data.first_name else '❌'}
- Signed Ethics Form: {'✅' if user_data.ethics_form.signtime != 0 else '❌'}
- Paid $10 dues: ✅

Please complete all of these to become a full member. Once you do, visit https://{Settings().http.domain}/profile to re-run this check.

If you think you have completed all of these, please reach out to an Exec on the Hack@UCF Discord.

We hope to see you soon,
  - Hack@UCF Bot
"""
                Discord.send_message(discord_id, fail_msg)

            else:
                logger.info("\tDid not pay dues yet.")

        return False
