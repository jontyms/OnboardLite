import re
import uuid
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, validator
from sqlmodel import Field, Relationship, SQLModel


class DiscordModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = None
    mfa: Optional[bool] = None
    avatar: Optional[str] = None
    banner: Optional[str] = None
    color: Optional[int] = None
    nitro: Optional[int] = None
    locale: Optional[str] = None
    username: str

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="usermodel.id")
    user: "UserModel" = Relationship(back_populates="discord")


class EthicsFormModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hack_others: Optional[bool] = False
    hack_ucf: Optional[bool] = False
    interrupt_ucf: Optional[bool] = False
    manip_traffic: Optional[bool] = False
    bypass_dhcp: Optional[bool] = False
    pirate: Optional[bool] = False
    host_at_ucf: Optional[bool] = False
    cloud_aup: Optional[bool] = False
    signtime: Optional[int] = 0

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="usermodel.id")
    user: "UserModel" = Relationship(back_populates="ethics_form")


class UserModel(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    discord_id: str = Field(unique=True)
    ucf_id: Optional[int] = Field(unique=True, default=None)
    nid: Optional[str] = Field(unique=True, default=None)
    ops_email: Optional[str] = None
    infra_email: Optional[str] = None
    minecraft: Optional[str] = ""
    github: Optional[str] = ""
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
    sudo: Optional[bool] = False
    did_pay_dues: Optional[bool] = False
    join_date: Optional[int] = None
    mentor_name: Optional[str] = None
    is_full_member: Optional[bool] = False
    can_vote: Optional[bool] = False
    experience: Optional[int] = None
    curiosity: Optional[str] = None
    c3_interest: Optional[bool] = False
    attending: Optional[str] = ""
    comments: Optional[str] = ""

    discord: DiscordModel = Relationship(back_populates="user")
    ethics_form: EthicsFormModel = Relationship(back_populates="user")
    # cyberlab_monitor: CyberLabModel = Relationship(back_populates="user")
    # mentee: MenteeModel = Relationship(back_populates="user")

    @validator("nid")
    def nid_length(cls, nid):
        # regex for NID
        pattern = re.compile(r"^([a-z]{2}[0-9]{6})$")
        if pattern.match(nid) is None:
            raise ValueError("NID must be 2 letters followed by 6 numbers")
        if len(nid) != 8:
            raise ValueError("NID must be 8 characters long")
        return nid

    @validator("shirt_size")
    def shirt_size_length(cls, shirt_size):
        # enum for shirt sizes
        sizes = ["S", "M", "L", "XL", "2XL", "3XL"]
        if shirt_size not in sizes:
            raise ValueError("Shirt size must be one of S, M, L, XL, 2XL, 3XL")
        return shirt_size

    @validator("email")
    def nid_regex(cls, email):
        # regex for email
        pattern = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
        if pattern.match(email) is None:
            raise ValueError("Email failed regex validation")


# What admins can edit.
class UserModelMutable(BaseModel):
    # Identifiers
    id: Optional[str] = None
    discord_id: Optional[str] = None
    ucf_id: Optional[int] = None
    nid: Optional[str] = None
    ops_email: Optional[str] = None
    infra_email: Optional[str] = None

    minecraft: Optional[str] = None
    github: Optional[str] = None

    # PII
    first_name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[str] = None
    is_returning: Optional[bool] = None
    gender: Optional[str] = None
    major: Optional[str] = None
    class_standing: Optional[str] = None
    shirt_size: Optional[str] = None
    did_get_shirt: Optional[bool] = None
    phone_number: Optional[int] = None

    # Permissions and Member Status
    sudo: Optional[bool] = None
    did_pay_dues: Optional[bool] = None

    # Mentorship Program
    mentor_name: Optional[str] = None

    is_full_member: Optional[bool] = None
    can_vote: Optional[bool] = False

    # Other models
    experience: Optional[int] = None
    curiosity: Optional[str] = None
    c3_interest: Optional[bool] = None

    # Other things
    attending: Optional[str] = None
    comments: Optional[str] = None
    discord: Optional[DiscordModel] = None
    ethics_form: Optional[EthicsFormModel] = None

class PublicContact(BaseModel):
    first_name: str
    surname: str
    ops_email: str





def user_to_dict(model):
    if model is None:
        return None
    if isinstance(model, list):
        return [user_to_dict(item) for item in model]
    if isinstance(model, (SQLModel, BaseModel)):
        data = model.model_dump()
        for key, value in model.__dict__.items():
            if isinstance(value, (SQLModel, BaseModel)):
                data[key] = user_to_dict(value)
            elif isinstance(value, list) and value and isinstance(value[0], (SQLModel, BaseModel)):
                data[key] = user_to_dict(value)
        return data


def user_update_instance(instance: SQLModel, data: dict[str, Any]) -> None:
    for key, value in data.items():
        if isinstance(value, dict):
            nested_instance = getattr(instance, key, None)
            if nested_instance is not None:
                user_update_instance(nested_instance, value)
            else:
                nested_model_class = instance.__class__.__annotations__.get(key)
                if nested_model_class:
                    new_nested_instance = nested_model_class()
                    user_update_instance(new_nested_instance, value)
        else:
            if value is not None:
                setattr(instance, key, value)



# Removed unneeded functionality

# class CyberLabModel(SQLModel, table=True):
#    id: Optional[int] = Field(default=None, primary_key=True)
#    resource: Optional[bool] = False
#    clean: Optional[bool] = False
#    no_profane: Optional[bool] = False
#    access_control: Optional[bool] = False
#    report_damage: Optional[bool] = False
#    be_nice: Optional[bool] = False
#    can_revoke: Optional[bool] = False
#    signtime: Optional[int] = 0
#
#    user_id: Optional[int] = Field(default=None, foreign_key="usermodel.id")
#    user: "UserModel" = Relationship(back_populates="cyberlab_monitor")
#
# class MenteeModel(SQLModel, table=True):
#    id: Optional[int] = Field(default=None, primary_key=True)
#    schedule: Optional[str] = None
#    time_in_cyber: Optional[str] = None
#    personal_proj: Optional[str] = None
#    hope_to_gain: Optional[str] = None
#    domain_interest: Optional[str] = None
#
#    user_id: Optional[int] = Field(default=None, foreign_key="usermodel.id")
#    user: "UserModel" = Relationship(back_populates="mentee")
