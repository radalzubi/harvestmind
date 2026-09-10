import { redirect } from "next/navigation";

// The first ZAAD engine's page is superseded by the network workspace (the frozen P1 optimizer).
// The old page is kept at /zaad/legacy while the legacy planners remain enabled on the API.
export default function ZaadPage() {
  redirect("/zaad/network");
}
