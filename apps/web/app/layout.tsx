import type { Metadata } from "next";
import "./globals.css";
import "./monitoring/monitoring.css";

export const metadata: Metadata = {
  title: "IDX Trade — Model Observatory",
  description: "Research-only monitoring dashboard for IDX Trade model generations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
