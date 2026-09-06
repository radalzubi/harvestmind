import type { Metadata } from "next";
import { ContactContent } from "@/components/site/ContactContent";

export const metadata: Metadata = { title: "Contact · zaad" };

export default function Page() { return <ContactContent />; }
