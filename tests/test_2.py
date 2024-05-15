import pytest  
import sys
import os

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


from app.main import app, get_session



@pytest.fixture(name="session")  
def session_fixture():  
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session  




def test_create_hero(session: Session):  


    def get_session_override():
        return session  



    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)

    response = client.get("/api/")
    assert response.status_code == 200
