import { redirect } from "next/navigation";

/** Admin keys belong in a trusted shell, never in the operator browser UI. */
export default function AdminPage() {
  redirect("/access");
}
