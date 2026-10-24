from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from trippilot.auth.dependencies import get_current_membership
from trippilot.bookings.schemas import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    PaginatedBookingsResponse,
)
from trippilot.db.session import get_db
from trippilot.models import Booking, Customer, Membership, Trip

router = APIRouter(prefix="/api/v1", tags=["bookings"])


def get_booking_in_scope(
    booking_id: UUID,
    membership: Membership,
    database: Session,
) -> Booking:
    booking = database.scalar(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.organization_id == membership.organization_id,
        )
    )
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


@router.get("/bookings", response_model=PaginatedBookingsResponse)
def list_bookings(
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> PaginatedBookingsResponse:
    bookings = database.scalars(
        select(Booking)
        .where(Booking.organization_id == membership.organization_id)
        .order_by(Booking.booked_date.desc(), Booking.created_at.desc())
    ).all()
    return PaginatedBookingsResponse(
        items=[BookingResponse.model_validate(booking) for booking in bookings],
        count=len(bookings),
    )


@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> BookingResponse:
    trip = database.scalar(
        select(Trip).where(
            Trip.id == payload.trip_id,
            Trip.organization_id == membership.organization_id,
        )
    )
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    customer = database.scalar(
        select(Customer).where(
            Customer.id == payload.customer_id,
            Customer.organization_id == membership.organization_id,
        )
    )
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    booking = Booking(
        organization_id=membership.organization_id,
        trip_id=payload.trip_id,
        customer_id=payload.customer_id,
        booking_type=payload.booking_type,
        supplier=payload.supplier,
        external_reference=payload.external_reference,
        status=payload.status,
        booked_date=payload.booked_date,
        travel_date=payload.travel_date,
        amount=payload.amount,
        currency=payload.currency,
        notes=payload.notes,
    )
    database.add(booking)
    database.commit()
    database.refresh(booking)
    return BookingResponse.model_validate(booking)


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: UUID,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> BookingResponse:
    return BookingResponse.model_validate(get_booking_in_scope(booking_id, membership, database))


@router.patch("/bookings/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: UUID,
    payload: BookingUpdate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> BookingResponse:
    booking = get_booking_in_scope(booking_id, membership, database)
    updates = payload.model_dump(exclude_unset=True)

    if payload.trip_id is not None:
        trip = database.scalar(
            select(Trip).where(
                Trip.id == payload.trip_id,
                Trip.organization_id == membership.organization_id,
            )
        )
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    if payload.customer_id is not None:
        customer = database.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.organization_id == membership.organization_id,
            )
        )
        if customer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    for field, value in updates.items():
        if value is not None:
            setattr(booking, field, value)

    database.commit()
    database.refresh(booking)
    return BookingResponse.model_validate(booking)
