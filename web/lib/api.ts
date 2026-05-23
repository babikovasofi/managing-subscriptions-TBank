import type {
  ActionRequest,
  ActionResponse,
  ActionType,
  AnalyticsResponse,
  ClientsResponse,
  ManualSubscriptionRequest,
  NotificationsResponse,
  SubscriptionResponse,
  SubscriptionsResponse,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const V1 = `${API_BASE}/api/v1`;

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${V1}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getClients(): Promise<ClientsResponse> {
  return fetchJson<ClientsResponse>("/clients");
}

export function getSubscriptions(clientId: string): Promise<SubscriptionsResponse> {
  return fetchJson<SubscriptionsResponse>(
    `/clients/${encodeURIComponent(clientId)}/subscriptions`
  );
}

export function getAnalytics(clientId: string): Promise<AnalyticsResponse> {
  return fetchJson<AnalyticsResponse>(
    `/clients/${encodeURIComponent(clientId)}/analytics`
  );
}

export function getNotifications(clientId: string): Promise<NotificationsResponse> {
  return fetchJson<NotificationsResponse>(
    `/clients/${encodeURIComponent(clientId)}/notifications`
  );
}

export function postAction(
  clientId: string,
  merchantName: string,
  actionType: ActionType
): Promise<void> {
  const body: ActionRequest = { action_type: actionType, merchant_name: merchantName };
  return fetchJson<ActionResponse>(
    `/clients/${encodeURIComponent(clientId)}/actions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  ).then(() => undefined);
}

export function addManualSubscription(
  clientId: string,
  data: ManualSubscriptionRequest
): Promise<SubscriptionResponse> {
  return fetchJson<SubscriptionResponse>(
    `/clients/${encodeURIComponent(clientId)}/subscriptions/manual`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
}
