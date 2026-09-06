import type { Metadata } from "next";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { ProductContent } from "@/components/site/ProductContent";

export const metadata: Metadata = pageMetadata({ title: "How ZAAD Works: Inventory Optimization Software for Distributors", description: "How ZAAD turns purchase orders, receipts and stock counts into a purchasing plan: read your current policy, backtest candidate optimizers on your own history, and change orders only when the evidence says so.", path: "/product" });

export default function Page() { return (<><JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "How it works", path: "/product" }])} /><ProductContent /></>); }
