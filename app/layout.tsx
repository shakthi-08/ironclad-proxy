// @ts-expect-error CSS is processed by the Next.js build pipeline.
import "./globals.css";

type ReactNode = unknown;

const createElement = (
  type: string,
  props: Record<string, unknown> | null,
  ...children: ReactNode[]
) => ({
  $$typeof: Symbol.for("react.element"),
  type,
  key: null,
  ref: null,
  props: {
    ...(props ?? {}),
    ...(children.length === 1
      ? { children: children[0] }
      : children.length > 1
        ? { children }
        : {}),
  },
});

export const metadata = {
  title: "Ironclad Proxy · SOC",
  description: "Zero-trust hot wallet security telemetry",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return createElement(
    "html",
    { lang: "en" },
    createElement("body", null, children),
  );
}
