# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import UserModel
from app.routes.infra import ERR_VPN_CONFIG_NOT_FOUND
from app.util.auth_dependencies import Authentication


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


def _second_user(session: Session) -> UserModel:
    # A returning member who signed in with a *different* Discord account and
    # therefore got a fresh, empty row. Submitting the form with the details
    # from their original account collides on the unique columns.
    other = UserModel(discord_id="999999999999999999", infra_email="")
    session.add(other)
    session.commit()
    return other


def _form_body(**overrides):
    body = {
        "first_name": "Test",
        "surname": "User",
        "email": "new_email@example.com",
        "ucf_student": "Yes",
        "nid": "zz999999",
    }
    body.update(overrides)
    return body


def test_duplicate_email_is_a_friendly_422(client: TestClient, session: Session, test_user: UserModel):
    other = _second_user(session)
    jwt = Authentication.create_jwt(other)

    response = client.post("/api/form/2", cookies={"token": jwt}, json=_form_body(email=test_user.email))

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("That email is already registered")
    # The raw SQL (name, email, NID of the other member) must not leak.
    assert "UPDATE usermodel" not in detail
    assert "ko123456" not in detail


def test_duplicate_nid_is_a_friendly_422(client: TestClient, session: Session, test_user: UserModel):
    other = _second_user(session)
    jwt = Authentication.create_jwt(other)

    response = client.post("/api/form/2", cookies={"token": jwt}, json=_form_body(nid=test_user.nid))

    assert response.status_code == 422
    assert response.json()["detail"].startswith("That NID is already registered")

