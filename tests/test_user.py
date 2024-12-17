# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import UserModel
from app.routes.infra import ERR_VPN_CONFIG_NOT_FOUND


# jwt: str
@patch("app.util.approve.Approve.approve_member", return_value=None)
def test_profile(mock_approve, client: TestClient, jwt: str):
    response = client.get("/profile/", cookies={"token": jwt})
    # response = client.get("/profile")
    assert response.status_code == 200
    assert "test_user@example.com" in response.text


def test_openvpn(client: TestClient, jwt: str):
    response = client.get("/infra/openvpn", cookies={"token": jwt})
    assert response.status_code == 500
    assert response.json().get("detail") == ERR_VPN_CONFIG_NOT_FOUND.detail


def test_db(client: TestClient, session: Session, jwt: str):
    user_in_db = session.query(UserModel).filter(UserModel.ucf_id == 123456).first()
    assert user_in_db is not None
    assert user_in_db.email == "test_user@example.com"
