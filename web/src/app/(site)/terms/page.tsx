import type { Metadata } from "next";
import { LegalContent } from "@/components/site/LegalContent";

export const metadata: Metadata = { title: "Terms · zaad" };

export default function Page() { return <LegalContent kind="terms" />; }
