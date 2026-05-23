from pydantic import BaseModel


class PriceHistoryItem(BaseModel):
    date: str
    amount: float


class SubscriptionResponse(BaseModel):
    client_id: str
    merchant_name: str
    category: str
    amount: float
    monthly_amount: float
    price_history: list[PriceHistoryItem]
    period_days: int
    first_payment_date: str
    last_payment_date: str
    next_payment_date: str
    n_payments: int
    status: str
    confidence: str
    reasons: list[str]
    ml_probability: float
    is_important: bool
    is_muted: bool
    is_hidden: bool
    is_false_positive: bool
    is_manual: bool


class TopSubscription(BaseModel):
    merchant_name: str
    category: str
    amount: float
    monthly_amount: float
    status: str


class Notification(BaseModel):
    date: str
    text: str
    type: str
    merchant_name: str | None = None


class Recommendation(BaseModel):
    merchant_name: str
    text: str
    reasons: list[str]
    monthly_amount: float


class ClientInfo(BaseModel):
    id: str
    label: str


class ClientListResponse(BaseModel):
    simulation_today: str
    clients: list[ClientInfo]


class SubscriptionsListResponse(BaseModel):
    client_id: str
    subscriptions: list[SubscriptionResponse]


class AnalyticsResponse(BaseModel):
    client_id: str
    monthly_total: float
    potential_savings: float
    top_3: list[TopSubscription]
    recommendations: list[Recommendation]


class NotificationsResponse(BaseModel):
    client_id: str
    notifications: list[Notification]


class ActionRequest(BaseModel):
    action_type: str
    merchant_name: str


class ActionResponse(BaseModel):
    ok: bool


class ManualSubscriptionRequest(BaseModel):
    merchant_name: str
    amount: float
    period_days: int
    category: str
