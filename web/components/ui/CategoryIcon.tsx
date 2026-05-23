import type { SubscriptionCategory } from "@/lib/types";

const CAT_CLASS: Record<SubscriptionCategory, string> = {
  streaming_video: "cat-icon--cinema",
  streaming_music: "cat-icon--music",
  cloud_storage:   "cat-icon--cloud",
  education:       "cat-icon--edu",
  gaming:          "cat-icon--gaming",
  food_delivery:   "cat-icon--alert",
  productivity:    "cat-icon--info",
  reading:         "cat-icon--cinema-2",
  other:           "cat-icon--info",
};

const SIZE_CLASS: Record<"sm" | "md" | "lg", string> = {
  sm: "cat-icon--sm",
  md: "cat-icon--md",
  lg: "cat-icon--lg",
};

function FilmIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="20" height="20" rx="3"/>
      <line x1="7" y1="2" x2="7" y2="22"/>
      <line x1="17" y1="2" x2="17" y2="22"/>
      <line x1="2" y1="12" x2="22" y2="12"/>
      <line x1="2" y1="7" x2="7" y2="7"/>
      <line x1="17" y1="7" x2="22" y2="7"/>
      <line x1="17" y1="17" x2="22" y2="17"/>
      <line x1="2" y1="17" x2="7" y2="17"/>
    </svg>
  );
}

function MusicIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="18" r="3"/>
      <circle cx="18" cy="16" r="3"/>
      <polyline points="11 18 11 7 21 5 21 16"/>
      <line x1="11" y1="12" x2="21" y2="10"/>
    </svg>
  );
}

function CloudIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
    </svg>
  );
}

function GraduationIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
      <path d="M6 12v5c3 3 9 3 12 0v-5"/>
    </svg>
  );
}

function GamepadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="6" y1="12" x2="10" y2="12"/>
      <line x1="8" y1="10" x2="8" y2="14"/>
      <circle cx="15" cy="12" r="1" fill="currentColor"/>
      <circle cx="17" cy="10" r="1" fill="currentColor"/>
      <rect x="2" y="8" width="20" height="10" rx="5"/>
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  );
}

function getIcon(category: SubscriptionCategory) {
  switch (category) {
    case "streaming_video": return <FilmIcon />;
    case "streaming_music": return <MusicIcon />;
    case "cloud_storage":   return <CloudIcon />;
    case "education":       return <GraduationIcon />;
    case "gaming":          return <GamepadIcon />;
    case "food_delivery":   return <SendIcon />;
    case "productivity":    return <ClockIcon />;
    case "reading":         return <MusicIcon />;
    case "other":           return <ClockIcon />;
    default:                return <ClockIcon />;
  }
}

interface Props {
  category: SubscriptionCategory;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function CategoryIcon({ category, size = "md", className = "" }: Props) {
  const catClass = CAT_CLASS[category] ?? "cat-icon--info";
  const sizeClass = SIZE_CLASS[size];
  return (
    <div className={`cat-icon ${sizeClass} ${catClass} ${className}`}>
      {getIcon(category)}
    </div>
  );
}
