import "./globals.css";
import Background3D from "./components/Background3D";

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
        <Background3D />
        {children}
      </body>
    </html>
  );
}
