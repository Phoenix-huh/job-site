import "./globals.css";
import Themed3DFX from "./components/Themed3DFX";

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
        <Themed3DFX />
        {children}
      </body>
    </html>
  );
}
