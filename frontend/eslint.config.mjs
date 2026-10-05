import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
  {
    rules: {
      // Fetch-on-mount in app/page.tsx is the standard pattern, not a synchronous setState footgun.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
