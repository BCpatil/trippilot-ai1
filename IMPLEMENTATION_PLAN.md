# TripPilot AI — Implementation Plan

## Product direction

TripPilot AI is a multi-tenant operations workspace for small and mid-sized travel agencies, tour operators, and corporate travel teams. It helps staff manage customers, trips, manual booking records, budgets, expenses, and itineraries in one place. It is an operations system, not an online travel agency: the MVP will not claim to search live inventory, issue tickets, process payments, or connect to external booking providers.

## 1. Product requirements and MVP scope

### MVP includes
- Organization workspaces with authenticated users and role-based permissions.
- A dashboard with organization-scoped booking and revenue summaries, customer counts, upcoming trips, and useful charts.
- Customer records with search, filtering, detail, and trip history.
- Trips with dates, destination, traveller count, budget, preferences, and lifecycle status.
- Itinerary days and activities that staff can create and edit.
- Manual booking records with supplier/reference details, amounts, dates, and status; create, edit, cancel, and track them.
- Trip budgets and expense records, including category, amount, currency, date, and notes.
- Itinerary generation from the trip's dates, budget, traveller count, destination, and preferences. The first version will use a deterministic planner and a small clearly identified sample content catalog. It will be useful and testable, but will not imply live availability or verified destination advice.
- API documentation, migrations, tests, seed/demo data, error handling, and documented local startup.

### Explicitly out of MVP
- Live flight, hotel, activity, or insurance search/reservations.
- Payment collection, ticket issuance, supplier synchronization, and real-time pricing.
- External generative-AI calls, unless a provider and credentials are intentionally selected later.
- Enterprise SSO, complex approval workflows, mobile apps, and granular custom roles.

### Product success criteria
A new organization can sign in, create and manage customers and trips, record bookings and expenses, generate/edit a draft itinerary, and see correct dashboard totals. A user in one organization cannot read or change another organization's records, including through guessed IDs or modified requests.

## 2. User roles and user journeys

| Role | Intended access |
| --- | --- |
| Owner | Full organization access, membership administration, and all operational data. |
| Admin | Manage members and all operational data; cannot transfer or delete the organization owner. |
| Manager | Manage customers, trips, itineraries, bookings, and expenses; view reports. |
| Agent | Create and update customers, trips, itineraries, and bookings; limited organization settings. |
| Finance | View customers/trips as needed; manage booking financial fields and expenses; view financial reports. |
| Viewer | Read-only access to operational records and dashboard. |

MVP can start with Owner, Admin, Manager, Agent, and Viewer if keeping Finance permissions separate would delay delivery. Enforce permissions on the API, not only by hiding frontend controls.

### Main user journeys
1. An owner registers an organization, signs in, and adds staff by invitation.
2. An agent finds or creates a customer, creates a trip, records dates/budget/preferences, and drafts an itinerary.
3. An agent adds or edits manual booking records and tracks their status; cancellations are recorded rather than silently deleting history.
4. Staff record expenses and compare trip spend against its budget.
5. A manager reviews organization-level KPIs, upcoming trips, booking status, and revenue trends.

## 3. Frontend architecture

- React + TypeScript + Vite, with feature-oriented folders rather than one large application component.
- Tailwind CSS and shadcn/ui primitives for accessible forms, dialogs, menus, tables, and navigation; shared TripPilot components wrap repeated patterns.
- React Router for page navigation; TanStack Query for API requests, caching, loading, and invalidation; React Hook Form + Zod for client-side form ergonomics. The backend remains the source of truth for validation.
- Recharts for dashboard visualizations; charts receive data from organization-scoped API responses rather than hard-coded metrics.
- Suggested layout: `src/app` (routing/providers), `src/features/{dashboard,customers,trips,bookings,expenses,auth}`, `src/components`, `src/lib` (API client and helpers), and `src/types`.
- Use a typed API client, centralized error parsing, and explicit loading, empty, success, and error states. Protect routes for signed-out users, while treating API permissions as authoritative.
- Design direction: deep navy navigation, white working surfaces, restrained teal actions/highlights, clear typography, compact data-dense tables, and consistent spacing. Use responsive navigation and table alternatives on narrow screens; maintain keyboard navigation and visible focus states.

## 4. Backend architecture

- FastAPI application organized by domain: `auth`, `organizations`, `customers`, `trips`, `itineraries`, `bookings`, `expenses`, and `dashboard`.
- Keep API routers thin. Put business rules in service functions, persistence in SQLAlchemy models/repositories as appropriate, and request/response contracts in Pydantic schemas.
- PostgreSQL with SQLAlchemy 2.x; Alembic owns schema migrations. Use decimal/numeric columns for money, explicit currency codes, UTC timestamps, and database constraints for invariants.
- Configuration comes from environment variables, validated at startup. Keep `.env` ignored and provide `.env.example` with placeholders only.
- Consistent error responses for validation, not-found, conflict, authentication, and authorization failures. Add request logging without passwords, tokens, or sensitive customer details.
- Generate OpenAPI docs through FastAPI and document authentication and tenant-scoped behavior.

## 5. Database schema and relationships

Every organization-owned record carries a non-null `organization_id`. Queries and writes are scoped through the authenticated membership's organization context.

- `users`: id, normalized unique email, password hash, name, active state, timestamps.
- `organizations`: id, name, slug, default currency, timestamps.
- `memberships`: id, organization_id, user_id, role, status, timestamps; unique `(organization_id, user_id)`. This supports a user belonging to more than one organization.
- `invitations` (after initial auth slice): organization_id, normalized email, role, hashed/expiring token, invited_by, accepted_at.
- `customers`: organization_id, name, email/phone, notes, created/updated timestamps; organization-scoped uniqueness where appropriate.
- `trips`: organization_id, customer_id, title, destination, start/end dates, traveller count, budget amount/currency, preferences, status, created_by, timestamps. Customer foreign key must also be tenant-safe.
- `itinerary_days`: organization_id, trip_id, date, position, title/notes.
- `itinerary_items`: organization_id, itinerary_day_id, position, title, description, category, start/end time, estimated cost/currency, source label, generation metadata if needed.
- `bookings`: organization_id, trip_id, customer_id, booking type, supplier, external reference (optional/manual), status, booked/travel dates, amount/currency, cancellation timestamp, notes, created/updated timestamps.
- `expenses`: organization_id, trip_id, category, description, amount/currency, incurred date, created_by, timestamps.
- Optional `audit_events`: organization_id, actor_id, action, entity type/id, timestamp, and minimal safe metadata for important status/financial changes.

Relationships: one organization has many memberships and operational records; users join organizations through memberships; a customer has many trips; a trip has itinerary days, bookings, and expenses; an itinerary day has ordered itinerary items. Use foreign keys and, where practical, composite organization-aware keys/constraints so an organization-owned child cannot point at a parent from another organization. Do not cascade-delete financial history by default.

## 6. API endpoint plan

All endpoints are versioned under `/api/v1`. List endpoints use bounded pagination, stable sorting, and validated filters. Organization scope is derived from authenticated membership/context, not trusted from a request body.

### Authentication and organizations
- `POST /auth/register` — create initial user and organization (or defer open registration in favor of seeded owner for demo).
- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
- `GET /organizations/current`, `PATCH /organizations/current`.
- `GET /organizations/current/members`; `POST /organizations/current/invitations`; accept invitation endpoint as a later MVP slice.

### Customers
- `GET /customers` with search and pagination; `POST /customers`.
- `GET /customers/{id}`; `PATCH /customers/{id}`; archive endpoint or status field instead of destructive deletion.

### Trips and itinerary
- `GET /trips` with date/status/customer/search filters; `POST /trips`.
- `GET /trips/{id}`; `PATCH /trips/{id}`; status/archive action.
- `GET /trips/{id}/itinerary`; create/update/delete itinerary day and item endpoints.
- `POST /trips/{id}/itinerary/generate` — validate trip inputs, return a draft proposal, and persist only when explicitly confirmed or saved.

### Bookings and expenses
- `GET /bookings` with trip/status/type/date filters; `POST /bookings`; `GET /bookings/{id}`; `PATCH /bookings/{id}`; `POST /bookings/{id}/cancel`.
- `GET /trips/{id}/expenses`; `POST /trips/{id}/expenses`; `PATCH /expenses/{id}`; delete only where policy permits, otherwise mark void.
- `GET /trips/{id}/budget-summary` — budget, booked amount, expenses, and remaining amount with currency-aware rules.

### Dashboard and operations
- `GET /dashboard/summary` — organization-scoped KPIs and date range.
- `GET /dashboard/revenue` and `/dashboard/booking-status` — grouped chart data with explicit definitions and date range.
- `GET /health/live` and `/health/ready` for process and dependency health.

## 7. Authentication and multi-tenant security design

- Hash passwords with Argon2id using a maintained library; never store plaintext passwords or return password hashes.
- For a browser app, prefer short-lived access credentials in Secure, HttpOnly, SameSite cookies and add CSRF protection for state-changing requests. Configure local development separately (HTTPS is required for Secure cookies outside localhost). Avoid storing long-lived bearer tokens in local storage.
- Authenticate the user, resolve an active organization membership, and pass a server-created organization context into service/repository functions. For users with multiple organizations, expose an explicit organization switch that validates membership before changing context.
- Apply organization filters to every list, detail, update, delete, aggregate, and background task. Do not use client-provided `organization_id` as authorization. Return 404 for inaccessible tenant-owned IDs where that avoids resource enumeration.
- Centralize role checks and enforce them at endpoints/service boundaries. Validate ownership of related customer/trip/day IDs on every write.
- Add tenant-aware foreign-key/unique constraints where feasible, rate-limit login/invitation paths, use generic login errors, and audit sensitive changes without logging secrets.
- Security tests must prove cross-organization reads, updates, deletes, aggregates, and mismatched parent-child references are rejected.

## 8. UI page list and design system

1. Sign in / create organization, plus invitation acceptance.
2. Dashboard: KPI strip, bookings/revenue charts, upcoming trips, and actionable status lists.
3. Customers: searchable/filterable table, create/edit form, and customer detail with trips.
4. Trips: list/calendar-style upcoming view, create/edit form, and trip detail workspace.
5. Trip detail tabs: overview, itinerary, bookings, and budget/expenses.
6. Itinerary editor: ordered day sections, editable activities, generation inputs/result review, and save state.
7. Bookings: filtered operational table and create/edit/cancel flow.
8. Expenses: trip-scoped records and budget summary.
9. Organization settings and member management (incremental, permission-gated).

Design tokens should define navy, teal, neutrals, semantic status colors, typography, spacing, borders, and focus rings centrally. Reuse page headers, form fields, status badges, empty states, confirmation dialogs, data tables, and toast/error patterns. Use realistic fictional seed data with clearly fictional names and no real personal information. Every major page must have loading, empty, success, and recoverable error states; destructive or irreversible actions require confirmation.

## 9. Testing strategy

- Backend unit tests for status transitions, budget calculations, itinerary constraints, and role policy.
- FastAPI integration tests for validation, pagination/filtering, auth, and CRUD using a dedicated test PostgreSQL database where practical.
- Security regression tests with two organizations and users covering all tenant boundaries, aggregates, and related-record assignments.
- Migration checks: upgrade from empty database and verify schema; include downgrade review for each migration.
- Frontend tests with Vitest + React Testing Library for forms, loading/error/empty states, route access, and important user interactions.
- End-to-end smoke test with Playwright for sign-in, create customer/trip, add booking/expense, dashboard visibility, and tenant isolation if test setup supports two accounts.
- CI should run lint, typecheck, backend tests, frontend tests, and migration checks. Keep demo seeds deterministic and separate from production startup.

## 10. Local deployment strategy

- Docker Compose for PostgreSQL and application services; bind-mount source for a convenient development loop, with health checks and a named database volume.
- `.env.example` documents required values. Local secrets stay in ignored `.env`; generate a distinct development secret and never commit it.
- Backend startup waits for database readiness and runs migrations through an explicit command/task, not an unsafe hidden production side effect. Provide a seed command for fictional demo data.
- Frontend Vite dev server proxies `/api` to FastAPI; document URLs for the app, API, and Swagger docs. Also provide a containerized production-style build path once the MVP works.
- Document database reset as a clearly destructive, opt-in developer command. Do not use it automatically in startup scripts.
- Deployment beyond local development will require HTTPS, managed secret storage, backups, monitoring, and a reviewed migration/rollback process; do not present a local Compose file as production-ready by itself.

## 11. Phased implementation checklist

### Phase 0 — Foundation
- [x] Confirm this architecture and MVP boundary.
- [x] Scaffold separate `frontend/` and `backend/` projects, Git ignore rules, formatting/linting, and environment examples.
- [x] Add Compose PostgreSQL, health checks, and a minimal documented local startup.

### Phase 1 — Backend foundations and tenant security
- [x] Add FastAPI configuration, SQLAlchemy session management, Alembic, and a liveness endpoint.
- [x] Implement user, organization, membership models and initial migration.
- [x] Implement Argon2 password hashing, CSRF-protected login/logout, short-lived sessions, membership context, and role policy.
- [x] Add two-tenant authentication-context tests; extend boundary coverage to each operational resource as those endpoints are built.

### Phase 2 — Core operations
- [x] Implement customers and trips with schemas, services, scoped queries, migrations, and tests.
- [x] Implement itinerary day/item editing and validation.
- [x] Implement manual booking lifecycle and cancellation history.
- [x] Implement expenses and currency-aware budget summaries.

### Phase 3 — Frontend shell and workflows
- [x] Establish tokens, responsive application shell, navigation, form/table patterns, and API client.
- [x] Build sign-in and organization context handling.
- [x] Build customer and trip list/create/edit workflows.
- [ ] Build itinerary editor and manual booking/expense workflows with all UI states.

### Phase 4 — Dashboard and itinerary generation
- [x] Add scoped dashboard aggregation endpoints and tests.
- [x] Build KPI, chart, and upcoming-trip views using real API data.
- [ ] Implement deterministic itinerary proposal generation with explicit constraints, sample catalog attribution, and user review before save.

### Phase 5 — Quality and delivery
- [ ] Add fictional demo seed data and a guided smoke-test workflow.
- [ ] Add frontend tests and end-to-end happy-path/tenant regression coverage.
- [ ] Add CI for lint, types, tests, and migrations.
- [ ] Finish setup, API, architecture, security, troubleshooting, and deployment documentation.
- [ ] Review accessibility, responsive layouts, authorization matrix, and claims about integrations before release.

## Recommended build order

Prioritize a narrow vertical slice: local database and migrations, authentication plus organization isolation, then customer/trip creation from UI through API to database. This validates the architecture early. Add the remaining domains one at a time, then dashboard aggregation and itinerary generation. That order keeps the project teachable and ensures the security boundary is in place before operational features multiply.
