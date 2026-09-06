import type { Metadata } from "next";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { SectorsContent } from "@/components/site/SectorsContent";

export const metadata: Metadata = pageMetadata({ title: "Sectors: Supply Planning for Produce, Meat and Commercial Importers", description: "Inventory and supply planning for fresh produce importers, meat and seafood distributors, and commercial goods wholesalers who order in cases and pallets.", path: "/sectors" });

export default function Page() { return (<><JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Sectors", path: "/sectors" }])} /><SectorsContent /></>); }
