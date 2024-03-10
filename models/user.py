from typing import Optional

from pydantic import BaseModel


class DiscordModel(BaseModel):
    email: Optional[str] = None
    mfa: Optional[bool] = None
    avatar: Optional[str] = None
    banner: Optional[str] = None
    color: Optional[int] = None
    nitro: Optional[int] = None
    locale: Optional[str] = None
    username: str


class EthicsFormModel(BaseModel):
    hack_others: Optional[bool] = False
    hack_ucf: Optional[bool] = False
    interrupt_ucf: Optional[bool] = False
    manip_traffic: Optional[bool] = False
    bypass_dhcp: Optional[bool] = False
    pirate: Optional[bool] = False
    host_at_ucf: Optional[bool] = False
    signtime: Optional[int] = 0


class CyberLabModel(BaseModel):
    resource: Optional[bool] = False
    clean: Optional[bool] = False
    no_profane: Optional[bool] = False
    access_control: Optional[bool] = False
    report_damage: Optional[bool] = False
    be_nice: Optional[bool] = False
    can_revoke: Optional[bool] = False
    signtime: Optional[int] = 0


class MenteeModel(BaseModel):
    schedule: Optional[str] = None
    time_in_cyber: Optional[str] = None
    personal_proj: Optional[str] = None
    hope_to_gain: Optional[str] = None
    domain_interest: Optional[str] = None


class UserModel(BaseModel):
    # Identifiers
    id: str
    discord_id: str
    ucf_id: Optional[int] = None
    nid: Optional[str] = None
    ops_email: Optional[str] = None
    infra_email: Optional[str] = None

    minecraft: Optional[str] = ""
    github: Optional[str] = ""

    # PII
    first_name: Optional[str] = ""
    surname: Optional[str] = ""
    email: Optional[str] = ""
    is_returning: Optional[bool] = False
    gender: Optional[str] = ""
    major: Optional[str] = ""
    class_standing: Optional[str] = ""
    shirt_size: Optional[str] = ""
    did_get_shirt: Optional[bool] = False
    time_availability: Optional[str] = ""
    phone_number: Optional[int] = 0

    # Permissions and Member Status
    sudo: Optional[bool] = False
    did_pay_dues: Optional[bool] = False
    join_date: Optional[int] = None

    # Paperwork Signed
    ethics_form: Optional[EthicsFormModel] = EthicsFormModel()
    cyberlab_monitor: Optional[CyberLabModel] = CyberLabModel()

    # Mentorship Program
    mentee: Optional[MenteeModel] = MenteeModel()
    mentor_name: Optional[str] = None

    is_full_member: Optional[bool] = False
    can_vote: Optional[bool] = False

    # Other models
    discord: DiscordModel
    experience: Optional[int] = None
    curiosity: Optional[str] = None
    c3_interest: Optional[bool] = False

    # Other things
    attending: Optional[str] = ""
    comments: Optional[str] = ""


# What admins can edit.
class UserModelMutable(BaseModel):
    # Identifiers
    id: str
    discord_id: Optional[str]
    ucf_id: Optional[int]
    nid: Optional[str]
    ops_email: Optional[str]
    infra_email: Optional[str]

    minecraft: Optional[str]
    github: Optional[str]

    # PII
    first_name: Optional[str]
    surname: Optional[str]
    email: Optional[str]
    is_returning: Optional[bool]
    gender: Optional[str]
    major: Optional[str]
    class_standing: Optional[str]
    shirt_size: Optional[str]
    did_get_shirt: Optional[bool]
    phone_number: Optional[int]

    # Permissions and Member Status
    sudo: Optional[bool]
    did_pay_dues: Optional[bool]

    # Mentorship Program
    mentor_name: Optional[str] = None

    is_full_member: Optional[bool]
    can_vote: Optional[bool] = False

    # Other models
    experience: Optional[int]
    curiosity: Optional[str]
    c3_interest: Optional[bool]

    # Other things
    attending: Optional[str]
    comments: Optional[str]


class PublicContact(BaseModel):
    first_name: str
    surname: str
    ops_email: str
