import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OMR Checker",
  description: "Create, scan, review, and evaluate OMR answer sheets.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
