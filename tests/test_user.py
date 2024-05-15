import os
import sys
import pytest
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

# Add the project root to the PYTHONPATH
from app.main import app
from app.util.authentication import Authentication
from app.models.user import UserModel
from app.util.database import get_session

DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, echo=True)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_test_session():
        yield session

    app.dependency_overrides[get_session] = get_test_session
    return TestClient(app)

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    test_user = UserModel(
        id=uuid.uuid4(),
        discord_id="669276074563666347",
        ucf_id=123456,
        nid="jo873101",
        ops_email="ops_test@example.com",
        infra_email="infra_test@example.com",
        minecraft="test_minecraft",
        github="test_github",
        first_name="Test",
        surname="User",
        email="test_user@example.com",
        is_returning=False,
        gender="M",
        major="Computer Science",
        class_standing="Senior",
        shirt_size="M",
        did_get_shirt=False,
        phone_number=1234567890,
        sudo=False,
        did_pay_dues=False,
        mentor_name="Test Mentor",
        is_full_member=False,
        can_vote=False,
        experience=1,
        curiosity="Very curious",
        c3_interest=False,
        attending="Yes",
        comments="Test comments"
    )
    session.add(test_user)
    session.commit()
    return test_user

@pytest.fixture(name="jwt")
def jwt_fixture(test_user: UserModel):
    return Authentication.create_jwt(test_user)



def test_get_profile(client: TestClient, jwt: str):
    response = client.get("/profile/", cookies={"token": jwt})
    assert response.status_code == 200
