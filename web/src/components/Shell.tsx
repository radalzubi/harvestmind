"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";

const PUBLIC_PREFIXES = [
  "/about",
  "/contact",
  "/get-started",
  "/privacy",
  "/product",
  "/sectors",
  "/security",
  "/terms",
];

/** Public pages supply their own site navigation; every workspace route, including `/`, keeps the existing shell. */
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const isPublic = PUBLIC_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );

  if (isPublic) return <>{children}</>;

  return (
    <div className="app">
      <Sidebar />
      <div className="main">
        <Topbar />
        {children}
      </div>
    </div>
  );
}
