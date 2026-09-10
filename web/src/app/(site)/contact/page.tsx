import type { Metadata } from "next";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { ContactContent } from "@/components/site/ContactContent";

export const metadata: Metadata = pageMetadata({ title: "Contact ZAAD", description: "Talk to ZAAD about inventory optimization and supply resilience for your distribution or import business.", path: "/contact" });

export default function Page() { return (<><JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Contact", path: "/contact" }])} /><ContactContent /></>); }
