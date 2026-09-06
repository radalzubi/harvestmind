import type { Metadata } from "next";
import { Bricolage_Grotesque, IBM_Plex_Sans_Arabic, Instrument_Sans } from "next/font/google";
import { HOME_DESCRIPTION, HOME_TITLE, SHARE_IMAGE, SITE_NAME, SITE_URL } from "@/lib/seo";
import "./globals.css";
import "./site.css";
import { Shell } from "@/components/Shell";
import { ToastProvider } from "@/components/Toast";
import { LocaleProvider } from "@/lib/i18n";

const sans = Instrument_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-sans", display: "swap" });
const display = Bricolage_Grotesque({ subsets: ["latin"], weight: ["500", "600"], variable: "--font-display", display: "swap" });
const arabic = IBM_Plex_Sans_Arabic({ subsets: ["arabic"], weight: ["400", "500", "600"], variable: "--font-arabic", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: SITE_NAME,
  title: { default: HOME_TITLE, template: `%s | ${SITE_NAME}` },
  description: HOME_DESCRIPTION,
  openGraph: { siteName: SITE_NAME, type: "website", url: `${SITE_URL}/`, locale: "en_US", images: [SHARE_IMAGE] },
  twitter: { card: "summary_large_image" },
  icons: {
    // favicon.ico in src/app is linked automatically; these add the vector and larger raster marks.
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }, { url: "/icon-192.png", sizes: "192x192", type: "image/png" }],
    apple: [{ url: "/apple-icon.png", sizes: "180x180" }],
  },
  formatDetection: { telephone: false },
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
