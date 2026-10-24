export type OrganizationMembership = {
  organization_id: string;
  organization_name: string;
  role: string;
};

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
  organization_name: string;
  role: string;
};

export type DashboardSummary = {
  start_date: string;
  end_date: string;
  active_customer_count: number;
  upcoming_trip_count: number;
  booking_count: number;
  booking_value_by_currency: { currency: string; amount: string }[];
};

export type RevenuePoint = {
  booked_date: string;
  currency: string;
  booking_count: number;
  booking_value: string;
};

export type BookingStatus = { status: string; count: number };
export type Trip = {
  id: string;
  customer_id: string;
  created_by: string;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  traveler_count: number;
  budget_amount: string;
  currency: string;
  preferences: string | null;
  status: string;
};
export type Customer = {
  id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  notes: string | null;
  is_active: boolean;
};

export type CustomerInput = Pick<Customer, "first_name" | "last_name" | "email" | "phone" | "notes">;
export type TripInput = Pick<
  Trip,
  | "customer_id"
  | "title"
  | "destination"
  | "start_date"
  | "end_date"
  | "traveler_count"
  | "budget_amount"
  | "currency"
  | "preferences"
  | "status"
>;

type RequestOptions = RequestInit & {
  organizationId?: string;
  csrfToken?: string;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { organizationId, csrfToken, headers, ...init } = options;
  const requestHeaders = new Headers(headers);
  if (organizationId) requestHeaders.set("X-Organization-ID", organizationId);
  if (csrfToken) requestHeaders.set("X-CSRF-Token", csrfToken);
  if (init.body && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: requestHeaders,
    credentials: "same-origin",
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  csrf: () => request<{ csrf_token: string }>("/auth/csrf"),
  organizations: () => request<OrganizationMembership[]>("/auth/organizations"),
  currentUser: (organizationId: string) =>
    request<CurrentUser>("/auth/me", { organizationId }),
  login: (email: string, password: string, csrfToken: string) =>
    request<{ status: string; csrf_token: string }>("/auth/login", {
      method: "POST",
      csrfToken,
      body: JSON.stringify({ email, password }),
    }),
  register: (
    email: string,
    fullName: string,
    organizationName: string,
    password: string,
    csrfToken: string,
  ) =>
    request<{ status: string; csrf_token: string }>("/auth/register", {
      method: "POST",
      csrfToken,
      body: JSON.stringify({
        email,
        full_name: fullName,
        organization_name: organizationName,
        password,
      }),
    }),
  logout: (csrfToken: string) =>
    request<{ status: string }>("/auth/logout", {
      method: "POST",
      csrfToken,
    }),
  dashboard: (organizationId: string, startDate: string, endDate: string) => {
    const range = `?start_date=${startDate}&end_date=${endDate}`;
    return Promise.all([
      request<DashboardSummary>(`/dashboard/summary${range}`, { organizationId }),
      request<{ items: RevenuePoint[] }>(`/dashboard/revenue${range}`, { organizationId }),
      request<{ items: BookingStatus[] }>(`/dashboard/booking-status${range}`, {
        organizationId,
      }),
      request<{ items: Trip[] }>("/trips", { organizationId }),
      request<{ items: Customer[] }>("/customers", { organizationId }),
    ]).then(([summary, revenue, statuses, trips, customers]) => ({
      summary,
      revenue: revenue.items,
      statuses: statuses.items,
      trips: trips.items,
      customers: customers.items,
    }));
  },
  createCustomer: (organizationId: string, payload: CustomerInput, csrfToken: string) =>
    request<Customer>("/customers", {
      method: "POST",
      organizationId,
      csrfToken,
      body: JSON.stringify(payload),
    }),
  updateCustomer: (
    organizationId: string,
    customerId: string,
    payload: CustomerInput,
    csrfToken: string,
  ) =>
    request<Customer>(`/customers/${customerId}`, {
      method: "PATCH",
      organizationId,
      csrfToken,
      body: JSON.stringify(payload),
    }),
  createTrip: (organizationId: string, payload: TripInput, csrfToken: string) =>
    request<Trip>("/trips", {
      method: "POST",
      organizationId,
      csrfToken,
      body: JSON.stringify(payload),
    }),
  updateTrip: (organizationId: string, tripId: string, payload: TripInput, csrfToken: string) =>
    request<Trip>(`/trips/${tripId}`, {
      method: "PATCH",
      organizationId,
      csrfToken,
      body: JSON.stringify(payload),
    }),
};
