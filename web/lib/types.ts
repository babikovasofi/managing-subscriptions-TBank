// ── Enums ──────────────────────────────────────────────────────────────────

export type SubscriptionStatus =
  | "active"
  | "price_increased"
  | "possibly_unused"
  | "trial_ending";

export type SubscriptionConfidence = "high" | "low";

export type SubscriptionCategory =
  | "streaming_video"
  | "streaming_music"
  | "cloud_storage"
  | "education"
  | "gaming"
  | "food_delivery"
  | "productivity"
  | "reading"
  | "other";

export type NotificationType =
  | "upcoming_payment"
  | "trial_ending"
  | "price_increased"
  | "summary";

export type ActionType =
  | "mark_important"
  | "unmark_important"
  | "mute_notifications"
  | "unmute_notifications"
  | "mark_false_positive"
  | "hide"
  | "unhide";

// ── Clients ────────────────────────────────────────────────────────────────

export interface ClientItem {
  id: string;
  label: string;
}

export interface ClientsResponse {
  simulation_today: string;
  clients: ClientItem[];
}

// ── Subscriptions ──────────────────────────────────────────────────────────

export interface PriceHistoryEntry {
  date: string;
  amount: number;
}

export interface SubscriptionResponse {
  client_id: string;
  merchant_name: string;
  category: SubscriptionCategory;
  amount: number;
  monthly_amount: number;
  price_history: PriceHistoryEntry[];
  period_days: number;
  first_payment_date: string;
  last_payment_date: string;
  next_payment_date: string;
  n_payments: number;
  status: SubscriptionStatus;
  confidence: SubscriptionConfidence;
  reasons: string[];
  ml_probability: number;
  is_important: boolean;
  is_muted: boolean;
  is_hidden: boolean;
  is_false_positive: boolean;
  is_manual: boolean;
}

export interface SubscriptionsResponse {
  client_id: string;
  subscriptions: SubscriptionResponse[];
}

// ── Analytics ──────────────────────────────────────────────────────────────

export interface TopSubscription {
  merchant_name: string;
  category: SubscriptionCategory;
  amount: number;
  monthly_amount: number;
  status: SubscriptionStatus;
}

export interface Recommendation {
  merchant_name: string;
  text: string;
  reasons: string[];
  monthly_amount: number;
}

export interface AnalyticsResponse {
  client_id: string;
  monthly_total: number;
  potential_savings: number;
  top_3: TopSubscription[];
  recommendations: Recommendation[];
}

// ── Notifications ──────────────────────────────────────────────────────────

export interface Notification {
  date: string;
  text: string;
  type: NotificationType;
  merchant_name: string | null;
}

export interface NotificationsResponse {
  client_id: string;
  notifications: Notification[];
}

// ── Actions ────────────────────────────────────────────────────────────────

export interface ActionRequest {
  action_type: ActionType;
  merchant_name: string;
}

export interface ActionResponse {
  ok: boolean;
}

// ── Manual subscription ────────────────────────────────────────────────────

export interface ManualSubscriptionRequest {
  merchant_name: string;
  amount: number;
  period_days: number;
  category: SubscriptionCategory;
}
