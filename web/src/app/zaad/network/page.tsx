import { redirect } from "next/navigation";

/** Superseded by DECISIONS; the raw canonical console now lives at /advanced/planner. */
export default function Page() {
  redirect("/decisions");
}
