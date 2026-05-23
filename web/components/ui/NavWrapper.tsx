"use client";
import { usePathname } from "next/navigation";
import { BottomNav } from "./BottomNav";

export function NavWrapper() {
  const pathname = usePathname();
  if (pathname === "/add") return null;
  return <BottomNav />;
}
