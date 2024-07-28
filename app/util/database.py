import logging

# Create the database
from alembic import script
from alembic.runtime import migration
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.util.settings import Settings

DATABASE_URL = Settings().database.url
logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    # echo=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

if "sqlite:///:memory:" in DATABASE_URL:
    SQLModel.metadata.create_all(engine)
    logger.info("Tables created in SQLite in-memory database.")


def init_db():
    return


def get_session():
    with Session(engine) as session:
        yield session


def check_current_head(alembic_cfg, connectable):
    # type: (config.Config, engine.Engine) -> bool
    # cfg = config.Config("../alembic.ini")
    directory = script.ScriptDirectory.from_config(alembic_cfg)
    with connectable.begin() as connection:
        context = migration.MigrationContext.configure(connection)
        return set(context.get_current_heads()) == set(directory.get_heads())
