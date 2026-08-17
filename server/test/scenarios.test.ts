import {
  applyD1Migrations,
  createExecutionContext,
  waitOnExecutionContext,
} from "cloudflare:test";
import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import worker, { scenarioId } from "../src/index";

const SCENARIO = `from box2d_testbed.base_test import BaseTest


class Falling(BaseTest, category="User", name="falling"):
    def setup(self):
        self.world.new_body().static().segment((-10, 0), (10, 0)).build()
`;

/** Drive the worker the way a request would, with its own execution context. */
async function call(path: string, init?: RequestInit): Promise<Response> {
  const request = new Request(`https://scenarios.example/${path}`, init);
  const ctx = createExecutionContext();
  const response = await worker.fetch(request, env, ctx);
  // The GET path caches in the background; without this the put can outlive
  // the test and the next one starts against a half-finished write.
  await waitOnExecutionContext(ctx);
  return response;
}

function post(source: string): Promise<Response> {
  return call("s", { method: "POST", body: source });
}

function postBytes(source: Uint8Array): Promise<Response> {
  return call("s", { method: "POST", body: source });
}

beforeEach(async () => {
  // The migrations the deployed database gets, so a mistake in one shows up
  // here rather than the first time it is applied for real.
  await applyD1Migrations(env.DB, env.TEST_MIGRATIONS);
  await env.DB.exec("DELETE FROM scenarios");
});

describe("storing a scenario", () => {
  it("returns an id, a size and a link to follow", async () => {
    const response = await post(SCENARIO);

    expect(response.status).toBe(201);
    const body = (await response.json()) as Record<string, unknown>;
    expect(body.id).toMatch(/^[0-9a-f]{64}$/);
    expect(body.bytes).toBe(new TextEncoder().encode(SCENARIO).length);
    expect(body.url).toBe(`https://scenarios.example/s/${body.id}`);
    expect(response.headers.get("location")).toBe(body.url);
  });

  it("and the link leads to exactly what was posted", async () => {
    const { url } = (await (await post(SCENARIO)).json()) as { url: string };

    const fetched = await call(new URL(url).pathname.slice(1));

    expect(fetched.status).toBe(200);
    expect(await fetched.text()).toBe(SCENARIO);
    expect(fetched.headers.get("content-type")).toContain("text/x-python");
  });

  it("names it after its own content", async () => {
    const body = (await (await post(SCENARIO)).json()) as { id: string };

    // The same hash the Python side computes, which is what lets either end
    // work out an id without asking the other.
    expect(body.id).toBe(await scenarioId(SCENARIO));
  });

  it("gives the same link for the same source, and stores one copy", async () => {
    const first = await post(SCENARIO);
    const second = await post(SCENARIO);

    expect(first.status).toBe(201);
    expect(second.status).toBe(200);
    const a = (await first.json()) as { url: string };
    const b = (await second.json()) as { url: string };
    expect(b.url).toBe(a.url);

    const { count } = (await env.DB.prepare(
      "SELECT count(*) AS count FROM scenarios",
    ).first<{ count: number }>())!;
    expect(count).toBe(1);
  });

  it("settles two simultaneous posts as one creation", async () => {
    const [first, second] = await Promise.all([post(SCENARIO), post(SCENARIO)]);

    expect([first.status, second.status].sort()).toEqual([200, 201]);
    const a = (await first.json()) as { id: string };
    const b = (await second.json()) as { id: string };
    expect(a.id).toBe(b.id);
  });

  it("gives different links to sources that differ at all", async () => {
    const a = (await (await post(SCENARIO)).json()) as { id: string };
    const b = (await (await post(SCENARIO + "# a trailing comment\n")).json()) as {
      id: string;
    };

    expect(b.id).not.toBe(a.id);
  });

  it("records what it stored", async () => {
    const { id } = (await (await post(SCENARIO)).json()) as { id: string };

    const row = await env.DB.prepare(
      "SELECT source, bytes, created_at FROM scenarios WHERE id = ?",
    )
      .bind(id)
      .first<{ source: string; bytes: number; created_at: number }>();

    expect(row?.source).toBe(SCENARIO);
    expect(row?.bytes).toBe(new TextEncoder().encode(SCENARIO).length);
    expect(row?.created_at).toBeGreaterThan(0);
  });
});

describe("refusing what is not a scenario", () => {
  it("turns away an empty body", async () => {
    const response = await post("   \n  ");

    expect(response.status).toBe(400);
    expect(await response.text()).toContain("empty");
  });

  it("turns away something too big to be one", async () => {
    const response = await post("x".repeat(64 * 1024 + 1));

    expect(response.status).toBe(413);
    expect(await response.text()).toContain("the limit is");
  });

  it("measures the cap in bytes rather than characters", async () => {
    // Two bytes each in UTF-8, so this is over the cap while being under it
    // by any count of characters.
    const response = await post("é".repeat(33 * 1024));

    expect(response.status).toBe(413);
  });

  it("keeps a scenario that is exactly at the cap", async () => {
    const response = await post("x".repeat(64 * 1024));

    expect(response.status).toBe(201);
  });

  it("rejects bytes that are not UTF-8", async () => {
    const response = await postBytes(new Uint8Array([0x66, 0x6f, 0x80]));

    expect(response.status).toBe(400);
    expect(await response.text()).toContain("UTF-8");
  });

  it("returns UTF-8 with a byte-order mark byte for byte", async () => {
    const source = new Uint8Array([0xef, 0xbb, 0xbf, 0x78, 0x20, 0x3d, 0x20, 0x31]);
    const stored = await postBytes(source);
    const { url } = (await stored.json()) as { url: string };

    const fetched = await call(new URL(url).pathname.slice(1));

    expect(new Uint8Array(await fetched.arrayBuffer())).toEqual(source);
  });

  it("does not alias different content even if its id is already occupied", async () => {
    const id = await scenarioId(SCENARIO);
    await env.DB.prepare(
      "INSERT INTO scenarios (id, source, bytes, created_at) VALUES (?, ?, ?, ?)",
    )
      .bind(id, "different", 9, Date.now())
      .run();

    const response = await post(SCENARIO);

    expect(response.status).toBe(409);
  });
});

describe("reading a scenario", () => {
  it("says so when there is none", async () => {
    const response = await call(`s/${"0".repeat(64)}`);

    expect(response.status).toBe(404);
  });

  it("refuses an id that could not be one", async () => {
    // Uppercase is out too: an id is one spelling of one hash, or it would not
    // be safe to cache a response against it forever.
    for (const bad of [
      "nonsense",
      "A".repeat(64),
      "0".repeat(63),
      "0".repeat(65),
    ]) {
      const response = await call(`s/${bad}`);
      expect(response.status, bad).toBe(400);
    }
  });

  it("never sees a path trying to climb out of /s/", async () => {
    const response = await call("s/../../etc/passwd");

    // 404 rather than 400: the URL is normalised to /etc/passwd before routing,
    // so it does not match the scenario route at all and the id check never
    // runs. Worth pinning -- it is the reason nothing here does path
    // arithmetic, and it would be a bad thing to start doing later.
    expect(response.status).toBe(404);
  });

  it("promises the answer will never change", async () => {
    const { id } = (await (await post(SCENARIO)).json()) as { id: string };

    const response = await call(`s/${id}`);

    // What makes the store cheap to run: an id cannot come to mean something
    // else, so nothing downstream ever has to ask twice.
    expect(response.headers.get("cache-control")).toContain("immutable");
  });

  it("is served straight from the cache the second time", async () => {
    const { id } = (await (await post(SCENARIO)).json()) as { id: string };
    await call(`s/${id}`);

    // Gone from the database, still answered -- which only the cache can do.
    await env.DB.exec("DELETE FROM scenarios");
    const response = await call(`s/${id}`);

    expect(response.status).toBe(200);
    expect(await response.text()).toBe(SCENARIO);
  });

  it("answers HEAD with GET's headers and no source", async () => {
    const { id } = (await (await post(SCENARIO)).json()) as { id: string };

    const response = await call(`s/${id}`, { method: "HEAD" });

    expect(response.status).toBe(200);
    expect(response.headers.get("content-length")).toBe(
      String(new TextEncoder().encode(SCENARIO).length),
    );
    expect(await response.text()).toBe("");
  });

  it("uses one cache entry regardless of a query string", async () => {
    const { id } = (await (await post(SCENARIO)).json()) as { id: string };
    await call(`s/${id}?from=shared-link`);
    await env.DB.exec("DELETE FROM scenarios");

    const response = await call(`s/${id}`);

    expect(response.status).toBe(200);
    expect(await response.text()).toBe(SCENARIO);
  });
});

describe("the routes themselves", () => {
  it("explains itself at the root", async () => {
    const response = await call("");

    expect(response.status).toBe(200);
    expect(await response.text()).toContain("POST /s");
  });

  it("answers a preflight, so a browser on another origin can post", async () => {
    const response = await call("s", { method: "OPTIONS" });

    expect(response.status).toBe(204);
    expect(response.headers.get("access-control-allow-origin")).toBe("*");
    expect(response.headers.get("access-control-allow-methods")).toContain("POST");
  });

  it("allows any origin to read, since everything here is public", async () => {
    const { id } = (await (await post(SCENARIO)).json()) as { id: string };

    const response = await call(`s/${id}`);

    expect(response.headers.get("access-control-allow-origin")).toBe("*");
  });

  it("will not be written to by any other method", async () => {
    expect((await call("s", { method: "GET" })).status).toBe(405);
    const id = "0".repeat(64);
    expect((await call(`s/${id}`, { method: "DELETE" })).status).toBe(405);
    expect((await call(`s/${id}`, { method: "PUT" })).status).toBe(405);
  });

  it("has nothing else to offer", async () => {
    expect((await call("elsewhere")).status).toBe(404);
  });
});
