import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ironclad Proxy · SOC",
  description: "Zero-trust hot wallet security telemetry"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
