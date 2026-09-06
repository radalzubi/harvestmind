import type { Metadata } from "next";
import { SecurityContent } from "@/components/site/SecurityContent";

export const metadata: Metadata = { title: "Security · zaad" };

export default function Page() { return <SecurityContent />; }
