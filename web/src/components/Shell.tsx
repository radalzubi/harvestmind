"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";

const PUBLIC_PREFIXES = ["/get-started", "/product", "/sectors", "/security", "/about", "/contact", "/privacy", "/terms", "/resources", "/welcome"];

/** Public pages render bare (the site group adds its own nav); everything else gets the workspace shell. */
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const isPublic = pathname === "/" || PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
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
