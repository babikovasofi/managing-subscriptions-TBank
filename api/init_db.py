"""
Initialize the SQLite database with ML pipeline results.

Run once before starting the API:
  python -m api.init_db
"""

import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy.orm import sessionmaker

from api.db.models import Base, SubscriptionCache
from api.db.session import get_engine
from data.generator.config import TRANSACTIONS_OUTPUT_PATH
from ml.pipeline.analytics import DAYS_PER_MONTH
from ml.pipeline.run import run_pipeline


def main() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Tables created (or already exist).")

    print("Running ML pipeline on full dataset...")
    results = run_pipeline(TRANSACTIONS_OUTPUT_PATH)
    total_subs = sum(len(subs) for subs in results.values())
    print(f"Pipeline done: {len(results)} clients, {total_subs} subscriptions total.")

    Session = sessionmaker(bind=engine)
    with Session() as session:
        deleted = session.query(SubscriptionCache).delete()
        print(f"Cleared {deleted} old cache rows.")

        rows_added = 0
        for client_id, subs in results.items():
            for sub in subs:
                monthly = round(sub.amount * (DAYS_PER_MONTH / max(sub.period_days, 1)), 2)
                price_history_json = json.dumps([
                    {"date": d.isoformat(), "amount": float(a)}
                    for d, a in sub.price_history
                ])
                session.add(SubscriptionCache(
                    client_id=sub.client_id,
                    merchant_name=sub.merchant_name,
                    category=sub.category,
                    amount=sub.amount,
                    monthly_amount=monthly,
                    price_history_json=price_history_json,
                    period_days=sub.period_days,
                    first_payment_date=sub.first_payment_date.isoformat(),
                    last_payment_date=sub.last_payment_date.isoformat(),
                    next_payment_date=sub.next_payment_date.isoformat(),
                    n_payments=sub.n_payments,
                    status=sub.status,
                    confidence=sub.confidence,
                    reasons_json=json.dumps(sub.reasons, ensure_ascii=False),
                    ml_probability=sub.ml_probability,
                ))
                rows_added += 1

        session.commit()

    print(f"Wrote {rows_added} rows to subscriptions_cache.")
    print(f"DB path: {engine.url}")


if __name__ == "__main__":
    main()
