from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class SubscriptionCache(Base):
    __tablename__ = "subscriptions_cache"

    client_id = Column(String, primary_key=True)
    merchant_name = Column(String, primary_key=True)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    monthly_amount = Column(Float, nullable=False)
    price_history_json = Column(Text, nullable=False)  # [{date, amount}, ...]
    period_days = Column(Integer, nullable=False)
    first_payment_date = Column(String, nullable=False)  # ISO date
    last_payment_date = Column(String, nullable=False)
    next_payment_date = Column(String, nullable=False)
    n_payments = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    confidence = Column(String, nullable=False)
    reasons_json = Column(Text, nullable=False)          # [str, ...]
    ml_probability = Column(Float, nullable=False)


class UserAction(Base):
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String, nullable=False)
    merchant_name = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("client_id", "merchant_name", "action_type", name="uq_action"),
    )


class ManualSubscription(Base):
    __tablename__ = "manual_subscriptions"

    client_id = Column(String, primary_key=True)
    merchant_name = Column(String, primary_key=True)
    amount = Column(Float, nullable=False)
    period_days = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
