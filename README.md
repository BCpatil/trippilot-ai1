# TripPilot AI

TripPilot AI is a travel-operations workspace for travel agencies, tour operators, and corporate travel teams. It brings customer and trip records, itinerary data, manual bookings, expenses, and organization-level reporting into one application.

The project is an actively developed MVP. The FastAPI backend has operational APIs for customers, trips, itineraries, bookings, expenses, and dashboard reporting. The React frontend currently provides sign-in, organization selection, the dashboard, and customer and trip workflows. Booking and expense management, itinerary editing, and itinerary generation are not yet available in the frontend.

TripPilot AI is an operations tool, not an online travel agency. It does not search live travel inventory, issue tickets, process payments, or synchronize with suppliers. Dashboard metrics reflect records entered into this application; they are not live market prices or external booking data.

## Features

- User registration and login with Argon2 password hashing, short-lived session cookies, and CSRF protection.
- Organization memberships and organization-scoped access to business records.
- Customer and trip create, read, and update APIs; the frontend also supports customer and trip workflows.
- Itinerary day and activity APIs.
- Manual booking records and cancellation/status tracking through the API.
- Expense records and trip budget summaries through the API.
- Dashboard summary, booking-value, and booking-status endpoints with a connected dashboard UI.
- PostgreSQL persistence, versioned Alembic migrations, Docker Compose local development, and automated backend/frontend tests.

## Technology

| Area | Technologies |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Recharts, Lucide |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 17 |
| Tests | Pytest, Vitest, React Testing Library |
| Local services | Docker Compose |

## Project layout

```text
backend/
  migrations/         Alembic schema migrations
  src/trippilot/      FastAPI application and domain APIs
  tests/              Backend API and tenant-isolation tests
frontend/
  src/                React application, API client, and UI tests
docker-compose.yml    Local PostgreSQL, API, and frontend services
IMPLEMENTATION_PLAN.md  Product scope, architecture, security design, and roadmap
```

## Run locally with Docker

### Prerequisites

- Docker Desktop with Docker Compose
- Git

### Start the application

1. Clone the repository and move into the project directory.
2. Copy `.env.example` to `.env`.
3. Set `AUTH_SECRET` in `.env` to a generated signing key. For example:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

4. Start the services:

   ```powershell
   docker compose up --build
   ```

5. In a second terminal, apply database migrations:

   ```powershell
   docker compose exec api alembic upgrade head
   ```

6. Open the frontend at <http://localhost:5173>. The API documentation is at <http://localhost:8000/docs>, and the liveness endpoint is <http://localhost:8000/health/live>.

The example database credentials are only for local development. Do not use them for a publicly exposed deployment.

### Run without Docker

Start PostgreSQL separately, then configure `DATABASE_URL` in `.env` (use `localhost` as the database host for a host-run API). From the project root:

```powershell
cd backend
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn trippilot.main:app --reload --app-dir src
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The Vite development server proxies `/api` requests to `http://localhost:8000` by default.

## API overview

The API is versioned under `/api/v1`. Interactive OpenAPI documentation is available at `/docs` when the backend is running.

| Area | Routes |
| --- | --- |
| Authentication | `/auth/csrf`, `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/organizations` |
| Customers | `/customers` and `/customers/{customer_id}` |
| Trips | `/trips` and `/trips/{trip_id}` |
| Itineraries | `/trips/{trip_id}/itinerary` and nested day/activity routes |
| Bookings | `/bookings` and `/bookings/{booking_id}` |
| Expenses | `/trips/{trip_id}/expenses` and nested expense routes |
| Budgets | `/trips/{trip_id}/budget-summary` |
| Dashboard | `/dashboard/summary`, `/dashboard/revenue`, `/dashboard/booking-status` |

Authenticated organization-scoped requests use the `X-Organization-ID` header. Mutating requests also require the CSRF token issued by the authentication API. The backend validates membership and scopes operational records to the authorized organization; a client-provided organization ID is not an authorization grant.

## Tests and quality checks

Run backend tests from `backend/`:

```powershell
python -m pytest
```

Run frontend checks from `frontend/`:

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

Backend tests cover authentication, customer/trip workflows, itinerary and booking APIs, expenses/budgets, dashboard reporting, and organization boundaries. Frontend tests cover sign-in, API-backed dashboard data, and customer/trip workflows.

## Security and deployment notes

- Keep `.env` local; it is excluded from Git. Only commit placeholder configuration such as `.env.example`.
- Generate a unique `AUTH_SECRET` for each environment and store production secrets in a managed secret store.
- Set `SECURE_COOKIES=true` when serving the application behind HTTPS.
- The included Compose configuration is for local development, not production deployment.
- Before deploying, configure HTTPS, production-grade database credentials, backups, monitoring, and a reviewed migration and rollback process.
- This MVP does not include live supplier integrations, payment processing, ticketing, or verified destination guidance.

## Development roadmap

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the detailed product scope, architecture, tenant-security requirements, testing strategy, and phased delivery checklist.
