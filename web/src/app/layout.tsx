import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "./site.css";
import { Shell } from "@/components/Shell";
import { ToastProvider } from "@/components/Toast";

const sans = Geist({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL("https://zaadsupply.com"),
  title: { default: "zaad", template: "%s" },
  description: "Purchasing decisions for businesses that import what they sell. Backtested on your own history, never a forecast of savings.",
  openGraph: { siteName: "zaad", type: "website", url: "https://zaadsupply.com" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <ToastProvider>
          <Shell>{children}</Shell>
        </ToastProvider>
      </body>
    </html>
  );
}
