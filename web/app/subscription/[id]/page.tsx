"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getSubscriptions, postAction } from "@/lib/api";
import type { SubscriptionResponse } from "@/lib/types";
import { useClient } from "@/lib/ClientContext";
import { CategoryIcon } from "@/components/ui/CategoryIcon";
import {
  formatRub,
  formatDateRu,
  daysUntil,
  daysLabel,
  shortMonthFromYYYYMM,
} from "@/lib/utils";

export default function SubscriptionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { clientId, simulationToday } = useClient();
  const [sub, setSub] = useState<SubscriptionResponse | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  const merchantName = decodeURIComponent(params.id as string);

  const fetchSub = () => {
    if (!clientId) return;
    setLoading(true);
    getSubscriptions(clientId)
      .then((res) => {
        const found = res.subscriptions.find((s) => s.merchant_name === merchantName);
        setSub(found ?? null);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSub();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId, merchantName]);

  const handleAction = async (action: Parameters<typeof postAction>[2]) => {
    await postAction(clientId, merchantName, action);
    fetchSub();
  };

  if (loading && sub === undefined) {
    return (
      <div className="screen">
        <header className="top-bar">
          <button className="icon-button back-button" onClick={() => router.back()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6"/>
            </svg>
          </button>
          <div className="top-bar__center">Подписка</div>
          <div className="top-bar__spacer" />
        </header>
        <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-2)" }}>
          Загрузка...
        </div>
      </div>
    );
  }

  if (sub === null) {
    return (
      <div className="screen">
        <header className="top-bar">
          <button className="icon-button back-button" onClick={() => router.back()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6"/>
            </svg>
          </button>
          <div className="top-bar__center">Подписка</div>
          <div className="top-bar__spacer" />
        </header>
        <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-2)" }}>
          Подписка не найдена
        </div>
      </div>
    );
  }

  if (!sub) return null;

  // History chart computation
  const byMonth = new Map<string, number>();
  for (const e of sub.price_history) {
    byMonth.set(e.date.slice(0, 7), e.amount);
  }
  const months = Array.from(byMonth.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  const last6 = months.slice(-6);
  const maxAmt = last6.length > 0 ? Math.max(...last6.map(([, a]) => a)) : 1;
  const currentMonth = simulationToday.slice(0, 7);
  const newPrice = sub.amount;
  const bars = last6.map(([ym, amt]) => ({
    ym,
    amount: Math.round(amt),
    height: Math.round((amt / maxAmt) * 100),
    isNew: amt >= newPrice * 0.98,
    isCurrent: ym === currentMonth,
  }));

  // Price increase info
  let oldPrice: number | null = null;
  if (sub.status === "price_increased" && sub.price_history.length > 0) {
    const sorted = [...sub.price_history].sort((a, b) => a.date.localeCompare(b.date));
    for (const e of sorted) {
      if (e.amount < newPrice * 0.97) {
        oldPrice = e.amount;
        break;
      }
    }
  }

  const categoryLabel: Record<string, string> = {
    streaming_video: "Видеостриминг",
    streaming_music: "Музыкальный стриминг",
    cloud_storage: "Облачное хранилище",
    education: "Образование",
    gaming: "Игры",
    food_delivery: "Доставка еды",
    productivity: "Продуктивность",
    reading: "Чтение",
    other: "Другое",
  };

  const periodLabel = sub.period_days <= 8 ? "в неделю" : "в месяц";
  const nextDate = formatDateRu(sub.next_payment_date);
  const daysLeft = daysUntil(sub.next_payment_date, simulationToday);

  const showLegend = sub.status === "price_increased" && oldPrice !== null;

  return (
    <div className="screen">
      {/* Top bar */}
      <header className="top-bar">
        <button className="icon-button back-button" onClick={() => router.back()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <div className="top-bar__center">{sub.merchant_name}</div>
        <div className="top-bar__spacer" />
      </header>

      {/* Detail hero */}
      <div className="detail-hero">
        <div className="detail-hero__head">
          <CategoryIcon category={sub.category} size="lg" />
          <div className="detail-hero__meta">
            <div className="detail-hero__name">{sub.merchant_name}</div>
            <div className="detail-hero__sub">{categoryLabel[sub.category] ?? "Другое"}</div>
          </div>
        </div>
        <div className="detail-hero__price-row">
          <div className="detail-hero__price">
            {formatRub(sub.amount)}
            <span className="detail-hero__price-suffix">{periodLabel}</span>
          </div>
          {sub.status === "price_increased" && (
            <span className="badge badge--price badge--lg">
              <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 9V3M3 6l3-3 3 3"/>
              </svg>
              Цена выросла
            </span>
          )}
          {sub.status === "trial_ending" && (
            <span className="badge badge--trial badge--lg">
              Пробный период
            </span>
          )}
          {sub.status === "possibly_unused" && (
            <span className="badge badge--unused badge--lg">Не используется</span>
          )}
        </div>
        <div className="detail-hero__next">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="1" y="2" width="12" height="11" rx="2"/>
            <line x1="1" y1="5" x2="13" y2="5"/>
            <line x1="4" y1="1" x2="4" y2="3"/>
            <line x1="10" y1="1" x2="10" y2="3"/>
          </svg>
          Следующее списание <b>{nextDate}</b> — {daysLabel(daysLeft)}
        </div>
      </div>

      {/* "Что происходит" card */}
      <div className="card">
        <div className="card__title">Что происходит</div>

        {sub.status === "price_increased" && oldPrice !== null && (
          <>
            <div className="explain__delta">
              <span className="explain__old">{formatRub(oldPrice)}</span>
              <span className="explain__arrow">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 8h10M9 4l4 4-4 4"/>
                </svg>
              </span>
              <span className="explain__new">{formatRub(newPrice)}</span>
              <span className="explain__delta-badge">
                +{Math.round(((newPrice - oldPrice) / oldPrice) * 100)}%
              </span>
            </div>
            <div className="explain__text">
              Стоимость подписки выросла. За год вы заплатите дополнительно{" "}
              {formatRub(Math.abs((newPrice - oldPrice) * (365 / sub.period_days)))}.
            </div>
          </>
        )}

        {sub.status === "trial_ending" && (
          <div className="explain__text">
            Пробный период заканчивается. С <b>{formatDateRu(sub.next_payment_date)}</b> начнётся
            регулярное списание <b>{formatRub(sub.amount)}</b>.
          </div>
        )}

        {sub.status === "possibly_unused" && (
          <div className="explain__text">
            {sub.reasons[0] ?? "Похоже, вы давно не используете эту подписку."}
          </div>
        )}

        {sub.status === "active" && (
          <div className="explain__text">
            {sub.reasons[0] ?? "Подписка активна и регулярно списывается."}
          </div>
        )}
      </div>

      {/* History chart */}
      {bars.length > 0 && (
        <div className="card">
          <div className="card__title">История списаний</div>
          {showLegend && (
            <div className="history__legend">
              <div className="history__legend-item">
                <span className="history__legend-swatch history__legend-swatch--old" />
                Старая цена
              </div>
              <div className="history__legend-item">
                <span className="history__legend-swatch history__legend-swatch--new" />
                Новая цена
              </div>
            </div>
          )}
          <div className="history__chart">
            {bars.map(({ ym, amount, height, isNew }) => (
              <div key={ym} className={`history__bar${isNew && showLegend ? " history__bar--new" : ""}`}>
                <div className="history__bar-value">{amount}</div>
                <div className="history__bar-fill" style={{ height: `${Math.max(height, 8)}%` }} />
              </div>
            ))}
          </div>
          <div className="history__labels">
            {bars.map(({ ym, isCurrent }) => (
              <div key={ym} className={`history__label${isCurrent ? " history__label--current" : ""}`}>
                {shortMonthFromYYYYMM(ym)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <ul className="actions">
        <li>
          <button
            className="action"
            style={{ width: "100%", background: "none", border: "none", textAlign: "left" }}
            onClick={() => handleAction(sub.is_important ? "unmark_important" : "mark_important")}
          >
            <div className="cat-icon cat-icon--sm cat-icon--info">
              <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="9 2 11.09 7.26 17 7.27 12.5 10.73 14.18 16 9 12.77 3.82 16 5.5 10.73 1 7.27 6.91 7.26 9 2"/>
              </svg>
            </div>
            <div className="action__body">
              <div className="action__title">
                {sub.is_important ? "Убрать из важных" : "Отметить как важную"}
              </div>
              <div className="action__sub">
                {sub.is_important ? "Убрать метку важной подписки" : "Всегда показывать вверху"}
              </div>
            </div>
            <label className="toggle" onClick={(e) => e.stopPropagation()}>
              <input
                type="checkbox"
                checked={sub.is_important}
                onChange={() => handleAction(sub.is_important ? "unmark_important" : "mark_important")}
              />
              <div className="toggle__track">
                <div className="toggle__thumb" />
              </div>
            </label>
          </button>
        </li>
        <li>
          <button
            className="action"
            style={{ width: "100%", background: "none", border: "none", textAlign: "left" }}
            onClick={() => handleAction(sub.is_muted ? "unmute_notifications" : "mute_notifications")}
          >
            <div className="cat-icon cat-icon--sm cat-icon--cloud">
              <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 10a5 5 0 0 0-10 0c0 5-2 7-2 7h14s-2-2-2-7"/>
                <path d="M10.73 16a2 2 0 0 1-3.46 0"/>
              </svg>
            </div>
            <div className="action__body">
              <div className="action__title">
                {sub.is_muted ? "Включить уведомления" : "Отключить уведомления"}
              </div>
              <div className="action__sub">
                {sub.is_muted
                  ? "Снова получать напоминания"
                  : "Не напоминать об этой подписке"}
              </div>
            </div>
            <label className="toggle" onClick={(e) => e.stopPropagation()}>
              <input
                type="checkbox"
                checked={!sub.is_muted}
                onChange={() => handleAction(sub.is_muted ? "unmute_notifications" : "mute_notifications")}
              />
              <div className="toggle__track">
                <div className="toggle__thumb" />
              </div>
            </label>
          </button>
        </li>
      </ul>

      <ul className="actions">
        <li>
          <button
            className="action action--destructive"
            style={{ width: "100%", background: "none", border: "none", textAlign: "left" }}
            onClick={() => {
              if (window.confirm("Пометить как ошибочно определённую?")) {
                handleAction("mark_false_positive").then(() => router.push("/"));
              }
            }}
          >
            <div className="action__body">
              <div className="action__title">Это не подписка</div>
              <div className="action__sub" style={{ color: "var(--text-2)" }}>Убрать из списка подписок</div>
            </div>
            <div className="action__chev">
              <svg width="7" height="12" viewBox="0 0 7 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 1l5 5-5 5"/>
              </svg>
            </div>
          </button>
        </li>
        <li>
          <button
            className="action action--destructive"
            style={{ width: "100%", background: "none", border: "none", textAlign: "left" }}
            onClick={() => {
              if (window.confirm("Скрыть подписку?")) {
                handleAction("hide").then(() => router.push("/"));
              }
            }}
          >
            <div className="action__body">
              <div className="action__title">Скрыть подписку</div>
              <div className="action__sub" style={{ color: "var(--text-2)" }}>Не показывать в списке</div>
            </div>
            <div className="action__chev">
              <svg width="7" height="12" viewBox="0 0 7 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 1l5 5-5 5"/>
              </svg>
            </div>
          </button>
        </li>
      </ul>

      <div className="detail-bottom-pad" />
    </div>
  );
}
