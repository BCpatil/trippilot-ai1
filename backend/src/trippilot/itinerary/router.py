from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from trippilot.auth.dependencies import get_current_membership
from trippilot.db.session import get_db
from trippilot.itinerary.schemas import (
    ItineraryDayCreate,
    ItineraryDayResponse,
    ItineraryDayUpdate,
    ItineraryItemCreate,
    ItineraryItemResponse,
    ItineraryItemUpdate,
    ItineraryResponse,
)
from trippilot.models import ItineraryDay, ItineraryItem, Membership, Trip

router = APIRouter(prefix="/api/v1", tags=["itinerary"])


def get_trip_in_scope(
    trip_id: UUID,
    membership: Membership,
    database: Session,
) -> Trip:
    trip = database.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.organization_id == membership.organization_id,
        )
    )
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


@router.get("/trips/{trip_id}/itinerary", response_model=ItineraryResponse)
def get_trip_itinerary(
    trip_id: UUID,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> ItineraryResponse:
    get_trip_in_scope(trip_id, membership, database)
    days = database.scalars(
        select(ItineraryDay)
        .where(
            ItineraryDay.trip_id == trip_id,
            ItineraryDay.organization_id == membership.organization_id,
        )
        .order_by(ItineraryDay.day_date, ItineraryDay.position)
    ).all()

    result_days: list[ItineraryDayResponse] = []
    for day in days:
        items = database.scalars(
            select(ItineraryItem)
            .where(
                ItineraryItem.itinerary_day_id == day.id,
                ItineraryItem.organization_id == membership.organization_id,
            )
            .order_by(ItineraryItem.position)
        ).all()
        result_days.append(
            ItineraryDayResponse(
                id=day.id,
                trip_id=day.trip_id,
                organization_id=day.organization_id,
                day_date=day.day_date,
                title=day.title,
                notes=day.notes,
                position=day.position,
                created_at=day.created_at,
                updated_at=day.updated_at,
                items=[
                    ItineraryItemResponse(
                        id=item.id,
                        itinerary_day_id=item.itinerary_day_id,
                        organization_id=item.organization_id,
                        title=item.title,
                        description=item.description,
                        category=item.category,
                        start_time=item.start_time,
                        end_time=item.end_time,
                        position=item.position,
                        estimated_cost=item.estimated_cost,
                        currency=item.currency,
                        source_label=item.source_label,
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                    )
                    for item in items
                ],
            )
        )
    return ItineraryResponse(days=result_days)


@router.post("/trips/{trip_id}/itinerary/days", response_model=ItineraryDayResponse, status_code=status.HTTP_201_CREATED)
def create_itinerary_day(
    trip_id: UUID,
    payload: ItineraryDayCreate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> ItineraryDayResponse:
    get_trip_in_scope(trip_id, membership, database)
    day = ItineraryDay(
        organization_id=membership.organization_id,
        trip_id=trip_id,
        day_date=payload.day_date,
        title=payload.title,
        notes=payload.notes,
        position=(
            database.scalar(
                select(ItineraryDay.position)
                .where(ItineraryDay.trip_id == trip_id, ItineraryDay.organization_id == membership.organization_id)
                .order_by(ItineraryDay.position.desc())
                .limit(1)
            )
            or -1
        )
        + 1,
    )
    database.add(day)
    database.commit()
    database.refresh(day)
    return ItineraryDayResponse(
        id=day.id,
        trip_id=day.trip_id,
        organization_id=day.organization_id,
        day_date=day.day_date,
        title=day.title,
        notes=day.notes,
        position=day.position,
        created_at=day.created_at,
        updated_at=day.updated_at,
        items=[],
    )


@router.patch("/trips/{trip_id}/itinerary/days/{day_id}", response_model=ItineraryDayResponse)
def update_itinerary_day(
    trip_id: UUID,
    day_id: UUID,
    payload: ItineraryDayUpdate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> ItineraryDayResponse:
    get_trip_in_scope(trip_id, membership, database)
    day = database.scalar(
        select(ItineraryDay).where(
            ItineraryDay.id == day_id,
            ItineraryDay.trip_id == trip_id,
            ItineraryDay.organization_id == membership.organization_id,
        )
    )
    if day is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is not None:
            setattr(day, field, value)
    database.commit()
    database.refresh(day)

    items = database.scalars(
        select(ItineraryItem)
        .where(
            ItineraryItem.itinerary_day_id == day.id,
            ItineraryItem.organization_id == membership.organization_id,
        )
        .order_by(ItineraryItem.position)
    ).all()
    return ItineraryDayResponse(
        id=day.id,
        trip_id=day.trip_id,
        organization_id=day.organization_id,
        day_date=day.day_date,
        title=day.title,
        notes=day.notes,
        position=day.position,
        created_at=day.created_at,
        updated_at=day.updated_at,
        items=[
            ItineraryItemResponse(
                id=item.id,
                itinerary_day_id=item.itinerary_day_id,
                organization_id=item.organization_id,
                title=item.title,
                description=item.description,
                category=item.category,
                start_time=item.start_time,
                end_time=item.end_time,
                position=item.position,
                estimated_cost=item.estimated_cost,
                currency=item.currency,
                source_label=item.source_label,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ],
    )


@router.post(
    "/trips/{trip_id}/itinerary/days/{day_id}/items",
    response_model=ItineraryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_itinerary_item(
    trip_id: UUID,
    day_id: UUID,
    payload: ItineraryItemCreate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> ItineraryItemResponse:
    get_trip_in_scope(trip_id, membership, database)
    day = database.scalar(
        select(ItineraryDay).where(
            ItineraryDay.id == day_id,
            ItineraryDay.trip_id == trip_id,
            ItineraryDay.organization_id == membership.organization_id,
        )
    )
    if day is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")

    item = ItineraryItem(
        organization_id=membership.organization_id,
        itinerary_day_id=day.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        start_time=payload.start_time,
        end_time=payload.end_time,
        position=(
            database.scalar(
                select(ItineraryItem.position)
                .where(
                    ItineraryItem.itinerary_day_id == day.id,
                    ItineraryItem.organization_id == membership.organization_id,
                )
                .order_by(ItineraryItem.position.desc())
                .limit(1)
            )
            or -1
        )
        + 1,
        estimated_cost=payload.estimated_cost,
        currency=payload.currency,
        source_label=payload.source_label,
    )
    database.add(item)
    database.commit()
    database.refresh(item)
    return ItineraryItemResponse(
        id=item.id,
        itinerary_day_id=item.itinerary_day_id,
        organization_id=item.organization_id,
        title=item.title,
        description=item.description,
        category=item.category,
        start_time=item.start_time,
        end_time=item.end_time,
        position=item.position,
        estimated_cost=item.estimated_cost,
        currency=item.currency,
        source_label=item.source_label,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.patch("/trips/{trip_id}/itinerary/days/{day_id}/items/{item_id}", response_model=ItineraryItemResponse)
def update_itinerary_item(
    trip_id: UUID,
    day_id: UUID,
    item_id: UUID,
    payload: ItineraryItemUpdate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> ItineraryItemResponse:
    get_trip_in_scope(trip_id, membership, database)
    day = database.scalar(
        select(ItineraryDay).where(
            ItineraryDay.id == day_id,
            ItineraryDay.trip_id == trip_id,
            ItineraryDay.organization_id == membership.organization_id,
        )
    )
    if day is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")
    item = database.scalar(
        select(ItineraryItem).where(
            ItineraryItem.id == item_id,
            ItineraryItem.itinerary_day_id == day.id,
            ItineraryItem.organization_id == membership.organization_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary item not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is not None:
            setattr(item, field, value)
    database.commit()
    database.refresh(item)
    return ItineraryItemResponse(
        id=item.id,
        itinerary_day_id=item.itinerary_day_id,
        organization_id=item.organization_id,
        title=item.title,
        description=item.description,
        category=item.category,
        start_time=item.start_time,
        end_time=item.end_time,
        position=item.position,
        estimated_cost=item.estimated_cost,
        currency=item.currency,
        source_label=item.source_label,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
