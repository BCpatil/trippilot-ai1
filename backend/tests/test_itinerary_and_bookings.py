import uuid
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


def test_itinerary_and_booking_are_scoped_to_organization(client) -> None:
    test_client, test_session = client

    with test_session() as database:
        user = User(email="manager@example.com", full_name="Manager", password_hash="unused")
        org = Organization(name="Northwind Travel", slug="northwind-travel")
        other_org = Organization(name="Other Agency", slug="other-agency")
        database.add_all([user, org, other_org])
        database.flush()
        database.add(Membership(user_id=user.id, organization_id=org.id, role="manager"))
        database.add(Membership(user_id=user.id, organization_id=other_org.id, role="viewer"))

        customer = Customer(
            organization_id=org.id,
            first_name="Jamie",
            last_name="Ng",
            email="jamie@example.com",
            phone="+1-555-0100",
            notes="Prefers window seats",
        )
        database.add(customer)
        database.flush()
        trip = Trip(
            organization_id=org.id,
            customer_id=customer.id,
            created_by=user.id,
            title="Lisbon Family Getaway",
            destination="Lisbon, Portugal",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
            traveler_count=4,
            budget_amount=5200.00,
            currency="USD",
            preferences="Family-friendly hotel",
            status="draft",
        )
        database.add(trip)
        database.commit()
        user_id = user.id
        org_id = org.id
        other_org_id = other_org.id
        trip_id = trip.id

    token = security.create_access_token(str(user_id))
    test_client.cookies.set("trip_pilot_session", token)

    day = test_client.post(
        f"/api/v1/trips/{trip_id}/itinerary/days",
        headers={"X-Organization-ID": str(org_id)},
        json={
            "day_date": "2026-11-10",
            "title": "Arrival Day",
            "notes": "Transfer and check-in",
        },
    )
    assert day.status_code == 201
    day_id = day.json()["id"]

    item = test_client.post(
        f"/api/v1/trips/{trip_id}/itinerary/days/{day_id}/items",
        headers={"X-Organization-ID": str(org_id)},
        json={
            "title": "Hotel check-in",
            "description": "Arrive and settle in",
            "category": "lodging",
            "start_time": "15:00",
            "end_time": "16:00",
            "estimated_cost": 180.00,
            "currency": "USD",
            "source_label": "manual",
        },
    )
    assert item.status_code == 201

    itinerary = test_client.get(
        f"/api/v1/trips/{trip_id}/itinerary",
        headers={"X-Organization-ID": str(org_id)},
    )
    assert itinerary.status_code == 200
    assert itinerary.json()["days"][0]["items"][0]["title"] == "Hotel check-in"

    booking = test_client.post(
        "/api/v1/bookings",
        headers={"X-Organization-ID": str(org_id)},
        json={
            "trip_id": str(trip_id),
            "customer_id": str(test_client.get("/api/v1/customers", headers={"X-Organization-ID": str(org_id)}).json()["items"][0]["id"]),
            "booking_type": "hotel",
            "supplier": "Boutique Lisbon Inn",
            "external_reference": "BLI-1048",
            "status": "confirmed",
            "booked_date": "2026-10-20",
            "travel_date": "2026-11-10",
            "amount": 1180.00,
            "currency": "USD",
            "notes": "Three nights, breakfast included",
        },
    )
    assert booking.status_code == 201

    wrong_org_itinerary = test_client.get(
        f"/api/v1/trips/{trip_id}/itinerary",
        headers={"X-Organization-ID": str(other_org_id)},
    )
    assert wrong_org_itinerary.status_code == 404

    wrong_org_booking = test_client.post(
        "/api/v1/bookings",
        headers={"X-Organization-ID": str(other_org_id)},
        json={
            "trip_id": str(trip_id),
            "customer_id": str(uuid.uuid4()),
            "booking_type": "hotel",
            "supplier": "Other Hotel",
            "status": "confirmed",
            "booked_date": "2026-10-20",
            "travel_date": "2026-11-10",
            "amount": 200.0,
            "currency": "USD",
        },
    )
    assert wrong_org_booking.status_code == 404
