import type { Metadata } from "next";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { AboutContent } from "@/components/site/AboutContent";

export const metadata: Metadata = pageMetadata({ title: "About ZAAD: Inventory Optimization and Supply Resilience Software", description: "ZAAD is inventory optimization and supply resilience software for distributors and importers, built in Amman. Who we are, what the product does, and what it refuses to promise.", path: "/about" });

export default function Page() { return (<><JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "About", path: "/about" }])} /><AboutContent /></>); }
