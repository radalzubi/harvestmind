import type { Metadata } from "next";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { LegalContent } from "@/components/site/LegalContent";

export const metadata: Metadata = pageMetadata({ title: "Terms of Service", description: "The terms under which ZAAD provides its inventory optimization workspace and reports.", path: "/terms" });

export default function Page() { return (<><JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Terms", path: "/terms" }])} /><LegalContent kind="terms" /></>); }
