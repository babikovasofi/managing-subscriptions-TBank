# Handoff — T-Bank-inspired Subscriptions

Mobile screens (~430px) для «Управление подписками» в стиле Т-Банка. HTML + CSS, готов к подключению к API в Next.js.

> ⚠️ В макетах **не воспроизведены** охраняемые элементы фирстиля: щит-логотип «Т», пилюля «Т-БАНК», лицензированный шрифт **dsText/dsHeading**. Эстетика передана через близкие токены (цвета, скругления, шкала, плотность). Шрифт-плейсхолдер — **Manrope** (открытый аналог).

## Архитектура (mobile-first)

```html
<body>
  <div class="screen" data-screen-label="...">   <!-- max-width 430, mx auto -->
    <header class="top-bar">...</header>
    <!-- content sections -->
  </div>
  <nav class="tabbar">...</nav>                  <!-- position: fixed, bottom: 0 -->
</body>
```

- `width=device-width, initial-scale=1, viewport-fit=cover`
- Контейнер `.screen` — 100%, max-width 430, по центру
- Все раскладки **в одну колонку**, без сайдбаров и горизонтальных сеток
- Tabbar — `position: fixed`, viewport-scoped, centered, max-width 430
- Touch-таргеты ≥ 44px (`.icon-button`, `.client-switcher`, `.btn--md`, `.row`)
- Safe-area (`env(safe-area-inset-*)`) учтены для notch / home indicator

## Структура файлов

| Файл | Что |
|---|---|
| **`design-system.css`** | 🎯 **Один блок:** все токены, обе темы, типографика, кнопки, бейджи, иконки категорий. Это то, что просили на хэндофф. |
| `tokens.css` | Альтернативный split — только переменные. |
| `app.css` | Общий хром: phone-frame, status-bar, top-bar, tab-bar, ряды, общие компоненты. |
| `theme.js` | Pre-paint apply + handler для `data-action="toggle-theme"`. Тема сохраняется в `localStorage` под ключом `tb-theme`. |
| `subscriptions.css` / `detail.css` / `analytics.css` / `notifications.css` / `add.css` | Per-screen стили. |
| `brand-system.md` | Подробная сводка по тому, как извлечены и применены токены. |

## HTML-файлы экранов

| Файл | Назначение |
|---|---|
| **`Subscriptions.html`** | Главный: список из 6 подписок, переключатель темы. |
| `Subscription Detail.html` | Детали (на примере «Цена выросла» — Кинопоиск HD). |
| `Analytics.html` | Donut по категориям + Топ-3 + «Можно сэкономить». |
| `Notifications.html` | Лента, сгруппированная по дням. |
| `Add Subscription.html` | Bottom-sheet с формой. |
| `All Screens.html` | Обзорный canvas (для ревью). |

## Темы

```html
<html data-theme="dark">  <!-- default -->
<html data-theme="light">
```

Подключай `theme.js` синхронно в `<head>` — он применяет сохранённую тему до first paint. Переключатель только на главном экране (`Subscriptions.html`), состояние общее для всех экранов через `localStorage.tb-theme`.

## Иерархия 4 статусов подписки

```html
<li data-status="trial_ending">
  …
  <span class="badge badge--trial">Пробный · 2 дня</span>
</li>
```

| `data-status` | Бейдж | Когда показывать |
|---|---|---|
| `trial_ending` | `.badge--trial` — solid orange | Пробный период заканчивается ≤ N дней |
| `price_increased` | `.badge--price` — tinted orange + ↑ | Цена выросла |
| `possibly_unused` | `.badge--unused` — нейтраль + янтарная точка | Не открывали ≥ 30 дней |
| `active` | без чипа (опционально зелёная точка `.sub__active-dot`) | Норма |

🚫 **Никогда** не используй красный `#F52222` для статусов — он зарезервирован для destructive-действий (удалить/скрыть). Банк не должен пугать клиента.

## Контракт `data-action` для Next.js

| Экран | Селектор | `data-action` | Дополнительно |
|---|---|---|---|
| Subscriptions | `.client-switcher` | `open-client-switcher` | |
| Subscriptions | `#theme-toggle` | `toggle-theme` | |
| Subscriptions | `.insight__cta` | `navigate-analytics` | href `/analytics` |
| Subscriptions | `.sub` (×6) | `open-subscription` | `data-subscription-id` |
| Subscription Detail | `.action` (×2 toggle) | `toggle-important`, `toggle-notifications` | input[type=checkbox] |
| Subscription Detail | `.action` row | `mark-not-subscription` | |
| Subscription Detail | `.action--destructive` | `hide-subscription` | |
| Analytics | `.rank` (×3) | `open-subscription` | `data-subscription-id` |
| Notifications | `.notif` (×5) | `open-notification` | `data-notification-id` |
| Add | `.sheet__close` | `close-sheet` | |
| Add | `.segmented__item` (×3) | `set-period` | `data-period="week\|month\|year"` |
| Add | `.field--picker` | `pick-category` | |
| Add | `.btn--primary` (submit) | `submit-subscription` | |

Tab-bar и back-button — обычная навигация по `href`, `data-action` не нужен.

## Quick start (Next.js)

1. Скопировать `design-system.css` в `app/globals.css` (или импортировать в `layout.tsx`).
2. Загрузить Manrope через `next/font/google`:
   ```ts
   import { Manrope } from 'next/font/google';
   const manrope = Manrope({ subsets: ['cyrillic','latin'], weight: ['400','500','600','700','800'] });
   ```
3. На корневом `<html>` поставить `data-theme="dark"` (или применить логику из `theme.js` через `useEffect`).
4. На клик `[data-action="toggle-theme"]` менять `data-theme` и писать в `localStorage`.
5. Подключить обработчики на `[data-action="*"]` — атрибуты сами говорят, куда вести.

## Известное и важное

- **Шрифт:** Manrope — плейсхолдер. На бою заменяй на лицензированный фирменный.
- **Иконки сервисов:** в макетах используются обобщённые **категорийные** глифы (фильм / музыка / геймпад / облако / шапочка). На бою — подставляй реальные логотипы сервисов из своего лицензированного набора.
- **Логотип Т-Банка:** не в дизайне; добавь его в брандированном виде сам.
