import boto3

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import HTMLResponse

from pydantic import validator, error_wrappers

from typing import Optional
from models.user import PublicContact
from models.info import InfoModel

from util.authentication import Authentication
from util.errors import Errors
from util.options import Options
from util.kennelish import Kennelish, Transformer

options = Options.fetch()

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses=Errors.basic_http()
)


"""
Renders the Admin home page.
"""
@router.get("/")
@Authentication.admin
async def admin(request: Request, token: Optional[str] = Cookie(None)):
    return "admin w00t"

