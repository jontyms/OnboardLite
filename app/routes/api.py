# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models.info import InfoModel
from app.models.user import PublicContact, UserModel, user_update_instance
from app.util.auth_dependencies import CurrentMember
from app.util.database import get_session
from app.util.forms import Forms, apply_fuzzy_parsing, transform_dict
from app.util.kennelish import Transformer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API"])


@router.get("/")
async def get_root():
    """
    Get API information.
    """
    return InfoModel(
        name="OnboardLite",
        description="Hack@UCF's in-house membership management suite.",
        credits=[
            PublicContact(
                first_name="Jonathan",
                surname="Styles",
                ops_email="jstyles@hackucf.org",
            )
        ],
    )


@router.get("/form/{num}")
async def get_form(num: str):
    """
    Gets the JSON markup for a Kennelish file. For client-side rendering (if that ever becomes a thing).
    Note that Kennelish form files are NOT considered sensitive.
    """
    try:
        return Forms.get_form_body(num)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Form not found")


"""
Renders a Kennelish form file as HTML (with user data). Intended for AJAX applications.
"""
# TODO Fix or remove this route, Do we even need it?
#
# @router.get("/form/{num}/html", response_class=HTMLResponse)
# @Authentication.member
# async def get_form_html(
#    request: Request,
#    token: Optional[str] = Cookie(None),
#    user_jwt: Optional[object] = {},
#    num: str = 1,
# ):
#    # AWS dependencies
#    # dynamodb = boto3.resource("dynamodb")
#    # table = dynamodb.Table(Settings().aws.table)
#
#    # Get form object
#    try:
#        data = Forms.get_form_body(num)
#    except FileNotFoundError:
#        return HTTPException(status_code=404, detail="Form not found")
#    # Get data from DynamoDB
#    user_data = table.get_item(Key={"id": user_jwt.get("id")}).get("Item", None)
#
#    # Have Kennelish parse the data.
#    body = Kennelish.parse(data, user_data)
#
#    return body


"""
Allows updating the user's database using a schema assumed by the Kennelish file.
"""


# @router.post("/form/ethics_form_midway")
# @Authentication.member
# async def post_ethics_form(
#    request: Request,
#    token: Optional[str] = Cookie(None),
#    user_jwt: Optional[object] = {},
#    session: Session = Depends(get_session),
# ):
#    try:
#        ethics_form_data = EthicsFormUpdate.model_validate(await request.json())
#    except json.JSONDecodeError:
#        return {"description": "Malformed JSON input."}
#    user_id = user_jwt.get("id")
#    # Retrieve existing user model from the database
#    statement = select(UserModel).where(UserModel.id == user_id)
#    result = session.exec(statement)
#    user = result.one_or_none()
#
#    if not user:
#        raise HTTPException(status_code=404, detail="User not found")
#
#    # Update the ethics form with new values
#    validated_data = apply_fuzzy_parsing(
#        ethics_form_data.model_dump(exclude_unset=True), EthicsFormModel
#    )
#    print(validated_data.dict())
#    for key, value in validated_data:
#        if value is not None:
#            setattr(user.ethics_form, key, value)
#
#    # Save the updated model back to the database
#    session.add(user)
#    session.commit()
#    session.refresh(user)
#
#    return user.ethics_form.dict()
#
#
# Human-readable names for the unique columns a member can collide on when
# filling in the form. Anything else falls through to a generic message.
_UNIQUE_FIELD_LABELS = {
    "usermodel.email": "email",
    "uq_usermodel_email": "email",
    "usermodel.nid": "NID",
    "usermodel.ucf_id": "UCF ID",
}


def _integrity_error_message(e: IntegrityError) -> str:
    """
    Turn a UNIQUE-constraint failure into a message we can show the member.

    The overwhelmingly common cause is a returning member who signed in with a
    *different* Discord account and re-entered the email/NID already on their
    original account. That is a user-flow, not a crash, so log at warning and
    keep the raw SQL (which carries their name, email and NID) out of the
    response.
    """
    raw = str(e.orig) if e.orig is not None else str(e)
    logger.warning("Form submit rejected by unique constraint: %s", raw.splitlines()[0])

    for key, label in _UNIQUE_FIELD_LABELS.items():
        if key in raw:
            return f"That {label} is already registered to another account. If it's yours, you may have signed in with a different Discord account than before - create a thread in #infra-helpdesk on Discord so we can migrate it."

    return "Something you entered is already registered to another account. Create a thread in #infra-helpdesk on Discord for help."


@router.post("/form/{num}")
async def post_form(
    request: Request,
    current_user: CurrentMember,
    num: str,
    session: Session = Depends(get_session),
):
    # Get Kennelish data
    try:
        kennelish_data = Forms.get_form_body(num)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Form not found")

    model = Transformer.kennelish_to_pydantic(kennelish_data)

    # Parse and Validate inputs
    try:
        inp = await request.json()
    except json.JSONDecodeError:
        return {"description": "Malformed JSON input."}

    model_validated = model(**inp).model_dump()

    validated_data = apply_fuzzy_parsing(model_validated)

    # Transform the dictionary
    validated_data = transform_dict(validated_data)

    statement = select(UserModel).where(UserModel.id == uuid.UUID(current_user["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))  # type: ignore[bad-argument-type]
    result = session.exec(statement)
    user = result.one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="User not found")

    user_update_instance(user, validated_data)

    # Save the updated model back to the database
    session.add(user)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_integrity_error_message(e)) from e
    session.refresh(user)

    return user.model_dump()


@router.get("/member/{member_id}/dues")
async def get_member_dues_status(
    member_id: str,
    current_user: CurrentMember,
    session: Session = Depends(get_session),
):
    """
    Get dues payment status for a member by their ID.
    Returns true if dues are paid, false if not paid or member not found.
    """
    try:
        # Try to parse member_id as UUID
        member_uuid = uuid.UUID(member_id)
        statement = select(UserModel).where(UserModel.id == member_uuid)
        user = session.exec(statement).one_or_none()

        if not user:
            return {"dues": False}

        return {"dues": bool(user.did_pay_dues)}
    except ValueError:
        # Invalid UUID format
        return {"dues": False}
    except Exception:
        # Any other error, return false for safety
        return {"dues": False}
