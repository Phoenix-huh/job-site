import "./globals.css";

export const metadata = {
  title: "ShieldDB — Job Scam Intelligence",
  description: "Real-time job listing scanner with 20-parameter scam detection engine. Protecting job seekers from fraud with threat intelligence that scores every listing.",
};

import { NotificationToast } from "@/components/NotificationToast";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet" />
      </head>
      <body>
        <NotificationToast />
        {children}
      </body>
    </html>
  );
}
