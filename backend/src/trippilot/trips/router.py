from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from trippilot.auth.dependencies import get_current_membership, require_csrf
from trippilot.db.session import get_db
from trippilot.models import Customer, Membership, Trip
from trippilot.trips.schemas import PaginatedTripsResponse, TripCreate, TripResponse, TripUpdate

router = APIRouter(prefix="/api/v1", tags=["trips"])


@router.get("/trips", response_model=PaginatedTripsResponse)
def list_trips(
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> PaginatedTripsResponse:
    trips = database.scalars(
        select(Trip)
        .where(Trip.organization_id == membership.organization_id)
        .order_by(Trip.start_date.desc())
    ).all()
    return PaginatedTripsResponse(
        items=[TripResponse.model_validate(trip) for trip in trips],
        count=len(trips),
    )


@router.post(
    "/trips",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_trip(
    payload: TripCreate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> TripResponse:
    customer = database.get(Customer, payload.customer_id)
    if customer is None or customer.organization_id != membership.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    trip = Trip(
        organization_id=membership.organization_id,
        customer_id=payload.customer_id,
        created_by=membership.user_id,
        title=payload.title,
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        traveler_count=payload.traveler_count,
        budget_amount=payload.budget_amount,
        currency=payload.currency,
        preferences=payload.preferences,
        status=payload.status,
    )
    database.add(trip)
    database.commit()
    database.refresh(trip)
    return TripResponse.model_validate(trip)


@router.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: UUID,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> TripResponse:
    trip = database.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.organization_id == membership.organization_id,
        )
    )
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return TripResponse.model_validate(trip)


@router.patch(
    "/trips/{trip_id}",
    response_model=TripResponse,
    dependencies=[Depends(require_csrf)],
)
def update_trip(
    trip_id: UUID,
    payload: TripUpdate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> TripResponse:
    trip = database.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.organization_id == membership.organization_id,
        )
    )
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return TripResponse.model_validate(trip)

    if payload.customer_id is not None:
        customer = database.get(Customer, payload.customer_id)
        if customer is None or customer.organization_id != membership.organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    start_date = updates.get("start_date", trip.start_date)
    end_date = updates.get("end_date", trip.end_date)
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be on or after start_date")

    for field, value in updates.items():
        if value is not None or field == "preferences":
            setattr(trip, field, value)

    database.commit()
    database.refresh(trip)
    return TripResponse.model_validate(trip)
