/**
 * The engine's build warnings, in the operator's vocabulary.
 *
 * These are written for an engineer — they name staging tables, migrations and service ids — and
 * they are the only place the product tells an operator that something in their own data limits
 * what ZAAD could do. So they are **formatted, never paraphrased**: every content word the engine
 * chose survives, and only its references to things an operator has no name for are translated.
 *
 * Two of them are dropped entirely rather than translated: a phase the workspace never declared is
 * not a data problem, and nobody needs to hear about `stg_recourse_spec`.
 */

/** A staging table as the operator knows it: the file they uploaded. */
function fileNamed(table: string): string {
  return `your ${table.replace(/^stg_(fmcg_)?/, "").replaceAll("_", " ")} upload`;
}

export function operatorWarning(warning: string): string | null {
  // "recourse requested but the vault declares no recourse specification (…)" — a capability the
  // operator never asked for, absent because they never declared it. Not a problem; not shown.
  if (/requested but the vault declares no/i.test(warning)) return null;

  const said = warning
    // A parenthetical table-and-migration reference is engineering provenance, not information.
    .replace(/\s*\(stg_[a-z_]+(\s*\/\s*stg_[a-z_]+)*(, migration \d+)?\)/gi, "")
    // "in stg_fmcg_lanes:" — naming the table produced "in lanes:", which reads as a field label.
    // The operator's name for that table is the file they uploaded.
    .replace(/\bstg_[a-z_]+\b/gi, (table) => fileNamed(table))
    // `QA-001075@QA-BR-AQABA` is how the engine writes a product at a place. The rest of the
    // product writes it "QA-001075 at QA-BR-AQABA"; so does this. Neither side may contain a dot,
    // so an address that happens to appear in a warning is left exactly as it was written.
    .replace(/\b([A-Za-z0-9][\w-]*)@([A-Za-z0-9][\w-]*)\b(?!\.)/g, "$1 at $2")
    .trim();

  return said ? said.charAt(0).toUpperCase() + said.slice(1) : null;
}
