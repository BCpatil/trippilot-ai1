import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, test_session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_customer_and_trip_are_scoped_to_organization(client) -> None:
    test_client, test_session = client

    with test_session() as database:
        owner = User(email="owner@example.com", full_name="Owner", password_hash="unused")
        organization = Organization(name="Northwind Travel", slug="northwind-travel")
        other_org = Organization(name="Other Agency", slug="other-agency")
        database.add_all([owner, organization, other_org])
        database.flush()
        database.add(Membership(user_id=owner.id, organization_id=organization.id, role="owner"))
        database.add(Membership(user_id=owner.id, organization_id=other_org.id, role="viewer"))
        database.commit()
        owner_id = owner.id
        org_id = organization.id
        other_org_id = other_org.id

    token = security.create_access_token(str(owner_id))
    test_client.cookies.set("trip_pilot_session", token)
    test_client.cookies.set("trip_pilot_csrf", "test-csrf-token")

    create_customer = test_client.post(
        "/api/v1/customers",
        headers={"X-CSRF-Token": "test-csrf-token", "X-Organization-ID": str(org_id)},
        json={
            "first_name": "Jamie",
            "last_name": "Ng",
            "email": "jamie@example.com",
            "phone": "+1-555-0100",
            "notes": "VIP travel preferences",
        },
    )
    assert create_customer.status_code == 201
    customer_id = create_customer.json()["id"]

    clear_customer_fields = test_client.patch(
        f"/api/v1/customers/{customer_id}",
        headers={"X-CSRF-Token": "test-csrf-token", "X-Organization-ID": str(org_id)},
        json={"email": None, "phone": None, "notes": None},
    )
    assert clear_customer_fields.status_code == 200
    assert clear_customer_fields.json()["email"] is None
    assert clear_customer_fields.json()["phone"] is None
    assert clear_customer_fields.json()["notes"] is None

    list_customers = test_client.get("/api/v1/customers", headers={"X-Organization-ID": str(org_id)})
    assert list_customers.status_code == 200
    assert len(list_customers.json()["items"]) == 1

    create_trip = test_client.post(
        "/api/v1/trips",
        headers={"X-CSRF-Token": "test-csrf-token", "X-Organization-ID": str(org_id)},
        json={
            "customer_id": customer_id,
            "title": "Lisbon Family Getaway",
            "destination": "Lisbon, Portugal",
            "start_date": "2026-11-10",
            "end_date": "2026-11-16",
            "traveler_count": 4,
            "budget_amount": 5200.0,
            "currency": "USD",
            "preferences": "Family-friendly hotel and easy airport transfer",
        },
    )
    assert create_trip.status_code == 201
    trip_id = create_trip.json()["id"]

    clear_trip_preferences = test_client.patch(
        f"/api/v1/trips/{trip_id}",
        headers={"X-CSRF-Token": "test-csrf-token", "X-Organization-ID": str(org_id)},
        json={"preferences": None},
    )
    assert clear_trip_preferences.status_code == 200
    assert clear_trip_preferences.json()["preferences"] is None

    unauthorized_trip = test_client.get(
        f"/api/v1/trips/{trip_id}",
        headers={"X-Organization-ID": str(other_org_id)},
    )
    assert unauthorized_trip.status_code == 404

    unauthorized_customer = test_client.get(
        f"/api/v1/customers/{customer_id}",
        headers={"X-Organization-ID": str(other_org_id)},
    )
    assert unauthorized_customer.status_code == 404


def test_customer_create_requires_valid_organization_context(client) -> None:
    test_client, test_session = client

    with test_session() as database:
        user = User(email="agent@example.com", full_name="Agent", password_hash="unused")
        organization = Organization(name="Northwind Travel", slug="northwind-travel")
        database.add_all([user, organization])
        database.flush()
        database.add(Membership(user_id=user.id, organization_id=organization.id, role="agent"))
        database.commit()
        user_id = user.id

    token = security.create_access_token(str(user_id))
    test_client.cookies.set("trip_pilot_session", token)
    test_client.cookies.set("trip_pilot_csrf", "test-csrf-token")

    response = test_client.post(
        "/api/v1/customers",
        headers={"X-CSRF-Token": "test-csrf-token", "X-Organization-ID": str(uuid.uuid4())},
        json={
            "first_name": "Morgan",
            "last_name": "Lee",
            "email": "morgan@example.com",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"
