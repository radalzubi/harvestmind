import type { Metadata } from "next";
import { AboutContent } from "@/components/site/AboutContent";

export const metadata: Metadata = { title: "About · zaad" };

export default function Page() { return <AboutContent />; }
