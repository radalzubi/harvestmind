import type { Metadata } from "next";
import { Suspense } from "react";
import { GetStarted } from "@/components/site/GetStarted";

export const metadata: Metadata = { title: "Get started — zaad" };

export default function GetStartedPage() {
  return <Suspense fallback={null}><GetStarted /></Suspense>;
}
