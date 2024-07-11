from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import UserModel


# jwt: str
@patch("app.util.approve.Approve.approve_member", return_value=None)
def test_profile(mock_approve, client: TestClient, jwt: str):
    response = client.get("/profile/", cookies={"token": jwt})
    # response = client.get("/profile")
    assert response.status_code == 200
    assert "test_user@example.com" in response.text


def test_openvpn(client: TestClient, jwt: str):
    response = client.get("/infra/openvpn/", cookies={"token": jwt})
    assert response.status_code == 200


def test_db(client: TestClient, session: Session, jwt: str):
    user_in_db = session.query(UserModel).filter(UserModel.ucf_id == 123456).first()
    assert user_in_db is not None
    assert user_in_db.email == "test_user@example.com"
