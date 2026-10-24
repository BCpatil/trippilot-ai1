import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  Activity,
  CalendarDays,
  ChevronDown,
  CircleHelp,
  Compass,
  LayoutDashboard,
  LogOut,
  MapPin,
  Pencil,
  Plus,
  Search,
  Settings2,
  UsersRound,
  Wallet,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  type Customer,
  type CustomerInput,
  type OrganizationMembership,
  type Trip,
  type TripInput,
} from "./api";

type Period = "7 days" | "30 days";
type Screen = "checking" | "signed-out" | "organization-picker" | "dashboard";
type DashboardData = Awaited<ReturnType<typeof api.dashboard>>;

const bookingStatuses = ["confirmed", "tentative", "draft", "cancelled"];
const statusLabels: Record<string, string> = {
  confirmed: "Confirmed",
  tentative: "Tentative",
  draft: "Draft",
  cancelled: "Cancelled",
};

function formatCurrency(value: number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${Math.round(value).toLocaleString()}`;
  }
}

function formatDate(value: string, options: Intl.DateTimeFormatOptions = {}) {
  return new Intl.DateTimeFormat(undefined, options).format(new Date(`${value}T12:00:00`));
}

function dateRange(period: Period) {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - (period === "7 days" ? 6 : 29));
  const toIso = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };
  return { startDate: toIso(start), endDate: toIso(end) };
}

type CustomerWorkspaceProps = {
  customers: Customer[];
  loading: boolean;
  onSave: (customerId: string | null, payload: CustomerInput) => Promise<void>;
};

function CustomerWorkspace({ customers, loading, onSave }: CustomerWorkspaceProps) {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Customer | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<CustomerInput>({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    notes: "",
  });
  const visibleCustomers = customers.filter((customer) =>
    `${customer.first_name} ${customer.last_name} ${customer.email ?? ""}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );

  function startCreate() {
    setEditing(null);
    setDraft({ first_name: "", last_name: "", email: "", phone: "", notes: "" });
    setError("");
    setShowForm(true);
  }

  function startEdit(customer: Customer) {
    setEditing(customer);
    setDraft({
      first_name: customer.first_name,
      last_name: customer.last_name,
      email: customer.email ?? "",
      phone: customer.phone ?? "",
      notes: customer.notes ?? "",
    });
    setError("");
    setShowForm(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(editing?.id ?? null, {
        ...draft,
        email: draft.email?.trim() || null,
        phone: draft.phone?.trim() || null,
        notes: draft.notes?.trim() || null,
      });
      setShowForm(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Customer could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workspace-page">
      <div className="workspace-page-heading"><div><h2>Customers</h2><p>Manage customer contact records in this organization.</p></div><button className="primary-button compact-button" type="button" onClick={startCreate}><Plus size={15} />New customer</button></div>
      {showForm && <form className="workspace-form" onSubmit={submit}>
        <div className="workspace-form-heading"><h3>{editing ? "Edit customer" : "New customer"}</h3><button type="button" className="icon-command" aria-label="Close customer form" onClick={() => setShowForm(false)}>×</button></div>
        <div className="form-grid"><label>First name<input required maxLength={80} value={draft.first_name} onChange={(event) => setDraft({ ...draft, first_name: event.target.value })} /></label><label>Last name<input required maxLength={80} value={draft.last_name} onChange={(event) => setDraft({ ...draft, last_name: event.target.value })} /></label><label>Email<input type="email" maxLength={320} value={draft.email ?? ""} onChange={(event) => setDraft({ ...draft, email: event.target.value })} /></label><label>Phone<input type="tel" maxLength={40} value={draft.phone ?? ""} onChange={(event) => setDraft({ ...draft, phone: event.target.value })} /></label><label className="form-wide">Notes<textarea maxLength={2000} rows={3} value={draft.notes ?? ""} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} /></label></div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions"><button className="quiet-button" type="button" onClick={() => setShowForm(false)}>Cancel</button><button className="primary-button compact-button" type="submit" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Create customer"}</button></div>
      </form>}
      <section className="panel records-panel">
        <div className="records-toolbar"><label className="search-box"><Search size={15} /><span className="sr-only">Search customers</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name or email" /></label><span>{visibleCustomers.length} customers</span></div>
        <div className="trip-table-wrap"><table><thead><tr><th>CUSTOMER</th><th>EMAIL</th><th>PHONE</th><th>STATUS</th><th aria-label="Actions" /></tr></thead><tbody>{visibleCustomers.map((customer) => <tr key={customer.id}><td><strong>{customer.first_name} {customer.last_name}</strong><span>Customer record</span></td><td>{customer.email || "—"}</td><td>{customer.phone || "—"}</td><td><span className={`trip-status ${customer.is_active ? "green" : "amber"}`}><i />{customer.is_active ? "Active" : "Inactive"}</span></td><td><button type="button" className="icon-command" aria-label={`Edit ${customer.first_name} ${customer.last_name}`} onClick={() => startEdit(customer)}><Pencil size={14} /></button></td></tr>)}</tbody></table>
          {loading && customers.length === 0 && <div className="empty-state" role="status">Loading customers…</div>}
          {!loading && visibleCustomers.length === 0 && <div className="empty-state"><UsersRound size={18} /><strong>{query ? "No matching customers" : "No customers yet"}</strong><span>{query ? "Try a different name or email." : "Create a customer to start organizing trips."}</span></div>}
        </div>
      </section>
    </section>
  );
}

type TripWorkspaceProps = {
  trips: Trip[];
  customers: Customer[];
  loading: boolean;
  onSave: (tripId: string | null, payload: TripInput) => Promise<void>;
};

const emptyTrip: TripInput = {
  customer_id: "",
  title: "",
  destination: "",
  start_date: "",
  end_date: "",
  traveler_count: 1,
  budget_amount: "",
  currency: "USD",
  preferences: "",
  status: "draft",
};

function TripWorkspace({ trips, customers, loading, onSave }: TripWorkspaceProps) {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Trip | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<TripInput>(emptyTrip);
  const customersById = useMemo(() => new Map(customers.map((customer) => [customer.id, customer])), [customers]);
  const visibleTrips = trips.filter((trip) => {
    const customer = customersById.get(trip.customer_id);
    return `${trip.title} ${trip.destination} ${customer?.first_name ?? ""} ${customer?.last_name ?? ""}`
      .toLowerCase()
      .includes(query.trim().toLowerCase());
  });

  function startCreate() {
    setEditing(null);
    setDraft({ ...emptyTrip, customer_id: customers[0]?.id ?? "" });
    setError("");
    setShowForm(true);
  }

  function startEdit(trip: Trip) {
    setEditing(trip);
    setDraft({
      customer_id: trip.customer_id,
      title: trip.title,
      destination: trip.destination,
      start_date: trip.start_date,
      end_date: trip.end_date,
      traveler_count: trip.traveler_count,
      budget_amount: trip.budget_amount,
      currency: trip.currency,
      preferences: trip.preferences ?? "",
      status: trip.status,
    });
    setError("");
    setShowForm(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(editing?.id ?? null, {
        ...draft,
        traveler_count: Number(draft.traveler_count),
        budget_amount: String(draft.budget_amount),
        preferences: draft.preferences?.trim() || null,
        currency: draft.currency.toUpperCase(),
      });
      setShowForm(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Trip could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workspace-page">
      <div className="workspace-page-heading"><div><h2>Trips</h2><p>Plan customer travel and keep key trip details current.</p></div><button className="primary-button compact-button" type="button" onClick={startCreate} disabled={!customers.length}><Plus size={15} />New trip</button></div>
      {showForm && <form className="workspace-form" onSubmit={submit}>
        <div className="workspace-form-heading"><h3>{editing ? "Edit trip" : "New trip"}</h3><button type="button" className="icon-command" aria-label="Close trip form" onClick={() => setShowForm(false)}>×</button></div>
        {!customers.length && <p className="form-error">Create a customer before adding a trip.</p>}
        <div className="form-grid"><label>Customer<select required value={draft.customer_id} onChange={(event) => setDraft({ ...draft, customer_id: event.target.value })}><option value="" disabled>Select a customer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.first_name} {customer.last_name}</option>)}</select></label><label>Trip title<input required maxLength={160} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label><label className="form-wide">Destination<input required maxLength={200} value={draft.destination} onChange={(event) => setDraft({ ...draft, destination: event.target.value })} /></label><label>Start date<input required type="date" value={draft.start_date} onChange={(event) => setDraft({ ...draft, start_date: event.target.value })} /></label><label>End date<input required type="date" min={draft.start_date || undefined} value={draft.end_date} onChange={(event) => setDraft({ ...draft, end_date: event.target.value })} /></label><label>Travelers<input required type="number" min={1} max={200} value={draft.traveler_count} onChange={(event) => setDraft({ ...draft, traveler_count: Number(event.target.value) })} /></label><label>Budget<input required type="number" min="0.01" step="0.01" value={draft.budget_amount} onChange={(event) => setDraft({ ...draft, budget_amount: event.target.value })} /></label><label>Currency<input required minLength={3} maxLength={3} value={draft.currency} onChange={(event) => setDraft({ ...draft, currency: event.target.value.toUpperCase() })} /></label><label>Status<select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="draft">Draft</option><option value="confirmed">Confirmed</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></label><label className="form-wide">Preferences<textarea maxLength={2000} rows={3} value={draft.preferences ?? ""} onChange={(event) => setDraft({ ...draft, preferences: event.target.value })} /></label></div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions"><button className="quiet-button" type="button" onClick={() => setShowForm(false)}>Cancel</button><button className="primary-button compact-button" type="submit" disabled={saving || !customers.length}>{saving ? "Saving…" : editing ? "Save changes" : "Create trip"}</button></div>
      </form>}
      <section className="panel records-panel">
        <div className="records-toolbar"><label className="search-box"><Search size={15} /><span className="sr-only">Search trips</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search title, destination, customer" /></label><span>{visibleTrips.length} trips</span></div>
        <div className="trip-table-wrap"><table><thead><tr><th>TRIP</th><th>DESTINATION</th><th>DATES</th><th>STATUS</th><th aria-label="Actions" /></tr></thead><tbody>{visibleTrips.map((trip) => {
          const customer = customersById.get(trip.customer_id);
          const tone = trip.status === "confirmed" ? "green" : trip.status === "cancelled" ? "amber" : "blue";
          return <tr key={trip.id}><td><strong>{trip.title}</strong><span>{customer ? `${customer.first_name} ${customer.last_name}` : "Customer record"}</span></td><td>{trip.destination}</td><td>{formatDate(trip.start_date, { month: "short", day: "numeric" })} – {formatDate(trip.end_date, { month: "short", day: "numeric", year: "numeric" })}</td><td><span className={`trip-status ${tone}`}><i />{trip.status.replaceAll("_", " ")}</span></td><td><button type="button" className="icon-command" aria-label={`Edit ${trip.title}`} onClick={() => startEdit(trip)}><Pencil size={14} /></button></td></tr>;
        })}</tbody></table>
          {loading && trips.length === 0 && <div className="empty-state" role="status">Loading trips…</div>}
          {!loading && visibleTrips.length === 0 && <div className="empty-state"><Compass size={18} /><strong>{query ? "No matching trips" : "No trips yet"}</strong><span>{query ? "Try another title, destination, or customer." : "Create a trip to start planning a journey."}</span></div>}
        </div>
      </section>
    </section>
  );
}

function App() {
  const [screen, setScreen] = useState<Screen>("checking");
  const [organizations, setOrganizations] = useState<OrganizationMembership[]>([]);
  const [organization, setOrganization] = useState<OrganizationMembership | null>(null);
  const [userName, setUserName] = useState("");
  const [csrfToken, setCsrfToken] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [authError, setAuthError] = useState("");
  const [busy, setBusy] = useState(false);
  const [period, setPeriod] = useState<Period>("30 days");
  const [tripSearch, setTripSearch] = useState("");
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState("");
  const [selectedCurrency, setSelectedCurrency] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [activeView, setActiveView] = useState<"overview" | "trips" | "customers">("overview");

  useEffect(() => {
    let active = true;
    const restoreSession = async () => {
      try {
        const csrf = await api.csrf();
        const memberships = await api.organizations();
        if (!active) return;
        setCsrfToken(csrf.csrf_token);
        setOrganizations(memberships);
        setScreen(memberships.length > 1 ? "organization-picker" : "signed-out");
        if (memberships.length === 1) {
          const membership = memberships[0];
          if (!membership) return;
          const current = await api.currentUser(membership.organization_id);
          if (!active) return;
          setOrganization(membership);
          setUserName(current.full_name);
          setScreen("dashboard");
        }
      } catch {
        if (active) setScreen("signed-out");
      }
    };
    void restoreSession();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (screen !== "dashboard" || !organization) return;
    let active = true;
    const { startDate, endDate } = dateRange(period);
    setDashboardLoading(true);
    setDashboardError("");
    void api
      .dashboard(organization.organization_id, startDate, endDate)
      .then((result) => {
        if (!active) return;
        setDashboard(result);
        const currencies = [...new Set(result.revenue.map((point) => point.currency))];
        setSelectedCurrency((current) =>
          currencies.includes(current) ? current : currencies[0] ?? "",
        );
      })
      .catch((error: unknown) => {
        if (active) {
          setDashboardError(
            error instanceof Error ? error.message : "Dashboard data could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (active) setDashboardLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organization, period, reloadKey, screen]);

  const customersById = useMemo(
    () => new Map(dashboard?.customers.map((customer) => [customer.id, customer]) ?? []),
    [dashboard],
  );
  const filteredTrips = useMemo(() => {
    const query = tripSearch.trim().toLowerCase();
    return (dashboard?.trips ?? [])
      .filter((trip) => trip.start_date >= new Date().toISOString().slice(0, 10))
      .filter((trip) => trip.status !== "cancelled" && trip.status !== "completed")
      .filter((trip) => {
        if (!query) return true;
        const customer = customersById.get(trip.customer_id);
        const customerName = customer ? `${customer.first_name} ${customer.last_name}` : "";
        return `${trip.title} ${trip.destination} ${customerName}`.toLowerCase().includes(query);
      })
      .sort((left, right) => left.start_date.localeCompare(right.start_date))
      .slice(0, 5);
  }, [customersById, dashboard, tripSearch]);
  const chartData = useMemo(() => {
    const points = dashboard?.revenue.filter((point) => point.currency === selectedCurrency) ?? [];
    return points.map((point) => ({
      label: formatDate(point.booked_date, { month: "short", day: "numeric" }),
      revenue: Number(point.booking_value),
      bookings: point.booking_count,
    }));
  }, [dashboard, selectedCurrency]);
  const statusCounts = useMemo(() => {
    const counts = new Map(dashboard?.statuses.map(({ status, count }) => [status, count]) ?? []);
    return bookingStatuses.map((status) => ({ status, count: counts.get(status) ?? 0 }));
  }, [dashboard]);
  const statusTotal = statusCounts.reduce((total, item) => total + item.count, 0);
  const range = dateRange(period);
  const currencies = [...new Set(dashboard?.revenue.map((point) => point.currency) ?? [])];

  async function openWorkspace(membership: OrganizationMembership) {
    setBusy(true);
    setAuthError("");
    setDashboard(null);
    try {
      const current = await api.currentUser(membership.organization_id);
      setOrganization(membership);
      setUserName(current.full_name);
      setActiveView("overview");
      setScreen("dashboard");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Workspace could not be opened.");
    } finally {
      setBusy(false);
    }
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setAuthError("");
    try {
      const csrf = await api.csrf();
      const result =
        authMode === "login"
          ? await api.login(email, password, csrf.csrf_token)
          : await api.register(email, fullName, organizationName, password, csrf.csrf_token);
      setCsrfToken(result.csrf_token);
      const memberships = await api.organizations();
      setOrganizations(memberships);
      const [membership] = memberships;
      if (memberships.length === 1 && membership) {
        await openWorkspace(membership);
      } else if (memberships.length > 1) {
        setScreen("organization-picker");
      } else {
        setAuthError("This account does not have an organization workspace.");
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setBusy(true);
    try {
      const csrf = csrfToken ? { csrf_token: csrfToken } : await api.csrf();
      await api.logout(csrf.csrf_token);
    } catch {
      // Clear the local workspace even if the session has already expired.
    }
    setOrganization(null);
    setOrganizations([]);
    setDashboard(null);
    setUserName("");
    setPassword("");
    setScreen("signed-out");
    setBusy(false);
  }

  async function saveCustomer(customerId: string | null, payload: CustomerInput) {
    if (!organization) return;
    if (customerId) {
      await api.updateCustomer(organization.organization_id, customerId, payload, csrfToken);
    } else {
      await api.createCustomer(organization.organization_id, payload, csrfToken);
    }
    setReloadKey((value) => value + 1);
  }

  async function saveTrip(tripId: string | null, payload: TripInput) {
    if (!organization) return;
    if (tripId) {
      await api.updateTrip(organization.organization_id, tripId, payload, csrfToken);
    } else {
      await api.createTrip(organization.organization_id, payload, csrfToken);
    }
    setReloadKey((value) => value + 1);
  }

  if (screen === "checking") {
    return <main className="auth-screen"><p role="status">Checking your TripPilot workspace…</p></main>;
  }

  if (screen === "signed-out") {
    return (
      <main className="auth-screen">
        <section className="auth-panel" aria-labelledby="auth-title">
          <a className="brand auth-brand" href="#signin" aria-label="TripPilot AI">
            <span className="brand-mark"><Compass size={20} strokeWidth={2.2} /></span>
            <span className="brand-copy"><strong>trip<span>pilot</span></strong><small>TRAVEL OPERATIONS</small></span>
          </a>
          <p className="eyebrow">TRAVEL OPERATIONS</p>
          <h1 id="auth-title">{authMode === "login" ? "Welcome back" : "Create your workspace"}</h1>
          <p className="heading-subtitle">{authMode === "login" ? "Sign in to your agency workspace." : "Start managing trips with your team."}</p>
          <div className="auth-tabs" role="tablist" aria-label="Account access">
            <button type="button" role="tab" aria-selected={authMode === "login"} onClick={() => { setAuthMode("login"); setAuthError(""); }}>Sign in</button>
            <button type="button" role="tab" aria-selected={authMode === "register"} onClick={() => { setAuthMode("register"); setAuthError(""); }}>Create account</button>
          </div>
          <form className="auth-form" onSubmit={submitAuth}>
            {authMode === "register" && <>
              <label>Full name<input autoComplete="name" required value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
              <label>Agency name<input autoComplete="organization" required minLength={2} value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} /></label>
            </>}
            <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label>Password<input type="password" autoComplete={authMode === "login" ? "current-password" : "new-password"} required minLength={authMode === "register" ? 12 : 1} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {authError && <p className="form-error" role="alert">{authError}</p>}
            <button className="primary-button" type="submit" disabled={busy}>{busy ? "Please wait…" : authMode === "login" ? "Sign in" : "Create workspace"}</button>
          </form>
        </section>
      </main>
    );
  }

  if (screen === "organization-picker") {
    return (
      <main className="auth-screen">
        <section className="auth-panel workspace-picker" aria-labelledby="workspace-title">
          <p className="eyebrow">WORKSPACE ACCESS</p>
          <h1 id="workspace-title">Choose an organization</h1>
          <p className="heading-subtitle">Select the workspace you want to open.</p>
          <div className="workspace-options">
            {organizations.map((membership) => (
              <button type="button" key={membership.organization_id} onClick={() => void openWorkspace(membership)} disabled={busy}>
                <span className="workspace-avatar">{membership.organization_name.slice(0, 1).toUpperCase()}</span>
                <span><strong>{membership.organization_name}</strong><small>{membership.role}</small></span>
                <ChevronDown size={16} className="workspace-option-arrow" />
              </button>
            ))}
          </div>
          {authError && <p className="form-error" role="alert">{authError}</p>}
          <button type="button" className="quiet-button" onClick={() => void signOut()}>Sign out</button>
        </section>
      </main>
    );
  }

  const summary = dashboard?.summary;
  const bookingValue = summary?.booking_value_by_currency.length
    ? summary.booking_value_by_currency.map(({ amount, currency }) => formatCurrency(Number(amount), currency)).join(" · ")
    : "—";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="TripPilot AI overview">
          <span className="brand-mark"><Compass size={20} strokeWidth={2.2} /></span>
          <span className="brand-copy"><strong>trip<span>pilot</span></strong><small>TRAVEL OPERATIONS</small></span>
        </a>
        <div className="workspace-switcher">
          <span className="workspace-avatar">{organization?.organization_name.slice(0, 1).toUpperCase()}</span>
          <span className="workspace-copy"><strong>{organization?.organization_name}</strong><small>{organization?.role} workspace</small></span>
          {organizations.length > 1 && <button type="button" className="workspace-change" aria-label="Change organization" onClick={() => setScreen("organization-picker")}><ChevronDown size={15} /></button>}
        </div>
        <p className="nav-caption">WORKSPACE</p>
        <nav className="primary-nav" aria-label="Main navigation">
          <button className={`nav-item${activeView === "overview" ? " active" : ""}`} type="button" onClick={() => setActiveView("overview")}><LayoutDashboard size={18} strokeWidth={1.9} /><span>Overview</span></button>
          <button className={`nav-item${activeView === "trips" ? " active" : ""}`} type="button" onClick={() => setActiveView("trips")}><Compass size={18} strokeWidth={1.9} /><span>Trips</span></button>
          <button className={`nav-item${activeView === "customers" ? " active" : ""}`} type="button" onClick={() => setActiveView("customers")}><UsersRound size={18} strokeWidth={1.9} /><span>Customers</span></button>
          <button className="nav-item" type="button" disabled title="Booking management is not available yet"><CalendarDays size={18} strokeWidth={1.9} /><span>Bookings</span></button>
          <button className="nav-item" type="button" disabled title="Expense management is not available yet"><Wallet size={18} strokeWidth={1.9} /><span>Expenses</span></button>
        </nav>
        <div className="sidebar-bottom">
          <button className="nav-item" type="button" disabled title="Settings will be added in a later build step"><Settings2 size={18} /><span>Settings</span></button>
          <button className="nav-item" type="button" disabled title="Help center will be added in a later build step"><CircleHelp size={18} /><span>Help center</span></button>
          <div className="profile-row"><span className="profile-avatar">{userName.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</span><span className="profile-copy"><strong>{userName}</strong><small>{organization?.role}</small></span><button className="signout-button" type="button" aria-label="Sign out" title="Sign out" onClick={() => void signOut()}><LogOut size={16} /></button></div>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="breadcrumb"><span>{organization?.organization_name}</span><span className="breadcrumb-slash">/</span><strong>{activeView === "overview" ? "Overview" : activeView === "trips" ? "Trips" : "Customers"}</strong></div>
          <div className="topbar-right"><span className="live-label"><span /> CONNECTED</span><div className="date-button" aria-label={`${formatDate(range.startDate, { month: "short", day: "numeric" })} to ${formatDate(range.endDate, { month: "short", day: "numeric", year: "numeric" })}`}><CalendarDays size={16} /><span>{formatDate(range.startDate, { month: "short", day: "numeric" })} – {formatDate(range.endDate, { month: "short", day: "numeric", year: "numeric" })}</span></div></div>
        </header>

        <div className="page-content">
          <section className="page-heading">
            <div><p className="eyebrow">TRAVEL OPERATIONS</p><h1>{activeView === "overview" ? `Good morning, ${userName.split(" ")[0]}` : activeView === "trips" ? "Trips" : "Customers"}</h1><p className="heading-subtitle">{activeView === "overview" ? "A clear view of your agency’s current activity." : activeView === "trips" ? "Plan customer travel and keep trip details current." : "Manage customer contact records for your organization."}</p></div>
          </section>

          {dashboardError && <div className="dashboard-alert" role="alert"><span>{dashboardError}</span><button type="button" onClick={() => setReloadKey((value) => value + 1)}>Retry</button></div>}

          {activeView === "overview" && <>
          <section className="metrics-grid" aria-label="Key business metrics" aria-busy={dashboardLoading}>
            <article className="metric-card"><div className="metric-top"><span className="metric-label">Booking value</span><span className="metric-icon teal"><Wallet size={18} /></span></div><div className="metric-value metric-multicurrency">{dashboardLoading && !summary ? "Loading…" : bookingValue}</div><div className="metric-foot"><span>Non-cancelled bookings</span></div></article>
            <article className="metric-card"><div className="metric-top"><span className="metric-label">Bookings</span><span className="metric-icon blue"><CalendarDays size={18} /></span></div><div className="metric-value">{summary?.booking_count ?? (dashboardLoading ? "…" : "0")}</div><div className="metric-foot"><span>In selected period</span></div></article>
            <article className="metric-card"><div className="metric-top"><span className="metric-label">Active customers</span><span className="metric-icon coral"><UsersRound size={18} /></span></div><div className="metric-value">{summary?.active_customer_count ?? (dashboardLoading ? "…" : "0")}</div><div className="metric-foot"><span>Across this workspace</span></div></article>
            <article className="metric-card"><div className="metric-top"><span className="metric-label">Upcoming trips</span><span className="metric-icon amber"><MapPin size={18} /></span></div><div className="metric-value">{summary?.upcoming_trip_count ?? (dashboardLoading ? "…" : "0")}</div><div className="metric-foot"><span>Not cancelled or completed</span></div></article>
          </section>

          <section className="overview-grid">
            <article className="panel revenue-panel">
              <div className="panel-heading"><div><div className="panel-title-row"><h2>Booking value</h2></div><p>Recorded booking value by date</p></div><div className="chart-controls"><label className="select-wrap"><span className="sr-only">Revenue chart period</span><select value={period} onChange={(event) => setPeriod(event.target.value as Period)}><option>7 days</option><option>30 days</option></select><ChevronDown size={14} /></label><label className="select-wrap"><span className="sr-only">Chart currency</span><select value={selectedCurrency} onChange={(event) => setSelectedCurrency(event.target.value)} disabled={!currencies.length} aria-label="Chart currency">{currencies.length ? currencies.map((currency) => <option key={currency}>{currency}</option>) : <option value="">No data</option>}</select><ChevronDown size={14} /></label></div></div>
              <div className="chart-legend"><span><i className="legend-dot revenue-dot" /> Booking value</span></div>
              <div className="chart-wrap">
                {chartData.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -14 }}>
                  <defs><linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#168b83" stopOpacity={0.18} /><stop offset="95%" stopColor="#168b83" stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid stroke="#edf1f2" vertical={false} /><XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: "#879397", fontSize: 11 }} dy={10} /><YAxis axisLine={false} tickLine={false} tick={{ fill: "#879397", fontSize: 11 }} tickFormatter={(value: number) => `${selectedCurrency} ${Math.round(value / 1000)}k`} />
                  <Tooltip formatter={(value) => [formatCurrency(Number(value), selectedCurrency), "Booking value"]} contentStyle={{ border: "1px solid #e5ebec", borderRadius: 8, boxShadow: "0 8px 24px #16343b14" }} />
                  <Area type="monotone" dataKey="revenue" stroke="#168b83" strokeWidth={2.5} fill="url(#revenueFill)" activeDot={{ r: 4, fill: "#168b83", stroke: "#fff", strokeWidth: 2 }} />
                </AreaChart></ResponsiveContainer> : <div className="chart-empty">{dashboardLoading ? "Loading booking activity…" : "No booking value recorded for this period."}</div>}
              </div>
              <div className="chart-total"><span>Period total{selectedCurrency ? ` · ${selectedCurrency}` : ""}</span><strong>{selectedCurrency ? formatCurrency(chartData.reduce((sum, point) => sum + point.revenue, 0), selectedCurrency) : "—"}</strong><span className="chart-total-note">Cancelled bookings excluded</span></div>
            </article>

            <article className="panel bookings-panel">
              <div className="panel-heading"><div><h2>Booking status</h2><p>Bookings recorded in this period</p></div><span className="icon-button" aria-hidden="true"><Activity size={17} /></span></div>
              <div className="booking-total"><strong>{statusTotal}</strong><span>total bookings</span></div>
              <div className="status-track" aria-label="Booking status distribution">{statusCounts.map(({ status, count }) => <span key={status} className={`track-${status}`} style={{ flex: count }} />)}</div>
              <div className="status-list">{statusCounts.map(({ status, count }) => <div key={status}><span><i className={`status-dot ${status}-dot`} />{statusLabels[status]}</span><strong>{count}{statusTotal > 0 && <small>{((count / statusTotal) * 100).toFixed(1)}%</small>}</strong></div>)}</div>
              <div className="panel-note"><span className="note-indicator" /> Status reflects all booking records in the selected period</div>
            </article>
          </section>

          <section className="panel trips-panel">
            <div className="panel-heading trips-heading"><div><h2>Upcoming trips</h2><p>Your next departures, all in one place</p></div><div className="trip-controls"><label className="search-box"><Search size={15} /><span className="sr-only">Search upcoming trips</span><input value={tripSearch} onChange={(event) => setTripSearch(event.target.value)} placeholder="Search trips or clients" /></label></div></div>
            <div className="trip-table-wrap"><table><thead><tr><th>TRIP</th><th>DESTINATION</th><th>TRAVEL DATES</th><th>STATUS</th></tr></thead><tbody>{filteredTrips.map((trip) => {
              const customer = customersById.get(trip.customer_id);
              const tone = trip.status === "confirmed" ? "green" : trip.status === "draft" ? "amber" : "blue";
              return <tr key={trip.id}><td><strong>{trip.title}</strong><span>{customer ? `${customer.first_name} ${customer.last_name}` : "Customer record"}</span></td><td><span className="destination-cell"><MapPin size={14} />{trip.destination}</span></td><td>{formatDate(trip.start_date, { month: "short", day: "numeric" })} – {formatDate(trip.end_date, { month: "short", day: "numeric", year: "numeric" })}</td><td><span className={`trip-status ${tone}`}><i />{trip.status.replaceAll("_", " ")}</span></td></tr>;
            })}</tbody></table>
              {dashboardLoading && !dashboard && <div className="empty-state" role="status">Loading upcoming trips…</div>}
              {!dashboardLoading && filteredTrips.length === 0 && <div className="empty-state"><Search size={18} /><strong>{tripSearch ? "No matching trips" : "No upcoming trips"}</strong><span>{tripSearch ? "Try another destination or customer name." : "Future trips will appear here."}</span></div>}
            </div>
            <div className="table-footer"><span>Showing {filteredTrips.length} upcoming trips</span><span>Workspace data · refreshed when the period changes</span></div>
          </section>

          <footer className="page-footer"><span>TripPilot AI <span className="footer-separator">·</span> Travel operations, made clearer.</span><span>Booking values remain in their original currencies</span></footer>
          </>}
          {activeView === "customers" && <CustomerWorkspace customers={dashboard?.customers ?? []} loading={dashboardLoading} onSave={saveCustomer} />}
          {activeView === "trips" && <TripWorkspace trips={dashboard?.trips ?? []} customers={dashboard?.customers ?? []} loading={dashboardLoading} onSave={saveTrip} />}
        </div>
      </main>
    </div>
  );
}

export default App;
