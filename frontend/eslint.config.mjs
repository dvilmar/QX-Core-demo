import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
  {
    rules: {
      // The initial-load effect in app/page.tsx fetches on mount and calls
      // setState in the resolved promise -- the standard "fetch data when
      // this component mounts" pattern, not a synchronous setState-in-effect
      // footgun. There's no external system to subscribe to for the very
      // first load (the WebSocket effect below it is the subscription; this
      // one is the one-time initial fetch it can't replace).
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
