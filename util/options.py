import os
from pydantic import BaseModel, SecretStr, constr
from pydantic_settings import BaseSettings
import yaml
import json
import subprocess
from functools import lru_cache

#TODO
# 1. Add constr to strings to enforce length and format
# 2. Test Bitwarden overwrites

yaml_settings = dict()

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "../config/options.yml")) as f:
    yaml_settings.update(yaml.load(f, Loader=yaml.FullLoader))
def parse_json_to_dict(json_string):
    data = json.loads(json_string)
    return {item['key']: item['value'] for item in data}

try:
    command = f"bws secret list {yaml_settings['bws']['project_id']}"
    bitwarden_raw = subprocess.check_output(command, shell=True, text=True)
except Exception as e:
    print(e)
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
    if top_key in yaml_settings:
        for nested_key, value in nested_dict.items():
            yaml_settings[top_key][nested_key] = value

class DiscordConfig(BaseModel):
    bot_token: SecretStr
    client_id: int
    guild_id: int
    member_role: int
    redirect_base: str
    scope: str
    secret: SecretStr

discord_config = DiscordConfig(**yaml_settings['discord'])
class StripeConfig(BaseModel):
    api_key: SecretStr
    webhook_secret: SecretStr
    price_id: str
    url_success: str
    url_failure: str
stripe_config = StripeConfig(**yaml_settings['stripe']) 

class EmailConfig(BaseModel):
    smtp_server: str 
    email: str
    password: SecretStr
email_config = EmailConfig(**yaml_settings['email']) 

class JwtConfig(BaseModel):
    secret: SecretStr
    algorithm: str
    lifetime_user: int
    lifetime_sudo: int
jwt_config = JwtConfig(**yaml_settings['jwt'])

class DynamodbConfig(BaseModel):
    table: str
dynamodb_config = DynamodbConfig(**yaml_settings['aws']['dynamodb'])

class InfraConfig(BaseModel):
    wifi: str
    horizon: str
    application_credential_id: str
    application_credential_secret: SecretStr
    tf_directory: str
infra_config = InfraConfig(**yaml_settings['infra'])

class RedisConfig(BaseModel):
    host: str
    port: int
    db: int
redis_config = RedisConfig(**yaml_settings['redis'])

class HttpConfig(BaseModel):
    domain: str 
http_config = HttpConfig(**yaml_settings['http'])

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
