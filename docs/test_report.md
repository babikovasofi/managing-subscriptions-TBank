# Integration Test Report

**Date:** 2026-05-24  
**API:** http://localhost:8000  
**simulation_today:** 2026-05-22

---

## Summary

| # | Проверка | Результат | Баги |
|---|---|---|---|
| 1 | GET /clients | ✅ PASS | — |
| 2 | Статусы по 10 сценариям | ✅ PASS | — |
| 3 | Аналитика | ✅ PASS | Грязные данные в БД (см. ниже) |
| 4 | Уведомления | ⚠️ PARTIAL | API генерирует тип `possibly_unused`, которого нет в ТЗ |
| 5 | Действия пользователя | ✅ PASS | — |
| 6 | Ручное добавление | ✅ PASS | — |

---

## Проверка 1: GET /clients

- [x] Все 10 scripted_01–10 присутствуют
- [x] display_name не пустой у каждого
- [x] scripted_01 = "Анна Петрова", scripted_03 = "Максим Орлов" — верно
- [x] Hard-negative клиенты scripted_11–19 отсутствуют
- [x] simulation_today = "2026-05-22" присутствует

---

## Проверка 2: Статусы по сценариям

| client | сценарий | подписок | ожид. статус | реальный статус | OK? |
|---|---|---|---|---|---|
| scripted_01 | price_increase | 2 | price_increased | price_increased ✓ (+ active) | ✅ |
| scripted_02 | trial_ending | 1 | trial_ending | trial_ending | ✅ |
| scripted_03 | abandoned_gaming | 1 | possibly_unused | possibly_unused | ✅ |
| scripted_04 | heavy_user | 9 (включая тест) | active ≥6 | active + price_increased | ✅ |
| scripted_05 | newbie | 1 | active | active | ✅ |
| scripted_06 | overlapping_dates | 4 | active | active | ✅ |
| scripted_07 | former_user | 2 | active/мало | active | ✅ |
| scripted_08 | duplicate_services | 2 | active (оба) | active | ✅ |
| scripted_09 | false_positive_trap | 1 (Telegram) | фитнес∉list | фитнес не попал | ✅ |
| scripted_10 | family_plan | 1 | active | active | ✅ |

Примечание по scripted_09: у клиента есть Telegram Premium (реальная подписка). Абонемент фитнес-клуба (ложный триггер) в список **не попал** — ML отработал корректно.

---

## Проверка 3: Аналитика

**scripted_01:**
- monthly_total: 597.21 ✅
- monthly_delta_rub: -5.95, text: "-6 ₽ за месяц" ✅
- potential_savings: 0.0 ✅
- top_3: возвращает 2 (у клиента всего 2 подписки) — **не баг**, ожидаемо ✅
- recommendations: 0 ✅

**scripted_04:**
- monthly_total: 17 395.43 ✅
- monthly_delta_rub: 9361.48, text: "+9361 ₽ за месяц" ✅
- potential_savings: 460.14 ✅
- top_3: 3 записи ✅
- recommendations: 1 ✅

### Замечание: грязные данные (не баг кода)

В таблице `manual_subscriptions` обнаружена запись-артефакт от предыдущей тест-сессии (2026-05-23):

```
client_id=scripted_04, merchant_name='оо', amount=9090.0
```

Эта запись появляется в top_3 аналитики и в списке подписок scripted_04. **Фикс перед деплоем: очистить `manual_subscriptions` через `DELETE FROM manual_subscriptions`.**

---

## Проверка 4: Уведомления

| client | тип | ожид. | реальный | OK? |
|---|---|---|---|---|
| scripted_01 | price_increased | есть | есть | ✅ |
| scripted_01 | summary | есть | есть | ✅ |
| scripted_02 | trial_ending | есть | есть | ✅ |
| scripted_02 | summary | есть | есть | ✅ |
| scripted_03 | possibly_unused | **не должно быть** | **есть** | ⚠️ |
| scripted_03 | upcoming_payment | — | есть | ✅ |
| scripted_03 | summary | есть | есть | ✅ |

### Баг: API генерирует тип `possibly_unused` (не в ТЗ)

**Описание:** Backend генерирует уведомления с `type: "possibly_unused"` для подписок со статусом `possibly_unused`. Однако:
- ТЗ §11 перечисляет только 4 триггера: `upcoming_payment`, `trial_ending`, `price_increased`, `summary` — `possibly_unused` отсутствует
- API-контракт (`docs/api_contract.md`) не включает этот тип
- `web/lib/types.ts`: `NotificationType` не содержит `"possibly_unused"` (удалён намеренно)

**Эффект:** Фронт получит уведомление с неизвестным типом. TypeScript не упадёт (runtime строка), но иконка/стиль будут неверными — уведомление не попадёт ни в один `if/switch` по типу.

**Предлагаемый фикс (на выбор):**
1. **Убрать генерацию из backend** — удалить блок, который добавляет possibly_unused уведомления в `api/app/main.py`.
2. **Добавить тип во фронт** — вернуть `"possibly_unused"` в `NotificationType` и добавить рендер иконки/текста в компонент уведомлений.

Вариант 1 соответствует ТЗ. Вариант 2 — дополнительная функциональность сверх ТЗ, обогащает демо для scripted_03.

---

## Проверка 5: Действия пользователя (scripted_01 / Кинопоиск HD)

| шаг | действие | ожид. | результат | OK? |
|---|---|---|---|---|
| 1 | mark_important | 200 ok:true | 200 ok:true | ✅ |
| 2 | GET → is_important | true | true | ✅ |
| 3 | mute_notifications | 200 ok:true | 200 ok:true | ✅ |
| 4 | mark_false_positive | 200 ok:true | 200 ok:true | ✅ |
| 5 | GET → is_false_positive + is_muted | true+true | true+true | ✅ |
| 5 | GET default list → Кинопоиск отсутствует | absent | absent | ✅ |
| 6 | hide | 200 ok:true | 200 ok:true | ✅ |
| 7 | GET → Кинопоиск отсутствует | absent | absent | ✅ |

Все флаги работают корректно, идемпотентность не нарушена.

---

## Проверка 6: Ручное добавление (scripted_05)

```
POST /api/v1/clients/scripted_05/subscriptions/manual
{"merchant_name": "Тест Сервис", "amount": 299, "period_days": 30, "category": "other"}
```

- HTTP 201 Created ✅
- merchant_name = "Тест Сервис" ✅
- is_manual = true ✅
- status = "active" ✅
- next_payment_date = "2026-06-21" (today + 30 дней) ✅
- Подписка появляется в GET /subscriptions ✅

---

## Итог: что нужно сделать перед деплоем

### Обязательно (блокирует деплой)
1. **Очистить грязные данные:** `DELETE FROM manual_subscriptions;` — убрать артефакт "оо" и тестовые записи.

### На обсуждение
2. **Possibly_unused уведомления:** решить — убрать из backend или добавить поддержку во фронт. Оба варианта допустимы, ждём решения.
