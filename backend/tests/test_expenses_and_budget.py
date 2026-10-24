from datetime import date

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
from trippilot.models import Customer, Membership, Organization, Trip, User


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


def test_expense_tracking_and_budget_summary_are_scoped_to_organization(client) -> None:
    test_client, test_session = client

    with test_session() as database:
        user = User(email="finance@example.com", full_name="Finance", password_hash="unused")
        organization = Organization(name="Northwind Travel", slug="northwind-travel")
        other_org = Organization(name="Other Agency", slug="other-agency")
        database.add_all([user, organization, other_org])
        database.flush()
        database.add(Membership(user_id=user.id, organization_id=organization.id, role="manager"))
        database.add(Membership(user_id=user.id, organization_id=other_org.id, role="viewer"))

        customer = Customer(
            organization_id=organization.id,
            first_name="Jamie",
            last_name="Ng",
            email="jamie@example.com",
        )
        database.add(customer)
        database.flush()

        trip = Trip(
            organization_id=organization.id,
            customer_id=customer.id,
            created_by=user.id,
            title="Lisbon Family Getaway",
            destination="Lisbon, Portugal",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
            traveler_count=4,
            budget_amount=5200.00,
            currency="USD",
            preferences="Hotel + transfers",
            status="draft",
        )
        database.add(trip)
        database.flush()
        database.commit()
        user_id = user.id
        org_id = organization.id
        other_org_id = other_org.id
        trip_id = trip.id

    token = security.create_access_token(str(user_id))
    test_client.cookies.set("trip_pilot_session", token)

    create_expense = test_client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        headers={"X-Organization-ID": str(org_id)},
        json={
            "category": "lodging",
            "description": "Hotel three nights",
            "amount": 1180.00,
            "currency": "USD",
            "incurred_date": "2026-11-11",
            "notes": "Paid in full",
        },
    )
    assert create_expense.status_code == 201

    summary = test_client.get(
        f"/api/v1/trips/{trip_id}/budget-summary",
        headers={"X-Organization-ID": str(org_id)},
    )
    assert summary.status_code == 200
    assert summary.json()["budget_amount"] == 5200.0
    assert summary.json()["expenses_total"] == 1180.0
    assert summary.json()["remaining_amount"] == 4020.0

    wrong_org_summary = test_client.get(
        f"/api/v1/trips/{trip_id}/budget-summary",
        headers={"X-Organization-ID": str(other_org_id)},
    )
    assert wrong_org_summary.status_code == 404

    wrong_org_expense = test_client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        headers={"X-Organization-ID": str(other_org_id)},
        json={
            "category": "meals",
            "description": "Wrong org expense",
            "amount": 25.00,
            "currency": "USD",
            "incurred_date": "2026-11-12",
        },
    )
    assert wrong_org_expense.status_code == 404
