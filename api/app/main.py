"""
FastAPI application — Subscription Manager API.

Run:
  uvicorn api.app.main:app --reload
"""

import json
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from api.app.schemas import (
    ActionRequest,
    ActionResponse,
    AnalyticsResponse,
    ClientInfo,
    ClientListResponse,
    ManualSubscriptionRequest,
    Notification,
    NotificationsResponse,
    Recommendation,
    SubscriptionResponse,
    SubscriptionsListResponse,
    TopSubscription,
)
from api.db.models import ManualSubscription, SubscriptionCache, UserAction
from api.db.session import get_db
from ml.pipeline.analytics import DAYS_PER_MONTH, compute_analytics
from ml.pipeline.schema import Subscription as SubModel
from ml.pipeline.time_utils import get_simulation_today

app = FastAPI(title="Subscription Manager API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── constants ─────────────────────────────────────────────────────────────────

_SCRIPTED_LABELS: dict[str, str] = {
    "scripted_01": "scripted_01 — рост цены",
    "scripted_02": "scripted_02 — пробный период",
    "scripted_03": "scripted_03 — заброшенный gaming",
    "scripted_04": "scripted_04 — много подписок",
    "scripted_05": "scripted_05 — новичок",
    "scripted_06": "scripted_06 — пересекающиеся даты",
    "scripted_07": "scripted_07 — бывший пользователь",
    "scripted_08": "scripted_08 — дублирующиеся сервисы",
    "scripted_09": "scripted_09 — ложный триггер",
    "scripted_10": "scripted_10 — семейный план",
}

_VALID_ACTIONS = {
    "mark_important", "unmark_important",
    "mute_notifications", "unmute_notifications",
    "mark_false_positive",
    "hide", "unhide",
}

# undo action → list of forward actions to delete
_UNDO_MAP: dict[str, list[str]] = {
    "unmark_important":    ["mark_important"],
    "unmute_notifications": ["mute_notifications"],
    "unhide":              ["hide", "mark_false_positive"],
}

_VALID_CATEGORIES = {
    "streaming_video", "streaming_music", "cloud_storage",
    "education", "gaming", "food_delivery", "productivity",
    "reading", "other",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _include_client(client_id: str) -> bool:
    if client_id.startswith("scripted_"):
        try:
            return 1 <= int(client_id.split("_")[1]) <= 10
        except (ValueError, IndexError):
            return False
    return client_id.startswith("client_")


def _get_user_flags(db: Session, client_id: str) -> dict[str, set[str]]:
    """Return {merchant_name: set(active action_types)} for this client."""
    rows = db.query(UserAction).filter(UserAction.client_id == client_id).all()
    flags: dict[str, set[str]] = {}
    for row in rows:
        flags.setdefault(row.merchant_name, set()).add(row.action_type)
    return flags


def _derive_flags(action_types: set[str]) -> dict[str, bool]:
    return {
        "is_important":     "mark_important"       in action_types,
        "is_muted":         "mute_notifications"   in action_types,
        "is_hidden":        "hide"                 in action_types,
        "is_false_positive": "mark_false_positive" in action_types,
    }


def _cache_row_to_response(
    row: SubscriptionCache,
    flags: dict[str, bool],
) -> SubscriptionResponse:
    return SubscriptionResponse(
        client_id=row.client_id,
        merchant_name=row.merchant_name,
        category=row.category,
        amount=row.amount,
        monthly_amount=row.monthly_amount,
        price_history=json.loads(row.price_history_json),
        period_days=row.period_days,
        first_payment_date=row.first_payment_date,
        last_payment_date=row.last_payment_date,
        next_payment_date=row.next_payment_date,
        n_payments=row.n_payments,
        status=row.status,
        confidence=row.confidence,
        reasons=json.loads(row.reasons_json),
        ml_probability=row.ml_probability,
        is_manual=False,
        **flags,
    )


def _manual_row_to_response(
    row: ManualSubscription,
    flags: dict[str, bool],
    today: date,
) -> SubscriptionResponse:
    next_date = today + timedelta(days=row.period_days)
    monthly = round(row.amount * (DAYS_PER_MONTH / max(row.period_days, 1)), 2)
    today_str = today.isoformat()
    return SubscriptionResponse(
        client_id=row.client_id,
        merchant_name=row.merchant_name,
        category=row.category,
        amount=row.amount,
        monthly_amount=monthly,
        price_history=[{"date": today_str, "amount": row.amount}],
        period_days=row.period_days,
        first_payment_date=today_str,
        last_payment_date=today_str,
        next_payment_date=next_date.isoformat(),
        n_payments=1,
        status="active",
        confidence="high",
        reasons=["Добавлено вручную"],
        ml_probability=1.0,
        is_manual=True,
        **flags,
    )


def _cache_row_to_submodel(row: SubscriptionCache) -> SubModel:
    price_history_raw = json.loads(row.price_history_json)
    price_history = [
        (date.fromisoformat(item["date"]), float(item["amount"]))
        for item in price_history_raw
    ]
    return SubModel(
        client_id=row.client_id,
        merchant_name=row.merchant_name,
        category=row.category,
        amount=row.amount,
        price_history=price_history,
        period_days=row.period_days,
        first_payment_date=date.fromisoformat(row.first_payment_date),
        last_payment_date=date.fromisoformat(row.last_payment_date),
        next_payment_date=date.fromisoformat(row.next_payment_date),
        n_payments=row.n_payments,
        status=row.status,
        confidence=row.confidence,
        reasons=json.loads(row.reasons_json),
        ml_probability=row.ml_probability,
    )


def _manual_row_to_submodel(row: ManualSubscription, today: date) -> SubModel:
    next_date = today + timedelta(days=row.period_days)
    return SubModel(
        client_id=row.client_id,
        merchant_name=row.merchant_name,
        category=row.category,
        amount=row.amount,
        price_history=[(today, row.amount)],
        period_days=row.period_days,
        first_payment_date=today,
        last_payment_date=today,
        next_payment_date=next_date,
        n_payments=1,
        status="active",
        confidence="high",
        reasons=["Добавлено вручную"],
        ml_probability=1.0,
    )


def _visible_submodels(
    db: Session,
    client_id: str,
    today: date,
    all_flags: dict[str, set[str]],
) -> list[SubModel]:
    """Visible (not hidden, not false_positive) subscriptions as SubModel objects."""
    subs: list[SubModel] = []
    for row in db.query(SubscriptionCache).filter(
        SubscriptionCache.client_id == client_id
    ).all():
        f = _derive_flags(all_flags.get(row.merchant_name, set()))
        if f["is_hidden"] or f["is_false_positive"]:
            continue
        subs.append(_cache_row_to_submodel(row))
    for row in db.query(ManualSubscription).filter(
        ManualSubscription.client_id == client_id
    ).all():
        f = _derive_flags(all_flags.get(row.merchant_name, set()))
        if f["is_hidden"] or f["is_false_positive"]:
            continue
        subs.append(_manual_row_to_submodel(row, today))
    return subs


def _require_client(client_id: str, db: Session) -> None:
    has_cache = db.query(SubscriptionCache.client_id).filter(
        SubscriptionCache.client_id == client_id
    ).first()
    has_manual = db.query(ManualSubscription.client_id).filter(
        ManualSubscription.client_id == client_id
    ).first()
    if not has_cache and not has_manual:
        raise HTTPException(status_code=404, detail="client not found")


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/clients", response_model=ClientListResponse)
def get_clients(db: Session = Depends(get_db)):
    cache_ids: set[str] = {
        r[0] for r in db.query(SubscriptionCache.client_id).distinct()
    }
    manual_ids: set[str] = {
        r[0] for r in db.query(ManualSubscription.client_id).distinct()
    }
    all_ids = cache_ids | manual_ids

    scripted = sorted(
        [c for c in all_ids if _include_client(c) and c.startswith("scripted_")],
        key=lambda x: int(x.split("_")[1]),
    )
    random_clients = sorted(c for c in all_ids if c.startswith("client_"))

    clients = [
        ClientInfo(id=cid, label=_SCRIPTED_LABELS.get(cid, cid))
        for cid in scripted + random_clients
    ]
    today = get_simulation_today().date()
    return ClientListResponse(simulation_today=today.isoformat(), clients=clients)


@app.get("/api/v1/clients/{client_id}/subscriptions", response_model=SubscriptionsListResponse)
def get_subscriptions(
    client_id: str,
    include_hidden: bool = False,
    db: Session = Depends(get_db),
):
    _require_client(client_id, db)
    today = get_simulation_today().date()
    all_flags = _get_user_flags(db, client_id)

    subs: list[SubscriptionResponse] = []

    for row in db.query(SubscriptionCache).filter(
        SubscriptionCache.client_id == client_id
    ).all():
        flags = _derive_flags(all_flags.get(row.merchant_name, set()))
        if not include_hidden and (flags["is_hidden"] or flags["is_false_positive"]):
            continue
        subs.append(_cache_row_to_response(row, flags))

    for row in db.query(ManualSubscription).filter(
        ManualSubscription.client_id == client_id
    ).all():
        flags = _derive_flags(all_flags.get(row.merchant_name, set()))
        if not include_hidden and (flags["is_hidden"] or flags["is_false_positive"]):
            continue
        subs.append(_manual_row_to_response(row, flags, today))

    subs.sort(key=lambda s: s.next_payment_date)
    return SubscriptionsListResponse(client_id=client_id, subscriptions=subs)


@app.get("/api/v1/clients/{client_id}/analytics", response_model=AnalyticsResponse)
def get_analytics(client_id: str, db: Session = Depends(get_db)):
    _require_client(client_id, db)
    today = get_simulation_today().date()
    all_flags = _get_user_flags(db, client_id)

    visible = _visible_submodels(db, client_id, today, all_flags)
    analytics = compute_analytics(client_id, visible)

    return AnalyticsResponse(
        client_id=client_id,
        monthly_total=round(analytics.monthly_total, 2),
        potential_savings=round(analytics.potential_savings, 2),
        top_3=[
            TopSubscription(
                merchant_name=s.merchant_name,
                category=s.category,
                amount=s.amount,
                monthly_amount=round(s.amount * DAYS_PER_MONTH / max(s.period_days, 1), 2),
                status=s.status,
            )
            for s in analytics.top_3
        ],
        recommendations=[
            Recommendation(
                merchant_name=r.merchant_name,
                text=r.text,
                reasons=r.reasons,
                monthly_amount=round(r.monthly_amount, 2),
            )
            for r in analytics.recommendations
        ],
    )


@app.get("/api/v1/clients/{client_id}/notifications", response_model=NotificationsResponse)
def get_notifications(client_id: str, db: Session = Depends(get_db)):
    _require_client(client_id, db)
    today = get_simulation_today().date()
    all_flags = _get_user_flags(db, client_id)

    muted: set[str] = set()
    visible: list[SubModel] = []

    for row in db.query(SubscriptionCache).filter(
        SubscriptionCache.client_id == client_id
    ).all():
        f = _derive_flags(all_flags.get(row.merchant_name, set()))
        if f["is_hidden"] or f["is_false_positive"]:
            continue
        if f["is_muted"]:
            muted.add(row.merchant_name)
        visible.append(_cache_row_to_submodel(row))

    for row in db.query(ManualSubscription).filter(
        ManualSubscription.client_id == client_id
    ).all():
        f = _derive_flags(all_flags.get(row.merchant_name, set()))
        if f["is_hidden"] or f["is_false_positive"]:
            continue
        if f["is_muted"]:
            muted.add(row.merchant_name)
        visible.append(_manual_row_to_submodel(row, today))

    analytics = compute_analytics(client_id, visible)

    notifications = [
        Notification(
            date=n.date.isoformat(),
            text=n.text,
            type=n.type,
            merchant_name=n.merchant_name,
        )
        for n in analytics.notifications
        # summary (merchant_name=None) is always included; others only if not muted
        if n.merchant_name is None or n.merchant_name not in muted
    ]
    return NotificationsResponse(client_id=client_id, notifications=notifications)


@app.post("/api/v1/clients/{client_id}/actions", response_model=ActionResponse)
def post_action(
    client_id: str,
    req: ActionRequest,
    db: Session = Depends(get_db),
):
    if req.action_type not in _VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"unknown action_type: {req.action_type}")

    has_cache = db.query(SubscriptionCache).filter(
        SubscriptionCache.client_id == client_id,
        SubscriptionCache.merchant_name == req.merchant_name,
    ).first()
    has_manual = db.query(ManualSubscription).filter(
        ManualSubscription.client_id == client_id,
        ManualSubscription.merchant_name == req.merchant_name,
    ).first()
    if not has_cache and not has_manual:
        raise HTTPException(status_code=400, detail="merchant not found for this client")

    if req.action_type in _UNDO_MAP:
        for forward_action in _UNDO_MAP[req.action_type]:
            db.query(UserAction).filter(
                UserAction.client_id == client_id,
                UserAction.merchant_name == req.merchant_name,
                UserAction.action_type == forward_action,
            ).delete()
    else:
        exists = db.query(UserAction).filter(
            UserAction.client_id == client_id,
            UserAction.merchant_name == req.merchant_name,
            UserAction.action_type == req.action_type,
        ).first()
        if not exists:
            db.add(UserAction(
                client_id=client_id,
                merchant_name=req.merchant_name,
                action_type=req.action_type,
            ))

    db.commit()
    return ActionResponse(ok=True)


@app.post(
    "/api/v1/clients/{client_id}/subscriptions/manual",
    response_model=SubscriptionResponse,
    status_code=201,
)
def add_manual_subscription(
    client_id: str,
    req: ManualSubscriptionRequest,
    db: Session = Depends(get_db),
):
    if not req.merchant_name.strip():
        raise HTTPException(status_code=400, detail="merchant_name cannot be empty")
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")
    if not (1 <= req.period_days <= 366):
        raise HTTPException(status_code=400, detail="period_days must be 1–366")
    if req.category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"invalid category: {req.category}")

    today = get_simulation_today().date()

    existing = db.query(ManualSubscription).filter(
        ManualSubscription.client_id == client_id,
        ManualSubscription.merchant_name == req.merchant_name,
    ).first()

    if existing:
        existing.amount = req.amount
        existing.period_days = req.period_days
        existing.category = req.category
        row = existing
    else:
        row = ManualSubscription(
            client_id=client_id,
            merchant_name=req.merchant_name,
            amount=req.amount,
            period_days=req.period_days,
            category=req.category,
        )
        db.add(row)

    db.commit()
    db.refresh(row)

    all_flags = _get_user_flags(db, client_id)
    flags = _derive_flags(all_flags.get(req.merchant_name, set()))
    return _manual_row_to_response(row, flags, today)
