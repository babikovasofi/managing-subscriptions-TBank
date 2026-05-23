"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface TabDef {
  href: string;
  label: string;
  icon: React.ReactNode;
  isAdd?: boolean;
}

const TABS: TabDef[] = [
  {
    href: "/",
    label: "Подписки",
    icon: (
      <svg viewBox="0 0 26 26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="5" width="20" height="16" rx="3"/>
        <line x1="3" y1="10" x2="23" y2="10"/>
        <line x1="8" y1="15" x2="12" y2="15"/>
        <line x1="8" y1="18" x2="16" y2="18"/>
      </svg>
    ),
  },
  {
    href: "/analytics",
    label: "Аналитика",
    icon: (
      <svg viewBox="0 0 26 26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="4" y1="22" x2="22" y2="22"/>
        <rect x="5" y="13" width="4" height="9" rx="1"/>
        <rect x="11" y="7" width="4" height="15" rx="1"/>
        <rect x="17" y="10" width="4" height="12" rx="1"/>
      </svg>
    ),
  },
  {
    href: "/notifications",
    label: "Уведомления",
    icon: (
      <svg viewBox="0 0 26 26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 10a7 7 0 0 0-14 0c0 7-3 9-3 9h20s-3-2-3-9"/>
        <path d="M14.73 22a2 2 0 0 1-3.46 0"/>
      </svg>
    ),
  },
  {
    href: "/add",
    label: "Добавить",
    icon: (
      <svg viewBox="0 0 26 26" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
        <line x1="13" y1="8" x2="13" y2="18"/>
        <line x1="8" y1="13" x2="18" y2="13"/>
      </svg>
    ),
    isAdd: true,
  },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="tabbar">
      {TABS.map(({ href, label, icon, isAdd }) => {
        const active = pathname === href;
        const tabClass = `tab${active ? " tab--active" : ""}${isAdd ? " tab--add" : ""}`;
        return (
          <Link key={href} href={href} className={tabClass}>
            {icon}
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
