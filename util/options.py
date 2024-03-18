import json
import logging
import os
import subprocess

import yaml
from pydantic import BaseModel, SecretStr, constr
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

def BitwardenConfig(settings_dict: dict):
    '''
    Takes a dict of settings loaded from yaml and adds the secrets from bitwarden to the settings dict.
    The bitwarden secrets are mapped to the settings dict using the bitwarden_mapping dict.
    The secrets are sourced based on a project id in the settings dict.
    '''
    logger.debug("Loading secrets from Bitwarden")
    try:
        command = f"bws secret list {settings_dict['bws']['project_id']}"
        bitwarden_raw = subprocess.check_output(command, shell=True, text=True)
    except Exception as e:
        logger.error(e)
    bitwarden_settings = parse_json_to_dict(bitwarden_raw)

    bitwarden_mapping = {
        'discord_bot_token': ('discord', 'bot_token'),
        'discord_client_id': ('discord', 'client_id'),
        'discord_secret': ('discord', 'secret'),
        'stripe_api_key': ('stripe', 'api_key'),
        'stripe_webhook_secret': ('stripe', 'webhook_secret'),
        'stripe_price_id': ('stripe', 'price_id'),
        'email_password': ('email', 'password'),
        'jwt_secret': ('jwt', 'secret'),
        'infra_wifi': ('infra', 'wifi'),
        'infra_application_credential_id': ('infra', 'application_credential_id'),
        'infra_configuration_credential_secret': ('infra', 'application_credential_secret')
    }

    bitwarden_mapped = {}
    for bw_key, nested_keys in bitwarden_mapping.items():
        if bw_key in bitwarden_settings:
            top_key, nested_key = nested_keys
            if top_key not in bitwarden_mapped:
                bitwarden_mapped[top_key] = {}
            bitwarden_mapped[top_key][nested_key] = bitwarden_settings[bw_key]

    for top_key, nested_dict in bitwarden_mapped.items():
        if top_key in settings_dict:
            for nested_key, value in nested_dict.items():
                settings_dict[top_key][nested_key] = value
    return settings_dict

settings_dict = dict()

# Reads config from ../config/options.yml
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "../config/options.yml")) as f:
    settings_dict.update(yaml.load(f, Loader=yaml.FullLoader))
def parse_json_to_dict(json_string):
    data = json.loads(json_string)
    return {item['key']: item['value'] for item in data}

# If bitwarden is enabled, add secrets to settings_dict
if settings_dict.get('bws').get('enable'):
    settings_dict = BitwardenConfig(settings_dict)


class DiscordConfig(BaseModel):
    """
    Represents the configuration settings for Discord integration.

    Attributes:
        bot_token (SecretStr): The secret token for the Discord bot.
        client_id (int): The client ID for the Discord application.
        guild_id (int): The ID of the HackUCF discord server.
        member_role (int): The ID of the role assigned to members.
        redirect_base (str): The base URL for redirecting after authentication.
        scope (str): The scope of permissions required for the Discord integration.
        secret (SecretStr): The secret key for the Discord oauth.
    """
    bot_token: SecretStr
    client_id: int
    guild_id: int
    member_role: int
    redirect_base: str
    scope: str
    secret: SecretStr

discord_config = DiscordConfig(**settings_dict['discord'])
class StripeConfig(BaseModel):
    """
    Configuration class for Stripe integration.

    Attributes:
        api_key (SecretStr): The API key for Stripe.
        webhook_secret (SecretStr): The webhook secret for Stripe.
        price_id (str): The ID of the price for the product.
        url_success (str): The URL to redirect to on successful payment.
        url_failure (str): The URL to redirect to on failed payment.
    """
    api_key: SecretStr
    webhook_secret: SecretStr
    price_id: str
    url_success: str
    url_failure: str
stripe_config = StripeConfig(**settings_dict['stripe'])

class EmailConfig(BaseModel):
    """
    Represents the configuration for an email.

    Attributes:
        smtp_server (str): The SMTP server address.
        email (str): The email address to send from also used as the login username.
        password (SecretStr): The password for the email account.
    """
    smtp_server: str
    email: str
    password: SecretStr
email_config = EmailConfig(**settings_dict['email'])

class JwtConfig(BaseModel):
    """
    Configuration class for JWT (JSON Web Token) settings.

    Attributes:
        secret (SecretStr): The secret key used for signing and verifying JWTs.(min_length=32)
        algorithm (str): The algorithm used for JWT encryption.
        lifetime_user (int): The lifetime (in seconds) of a user JWT.
        lifetime_sudo (int): The lifetime (in seconds) of a sudo JWT.
    """
    secret: SecretStr = constr(min_length=32)
    algorithm: str
    lifetime_user: int
    lifetime_sudo: int
jwt_config = JwtConfig(**settings_dict['jwt'])

class DynamodbConfig(BaseModel):
    table: str
dynamodb_config = DynamodbConfig(**settings_dict['aws']['dynamodb'])

class InfraConfig(BaseModel):
    """
    Represents the infrastructure configuration.

    Attributes:
        wifi (str): The WiFi password used in welcome messages.
        horizon (str): The url of the openstack horizon interface (also used to derive the keystone endpoint).
        application_credential_id (str): The application credential ID used to provision users and projects.
        application_credential_secret (SecretStr): The application credential secret used to provision users and projects.
        tf_directory (str): The Terraform directory.
    """
    wifi: str
    horizon: str
    application_credential_id: str
    application_credential_secret: SecretStr
    tf_directory: str
infra_config = InfraConfig(**settings_dict['infra'])

class RedisConfig(BaseModel):
    host: str
    port: int
    db: int
redis_config = RedisConfig(**settings_dict['redis'])

class HttpConfig(BaseModel):
    domain: str
http_config = HttpConfig(**settings_dict['http'])

class SingletonBaseSettingsMeta(type(BaseSettings), type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
class Settings(BaseSettings, metaclass=SingletonBaseSettingsMeta):
    discord: DiscordConfig = discord_config
    stripe: StripeConfig = stripe_config
    email: EmailConfig = email_config
    jwt: JwtConfig = jwt_config
    aws: DynamodbConfig = dynamodb_config
    infra: InfraConfig = infra_config
    redis: RedisConfig = redis_config
    http: HttpConfig = http_config
