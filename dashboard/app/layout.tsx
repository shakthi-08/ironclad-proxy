// The stylesheet is handled by Next.js at runtime; TypeScript does not type-check CSS imports.
// @ts-expect-error CSS modules are not declared in the current TypeScript configuration.
import "./globals.css";

export const metadata = {
  title: "Ironclad Proxy · SOC",
  description: "Zero-trust hot wallet security telemetry",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
