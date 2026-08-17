// The generated `cloudflare:workers` module exposes `env` as Cloudflare.Env.
// Extend that generated interface with the test-only migration binding added
// in vitest.config.ts; DB itself still comes from wrangler.jsonc.
declare namespace Cloudflare {
  interface Env {
    TEST_MIGRATIONS: D1Migration[];
  }
}
