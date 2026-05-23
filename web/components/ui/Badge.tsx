import type { SubscriptionStatus } from "@/lib/types";

const LABELS: Record<SubscriptionStatus, string> = {
  active:           "Активна",
  price_increased:  "Цена выросла",
  possibly_unused:  "Возможно, не нужна",
  trial_ending:     "Пробный период",
};

const CLASSES: Record<SubscriptionStatus, string> = {
  active:          "bg-tb-status-active-bg text-tb-status-active",
  price_increased: "bg-tb-status-price-bg text-tb-status-price",
  possibly_unused: "bg-tb-status-unused-bg text-tb-status-unused",
  trial_ending:    "bg-tb-status-trial-bg text-tb-status-trial",
};

interface BadgeProps {
  status: SubscriptionStatus;
  className?: string;
}

export function Badge({ status, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold leading-none ${CLASSES[status]} ${className}`}
    >
      {LABELS[status]}
    </span>
  );
}
