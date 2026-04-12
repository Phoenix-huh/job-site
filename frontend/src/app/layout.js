import "./globals.css";
import CinematicParallax from "./components/CinematicParallax";

export const metadata = {
  title: "ShieldDB — Job Scam Intelligence",
  description: "Real-time job listing scanner with 20-parameter scam detection engine. Protecting job seekers from fraud with threat intelligence that scores every listing.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <CinematicParallax />
        {children}
      </body>
    </html>
  );
}
