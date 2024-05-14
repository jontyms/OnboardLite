from typing import List, Optional

from pydantic import BaseModel
# Create the database
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine

DATABASE_URL = "sqlite:////app/database/database.db"
# TODO remove echo=True
engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
