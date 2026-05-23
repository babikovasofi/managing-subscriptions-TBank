import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import { ClientProvider } from "@/lib/ClientContext";
import { NavWrapper } from "@/components/ui/NavWrapper";

const manrope = Manrope({
  subsets: ["cyrillic", "latin"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Управление подписками",
  description: "Т-Банк — управление подписками",
};

const THEME_SCRIPT = `
try {
  var t = localStorage.getItem('tb-theme');
  document.documentElement.setAttribute('data-theme', t === 'light' ? 'light' : 'dark');
} catch(e) {}
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" data-theme="dark" className={manrope.className}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <ClientProvider>
          {children}
          <NavWrapper />
        </ClientProvider>
      </body>
    </html>
  );
}
