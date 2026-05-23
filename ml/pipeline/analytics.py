"""
Per-client subscription analytics: monthly totals, top subscriptions,
potential savings, notifications, and recommendations.

Public API:
  compute_analytics(client_id, subscriptions) -> ClientAnalytics
  compute_all_analytics(results) -> dict[str, ClientAnalytics]

CLI:
  python -m ml.pipeline.analytics   — demo for 4 scripted clients
"""

import statistics
import sys
from dataclasses import dataclass
from datetime import date

from ml.pipeline.schema import Subscription
from ml.pipeline.time_utils import get_simulation_today

DAYS_PER_MONTH: float = 30.44

_MONTH_NAMES_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

_SUB_PLURALS = ("подписку", "подписки", "подписок")


def _sub_plural(n: int) -> str:
    n10, n100 = n % 10, n % 100
    if 11 <= n100 <= 19:
        return _SUB_PLURALS[2]
    if n10 == 1:
        return _SUB_PLURALS[0]
    if 2 <= n10 <= 4:
        return _SUB_PLURALS[1]
    return _SUB_PLURALS[2]


def _fmt_date(d: date) -> str:
    return f"{d.day} {_MONTH_NAMES_GEN[d.month]}"


def _monthly_amount(sub: Subscription) -> float:
    """Normalize last payment amount to a monthly equivalent."""
    return sub.amount * (DAYS_PER_MONTH / max(sub.period_days, 1))


def _price_increase_amounts(sub: Subscription) -> tuple[float, float]:
    """Return (old_median, new_median), mirroring detect_price_increase logic."""
    amounts = [amt for _, amt in sub.price_history]
    if len(amounts) >= 6:
        return statistics.median(amounts[:3]), statistics.median(amounts[-3:])
    return statistics.median(amounts[:-1]), amounts[-1]


# ── output dataclasses ────────────────────────────────────────────────────────

@dataclass
class Notification:
    date: date
    text: str
    type: str           # upcoming_payment | trial_ending | price_increased | summary
    merchant_name: str | None = None


@dataclass
class Recommendation:
    merchant_name: str
    text: str
    reasons: list[str]
    monthly_amount: float


@dataclass
class ClientAnalytics:
    client_id: str
    monthly_total: float
    top_3: list[Subscription]
    potential_savings: float
    notifications: list[Notification]
    recommendations: list[Recommendation]


# ── core logic ────────────────────────────────────────────────────────────────

def compute_analytics(client_id: str, subscriptions: list[Subscription]) -> ClientAnalytics:
    today = get_simulation_today().date()
    subs = subscriptions

    monthly = {s.merchant_name: _monthly_amount(s) for s in subs}
    monthly_total = sum(monthly.values())

    top_3 = sorted(subs, key=lambda s: monthly[s.merchant_name], reverse=True)[:3]

    potential_savings = sum(
        monthly[s.merchant_name]
        for s in subs
        if s.status == "possibly_unused" and s.confidence == "high"
    )

    notifications: list[Notification] = []

    # Upcoming payments (0–7 days); skip trial_ending — they get their own message
    for s in sorted(subs, key=lambda x: x.next_payment_date):
        if s.status == "trial_ending":
            continue
        days = (s.next_payment_date - today).days
        if 0 <= days <= 7:
            if days == 0:
                text = f"Сегодня спишется {s.amount:.0f} ₽ за «{s.merchant_name}»."
            elif days == 1:
                text = f"Завтра спишется {s.amount:.0f} ₽ за «{s.merchant_name}»."
            elif days <= 4:
                text = f"Через {days} дня спишется {s.amount:.0f} ₽ за «{s.merchant_name}»."
            else:
                text = f"Через {days} дней спишется {s.amount:.0f} ₽ за «{s.merchant_name}»."
            notifications.append(Notification(
                date=today,
                text=text,
                type="upcoming_payment",
                merchant_name=s.merchant_name,
            ))

    for s in subs:
        if s.status == "trial_ending":
            notifications.append(Notification(
                date=today,
                text=(
                    f"Пробный период «{s.merchant_name}» заканчивается — "
                    f"первое полное списание ожидается {_fmt_date(s.next_payment_date)}."
                ),
                type="trial_ending",
                merchant_name=s.merchant_name,
            ))

    for s in subs:
        if s.status == "price_increased" and len(s.price_history) >= 2:
            old, new = _price_increase_amounts(s)
            notifications.append(Notification(
                date=today,
                text=f"Стоимость «{s.merchant_name}» выросла с {old:.0f} ₽ до {new:.0f} ₽.",
                type="price_increased",
                merchant_name=s.merchant_name,
            ))

    # Summary — always last
    if subs:
        notifications.append(Notification(
            date=today,
            text=(
                f"Вы платите за {len(subs)} {_sub_plural(len(subs))}, "
                f"общая сумма — {monthly_total:.0f} ₽/мес."
            ),
            type="summary",
            merchant_name=None,
        ))

    recommendations = [
        Recommendation(
            merchant_name=s.merchant_name,
            text=(
                f"Возможно, вам стоит проверить подписку «{s.merchant_name}» — "
                f"похоже, вы давно ею не пользуетесь."
            ),
            reasons=s.reasons,
            monthly_amount=monthly[s.merchant_name],
        )
        for s in subs
        if s.status == "possibly_unused" and s.confidence == "high"
    ]

    return ClientAnalytics(
        client_id=client_id,
        monthly_total=monthly_total,
        top_3=top_3,
        potential_savings=potential_savings,
        notifications=notifications,
        recommendations=recommendations,
    )


def compute_all_analytics(
    results: dict[str, list[Subscription]],
) -> dict[str, ClientAnalytics]:
    return {
        client_id: compute_analytics(client_id, subs)
        for client_id, subs in results.items()
    }


# ── CLI demo ──────────────────────────────────────────────────────────────────

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from data.generator.config import TRANSACTIONS_OUTPUT_PATH
    from ml.pipeline.run import run_pipeline

    _DEMO = [
        ("scripted_01", "price_increase"),
        ("scripted_02", "trial_ending"),
        ("scripted_03", "abandoned_gaming"),
        ("scripted_04", "heavy_user"),
    ]

    print("Running full pipeline...")
    results = run_pipeline(TRANSACTIONS_OUTPUT_PATH)
    all_analytics = compute_all_analytics(results)

    for client_id, scenario in _DEMO:
        a = all_analytics.get(client_id)
        if a is None:
            print(f"\n[{client_id}] NOT FOUND")
            continue

        print(f"\n{'=' * 72}")
        print(f"[{client_id}] {scenario}")
        print(f"  monthly_total:     {a.monthly_total:.0f} ₽/мес")
        print(f"  potential_savings: {a.potential_savings:.0f} ₽/мес")
        print(f"  top_3:")
        for s in a.top_3:
            print(f"    {s.merchant_name:<32} {_monthly_amount(s):.0f} ₽/мес")
        print(f"  notifications ({len(a.notifications)}):")
        for n in a.notifications:
            tag = f"[{n.type}]"
            print(f"    {tag:<24} {n.text}")
        if a.recommendations:
            print(f"  recommendations ({len(a.recommendations)}):")
            for r in a.recommendations:
                print(f"    {r.merchant_name}  ({r.monthly_amount:.0f} ₽/мес)")
                print(f"      {r.text}")
                for reason in r.reasons:
                    print(f"      - {reason}")


if __name__ == "__main__":
    main()
