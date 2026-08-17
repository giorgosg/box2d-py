import {
  cloudflareTest,
  readD1Migrations,
} from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";

// The real migrations, handed to the tests as a binding so they can apply them
// to their own database. Stating the schema in the test instead would leave the
// migration itself unexercised, free to drift from what the tests assume.
const migrations = await readD1Migrations("./migrations");

// The tests run inside workerd against a real local D1, rather than against a
// mock of it: the SQL, the hashing and the cache are the parts worth testing,
// and a stand-in for D1 would only prove the stand-in works.
export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        bindings: { TEST_MIGRATIONS: migrations },
      },
    }),
  ],
});
