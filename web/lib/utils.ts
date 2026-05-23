const MONTHS_LONG = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
const MONTHS_SHORT = ["Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"];

export function formatRub(amount: number): string {
  return `${Math.round(amount).toLocaleString("ru-RU")} ₽`;
}

export function daysUntil(targetDate: string, fromDate: string): number {
  const from = new Date(fromDate + "T00:00:00");
  const to = new Date(targetDate + "T00:00:00");
  return Math.round((to.getTime() - from.getTime()) / 86_400_000);
}

export function formatDateRu(isoDate: string): string {
  const d = new Date(isoDate + "T00:00:00");
  return `${d.getDate()} ${MONTHS_LONG[d.getMonth()]}`;
}

export function shortMonthFromYYYYMM(yyyymm: string): string {
  const m = parseInt(yyyymm.slice(5, 7), 10) - 1;
  return MONTHS_SHORT[m] ?? "";
}

export function daysLabel(days: number): string {
  if (days <= 0) return "сегодня";
  if (days === 1) return "через 1 день";
  if (days >= 2 && days <= 4) return `через ${days} дня`;
  return `через ${days} дней`;
}

export function notifGroupLabel(notifDate: string, simToday: string): string {
  const diff = daysUntil(notifDate, simToday);
  if (diff === 0) return "Сегодня";
  if (diff === -1) return "Вчера";
  return "Ранее";
}

export function clientInitials(label: string): string {
  const parts = label.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return label.slice(0, 2).toUpperCase();
}
