"use client";

import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";

const PUBLIC_PREFIXES = ["/get-started", "/product", "/how-it-works", "/sectors", "/security", "/about", "/contact", "/privacy", "/terms", "/resources", "/welcome"];

/** Public pages render bare (the site group adds its own nav); everything else gets the workspace shell.
 * `app-twin` lets the Network Twin, and only it, collapse the rail on narrow screens. */
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const isPublic = pathname === "/" || PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
  if (isPublic) return <>{children}</>;
  return (
    <div className={clsx("app", (pathname === "/network" || pathname.startsWith("/network/")) && "app-twin")}>
      <Sidebar />
      <div className="main">
        <Topbar />
        {children}
      </div>
    </div>
  );
}
