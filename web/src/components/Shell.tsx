"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";

const PUBLIC = ["/"];

/** Public pages render bare; everything else gets the workspace shell. */
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const isPublic = PUBLIC.includes(pathname);
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
