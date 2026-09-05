import type { Metadata } from "next";
import { HomeContent } from "@/components/site/HomeContent";

export const metadata: Metadata = {
  title: "zaad · purchasing decisions for businesses that import what they sell",
  description: "Upload a year of history. See how you order today, what a gated optimizer would have done on that same history, and the risk on your supply lanes now.",
};

export default function Home() { return <HomeContent />; }
