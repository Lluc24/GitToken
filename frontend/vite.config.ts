import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// Vercel system environment variable: the production host, without https://.
const productionHostVariable = "VERCEL_PROJECT_PRODUCTION_URL";

export default defineConfig(({ mode }) => {
  const productionHost = loadEnv(mode, ".", productionHostVariable)[
    productionHostVariable
  ];
  if (productionHost !== undefined && !/^[a-z0-9.-]+$/.test(productionHost)) {
    throw new Error(
      `${productionHostVariable} must be a bare host such as example.com, got ${JSON.stringify(productionHost)}`,
    );
  }
  return {
    plugins: [react(), tailwindcss()],
    envPrefix: ["VITE_", productionHostVariable],
    server: {
      proxy: { "/v1": "http://localhost:8000" },
    },
  };
});
