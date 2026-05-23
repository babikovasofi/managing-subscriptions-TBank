"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getNotifications } from "@/lib/api";
import type { Notification, NotificationType } from "@/lib/types";
import { useClient } from "@/lib/ClientContext";
import { daysUntil, notifGroupLabel } from "@/lib/utils";

const GROUP_ORDER = ["Сегодня", "Вчера", "Ранее"] as const;

function NotifIcon({ type }: { type: NotificationType }) {
  const iconClass = type === "summary" ? "cat-icon--summary" : "cat-icon--alert";
  return (
    <div className={`cat-icon cat-icon--sm ${iconClass}`}>
      {type === "price_increased" && (
        <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 14V4M5 8l4-4 4 4"/>
        </svg>
      )}
      {type === "trial_ending" && (
        <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="9" cy="9" r="7"/>
          <polyline points="9 5 9 9 12 11"/>
        </svg>
      )}
      {type === "upcoming_payment" && (
        <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="3" width="14" height="13" rx="2"/>
          <line x1="2" y1="7" x2="16" y2="7"/>
          <line x1="6" y1="1" x2="6" y2="4"/>
          <line x1="12" y1="1" x2="12" y2="4"/>
        </svg>
      )}
      {type === "possibly_unused" && (
        <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="9" cy="9" r="7"/>
          <line x1="9" y1="5" x2="9" y2="9"/>
          <circle cx="9" cy="12.5" r="0.5" fill="currentColor"/>
        </svg>
      )}
      {type === "summary" && (
        <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="3" y1="13" x2="15" y2="13"/>
          <rect x="4" y="8" width="3" height="5" rx="1"/>
          <rect x="8" y="4" width="3" height="9" rx="1"/>
          <rect x="12" y="6" width="3" height="7" rx="1"/>
        </svg>
      )}
    </div>
  );
}

const NOTIF_TITLE: Record<NotificationType, string> = {
  price_increased:  "Цена выросла",
  trial_ending:     "Пробный заканчивается",
  upcoming_payment: "Скоро списание",
  possibly_unused:  "Возможно, не нужна",
  summary:          "Сводка",
};

export default function NotificationsPage() {
  const router = useRouter();
  const { clientId, simulationToday } = useClient();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    getNotifications(clientId)
      .then((res) => setNotifications(res.notifications))
      .finally(() => setLoading(false));
  }, [clientId]);

  function getTimeDisplay(notifDate: string): string {
    if (!simulationToday) return "";
    const diff = daysUntil(notifDate, simulationToday);
    if (diff === 0) return "Сегодня";
    if (diff === 1) return "Завтра";
    if (diff > 1) return `Через ${diff}д`;
    if (diff === -1) return "Вчера";
    if (diff < -7) return "Ранее";
    return `${Math.abs(diff)}д назад`;
  }

  // Group notifications
  const groups = new Map<string, Notification[]>();
  for (const label of GROUP_ORDER) {
    groups.set(label, []);
  }
  for (const notif of notifications) {
    const label = simulationToday ? notifGroupLabel(notif.date, simulationToday) : "Ранее";
    const key = GROUP_ORDER.includes(label as typeof GROUP_ORDER[number]) ? label : "Ранее";
    groups.get(key)!.push(notif);
  }

  function handleNotifClick(notif: Notification) {
    if (notif.type === "summary" || !notif.merchant_name) {
      router.push("/analytics");
    } else {
      router.push(`/subscription/${encodeURIComponent(notif.merchant_name)}`);
    }
  }

  return (
    <div className="screen">
      <header className="top-bar">
        <div className="top-bar__spacer" />
        <div className="top-bar__center">Уведомления</div>
        <div className="top-bar__spacer" />
      </header>

      {loading ? (
        <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-2)" }}>
          Загрузка...
        </div>
      ) : notifications.length === 0 ? (
        <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-2)", fontSize: "var(--tb-fs-body)" }}>
          Уведомлений нет
        </div>
      ) : (
        <>
          {GROUP_ORDER.map((groupLabel) => {
            const items = groups.get(groupLabel) ?? [];
            if (items.length === 0) return null;
            return (
              <div key={groupLabel}>
                <div className="day-label">{groupLabel}</div>
                <ul className="notif-list">
                  {items.map((notif, idx) => (
                    <li key={`${notif.date}-${idx}`}>
                      <button
                        className="notif"
                        style={{ width: "100%", background: "none", border: "none", textAlign: "left" }}
                        onClick={() => handleNotifClick(notif)}
                      >
                        <NotifIcon type={notif.type} />
                        <div className="notif__body">
                          <div className="notif__title">{NOTIF_TITLE[notif.type]}</div>
                          <div className="notif__text">{notif.text}</div>
                        </div>
                        <div className="notif__right">
                          <span className="notif__time">{getTimeDisplay(notif.date)}</span>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
