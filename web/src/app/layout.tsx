import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { ToastProvider } from "@/components/Toast";

export const metadata: Metadata = {
  title: "HarvestMind",
  description: "AI-driven planning for fresh-produce food hubs",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>
          <div className="app">
            <Sidebar />
            <div className="main">
              <Topbar />
              {children}
            </div>
          </div>
        </ToastProvider>
      </body>
    </html>
  );
}
