from pydantic import BaseModel
from typing import Optional

class DiscordServersModel(BaseModel):
    ucf_hub:            Optional[bool] = False
    ucf_cecs:           Optional[bool] = False
    ucf_it:             Optional[bool] = False
    knight_hacks:       Optional[bool] = False
    ai_ucf:             Optional[bool] = False
    ncae_cybergames:    Optional[bool] = False
    honors_congress:    Optional[bool] = False
    nsa_codebreakers:   Optional[bool] = False
    sunshinectf:        Optional[bool] = False
    htb:                Optional[bool] = False
    metactf:            Optional[bool] = False
    cptc:               Optional[bool] = False
    acm:                Optional[bool] = False
    google_dev_ucf:     Optional[bool] = False


class DiscordModel(BaseModel):
    email:              str
    mfa:                bool
    avatar:             str
    banner:             Optional[str] = None
    color:              int
    nitro:              int
    locale:             str
    servers:            DiscordServersModel


class ExperienceModel(BaseModel):
    hacking:            Optional[int] = None
    phys_sec:           Optional[int] = None
    languages:          Optional[int] = None


class CuriosityModel(BaseModel):
    hacking:            Optional[int] = None
    phys_sec:           Optional[int] = None
    general:            Optional[int] = None


class InterestModel(BaseModel):
    gbm:                Optional[int] = None
    ctf_practice:       Optional[int] = None
    ctf_competitions:   Optional[int] = None
    bbq:                Optional[int] = None
    tailgating:         Optional[int] = None
    movies:             Optional[int] = None
    other:              Optional[int] = None
    ops:                Optional[int] = None
    knightsec:          Optional[int] = None
    ccdc:               Optional[int] = None
    cptc:               Optional[int] = None
    infra:              Optional[int] = None
    present:            Optional[int] = None
    research:           Optional[int] = None

class UserModel(BaseModel):
    # Identifiers
    id:                 str
    discord_id:         int
    ucf_id:             Optional[int] = None
    nid:                Optional[str] = None
    ops_email:          Optional[str] = None
    infra_email:        Optional[str] = None

    # PII
    first_name:         Optional[str] = ""
    surname:            Optional[str] = ""
    email:              Optional[str] = ""
    knights_email:      Optional[str] = ""
    is_returning:       Optional[bool] = False
    gender:             Optional[str] = ""
    major:              Optional[str] = ""
    class_standing:     Optional[str] = ""
    shirt_size:         Optional[str] = ""
    time_availability:  Optional[int] = 0

    # Permissions and Member Status
    sudo:               Optional[bool] = False
    did_pay_dues:       Optional[bool] = False
    join_date:          Optional[int] = None

    # Other models
    discord:            DiscordModel
    experience:         Optional[ExperienceModel] = ExperienceModel()
    curiosity:          Optional[CuriosityModel] = CuriosityModel()
    interest:           Optional[InterestModel] = InterestModel()


class PublicContact(BaseModel):
    first_name: str
    surname: str
    ops_email: str