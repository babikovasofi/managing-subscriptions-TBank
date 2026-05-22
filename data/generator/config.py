from datetime import datetime
from pathlib import Path

# === Воспроизводимость ===
RANDOM_SEED: int = 42

# === Клиенты ===
N_CLIENTS_RANDOM: int = 140
N_CLIENTS_SCRIPTED: int = 10

# === История ===
HISTORY_MONTHS: int = 12

# === Фиксированная дата "сегодня" в датасете ===
# Всё, что позже этой даты, не должно попасть в датасет.
SIMULATION_TODAY: datetime = datetime(2026, 5, 22)

# === Пути ===
_REPO_ROOT = Path(__file__).parent.parent.parent
REFERENCES_DIR: Path = _REPO_ROOT / "data" / "references"
OUTPUT_DIR: Path = _REPO_ROOT / "data" / "output"

SUBSCRIPTIONS_REF_PATH: Path = REFERENCES_DIR / "subscriptions.json"
REGULAR_MERCHANTS_REF_PATH: Path = REFERENCES_DIR / "regular_merchants.json"

TRANSACTIONS_OUTPUT_PATH: Path = OUTPUT_DIR / "transactions.csv"
LABELS_OUTPUT_PATH: Path = OUTPUT_DIR / "labels.csv"
META_OUTPUT_PATH: Path = OUTPUT_DIR / "meta.json"

# === Версия генератора (для meta.json) ===
GENERATOR_VERSION: str = "1.0.0"

# === Jitter для дат подписочных списаний ===
# Каждое списание смещается на ±PAYMENT_DATE_JITTER_DAYS случайно.
PAYMENT_DATE_JITTER_DAYS: int = 2

# === Шум по сумме подписок ===
# Реальная сумма = base_price * (1 + U(-AMOUNT_NOISE, +AMOUNT_NOISE))
AMOUNT_NOISE_FRACTION: float = 0.02  # ±2%

# === Диапазон транзакций на клиента в месяц ===
MIN_TRANSACTIONS_PER_MONTH: int = 30
MAX_TRANSACTIONS_PER_MONTH: int = 100

# === Параметры подписок ===
# Вероятность повышения цены за 12 месяцев истории (для случайных клиентов).
PRICE_INCREASE_PROBABILITY: float = 0.20
# Диапазон повышения цены: множитель к base_price.
PRICE_INCREASE_MIN_FACTOR: float = 1.15
PRICE_INCREASE_MAX_FACTOR: float = 1.30
# Вероятность пробного периода у подписки.
TRIAL_PERIOD_PROBABILITY: float = 0.10
# Сумма первого пробного списания (имитация "1 рубль").
TRIAL_AMOUNT_RUB: float = 1.0
# Продолжительность пробного периода в днях.
TRIAL_DURATION_DAYS: int = 30

# === Диапазон даты старта подписки ===
# Подписка могла начаться не раньше чем SUBSCRIPTION_MIN_AGE_MONTHS назад
# и не позже чем SUBSCRIPTION_MAX_AGE_MONTHS назад от SIMULATION_TODAY.
SUBSCRIPTION_MIN_AGE_MONTHS: int = 1
SUBSCRIPTION_MAX_AGE_MONTHS: int = 12

# === ID-схема клиентов ===
# Случайные: client_0001 … client_0140
# Режиссированные: scripted_01 … scripted_10
CLIENT_ID_RANDOM_PREFIX: str = "client"
CLIENT_ID_SCRIPTED_PREFIX: str = "scripted"
