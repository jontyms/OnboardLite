from fastapi import APIRouter
from fastapi import Query
# from models.user import UserModel
from typing import Optional

#APIRouter creates path operations for user module
router = APIRouter(
    prefix="/users",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)