from datetime import date, timedelta
from decimal import Decimal

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
from trippilot.models import Booking, Customer, Membership, Organization, Trip, User


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


def test_dashboard_aggregates_are_date_filtered_and_organization_scoped(client) -> None:
    test_client, test_session = client
    today = date.today()
    report_start = today - timedelta(days=10)
    report_end = today

    with test_session() as database:
        user = User(email="dashboard@example.com", full_name="Dashboard", password_hash="unused")
        organization = Organization(name="Northwind Travel", slug="northwind-travel")
        other_org = Organization(name="Other Agency", slug="other-agency")
        database.add_all([user, organization, other_org])
        database.flush()
        database.add_all(
            [
                Membership(user_id=user.id, organization_id=organization.id, role="manager"),
                Membership(user_id=user.id, organization_id=other_org.id, role="viewer"),
            ]
        )
        customer = Customer(
            organization_id=organization.id,
            first_name="Jamie",
            last_name="Ng",
            email="jamie@example.com",
        )
        other_customer = Customer(
            organization_id=other_org.id,
            first_name="Taylor",
            last_name="Reed",
            email="taylor@example.com",
        )
        database.add_all([customer, other_customer])
        database.flush()
        trip = Trip(
            organization_id=organization.id,
            customer_id=customer.id,
            created_by=user.id,
            title="Lisbon trip",
            destination="Lisbon",
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=10),
            traveler_count=2,
            budget_amount=Decimal("2000.00"),
            currency="USD",
            status="confirmed",
        )
        other_trip = Trip(
            organization_id=other_org.id,
            customer_id=other_customer.id,
            created_by=user.id,
            title="Tokyo trip",
            destination="Tokyo",
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=10),
            traveler_count=1,
            budget_amount=Decimal("3000.00"),
            currency="USD",
            status="confirmed",
        )
        database.add_all([trip, other_trip])
        database.flush()
        bookings = [
            Booking(
                organization_id=organization.id,
                trip_id=trip.id,
                customer_id=customer.id,
                booking_type="hotel",
                supplier="Harbor Hotel",
                status="confirmed",
                booked_date=today - timedelta(days=2),
                amount=Decimal("100.00"),
                currency="USD",
            ),
            Booking(
                organization_id=organization.id,
                trip_id=trip.id,
                customer_id=customer.id,
                booking_type="transfer",
                supplier="City Transfers",
                status="tentative",
                booked_date=today - timedelta(days=2),
                amount=Decimal("200.00"),
                currency="EUR",
            ),
            Booking(
                organization_id=organization.id,
                trip_id=trip.id,
                customer_id=customer.id,
                booking_type="activity",
                supplier="River Tours",
                status="cancelled",
                booked_date=today - timedelta(days=1),
                amount=Decimal("50.00"),
                currency="USD",
            ),
            Booking(
                organization_id=other_org.id,
                trip_id=other_trip.id,
                customer_id=other_customer.id,
                booking_type="flight",
                supplier="Other Air",
                status="confirmed",
                booked_date=today - timedelta(days=2),
                amount=Decimal("900.00"),
                currency="USD",
            ),
        ]
        database.add_all(bookings)
        database.commit()
        user_id = user.id
        organization_id = organization.id

    test_client.cookies.set("trip_pilot_session", security.create_access_token(str(user_id)))
    query = f"?start_date={report_start.isoformat()}&end_date={report_end.isoformat()}"
    headers = {"X-Organization-ID": str(organization_id)}

    summary = test_client.get(f"/api/v1/dashboard/summary{query}", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["active_customer_count"] == 1
    assert summary.json()["upcoming_trip_count"] == 1
    assert summary.json()["booking_count"] == 2
    assert summary.json()["booking_value_by_currency"] == [
        {"currency": "EUR", "amount": "200.00"},
        {"currency": "USD", "amount": "100.00"},
    ]

    revenue = test_client.get(f"/api/v1/dashboard/revenue{query}", headers=headers)
    assert revenue.status_code == 200
    assert revenue.json()["items"] == [
        {
            "booked_date": (today - timedelta(days=2)).isoformat(),
            "currency": "EUR",
            "booking_count": 1,
            "booking_value": "200.00",
        },
        {
            "booked_date": (today - timedelta(days=2)).isoformat(),
            "currency": "USD",
            "booking_count": 1,
            "booking_value": "100.00",
        },
    ]

    statuses = test_client.get(f"/api/v1/dashboard/booking-status{query}", headers=headers)
    assert statuses.status_code == 200
    assert statuses.json()["items"] == [
        {"status": "draft", "count": 0},
        {"status": "confirmed", "count": 1},
        {"status": "tentative", "count": 1},
        {"status": "cancelled", "count": 1},
    ]


def test_dashboard_rejects_reversed_date_range(client) -> None:
    test_client, test_session = client
    with test_session() as database:
        user = User(email="range@example.com", full_name="Range", password_hash="unused")
        organization = Organization(name="Range Agency", slug="range-agency")
        database.add_all([user, organization])
        database.flush()
        database.add(Membership(user_id=user.id, organization_id=organization.id, role="viewer"))
        database.commit()
        user_id = user.id
        organization_id = organization.id

    test_client.cookies.set("trip_pilot_session", security.create_access_token(str(user_id)))
    response = test_client.get(
        "/api/v1/dashboard/summary?start_date=2026-10-23&end_date=2026-10-01",
        headers={"X-Organization-ID": str(organization_id)},
    )
    assert response.status_code == 422