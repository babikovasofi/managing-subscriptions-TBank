"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAnalytics, getSubscriptions } from "@/lib/api";
import type {
  AnalyticsResponse,
  SubscriptionResponse,
  SubscriptionCategory,
} from "@/lib/types";
import { useClient } from "@/lib/ClientContext";
import { CategoryIcon } from "@/components/ui/CategoryIcon";
import { formatRub } from "@/lib/utils";

const CAT_COLORS: Record<SubscriptionCategory, string> = {
  streaming_video: "#FFDD2D",
  streaming_music: "#A855F7",
  cloud_storage:   "#3B82F6",
  education:       "#10B981",
  gaming:          "#F59E0B",
  food_delivery:   "#EF4444",
  productivity:    "#6366F1",
  reading:         "#14B8A6",
  other:           "#9CA3AF",
};

const CAT_LABELS: Record<SubscriptionCategory, string> = {
  streaming_video: "Видео",
  streaming_music: "Музыка",
  cloud_storage:   "Хранилище",
  education:       "Обучение",
  gaming:          "Игры",
  food_delivery:   "Доставка",
  productivity:    "Продуктивность",
  reading:         "Чтение",
  other:           "Другое",
};

export default function AnalyticsPage() {
  const router = useRouter();
  const { clientId } = useClient();
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [subscriptions, setSubscriptions] = useState<SubscriptionResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    Promise.all([getAnalytics(clientId), getSubscriptions(clientId)])
      .then(([an, subs]) => {
        setAnalytics(an);
        setSubscriptions(subs.subscriptions.filter((s) => !s.is_hidden && !s.is_false_positive));
      })
      .finally(() => setLoading(false));
  }, [clientId]);

  if (loading || !analytics) {
    return (
      <div className="screen">
        <header className="top-bar">
          <div className="top-bar__spacer" />
          <div className="top-bar__center">Аналитика</div>
          <div className="top-bar__spacer" />
        </header>
        <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-2)" }}>
          Загрузка...
        </div>
      </div>
    );
  }

  // Donut computation
  const catTotals = new Map<SubscriptionCategory, number>();
  for (const s of subscriptions) {
    const prev = catTotals.get(s.category) ?? 0;
    catTotals.set(s.category, prev + s.monthly_amount);
  }
  const catEntries = Array.from(catTotals.entries()).sort((a, b) => b[1] - a[1]);
  const total = analytics.monthly_total || 1;

  // Build conic-gradient
  let accumulated = 0;
  const gradientParts: string[] = [];
  for (const [cat, amt] of catEntries) {
    const pct = (amt / total) * 100;
    gradientParts.push(
      `${CAT_COLORS[cat]} ${accumulated.toFixed(1)}% ${(accumulated + pct).toFixed(1)}%`
    );
    accumulated += pct;
  }
  const conicGradient = `conic-gradient(${gradientParts.join(", ")})`;

  // Trial subscriptions for savings section
  const trialSubs = subscriptions.filter((s) => s.status === "trial_ending");
  const trialSavings = trialSubs.reduce((sum, s) => sum + s.monthly_amount, 0);
  const totalSavings = analytics.potential_savings + trialSavings;

  return (
    <div className="screen">
      <header className="top-bar">
        <div className="top-bar__spacer" />
        <div className="top-bar__center">Аналитика</div>
        <div className="top-bar__spacer" />
      </header>

      {/* Hero */}
      <section className="an-hero">
        <div className="an-hero__label">Подписки в месяц</div>
        <div className="an-hero__sum">
          {formatRub(analytics.monthly_total)}
          <span className="an-hero__sum-suffix">/ мес</span>
        </div>
        <div className="an-hero__meta">
          {subscriptions.length} активных подписок
        </div>
      </section>

      {/* Donut chart */}
      {catEntries.length > 0 && (
        <div className="donut-card">
          <div className="donut" style={{ background: conicGradient }}>
            <div className="donut__center">
              <div
                className="donut__center-value"
                style={{ fontSize: "48px", fontWeight: "800", lineHeight: 1 }}
              >
                {subscriptions.length}
              </div>
              <div className="donut__center-label">подписок</div>
            </div>
          </div>
          <div className="legend">
            {catEntries.slice(0, 5).map(([cat, amt]) => (
              <div key={cat} className="legend__item">
                <span
                  className="legend__swatch"
                  style={{
                    background: CAT_COLORS[cat],
                    display: "inline-block",
                    width: "10px",
                    height: "10px",
                    borderRadius: "3px",
                    flexShrink: 0,
                  }}
                />
                <span className="legend__label">{CAT_LABELS[cat]}</span>
                <span className="legend__value">{formatRub(amt)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top-3 */}
      {analytics.top_3.length > 0 && (
        <>
          <h2 className="section-title">Топ расходов</h2>
          <ul className="rank-list">
            {analytics.top_3.map((item, i) => (
              <li key={item.merchant_name}>
                <button
                  className="rank"
                  style={{ width: "100%", background: "none", border: "none", textAlign: "left" }}
                  onClick={() => router.push(`/subscription/${encodeURIComponent(item.merchant_name)}`)}
                >
                  <span className="rank__no">{i + 1}</span>
                  <CategoryIcon category={item.category} size="md" />
                  <div className="rank__body">
                    <div className="rank__name">{item.merchant_name}</div>
                    <div className="rank__pct">
                      {Math.round((item.monthly_amount / total) * 100)}% от бюджета
                    </div>
                  </div>
                  <span className="rank__price">{formatRub(item.monthly_amount)}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {/* Savings insight */}
      {(analytics.recommendations.length > 0 || trialSubs.length > 0) && (
        <>
          <h2 className="section-title">Можно сэкономить</h2>
          <div className="save-insight">
            <div className="save-insight__head">
              <div className="cat-icon cat-icon--sm cat-icon--summary">
                <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="9 2 11.09 7.26 17 7.27 12.5 10.73 14.18 16 9 12.77 3.82 16 5.5 10.73 1 7.27 6.91 7.26 9 2"/>
                </svg>
              </div>
              <div>
                <div className="save-insight__amount">{formatRub(totalSavings)}</div>
                <div className="save-insight__caption">потенциальная экономия в месяц</div>
              </div>
            </div>
            <ul className="save-insight__list">
              {analytics.recommendations.map((rec) => (
                <li key={rec.merchant_name} className="save-insight__item">
                  <span className="save-insight__dot" />
                  <span>
                    <b>{rec.merchant_name}</b> — {rec.text}{" "}
                    <span style={{ color: "var(--text-3)" }}>({formatRub(rec.monthly_amount)}/мес)</span>
                  </span>
                </li>
              ))}
              {trialSubs.map((s) => (
                <li key={s.merchant_name} className="save-insight__item">
                  <span className="save-insight__dot" />
                  <span>
                    <b>{s.merchant_name}</b> — пробный период заканчивается, начнётся регулярное списание{" "}
                    <span style={{ color: "var(--text-3)" }}>({formatRub(s.monthly_amount)}/мес)</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
