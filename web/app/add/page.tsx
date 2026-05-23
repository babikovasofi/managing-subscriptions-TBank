"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { addManualSubscription, getSubscriptions } from "@/lib/api";
import type { SubscriptionCategory, ManualSubscriptionRequest } from "@/lib/types";
import { useClient } from "@/lib/ClientContext";
import { CategoryIcon } from "@/components/ui/CategoryIcon";
import { formatRub } from "@/lib/utils";

const ALL_CATEGORIES: { value: SubscriptionCategory; label: string }[] = [
  { value: "streaming_video", label: "Видеостриминг" },
  { value: "streaming_music", label: "Музыка" },
  { value: "cloud_storage",   label: "Облако" },
  { value: "education",       label: "Образование" },
  { value: "gaming",          label: "Игры" },
  { value: "food_delivery",   label: "Доставка" },
  { value: "productivity",    label: "Продуктивность" },
  { value: "reading",         label: "Чтение" },
  { value: "other",           label: "Другое" },
];

export default function AddPage() {
  const router = useRouter();
  const { clientId } = useClient();
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [period, setPeriod] = useState<7 | 30>(30);
  const [category, setCategory] = useState<SubscriptionCategory>("streaming_video");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCategoryPicker, setShowCategoryPicker] = useState(false);
  const [bgTotal, setBgTotal] = useState<number | null>(null);
  const [bgCount, setBgCount] = useState<number | null>(null);

  // Remove body padding for this screen
  useEffect(() => {
    document.body.classList.add("is-sheet-screen");
    return () => document.body.classList.remove("is-sheet-screen");
  }, []);

  // Load background data for the teaser
  useEffect(() => {
    if (!clientId) return;
    getSubscriptions(clientId).then((res) => {
      const visible = res.subscriptions.filter((s) => !s.is_hidden && !s.is_false_positive);
      const total = visible.reduce((sum, s) => sum + s.monthly_amount, 0);
      setBgTotal(total);
      setBgCount(visible.length);
    });
  }, [clientId]);

  const categoryLabel = ALL_CATEGORIES.find((c) => c.value === category)?.label ?? "Другое";

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError("Введите название подписки");
      return;
    }
    const amountNum = parseFloat(amount);
    if (!amount || isNaN(amountNum) || amountNum <= 0) {
      setError("Введите корректную сумму");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const data: ManualSubscriptionRequest = {
        merchant_name: name.trim(),
        amount: amountNum,
        period_days: period,
        category,
      };
      await addManualSubscription(clientId, data);
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка при добавлении");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      {/* Background teaser */}
      <div className="screen" style={{ position: "relative", minHeight: "100dvh" }}>
        <div className="add-bg-hero">
          <div className="add-bg-hero__label">Подписки и сервисы</div>
          <div className="add-bg-hero__sum">
            {bgTotal !== null ? formatRub(bgTotal) : "—"}
          </div>
          <div className="add-bg-hero__meta">
            {bgCount !== null ? `${bgCount} активных` : ""}
          </div>
        </div>
      </div>

      {/* Backdrop */}
      <div className="sheet-backdrop" onClick={() => router.push("/")} />

      {/* Sheet */}
      <div className="sheet">
        <div className="sheet__grabber" />
        <div className="sheet__header">
          <div className="sheet__title">Добавить подписку</div>
          <button className="sheet__close" onClick={() => router.push("/")} aria-label="Закрыть">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M3 3l10 10M13 3L3 13"/>
            </svg>
          </button>
        </div>

        <div className="sheet__body">
          {/* Name field */}
          <div className={`field${name ? " field--filled" : ""}`}>
            <input
              className="field__input"
              type="text"
              placeholder=" "
              value={name}
              onChange={(e) => setName(e.target.value)}
              id="add-name"
            />
            <label className="field__label" htmlFor="add-name">Название сервиса</label>
          </div>

          {/* Amount field */}
          <div className={`field${amount ? " field--filled" : ""}`}>
            <input
              className="field__input"
              type="number"
              placeholder=" "
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              id="add-amount"
              min="1"
              step="0.01"
              style={{ paddingRight: "24px" }}
            />
            <label className="field__label" htmlFor="add-amount">Сумма</label>
            <span className="field__suffix">₽</span>
          </div>

          {/* Period segmented control */}
          <div className="field--period">
            <span className="field__label-static">Период списания</span>
            <div className="segmented">
              <button
                className={`segmented__item${period === 7 ? " segmented__item--active" : ""}`}
                onClick={() => setPeriod(7)}
                type="button"
              >
                Неделя
              </button>
              <button
                className={`segmented__item${period === 30 ? " segmented__item--active" : ""}`}
                onClick={() => setPeriod(30)}
                type="button"
              >
                Месяц
              </button>
            </div>
          </div>

          {/* Category picker */}
          <button
            className="field--picker"
            style={{ width: "100%", border: "none", background: "none", textAlign: "left" }}
            onClick={() => setShowCategoryPicker((v) => !v)}
            type="button"
          >
            <CategoryIcon category={category} size="sm" />
            <div className="field__col">
              <div className="field__hint">Категория</div>
              <div className="field__value">{categoryLabel}</div>
            </div>
            <span className="field__chev">
              <svg width="7" height="12" viewBox="0 0 7 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 1l5 5-5 5"/>
              </svg>
            </span>
          </button>

          {/* Category picker expanded */}
          {showCategoryPicker && (
            <div style={{
              background: "var(--surface-2)",
              borderRadius: "var(--tb-radius-lg)",
              overflow: "hidden",
              marginTop: "4px",
            }}>
              {ALL_CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    width: "100%",
                    padding: "12px 16px",
                    background: cat.value === category ? "var(--surface-3)" : "transparent",
                    border: "none",
                    textAlign: "left",
                    cursor: "pointer",
                    fontSize: "var(--tb-fs-bodyL)",
                    color: "var(--text-1)",
                    fontWeight: cat.value === category ? "700" : "500",
                    fontFamily: "inherit",
                  }}
                  onClick={() => {
                    setCategory(cat.value);
                    setShowCategoryPicker(false);
                  }}
                  type="button"
                >
                  <CategoryIcon category={cat.value} size="sm" />
                  <span>{cat.label}</span>
                </button>
              ))}
            </div>
          )}

          {/* Error message */}
          {error && (
            <div style={{
              padding: "12px 16px",
              background: "var(--tb-negative-bg)",
              borderRadius: "var(--tb-radius-md)",
              color: "var(--tb-negative)",
              fontSize: "var(--tb-fs-sm)",
              marginTop: "8px",
            }}>
              {error}
            </div>
          )}
        </div>

        <div className="sheet__footer">
          <button
            className="btn btn--lg btn--primary btn--block"
            onClick={handleSubmit}
            disabled={submitting}
            type="button"
          >
            {submitting ? "Добавление..." : "Добавить подписку"}
          </button>
        </div>
      </div>
    </>
  );
}
