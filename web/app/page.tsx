"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSubscriptions } from "@/lib/api";
import type { SubscriptionResponse } from "@/lib/types";
import { useClient } from "@/lib/ClientContext";
import { CategoryIcon } from "@/components/ui/CategoryIcon";
import { formatRub, daysUntil, formatDateRu, daysLabel } from "@/lib/utils";

export default function SubscriptionsPage() {
  const router = useRouter();
  const { clientId, simulationToday } = useClient();
  const [subscriptions, setSubscriptions] = useState<SubscriptionResponse[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSubscriptions(clientId)
      .then((res) => {
        setSubscriptions(res.subscriptions);
      })
      .finally(() => setLoading(false));
  }, [clientId]);

  function handleThemeToggle() {
    const html = document.documentElement;
    const current = html.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    html.setAttribute("data-theme", next);
    localStorage.setItem("tb-theme", next);
  }

  const visibleSubs = subscriptions
    ? subscriptions
        .filter((s) => !s.is_hidden && !s.is_false_positive)
        .sort((a, b) => a.next_payment_date.localeCompare(b.next_payment_date))
    : [];

  const totalMonthly = visibleSubs.reduce((sum, s) => sum + s.monthly_amount, 0);
  const activeCount = visibleSubs.length;
  const unusedSubs = visibleSubs.filter((s) => s.status === "possibly_unused");
  const trialSubs = visibleSubs.filter((s) => s.status === "trial_ending");
  const totalSavings =
    unusedSubs.reduce((sum, s) => sum + s.monthly_amount, 0) +
    trialSubs.reduce((sum, s) => sum + s.monthly_amount, 0);
  const showInsight = unusedSubs.length > 0 || trialSubs.length > 0;

  const topBar = (
    <header className="top-bar">
      <div className="top-bar__spacer" />
      <div className="top-bar__center">Подписки</div>
      <button
        className="icon-button theme-toggle"
        onClick={handleThemeToggle}
        aria-label="Сменить тему"
      >
        <svg className="moon" viewBox="0 0 22 22" fill="none">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <svg className="sun" viewBox="0 0 22 22" fill="none">
          <circle cx="11" cy="11" r="5" stroke="currentColor" strokeWidth="2"/>
          <line x1="11" y1="1" x2="11" y2="3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          <line x1="11" y1="19" x2="11" y2="21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          <line x1="1" y1="11" x2="3" y2="11" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          <line x1="19" y1="11" x2="21" y2="11" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </button>
    </header>
  );

  if (loading && !subscriptions) {
    return (
      <div className="screen">
        <main className="app">
          {topBar}
          <section className="hero">
            <div className="hero__label">Подписки и сервисы</div>
            <div className="hero__sum">
              <span className="hero__sum-amount" style={{ color: "var(--text-3)" }}>—</span>
              <span className="hero__sum-suffix">в месяц</span>
            </div>
            <div className="hero__meta">
              <span style={{ color: "var(--text-3)" }}>Загрузка...</span>
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="screen">
      <main className="app">
        {topBar}

        {/* Hero */}
        <section className="hero">
          <div className="hero__label">Подписки и сервисы</div>
          <div className="hero__sum">
            <span className="hero__sum-amount">{formatRub(totalMonthly)}</span>
            <span className="hero__sum-suffix">в месяц</span>
          </div>
          <div className="hero__meta">
            <span>{activeCount} активных</span>
          </div>
        </section>

        {/* Insight card */}
        {showInsight && (
          <aside className="insight">
            <div className="insight__row">
              <div className="cat-icon cat-icon--sm cat-icon--summary">
                <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="9 2 11.09 7.26 17 7.27 12.5 10.73 14.18 16 9 12.77 3.82 16 5.5 10.73 1 7.27 6.91 7.26 9 2"/>
                </svg>
              </div>
              <div className="insight__text">
                Можно экономить <b>{formatRub(totalSavings)}</b>.{" "}
                {unusedSubs.length > 0 && (
                  <span className="muted">
                    {unusedSubs.length === 1
                      ? "1 подписка не используется"
                      : `${unusedSubs.length} подписки не используются`}
                    {trialSubs.length > 0 ? ", " : ""}
                  </span>
                )}
                {trialSubs.length > 0 && (
                  <span className="muted">
                    у {trialSubs.length === 1 ? "1" : trialSubs.length} заканчивается пробный период
                  </span>
                )}
              </div>
            </div>
            <button
              className="insight__cta"
              onClick={() => router.push("/analytics")}
            >
              Показать в аналитике
              <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 3l4 4-4 4"/>
              </svg>
            </button>
          </aside>
        )}

        <h2 className="section-title">Ближайшие списания</h2>

        {/* Subscriptions list */}
        {visibleSubs.length === 0 ? (
          <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-2)", fontSize: "var(--tb-fs-body)" }}>
            Подписок не найдено
          </div>
        ) : (
          <ul className="subs">
            {visibleSubs.map((sub) => (
              <li key={sub.merchant_name}>
                <button
                  className="sub"
                  style={{ width: "100%", background: "none", border: "none", textAlign: "left" }}
                  onClick={() => router.push(`/subscription/${encodeURIComponent(sub.merchant_name)}`)}
                >
                  <CategoryIcon category={sub.category} size="md" />
                  <div className="sub__body">
                    <div className="sub__name">{sub.merchant_name}</div>
                    <div className="sub__meta">
                      {sub.status === "active" && <span className="sub__active-dot" />}
                      {sub.status === "possibly_unused" ? (
                        <span>Следующее {formatDateRu(sub.next_payment_date)}</span>
                      ) : (
                        <>
                          <span>{formatDateRu(sub.next_payment_date)}</span>
                          <span className="sub__meta-sep" />
                          <span>{daysLabel(daysUntil(sub.next_payment_date, simulationToday))}</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="sub__right">
                    <span className="sub__price">{formatRub(sub.amount)}</span>
                    {sub.status === "price_increased" && (
                      <span className="badge badge--price">
                        <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M5 8V2M2 5l3-3 3 3"/>
                        </svg>
                        Цена выросла
                      </span>
                    )}
                    {sub.status === "trial_ending" && (
                      <span className="badge badge--trial">
                        <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="5" cy="5" r="4"/>
                          <polyline points="5 3 5 5 7 6"/>
                        </svg>
                        Пробный
                      </span>
                    )}
                    {sub.status === "possibly_unused" && (
                      <span className="badge badge--unused">Не используется</span>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
