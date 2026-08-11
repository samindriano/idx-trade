import type { Metadata } from "next";
import "./globals.css";
import "./monitoring/monitoring.css";
import "./editorial.css";

export const metadata: Metadata = {
  title: "IDX Trade — Research Observatory",
  description: "Outcome-blind quantitative research monitoring for IDX Trade.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
