import type { Metadata } from "next";
import { NetworkTwin } from "@/components/network/NetworkTwin";

export const metadata: Metadata = { title: "Network Twin", robots: { index: false, follow: false } };

export default function NetworkPage() {
  return <NetworkTwin />;
}
