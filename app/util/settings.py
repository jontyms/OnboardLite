import json
import logging
import os
import pathlib
import re
import subprocess
from typing import Optional

import yaml
from pydantic import BaseModel, Field, SecretStr, constr, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

config_file = pathlib.Path(os.getenv("ONBOARD_CONFIG_FILE", "config.yml")).resolve()
onboard_env = os.getenv("ONBOARD_ENV", "prod")

if onboard_env == "dev":
    import hashlib
    import socket


def BitwardenConfig(settings: dict):
    """
    Takes a dict of settings loaded from yaml and adds the secrets from bitwarden to the settings dict.
    The bitwarden secrets are mapped to the settings dict using the bitwarden_mapping dict.
    The secrets are sourced based on a project id in the settings dict.
    """
    logger.debug("Loading secrets from Bitwarden")
    try:
        project_id = settings["bws"]["project_id"]
        if bool(re.search("[^a-z0-9-]", project_id)):
            raise ValueError("Invalid project id")
        command = ["bws", "secret", "list", project_id, "--output", "json"]
        env_vars = os.environ.copy()
        bitwarden_raw = subprocess.run(
            command, text=True, env=env_vars, capture_output=True
        ).stdout
    except Exception as e:
        logger.exception(e)
        raise e
    bitwarden_settings = parse_json_to_dict(bitwarden_raw)

    bitwarden_mapping = {
        "discord_bot_token": ("discord", "bot_token"),
        "discord_client_id": ("discord", "client_id"),
        "discord_secret": ("discord", "secret"),
        "stripe_api_key": ("stripe", "api_key"),
        "stripe_webhook_secret": ("stripe", "webhook_secret"),
        "stripe_price_id": ("stripe", "price_id"),
        "email_password": ("email", "password"),
        "jwt_secret": ("jwt", "secret"),
        "infra_wifi": ("infra", "wifi"),
        "infra_application_credential_id": ("infra", "application_credential_id"),
        "infra_configuration_credential_secret": (
            "infra",
            "application_credential_secret",
        ),
    }

    bitwarden_mapped = {}
    for bw_key, nested_keys in bitwarden_mapping.items():
        if bw_key in bitwarden_settings:
            top_key, nested_key = nested_keys
            if top_key not in bitwarden_mapped:
                bitwarden_mapped[top_key] = {}
            bitwarden_mapped[top_key][nested_key] = bitwarden_settings[bw_key]

    for top_key, nested_dict in bitwarden_mapped.items():
        if top_key in settings:
            for nested_key, value in nested_dict.items():
                settings[top_key][nested_key] = value
    return settings


settings = dict()

# Reads config from ../config/options.yml
if os.path.exists(config_file):
    with open(config_file) as f:
        settings.update(yaml.load(f, Loader=yaml.FullLoader))
else:
    logger.error("No config file found at: " + str(config_file))


def parse_json_to_dict(json_string):
    data = json.loads(json_string)
    return {item["key"]: item["value"] for item in data}


# If bitwarden is enabled, add secrets to settings
if settings.get("bws", {}).get("enable"):
    settings = BitwardenConfig(settings)

logger.debug("Final settings: %s", settings)


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
        enable (Optional[bool]): A flag indicating whether Discord integration is enabled.
    """

    bot_token: Optional[SecretStr] = Field(None)
    client_id: Optional[int] = Field(None)
    guild_id: Optional[int] = Field(None)
    member_role: Optional[int] = Field(None)
    redirect_base: Optional[str] = Field(None)
    scope: Optional[str] = Field(None)
    secret: Optional[SecretStr] = Field(None)
    enable: Optional[bool] = Field(True)

    @model_validator(mode="after")
    def check_required_fields(cls, values):
        enable = values.enable
        if enable:
            required_fields = [
                "bot_token",
                "client_id",
                "guild_id",
                "member_role",
                "redirect_base",
                "scope",
                "secret",
            ]
            for field in required_fields:
                if getattr(values, field) is None:
                    raise ValueError(f"Discord {field} is required when enable is True")
        return values


if settings.get("discord"):
    discord_config = DiscordConfig(**settings["discord"])
elif onboard_env == "dev":
    discord_config = DiscordConfig(enable=False, redirect_base="localhost")
else:
    logger.warn("Missing discord config")


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

    api_key: Optional[SecretStr] = Field(None)
    webhook_secret: Optional[SecretStr] = Field(None)
    price_id: Optional[str] = Field(None)
    url_success: Optional[str] = Field(None)
    url_failure: Optional[str] = Field(None)
    pause_payments: Optional[bool] = Field(False)

    @model_validator(mode="after")
    def check_required_fields(cls, values):
        enable = values.pause_payments
        if not enable:
            required_fields = [
                "api_key",
                "webhook_secret",
                "price_id",
                "url_success",
                "url_failure",
            ]
            for field in required_fields:
                if getattr(values, field) is None:
                    raise ValueError(
                        f"Stripe {field} is required when pause_payments is True"
                    )
        return values


if settings.get("stripe"):
    stripe_config = StripeConfig(**settings["stripe"])
elif onboard_env == "dev":
    stripe_config = StripeConfig(pause_payments=True)
else:
    logger.warn("Missing Stripe config")


class GoogleWalletConfig(BaseModel):
    """
    #TODO fix docs
    """

    auth_json: Optional[SecretStr] = Field(None)
    class_suffix: Optional[str] = Field(None)
    issuer_id: Optional[str] = Field(None)
    enable: Optional[bool] = Field(True)

    @model_validator(mode="after")
    def check_required_fields(cls, values):
        enable = values.enable
        if enable:
            required_fields = [
                "auth_json",
                "issuer_id",
                "class_suffix",
            ]
            for field in required_fields:
                if getattr(values, field) is None:
                    raise ValueError(
                        f"Google Wallet {field} is required when pause_payments is True"
                    )
        return values


if settings.get("google_wallet"):
    google_wallet_config = GoogleWalletConfig(**settings["google_wallet"])
elif onboard_env == "dev":
    google_wallet_config = GoogleWalletConfig(enable=False)
else:
    logger.warn("Missing GWallet config")


class EmailConfig(BaseModel):
    """
    Represents the configuration for an email.

    Attributes:
        smtp_server (str): The SMTP server address.
        email (str): The email address to send from also used as the login username.
        password (SecretStr): The password for the email account.
        enable (Optional[bool]): A flag indicating whether email integration is enabled.
    """

    smtp_server: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    password: Optional[SecretStr] = Field(None)
    enable: Optional[bool] = Field(True)

    @model_validator(mode="after")
    def check_required_fields(cls, values):
        enable = values.enable
        if enable:
            required_fields = ["smtp_server", "email", "password"]
            for field in required_fields:
                if getattr(values, field) is None:
                    raise ValueError(f"Email {field} is required when enable is True")
        return values


if settings.get("email"):
    email_config = EmailConfig(**settings["email"])
elif onboard_env == "dev":
    email_config = EmailConfig(enable=False)
else:
    logger.warn("Missing email config")


class JwtConfig(BaseModel):
    """
    Configuration class for JWT (JSON Web Token) settings.

    Attributes:
        secret (SecretStr): The secret key used for signing and verifying JWTs.
        algorithm (str): The algorithm used for JWT encryption.
        lifetime_user (int): The lifetime (in seconds) of a user JWT.
        lifetime_sudo (int): The lifetime (in seconds) of a sudo JWT.
    """

    secret: SecretStr = constr(min_length=32)
    algorithm: Optional[str] = Field("HS256")
    lifetime_user: Optional[int] = Field(9072000)
    lifetime_sudo: Optional[int] = Field(86400)


if settings.get("jwt"):
    jwt_config = JwtConfig(**settings["jwt"])
elif onboard_env == "dev":
    # Provides a stable secret per dev instance, horribly insecure for prod
    hostname = socket.gethostname()
    secret = hashlib.sha256(hostname.encode("utf-8")).hexdigest()
    jwt_config = JwtConfig(secret=secret)


class InfraConfig(BaseModel):
    """
    Represents the infrastructure configuration.

    Attributes:
        wifi (str): The WiFi password used in welcome messages.
        horizon (str): The url of the openstack horizon interface (also used to derive the keystone endpoint).
    """

    wifi: Optional[str] = Field(None)
    horizon: Optional[str] = Field(None)


if settings.get("infra"):
    infra_config = InfraConfig(**settings["infra"])
elif onboard_env == "dev":
    infra_config = InfraConfig()


class KeycloakConfig(BaseModel):
    username: Optional[str] = Field(None)
    password: Optional[SecretStr] = Field(None)
    url: Optional[str] = Field(None)
    realm: Optional[str] = Field(None)
    enable: Optional[bool] = Field(True)

    @model_validator(mode="after")
    def check_required_fields(cls, values):
        enable = values.enable
        if enable:
            required_fields = ["username", "password", "url", "realm"]
            for field in required_fields:
                if getattr(values, field) is None:
                    raise ValueError(
                        f"Keycloak {field} is required when enable is True"
                    )
        return values


if settings.get("keycloak"):
    keycloak_config = KeycloakConfig(**settings["keycloak"])
elif onboard_env == "dev":
    keycloak_config = KeycloakConfig(enable=False)
else:
    logger.warn("Missing Keycloak Config")


class CaptchaConfig(BaseModel):
    sitekey: Optional[SecretStr] = Field(None)
    secret: Optional[SecretStr] = Field(None)
    enable: Optional[bool] = Field(True)

    @model_validator(mode="after")
    def check_required_fields(cls, values):
        enable = values.enable
        if enable:
            required_fields = ["sitekey", "secret"]
            for field in required_fields:
                if getattr(values, field) is None:
                    raise ValueError(
                        f"Keycloak {field} is required when enable is True"
                    )
        return values


if settings.get("captcha"):
    captcha_config = KeycloakConfig(**settings["captcha"])
elif onboard_env == "dev":
    captcha = CaptchaConfig(enable=False)
else:
    logger.warn("Missing Captcha Config")


class TelemetryConfig(BaseModel):
    url: Optional[str] = None
    enable: Optional[bool] = False
    env: Optional[str] = "dev"


telemetry_config = TelemetryConfig(**settings.get("telemetry", {}))


class DatabaseConfig(BaseModel):
    url: str


if settings.get("database"):
    database_config = DatabaseConfig(**settings["database"])
elif onboard_env == "dev":
    database_config = DatabaseConfig(url="sqlite:///:memory:")
else:
    logger.warn("Missing database config")


class HttpConfig(BaseModel):
    domain: str


if settings.get("http"):
    http_config = HttpConfig(**settings["http"])
elif onboard_env == "dev":
    http_config = HttpConfig(domain="localhost:8000")
else:
    logger.warn("Missing http config")


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
    database: DatabaseConfig = database_config
    infra: InfraConfig = infra_config
    http: HttpConfig = http_config
    keycloak: KeycloakConfig = keycloak_config
    google_wallet: GoogleWalletConfig = google_wallet_config
    telemetry: Optional[TelemetryConfig] = telemetry_config
    captcha: Optional[CaptchaConfig] = captcha_config
    env: Optional[str] = onboard_env
