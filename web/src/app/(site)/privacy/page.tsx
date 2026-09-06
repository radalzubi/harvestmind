import type { Metadata } from "next";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { LegalContent } from "@/components/site/LegalContent";

export const metadata: Metadata = pageMetadata({ title: "Privacy Policy", description: "How ZAAD handles the data operators upload, what is pseudonymised, and what is never shared.", path: "/privacy" });

export default function Page() { return (<><JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Privacy", path: "/privacy" }])} /><LegalContent kind="privacy" /></>); }
