import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Customer, CustomerInput, Trip, TripInput } from "./api";

describe("authenticated dashboard", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    let authenticated = false;
    let customerRows: Customer[] = [{ id: "customer-1", first_name: "Jamie", last_name: "Ng", email: "jamie@example.com", phone: null, notes: null, is_active: true }];
    let tripRows: Trip[] = [{ id: "trip-1", customer_id: "customer-1", created_by: "user-1", title: "Lisbon plan", destination: "Lisbon, Portugal", start_date: "2026-11-10", end_date: "2026-11-16", traveler_count: 2, budget_amount: "1800.00", currency: "EUR", preferences: null, status: "confirmed" }];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";
      let body: unknown;
      let status = 200;

      if (path.endsWith("/auth/csrf")) body = { csrf_token: "csrf-test-token" };
      else if (path.endsWith("/auth/organizations")) {
        if (!authenticated) {
          status = 401;
          body = { detail: "Authentication required" };
        } else {
          body = [{ organization_id: "org-1", organization_name: "Northwind Travel", role: "manager" }];
        }
      } else if (path.endsWith("/auth/login") && method === "POST") {
        authenticated = true;
        body = { status: "authenticated", csrf_token: "csrf-test-token" };
      } else if (path.endsWith("/auth/me")) {
        body = { id: "user-1", email: "alex@example.com", full_name: "Alex Morgan", organization_id: "org-1", organization_name: "Northwind Travel", role: "manager" };
      } else if (path.includes("/dashboard/summary")) {
        body = { start_date: "2026-09-24", end_date: "2026-10-23", active_customer_count: 4, upcoming_trip_count: 2, booking_count: 2, booking_value_by_currency: [{ currency: "EUR", amount: "200.00" }, { currency: "USD", amount: "1250.00" }] };
      } else if (path.includes("/dashboard/revenue")) {
        body = { items: [{ booked_date: "2026-10-21", currency: "EUR", booking_count: 1, booking_value: "200.00" }, { booked_date: "2026-10-22", currency: "USD", booking_count: 1, booking_value: "1250.00" }] };
      } else if (path.includes("/dashboard/booking-status")) {
        body = { items: [{ status: "confirmed", count: 1 }, { status: "tentative", count: 1 }, { status: "draft", count: 0 }, { status: "cancelled", count: 0 }] };
      } else if (path.endsWith("/trips") && method === "POST") {
        const payload = JSON.parse(String(init?.body)) as TripInput;
        const trip = { ...payload, id: "trip-2", created_by: "user-1" };
        tripRows = [...tripRows, trip];
        body = trip;
      } else if (path.endsWith("/trips")) {
        body = { count: tripRows.length, items: tripRows };
      } else if (path.endsWith("/customers") && method === "POST") {
        const payload = JSON.parse(String(init?.body)) as CustomerInput;
        const customer = { ...payload, id: "customer-2", is_active: true };
        customerRows = [...customerRows, customer];
        body = customer;
      } else if (path.endsWith("/customers")) {
        body = { count: customerRows.length, items: customerRows };
      } else {
        status = 404;
        body = { detail: "Not found" };
      }

      return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
      } as Response;
    }));
  });

  it("signs in, selects the authorized workspace, and renders API-backed data", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Welcome back" });
    await user.type(screen.getByLabelText("Email address"), "alex@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Lisbon plan")).toBeInTheDocument();
    expect(screen.getAllByText("Northwind Travel").length).toBeGreaterThan(1);
    expect(screen.getByRole("heading", { name: "Booking value" })).toBeInTheDocument();
    expect(screen.queryByText("Autumn in Kyoto")).not.toBeInTheDocument();
    expect(screen.getByText("4", { selector: ".metric-value" })).toBeInTheDocument();
    const summaryRequest = vi.mocked(fetch).mock.calls.find(([input]) =>
      String(input).includes("/dashboard/summary"),
    );
    expect(new Headers(summaryRequest?.[1]?.headers).get("X-Organization-ID")).toBe("org-1");

    const currencySelect = screen.getByRole("combobox", { name: "Chart currency" });
    fireEvent.change(currencySelect, { target: { value: "USD" } });
    await waitFor(() => expect(screen.getByText("$1,250")).toBeInTheDocument());
  });

  it("creates a customer and a trip through organization-scoped API requests", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Welcome back" });
    await user.type(screen.getByLabelText("Email address"), "alex@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByText("Lisbon plan");

    await user.click(screen.getByRole("button", { name: "Customers" }));
    await user.click(screen.getByRole("button", { name: "New customer" }));
    await user.type(screen.getByLabelText("First name"), "Sam");
    await user.type(screen.getByLabelText("Last name"), "Rivera");
    await user.type(screen.getByLabelText("Email", { selector: "input" }), "sam@example.com");
    await user.click(screen.getByRole("button", { name: "Create customer" }));
    expect(await screen.findByText("Sam Rivera")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Trips" }));
    await user.click(screen.getByRole("button", { name: "New trip" }));
    await user.selectOptions(screen.getByLabelText("Customer"), "customer-2");
    await user.type(screen.getByLabelText("Trip title"), "Coastal break");
    await user.type(screen.getByLabelText("Destination"), "Porto, Portugal");
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-12-01" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2026-12-05" } });
    await user.clear(screen.getByLabelText("Budget"));
    await user.type(screen.getByLabelText("Budget"), "2400");
    await user.click(screen.getByRole("button", { name: "Create trip" }));
    expect(await screen.findByText("Coastal break")).toBeInTheDocument();

    const mutationCalls = vi.mocked(fetch).mock.calls.filter(([input, init]) =>
      ["POST", "PATCH"].includes(init?.method ?? "GET") &&
      (String(input).endsWith("/customers") || String(input).endsWith("/trips")),
    );
    expect(mutationCalls).toHaveLength(2);
    for (const [, init] of mutationCalls) {
      expect(new Headers(init?.headers).get("X-Organization-ID")).toBe("org-1");
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-test-token");
    }
  });
});
