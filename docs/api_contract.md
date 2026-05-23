# API Contract — Управление подписками

## Общее

**Base URL:** `/api/v1`

**Дата датасета:** `simulation_today` возвращается в ответе `GET /clients`.
Фронт использует её как «сегодня» для всех относительных дат (следующее списание, осталось дней и т.д.).

**Формат ошибок:**
```json
{"error": "client not found"}
```

**HTTP-статусы:** `200 OK` · `201 Created` · `400 Bad Request` · `404 Not Found`

---

## Типы данных

### SubscriptionResponse

Основной объект. Поля из `ml/pipeline/schema.py` + `monthly_amount` + user_actions оверлей.

```json
{
  "client_id":           "scripted_01",
  "merchant_name":       "Кинопоиск HD",
  "category":            "streaming_video",
  "amount":              398.0,
  "monthly_amount":      409.0,
  "price_history":       [
    {"date": "2025-06-22", "amount": 299.0},
    {"date": "2025-07-22", "amount": 299.0},
    {"date": "2026-04-22", "amount": 398.0}
  ],
  "period_days":         30,
  "first_payment_date":  "2025-06-22",
  "last_payment_date":   "2026-04-22",
  "next_payment_date":          "2026-05-22",
  "days_until_next_payment":    0,
  "n_payments":                 11,
  "status":              "price_increased",
  "confidence":          "high",
  "reasons":             ["Цена выросла с 299 ₽ до 398 ₽ (+99 ₽, +33%)"],
  "ml_probability":      0.98,
  "is_important":        false,
  "is_muted":            false,
  "is_hidden":           false,
  "is_false_positive":   false,
  "is_manual":           false
}
```

**Enums:**

| Поле | Значения |
|---|---|
| `category` | `streaming_video` · `streaming_music` · `cloud_storage` · `education` · `gaming` · `food_delivery` · `productivity` · `reading` · `other` |
| `status` | `active` · `price_increased` · `possibly_unused` · `trial_ending` |
| `confidence` | `high` · `low` |

`monthly_amount` = `amount × 30.44 / period_days` (вычисляется на бэке).

`days_until_next_payment` = `(next_payment_date − simulation_today).days` (вычисляется на бэке; может быть 0 или отрицательным).

**Флаги user_actions:**

| Флаг | Смысл | Влияние на список |
|---|---|---|
| `is_important` | Пользователь отметил как важную | — |
| `is_muted` | Уведомления отключены | Исключается из `/notifications` |
| `is_hidden` | Пользователь скрыл | Исключается из основного списка |
| `is_false_positive` | Пользователь отметил как ошибку ML | Исключается из основного списка |
| `is_manual` | Добавлена вручную, не из ML | — |

`is_hidden` и `is_false_positive` — разные флаги с разной семантикой, оба убирают подписку из основного списка.

---

### Notification

```json
{
  "date":          "2026-05-22",
  "text":          "Стоимость «Кинопоиск HD» выросла с 299 ₽ до 398 ₽.",
  "type":          "price_increased",
  "merchant_name": "Кинопоиск HD"
}
```

| Поле | Тип | Описание |
|---|---|---|
| `date` | string (ISO date) | Дата генерации уведомления |
| `text` | string | Текст на русском |
| `type` | string (enum) | `upcoming_payment` · `trial_ending` · `price_increased` · `summary` |
| `merchant_name` | string \| null | `null` для типа `summary` |

---

### TopSubscription (только внутри /analytics)

```json
{
  "merchant_name":  "Кинопоиск HD",
  "category":       "streaming_video",
  "amount":         398.0,
  "monthly_amount": 409.0,
  "status":         "price_increased"
}
```

---

### Recommendation

```json
{
  "merchant_name":  "VK Play Cloud",
  "text":           "Возможно, вам стоит проверить подписку «VK Play Cloud» — похоже, вы давно ею не пользуетесь.",
  "reasons":        [
    "За последние 3 месяца не было покупок в категории «игры» — возможно, вы не пользуетесь подпиской.",
    "Подписка активна 9 мес."
  ],
  "monthly_amount": 402.0
}
```

---

## Эндпоинты

### GET /clients

Список клиентов для демо-переключателя.

Порядок: scripted_01–10 первыми, затем client_0001…client_0140 в порядке id.
**Hard-negative клиенты (scripted_11–19) не включаются.**

**Ответ:**
```json
{
  "simulation_today": "2026-05-22",
  "clients": [
    {"id": "scripted_01", "label": "scripted_01 — рост цены",           "display_name": "Анна Петрова"},
    {"id": "scripted_02", "label": "scripted_02 — пробный период",      "display_name": "Дмитрий Соколов"},
    {"id": "scripted_03", "label": "scripted_03 — заброшенный gaming",  "display_name": "Максим Орлов"},
    {"id": "scripted_04", "label": "scripted_04 — много подписок",      "display_name": "Екатерина Волкова"},
    {"id": "scripted_05", "label": "scripted_05 — новичок",             "display_name": "Артём Новиков"},
    {"id": "scripted_06", "label": "scripted_06 — пересекающиеся даты", "display_name": "Ольга Кузнецова"},
    {"id": "scripted_07", "label": "scripted_07 — бывший пользователь", "display_name": "Илья Морозов"},
    {"id": "scripted_08", "label": "scripted_08 — дублирующиеся сервисы","display_name": "Полина Лебедева"},
    {"id": "scripted_09", "label": "scripted_09 — ложный триггер",      "display_name": "Кирилл Зайцев"},
    {"id": "scripted_10", "label": "scripted_10 — семейный план",       "display_name": "София Соловьёва"},
    {"id": "client_0001", "label": "client_0001",                       "display_name": "<faker ru_RU>"},
    {"id": "client_0002", "label": "client_0002",                       "display_name": "<faker ru_RU>"}
  ]
}
```

`display_name` — отображаемое имя для UI. Для `scripted_*` — фиксированные имена. Для `client_*` — детерминировано через `Faker('ru_RU').seed_instance(hash(client_id) % 2**32)`.
```

---

### GET /clients/{id}/subscriptions

**Query params:**

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `include_hidden` | bool | `false` | Включить подписки с `is_hidden=true` или `is_false_positive=true` |

**Ответ:**
```json
{
  "client_id": "scripted_01",
  "subscriptions": [
    { /* SubscriptionResponse */ },
    { /* SubscriptionResponse */ }
  ]
}
```

Порядок: `next_payment_date` ASC.
По умолчанию подписки с `is_hidden=true` или `is_false_positive=true` не включаются.

**Ошибки:** `404` если `client_id` не найден.

---

### GET /clients/{id}/analytics

**Ответ:**
```json
{
  "client_id":          "scripted_04",
  "monthly_total":      10763.0,
  "monthly_delta_rub":  -199.0,
  "monthly_delta_text": "-199 ₽ за месяц",
  "potential_savings":  769.0,
  "top_3": [
    {
      "merchant_name":  "Skillbox",
      "category":       "education",
      "amount":         4980.0,
      "monthly_amount": 4980.0,
      "status":         "active"
    },
    {
      "merchant_name":  "ChatGPT Plus",
      "category":       "productivity",
      "amount":         2580.0,
      "monthly_amount": 2580.0,
      "status":         "active"
    },
    {
      "merchant_name":  "GitHub Copilot",
      "category":       "productivity",
      "amount":         990.0,
      "monthly_amount": 1015.0,
      "status":         "active"
    }
  ],
  "recommendations": [
    {
      "merchant_name":  "Xbox Game Pass Ultimate",
      "text":           "Возможно, вам стоит проверить подписку «Xbox Game Pass Ultimate» — похоже, вы давно ею не пользуетесь.",
      "reasons":        [
        "За последние 3 месяца не было покупок в категории «игры» — возможно, вы не пользуетесь подпиской.",
        "Подписка активна 9 мес.",
        "Мерчант распознан как подписочный сервис."
      ],
      "monthly_amount": 769.0
    }
  ]
}
```

`top_3` и `potential_savings` учитывают только видимые (не hidden, не false_positive) подписки.

`monthly_delta_rub` = `monthly_total` (текущий) − сумма фактических платежей из `price_history` за предыдущий календарный месяц. `null` если данных за прошлый месяц нет или |delta| < 1 ₽.

`monthly_delta_text` — строка для UI: `"+N ₽ за месяц"` / `"-N ₽ за месяц"` / `null`.

---

### GET /clients/{id}/notifications

**Ответ:**
```json
{
  "client_id": "scripted_01",
  "notifications": [
    {
      "date":          "2026-05-22",
      "text":          "Стоимость «Кинопоиск HD» выросла с 299 ₽ до 398 ₽.",
      "type":          "price_increased",
      "merchant_name": "Кинопоиск HD"
    },
    {
      "date":          "2026-05-22",
      "text":          "Вы платите за 2 подписки, общая сумма — 612 ₽/мес.",
      "type":          "summary",
      "merchant_name": null
    }
  ]
}
```

Уведомления по подпискам с `is_muted=true` не включаются.
Уведомление `summary` присутствует всегда, пока есть хоть одна видимая подписка.

---

### POST /clients/{id}/actions

**Request body:**
```json
{
  "action_type":   "mark_important",
  "merchant_name": "Кинопоиск HD"
}
```

**Допустимые значения `action_type`:**

| Значение | Эффект |
|---|---|
| `mark_important` | `is_important = true` |
| `unmark_important` | `is_important = false` |
| `mute_notifications` | `is_muted = true` |
| `unmute_notifications` | `is_muted = false` |
| `mark_false_positive` | `is_false_positive = true` (убирает из основного списка) |
| `hide` | `is_hidden = true` (убирает из основного списка) |
| `unhide` | `is_hidden = false`, `is_false_positive = false` (возвращает в список) |

Все действия идемпотентны: повторная отправка возвращает `200 OK`, состояние не меняется.

**Ответ:**
```json
{"ok": true}
```

**Ошибки:** `400` если `action_type` неизвестен или `merchant_name` не найден у клиента.

---

### POST /clients/{id}/subscriptions/manual

**Request body:**
```json
{
  "merchant_name": "Notion",
  "amount":        900.0,
  "period_days":   30,
  "category":      "productivity"
}
```

| Поле | Тип | Обязательное | Ограничения |
|---|---|---|---|
| `merchant_name` | string | да | непустая строка |
| `amount` | number | да | > 0 |
| `period_days` | integer | да | 1–366 |
| `category` | string (enum) | да | из списка категорий |

**Ответ (201 Created):** полный `SubscriptionResponse` с:
- `is_manual = true`
- `status = "active"`
- `confidence = "high"`
- `reasons = ["Добавлено вручную"]`
- `ml_probability = 1.0`
- `next_payment_date` = дата первого ожидаемого списания (today + period_days)
- `price_history = [{"date": "<today>", "amount": <amount>}]`

**Ошибки:** `400` если поля невалидны.
