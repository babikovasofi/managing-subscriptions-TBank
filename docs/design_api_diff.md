# Design / API Gap Analysis

**Дата:** 2026-05-23  
**Ревьюер:** Claude Code  
**Метод:** Живые ответы API (`/api/v1`) для `scripted_01` и `scripted_03` сравнены с HTML-макетами в `/design/`.

API поднят локально через `python -m uvicorn api.app.main:app --port 8000`.  
Образцы ответов сохранены в `docs/api_samples/`.

---

## Расхождения (требуют решения)

| # | Экран | Что в макете | Что в API | Решение (предложение) |
|---|---|---|---|---|
| 1 | Subscriptions, Analytics Hero | `+199 ₽ за месяц` / `+199 ₽ к апрелю` | Нет поля. `analytics.monthly_total` — только текущий месяц, прошлого нет | TBD: убрать дельту из UI **либо** добавить поле `monthly_total_prev` в `/analytics` |
| 2 | Subscriptions (possibly_unused) | `42 дня без активности` в sub__meta вместо даты следующего списания | API не возвращает «последнюю дату активности». `reasons[0]` = «За последние 3 месяца не было покупок в категории «игры»» (без числа дней) | Показывать `next_payment_date` как у других карточек **либо** добавить поле `days_inactive` в `SubscriptionResponse` |
| 3 | Analytics | Donut-диаграмма с разбивкой по категориям: Обучение 1490, Видео 797, Игры 402, Музыка 299, Хранилище 149 | `/analytics` не содержит разбивки по категориям — только `monthly_total`, `top_3`, `recommendations` | Фронт вызывает `/subscriptions`, сам агрегирует `monthly_amount` по `category`. Добавлять поле в API не нужно, но явно задокументировать это как фронтенд-вычисление |
| 4 | Analytics «Можно сэкономить» | Показывает **и** `possibly_unused` (VK Play Cloud 402₽), **и** `trial_ending` (ivi 399₽) как потенциальную экономию; итого 801₽ | `recommendations[]` содержит **только** `possibly_unused`. `trial_ending`-подписки не попадают в `recommendations` и не учитываются в `potential_savings` | Фронт дополнительно читает `/subscriptions`, выбирает подписки со статусом `trial_ending`, добавляет их в блок «Можно сэкономить» рядом с `recommendations`; суммарная «экономия» = `potential_savings` + сумма trial_ending monthly_amount |
| 5 | Analytics «Можно сэкономить» | `Вы не открывали сервис 42 дня` в тексте рекомендации | `recommendation.reasons[0]` = «За последние 3 месяца не было покупок…» — нет числа дней | Использовать текст из `reasons[]` дословно, убрать «42 дня» из макета |
| 6 | Notifications | Тип «Возможно не используете» (notification `possibly_unused`) с текстом «Вы не открывали VK Play Cloud 42 дня» | API-типы уведомлений: `upcoming_payment · trial_ending · price_increased · summary`. Типа `possibly_unused` **нет**. Вместо него API присылает `upcoming_payment` для той же подписки | TBD: добавить тип `possibly_unused` в `/notifications` и в api_contract.md **либо** не показывать отдельный блок, а обозначить «Не используется» в тексте `upcoming_payment` |
| 7 | Notifications | Сводка «Потратили за апрель 2648₽. На 199₽ меньше, чем в мае» | API `summary` = «Вы платите за N подписок, общая сумма — X₽/мес.» (текущее состояние, нет исторических данных) | Использовать текст API дословно. Историческую сводку не показывать (нет данных) |
| 8 | Notifications | Временны́е метки внутри дня: «2ч», «5ч» | Поле `date` в уведомлении — ISO-дата (`YYYY-MM-DD`), время отсутствует | Показывать только дату («сегодня», «вчера», «3 дня назад»). Убрать часовую точность из макета |
| 9 | Notifications | Индикатор «не прочитано» (`.notif--unread`, красная точка) | API не хранит read/unread-состояние уведомлений | Хранить read-состояние только в `localStorage` (сброс при смене клиента). Пометить как frontend-only без персистентности |
| 10 | Add Subscription | Сегментированный контрол периода: **Неделя / Месяц / Год** | API принимает `period_days: 1–366`, т.е. Год (365) технически валиден. Но CLAUDE.md §14 явно: *«Не делаем годовые подписки в MVP»* | Убрать «Год» из сегментированного контрола. Оставить только **Неделя (7)** и **Месяц (30)** |
| 11 | Subscription Detail «Что происходит» | `с 1 апреля 2026` — дата начала роста цены | API в `reasons[0]` содержит текст «Цена выросла с X₽ до Y₽ (+Z₽, +N%)» без даты. Дата перехода **может** быть вычислена из `price_history` (первая запись с новой ценой), но явно не возвращается | Вычислять дату из `price_history` на фронте: найти первый элемент, где `amount ≥ new_price_threshold` |
| 12 | Subscription Detail «Что происходит» | `За год вы заплатите на 1 188₽ больше` | Не в API | Фронт вычисляет: `(new_monthly_amount − old_monthly_amount) × 12`. Старую цену берёт из `price_history[0]` |
| 13 | Subscription Detail | История bar-chart показывает 6 баров с месячными метками | `price_history` содержит все платежи (11 для scripted_01). Нет поля «месяц» — только дата и сумма | Фронт группирует `price_history` по месяцу (последнее значение в месяце), берёт последние 6 месяцев. Не gap, но нужно явно реализовать |
| 14 | Subscriptions, Add backdrop | Имя клиента «Анна Петрова», аватар «АП» | API `/clients` возвращает только `id` и `label` (например, `scripted_01 — рост цены`). Нет поля `name`, `avatar_initials` | Генерировать имя/инициалы из `label` (первые буквы) **либо** использовать `label` как отображаемое имя; убрать человеческое имя из макета |
| 15 | Subscriptions | iCloud+ как один из 6 сервисов в списке | Сервиса iCloud нет в `subscriptions.json` (удалён, заменён на МегаФон Облако). Будет отсутствовать в ответе `/subscriptions` любого клиента | Макет использует устаревший placeholder; в реализации использовать реальные данные из API — никакого action не требует |
| 16 | Subscriptions | `200 ГБ` и `курс «UX-дизайн»` в sub__meta для iCloud+ и Skillbox | В `SubscriptionResponse` нет поля `plan_name`, `tier`, `description` | Убрать статичные детали тарифа из sub__meta. Для `active`-подписок показывать только `next_payment_date` + «через N дней» |
| 17 | HANDOFF.md data-action | `data-action="mark-not-subscription"` | API action_type = `"mark_false_positive"` | Маппинг в реализации: по `data-action="mark-not-subscription"` отправлять `action_type: "mark_false_positive"`. Задокументировать явно |
| 18 | Subscriptions, Analytics | Цены в макете: Кинопоиск 398₽, VK Play Cloud 402₽ | API возвращает суммы с синтетическим джиттером: 396.26₽ и 401.1₽. Не совпадают до рубля | Ожидаемо — синтетика. Использовать `amount` из API, не захардкоживать суммы. Не issue для реализации |
| 19 | Analytics top_3 | Процент «52% всех расходов» рядом с названием | API top_3 не содержит процента. Есть `monthly_amount` и `analytics.monthly_total` | Фронт вычисляет: `round(item.monthly_amount / monthly_total * 100)`. Не gap, просто frontend-математика |
| 20 | Subscriptions, Notifications | Глубокая ссылка `data-subscription-id="kinopoisk-hd"` (slug) | API идентифицирует подписку по `merchant_name` (кириллическая строка `"Кинопоиск HD"`), нет числового или slug-идентификатора | Использовать `merchant_name` как ключ при вызове `POST /actions`. Slug в `data-subscription-id` — удобство для JS-роутинга, маппинг slug→merchant_name реализовать на фронте |

---

## Совпадает (правок не требует)

| Экран | Элемент | Статус |
|---|---|---|
| Все | 4 вкладки таба (Подписки / Аналитика / Уведомления / Добавить) | ✅ Соответствуют структуре |
| Все | `simulation_today` из `GET /clients` используется как «сегодня» | ✅ Системная дата не используется |
| Subscriptions | 4 статуса + классы бейджей (`data-status`, `.badge--trial/price/unused`) | ✅ Совпадают с API enum |
| Subscriptions | `merchant_name`, `amount`, `next_payment_date`, `status` | ✅ Все поля есть в API |
| Subscriptions | «через N дней» — вычисляется из `next_payment_date` и `simulation_today` | ✅ Данные для вычисления есть |
| Subscription Detail | Флаги `is_important`, `is_muted` → toggles «Важная» и «Уведомления» | ✅ API возвращает флаги, экшены есть |
| Subscription Detail | `hide` action → «Скрыть подписку» | ✅ `action_type: "hide"` в API |
| Subscription Detail | `mark_false_positive` → «Это не подписка» (через маппинг, см. #17) | ✅ Экшен есть |
| Subscription Detail | `price_history` для bar-chart | ✅ Массив дат+сумм есть |
| Analytics | `top_3` с `merchant_name`, `monthly_amount`, `status` | ✅ Возвращается из `/analytics` |
| Analytics | `potential_savings` (экономия только по `possibly_unused`) | ✅ Поле есть |
| Analytics | `recommendations[]` с `text`, `reasons`, `monthly_amount` | ✅ Массив есть |
| Notifications | Типы `price_increased`, `trial_ending`, `upcoming_payment` | ✅ Все три генерируются API |
| Notifications | Тип `summary` (всегда присутствует при наличии подписок) | ✅ Есть |
| Notifications | Группировка по дням — фронт считает сам из поля `date` | ✅ Данных достаточно |
| Add | Поля `merchant_name`, `amount`, `period_days`, `category` | ✅ Соответствуют `POST /subscriptions/manual` |
| Add | `period_days` integer 1–366 покрывает Неделю (7) и Месяц (30) | ✅ |
| Add | Enum категорий (Видео/Музыка/Игры/…) — совпадают с API category enum | ✅ |
| Все | `data-action` для навигации через tab-bar — обычные `href`, без API | ✅ |
| Все | Тема light/dark через `data-theme` + `localStorage` | ✅ Не связано с API |

---

## Итого по приоритетам

**Блокеры реализации (нужно решение до написания кода):**
- #1 `+199₽` — историческое сравнение (нет в API)
- #4 `trial_ending` в «Можно сэкономить» — не в `recommendations`
- #6 `possibly_unused` нотификация — нет типа в API
- #10 «Год» в форме — против политики CLAUDE.md

**Фронтенд-вычисления (не требуют изменений API, просто реализовать):**
- #3 Donut: агрегация по категориям из `/subscriptions`
- #11 Дата роста цены из `price_history`
- #12 Годовая переплата
- #13 Группировка `price_history` по месяцам для bar-chart
- #19 Процент в top_3

**Дизайн-правки (макет устарел / неточен):**
- #2, #5 «42 дня» — нет источника данных
- #7 Историческая сводка в summary
- #8 Часовые метки в уведомлениях
- #14 Имя клиента «Анна Петрова»
- #15 iCloud+ устарел
- #16 Детали тарифа (200 ГБ, курс)

**Маппинг (не gap, задокументировать):**
- #17 `mark-not-subscription` → `mark_false_positive`
- #20 slug → `merchant_name`
