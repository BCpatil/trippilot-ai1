from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trippilot.auth.router import router as auth_router
from trippilot.bookings.router import router as bookings_router
from trippilot.core.config import get_settings
from trippilot.customers.router import router as customers_router
from trippilot.dashboard.router import router as dashboard_router
from trippilot.expenses.router import router as expenses_router
from trippilot.itinerary.router import router as itinerary_router
from trippilot.trips.router import router as trips_router

settings = get_settings()
app = FastAPI(
    title="TripPilot AI API",
    description="Travel operations API for the TripPilot AI platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Organization-ID"],
)
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(trips_router)
app.include_router(itinerary_router)
app.include_router(bookings_router)
app.include_router(expenses_router)
app.include_router(dashboard_router)


@app.get("/health/live", tags=["health"])
def live_health() -> dict[str, str]:
    return {"status": "alive"}
