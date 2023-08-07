from pydantic import BaseModel
from typing import Optional

class DiscordModel(BaseModel):
    email:              str
    mfa:                bool
    avatar:             str
    banner:             Optional[str] = None
    color:              int
    nitro:              int
    locale:             str
    username:           str


class EthicsFormModel(BaseModel):
    hack_others:        Optional[bool] = False
    hack_ucf:           Optional[bool] = False
    interrupt_ucf:      Optional[bool] = False
    manip_traffic:      Optional[bool] = False
    bypass_dhcp:        Optional[bool] = False
    pirate:             Optional[bool] = False
    host_at_ucf:        Optional[bool] = False
    signtime:           Optional[int] = 0


class CyberLabModel(BaseModel):
    resource:           Optional[bool] = False
    clean:              Optional[bool] = False
    no_profane:         Optional[bool] = False
    access_control:     Optional[bool] = False
    report_damage:      Optional[bool] = False
    be_nice:            Optional[bool] = False
    can_revoke:         Optional[bool] = False
    signtime:           Optional[int] = 0


class UserModel(BaseModel):
    # Identifiers
    id:                 str
    discord_id:         int
    ucf_id:             Optional[int] = None
    nid:                Optional[str] = None
    ops_email:          Optional[str] = None
    infra_email:        Optional[str] = None

    minecraft:          Optional[str] = ""

    # PII
    first_name:         Optional[str] = ""
    surname:            Optional[str] = ""
    email:              Optional[str] = ""
    is_returning:       Optional[bool] = False
    gender:             Optional[str] = ""
    major:              Optional[str] = ""
    class_standing:     Optional[str] = ""
    shirt_size:         Optional[str] = ""
    did_get_shirt:      Optional[bool] = False
    time_availability:  Optional[str] = ""
    phone_number:       Optional[int] = 0

    # Permissions and Member Status
    sudo:               Optional[bool] = False
    did_pay_dues:       Optional[bool] = False
    join_date:          Optional[int] = None

    # Paperwork Signed
    ethics_form:        Optional[EthicsFormModel] = EthicsFormModel()
    cyberlab_monitor:   Optional[CyberLabModel] = CyberLabModel()
    
    is_full_member:     Optional[bool] = False

    # Other models
    discord:            DiscordModel
    experience:         Optional[int] = None
    curiosity:          Optional[str] = None
    c3_interest:        Optional[bool] = False

    # Other things
    attending:          Optional[str] = ""
    comments:           Optional[str] = ""


class PublicContact(BaseModel):
    first_name: str
    surname: str
    ops_email: str