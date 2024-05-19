# Create the database
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.util.settings import Settings

DATABASE_URL =  Settings().database.url
# TODO remove echo=True
engine = create_engine(
    DATABASE_URL,
    # echo=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
