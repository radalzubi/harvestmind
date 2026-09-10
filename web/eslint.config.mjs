// Canonical frontend lint (post-P1 integration): Next.js core-web-vitals + TypeScript presets.
// Errors block CI. Two rules are kept visible as warnings rather than blockers for now:
// react-hooks/set-state-in-effect (the React 19 rule; the site lineage's client-hydration effects
// predate it and are reworked separately) and @typescript-eslint/no-explicit-any (one chart helper).
// react/no-unescaped-entities is stylistic (apostrophes in copy) and is switched off.
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default [
  ...nextVitals,
  ...nextTs,
  { ignores: [".next/**", "out/**", "node_modules/**", "next-env.d.ts"] },
  {
    rules: {
      "react/no-unescaped-entities": "off",
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/immutability": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
];
