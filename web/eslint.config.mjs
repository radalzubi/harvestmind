import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default [
  ...nextVitals,
  ...nextTs,
  { ignores: [".next/**", "node_modules/**", "public/vendor/**", "scripts/**"] },
  // Plain quotes in JSX copy are readable and safe; the escaping rule adds noise, not safety.
  { rules: { "react/no-unescaped-entities": "off" } },
];
