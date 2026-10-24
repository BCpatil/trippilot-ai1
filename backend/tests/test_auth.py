import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from trippilot.auth import router as auth_router_module
from trippilot.auth import security
from trippilot.auth.dependencies import get_db
from trippilot.core.config import Settings
from trippilot.db.base import Base
from trippilot.main import app
from trippilot.models import Membership, Organization, User


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    test_settings = Settings(auth_secret="test-only-secret-value-with-at-least-32-chars")

    def override_get_db():
        database = test_session()
        try:
            yield database
        finally:
            database.close()

    monkeypatch.setattr(security, "get_settings", lambda: test_settings)
    monkeypatch.setattr(auth_router_module, "get_settings", lambda: test_settings)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, test_session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def get_csrf(client: TestClient) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_registration_creates_owner_and_issues_httponly_session(client) -> None:
    test_client, test_session = client
    csrf_token = get_csrf(test_client)

    response = test_client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "  ALEX@EXAMPLE.COM ",
            "full_name": " Alex Morgan ",
            "organization_name": "Northwind Travel",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "registered"
    assert "httponly" in response.headers["set-cookie"].lower()
    with test_session() as database:
        user = database.query(User).one()
        membership = database.query(Membership).one()
        assert user.email == "alex@example.com"
        assert user.password_hash != "correct-horse-battery-staple"
        assert membership.role == "owner"
    me_response = test_client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["organization_name"] == "Northwind Travel"


def test_registration_rejects_missing_csrf_header(client) -> None:
    test_client, test_session = client
    csrf_token = get_csrf(test_client)

    response = test_client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": "not-the-cookie-value"},
        json={
            "email": "alex@example.com",
            "full_name": "Alex Morgan",
            "organization_name": "Northwind Travel",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 403
    assert csrf_token != response.request.headers.get("X-CSRF-Token")
    with test_session() as database:
        assert database.query(User).count() == 0


def test_user_cannot_select_another_organizations_context(client) -> None:
    test_client, test_session = client
    with test_session() as database:
        user = User(email="agent@example.com", full_name="Agent", password_hash="unused")
        own_organization = Organization(name="Own Agency", slug="own-agency")
        foreign_organization = Organization(name="Other Agency", slug="other-agency")
        database.add_all([user, own_organization, foreign_organization])
        database.flush()
        database.add(Membership(user_id=user.id, organization_id=own_organization.id, role="agent"))
        database.commit()
        user_id = user.id
        foreign_organization_id = foreign_organization.id

    token = security.create_access_token(str(user_id))
    test_client.cookies.set("trip_pilot_session", token)
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"X-Organization-ID": str(foreign_organization_id)},
    )

    assert response.status_code == 404


def test_user_can_list_only_their_organization_memberships(client) -> None:
    test_client, test_session = client
    with test_session() as database:
        user = User(email="member@example.com", full_name="Member", password_hash="unused")
        member_organization = Organization(name="Member Agency", slug="member-agency")
        other_organization = Organization(name="Other Agency", slug="other-agency")
        database.add_all([user, member_organization, other_organization])
        database.flush()
        database.add(
            Membership(
                user_id=user.id,
                organization_id=member_organization.id,
                role="manager",
            )
        )
        database.commit()
        user_id = user.id
        expected_id = str(member_organization.id)

    test_client.cookies.set("trip_pilot_session", security.create_access_token(str(user_id)))
    response = test_client.get("/api/v1/auth/organizations")

    assert response.status_code == 200
    assert response.json() == [
        {
            "organization_id": expected_id,
            "organization_name": "Member Agency",
            "role": "manager",
        }
    ]


def test_login_and_logout_require_valid_csrf(client) -> None:
    test_client, _ = client
    csrf_token = get_csrf(test_client)
    register_response = test_client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "agent@example.com",
            "full_name": "Agent",
            "organization_name": "Northwind Travel",
            "password": "correct-horse-battery-staple",
        },
    )
    assert register_response.status_code == 201

    csrf_token = get_csrf(test_client)
    invalid_login = test_client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": "agent@example.com", "password": "incorrect-password"},
    )
    assert invalid_login.status_code == 401

    valid_login = test_client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": "agent@example.com", "password": "correct-horse-battery-staple"},
    )
    assert valid_login.status_code == 200
    assert "trip_pilot_session" in test_client.cookies

    csrf_token = valid_login.json()["csrf_token"]
    logout = test_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout.status_code == 200
    assert test_client.get("/api/v1/auth/me").status_code == 401