"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSubscriptions } from "@/lib/api";
import type { SubscriptionResponse } from "@/lib/types";
import { useClient } from "@/lib/ClientContext";
import { CategoryIcon } from "@/components/ui/CategoryIcon";
import { formatRub, daysUntil, formatDateRu, daysLabel, clientInitials } from "@/lib/utils";

export default function SubscriptionsPage() {
  const router = useRouter();
  const { clientId, simulationToday, clients, setClient } = useClient();
  const [subscriptions, setSubscriptions] = useState<SubscriptionResponse[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    if (!clientId) return;
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

  const currentClient = clients.find((c) => c.id === clientId);
  const initials = currentClient ? clientInitials(currentClient.label) : "—";
  const clientLabel = currentClient?.label ?? "Загрузка...";

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

  if (loading && !subscriptions) {
    return (
      <div className="screen">
        <main className="app">
          <header className="top-bar">
            <button className="client-switcher" onClick={() => setIsDropdownOpen((v) => !v)}>
              <span className="client-switcher__avatar">{initials}</span>
              <span className="client-switcher__name">{clientLabel}</span>
              <span className="client-switcher__chev">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </span>
            </button>
            <button className="icon-button theme-toggle" onClick={handleThemeToggle} aria-label="Сменить тему">
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
        {/* Top bar */}
        <header className="top-bar">
          <button
            className="client-switcher"
            onClick={() => setIsDropdownOpen((v) => !v)}
            aria-expanded={isDropdownOpen}
          >
            <span className="client-switcher__avatar">{initials}</span>
            <span className="client-switcher__name">{clientLabel}</span>
            <span className="client-switcher__chev">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </span>
          </button>
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

        {/* Client dropdown */}
        {isDropdownOpen && (
          <div
            style={{
              position: "absolute",
              top: "60px",
              left: "16px",
              right: "16px",
              background: "var(--surface-1)",
              borderRadius: "var(--tb-radius-2xl)",
              boxShadow: "var(--tb-shadow-popup)",
              zIndex: 100,
              overflow: "hidden",
            }}
          >
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {clients.map((c) => (
                <li key={c.id}>
                  <button
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "14px 16px",
                      cursor: "pointer",
                      fontSize: "var(--tb-fs-bodyL)",
                      color: "var(--text-1)",
                      background: c.id === clientId ? "var(--surface-3)" : "var(--surface-1)",
                      border: "none",
                      fontFamily: "inherit",
                      fontWeight: c.id === clientId ? "700" : "500",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "8px",
                    }}
                    onClick={() => {
                      setClient(c.id);
                      setIsDropdownOpen(false);
                    }}
                  >
                    <span>{c.label}</span>
                    {c.id === clientId && (
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8l4 4 6-6" stroke="var(--tb-positive-fg)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Click outside to close dropdown */}
        {isDropdownOpen && (
          <div
            style={{ position: "fixed", inset: 0, zIndex: 99 }}
            onClick={() => setIsDropdownOpen(false)}
          />
        )}

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
