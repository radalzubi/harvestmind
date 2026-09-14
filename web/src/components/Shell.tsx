"use client";

import { usePathname } from "next/navigation";
import { SessionProvider } from "@/lib/session";
import { WorkspaceDataProvider } from "@/lib/zaad/workspace-data";
import { WorkspaceShell } from "@/components/workspace/Shell";

const PUBLIC_PREFIXES = [
  "/get-started", "/product", "/how-it-works", "/sectors", "/security", "/about",
  "/contact", "/privacy", "/terms", "/resources", "/welcome", "/quote",
];

/**
 * Public pages render bare — the site group brings its own nav. Everything else is the
 * workspace, which always has a session and one shared read of the operator's plan behind it.
 */
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const isPublic = pathname === "/" || PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
  if (isPublic) return <SessionProvider>{children}</SessionProvider>;
  return (
    <SessionProvider>
      <WorkspaceDataProvider>
        <WorkspaceShell>{children}</WorkspaceShell>
      </WorkspaceDataProvider>
    </SessionProvider>
  );
}
