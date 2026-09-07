import type { Metadata } from "next";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { HowItWorks } from "@/components/site/hiw/HowItWorks";

export const metadata: Metadata = pageMetadata({
  title: "How ZAAD Works: An Interactive Walk Through One Purchasing Decision",
  description: "Follow a hypothetical distributor through a normal week, a supplier delay and the recovery: what ZAAD reads, how it measures uncertainty, why the current plan is the first candidate, and how LEAN, PROTECT, ALLOCATE and RECOVER modes change orders only where the evidence says so.",
  path: "/how-it-works",
});

export default function Page() {
  return (<><JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "How it works", path: "/how-it-works" }])} /><HowItWorks /></>);
}
