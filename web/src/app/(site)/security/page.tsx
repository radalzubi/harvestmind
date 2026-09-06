import type { Metadata } from "next";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { SecurityContent } from "@/components/site/SecurityContent";

export const metadata: Metadata = pageMetadata({ title: "ZAAD Security Architecture: Isolated Workspaces and Pseudonymised Data", description: "How ZAAD protects operator data: pseudonymisation on arrival, one isolated database per workspace, key-only access, and no training on customer data.", path: "/security" });

export default function Page() { return (<><JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Security", path: "/security" }])} /><SecurityContent /></>); }
