import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  as?: "div" | "article" | "section" | "li";
}

export function Card({ children, className = "", onClick, as: Tag = "div" }: CardProps) {
  const interactive = Boolean(onClick);
  return (
    <Tag
      className={`bg-tb-surface rounded-tb-lg shadow-tb-sm ${
        interactive
          ? "cursor-pointer transition-transform active:scale-[0.98] select-none"
          : ""
      } ${className}`}
      onClick={onClick}
    >
      {children}
    </Tag>
  );
}
