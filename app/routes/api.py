import json
import logging
from collections import defaultdict
from typing import Any, Dict, Optional, Type

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from pydantic import error_wrappers
from sqlalchemy.orm import selectinload
from sqlmodel import Session, SQLModel, select

from app.models.info import InfoModel
from app.models.user import (EthicsFormModel, PublicContact, UserModel,
                             UserModelMutable, to_dict)
from app.util import kennelish
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.errors import Errors
from app.util.forms import Forms, apply_fuzzy_parsing
from app.util.kennelish import Kennelish, Transformer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API"], responses=Errors.basic_http())


"""
Get API information.
"""


@router.get("/")
async def get_root():
    return InfoModel(
        name="OnboardLite",
        description="Hack@UCF's in-house membership management suite.",
        credits=[
            PublicContact(
                first_name="Jeffrey",
                surname="DiVincent",
                ops_email="jdivincent@hackucf.org",
            )
        ],
    )


"""
Gets the JSON markup for a Kennelish file. For client-side rendering (if that ever becomes a thing).
Note that Kennelish form files are NOT considered sensitive.
"""


@router.get("/form/{num}")
async def get_form(num: str):
    try:
        return Forms.get_form_body(num)
    except FileNotFoundError:
        return HTTPException(status_code=404, detail="Form not found")


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


#@router.post("/form/ethics_form_midway")
#@Authentication.member
#async def post_ethics_form(
#    request: Request,
#    token: Optional[str] = Cookie(None),
#    user_jwt: Optional[object] = {},
#    session: Session = Depends(get_session),
#):
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
@router.post("/form/{num}")
@Authentication.member
async def post_form(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    num: str = 1,
    session: Session = Depends(get_session),
):
    # Get Kennelish data
    try:
        kennelish_data = Forms.get_form_body(num)
    except FileNotFoundError:
        return HTTPException(status_code=404, detail="Form not found")

    model = Transformer.kennelish_to_pydantic(kennelish_data)

    # Parse and Validate inputs
    try:
        inp = await request.json()
    except json.JSONDecodeError:
        return {"description": "Malformed JSON input."}

    model_validated = model(**inp).model_dump()

    validated_data = apply_fuzzy_parsing(model_validated)

    def transform_dict(d):
       if not any('.' in key for key in d):
        return d
       nested_dict = defaultdict(dict)
       for key, value in d.items():
           parent, child = key.split('.')
           nested_dict[parent][child] = value
       return nested_dict

    # Transform the dictionary
    validated_data = transform_dict(validated_data)


    logger.warning(str(validated_data))


    statement = (
        select(UserModel)
        .where(UserModel.id == user_jwt["id"])
        .options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    )
    result = session.exec(statement)
    user = result.one_or_none()

    if not user:
        raise HTTPException(status_code=422, detail="User not found")

    logger.warning(validated_data)


    def update_instance(instance: SQLModel, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            if isinstance(value, dict):
                nested_instance = getattr(instance, key, None)
                if nested_instance is not None:
                    update_instance(nested_instance, value)
                else:
                    nested_model_class = instance.__class__.__annotations__.get(key)
                    if nested_model_class:
                        new_nested_instance = nested_model_class()
                        update_instance(new_nested_instance, value)
            else:
                setattr(instance, key, value)




    update_instance(user, validated_data)
    logger.warning(to_dict(user))

    # Save the updated model back to the database
    session.add(user)
    session.commit()
    session.refresh(user)

    return user.model_dump()
