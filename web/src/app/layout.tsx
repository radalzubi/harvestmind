import type { Metadata } from "next";
import { Bricolage_Grotesque, IBM_Plex_Sans_Arabic, Instrument_Sans } from "next/font/google";
import "./globals.css";
import "./site.css";
import { Shell } from "@/components/Shell";
import { ToastProvider } from "@/components/Toast";
import { LocaleProvider } from "@/lib/i18n";

const sans = Instrument_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-sans", display: "swap" });
const display = Bricolage_Grotesque({ subsets: ["latin"], weight: ["500", "600"], variable: "--font-display", display: "swap" });
const arabic = IBM_Plex_Sans_Arabic({ subsets: ["arabic"], weight: ["400", "500", "600"], variable: "--font-arabic", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL("https://zaadsupply.com"),
  title: { default: "zaad", template: "%s" },
  description: "Purchasing decisions for businesses that import what they sell. Backtested on your own history, never a forecast of savings.",
  openGraph: { siteName: "zaad", type: "website", url: "https://zaadsupply.com" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${display.variable} ${arabic.variable}`} suppressHydrationWarning>
      <body>
        <LocaleProvider>
          <ToastProvider>
            <Shell>{children}</Shell>
          </ToastProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
