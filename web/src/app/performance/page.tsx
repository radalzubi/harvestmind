import { redirect } from "next/navigation";

/** The former page rendered a committed JSON snapshot as if it were live. */
export default function PerformancePage() {
  redirect("/backtest");
}
