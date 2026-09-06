import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";
import { Suspense } from "react";
import { GetStarted } from "@/components/site/GetStarted";

export const metadata: Metadata = pageMetadata({ title: "Get Started with ZAAD", description: "Open a private ZAAD workspace or enter your key. Upload a year of purchasing history and run the diagnostic.", path: "/get-started" });

export default function GetStartedPage() {
  return <Suspense fallback={null}><GetStarted /></Suspense>;
}
