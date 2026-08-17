/**
 * A store for testbed scenarios, addressed by the hash of their source.
 *
 * Three routes: post a scenario and get a link back, follow the link to get the
 * source, and a plain-text page at the root saying so. There are no accounts and
 * nothing is private -- a link is the only handle on a scenario, and everyone
 * who has it can read it.
 *
 * Content addressing does most of the work. Posting the same source twice is the
 * same row and the same link, every response can be cached forever because an id
 * cannot come to mean something else, and there is nothing to update.
 */

// Env comes from worker-configuration.d.ts, which `wrangler types` generates
// from the bindings in wrangler.jsonc -- so the D1 binding is typed by the
// config that creates it rather than by a second declaration here.

/** Scenarios are a few KB of Python. Anything past this is not one. */
const MAX_BYTES = 64 * 1024;

/**
 * A complete SHA-256 digest. It is longer than a truncated id, but this store
 * is anonymous and public: shortening a content address only makes deliberate
 * collisions cheaper, while 64 hex characters are still an ordinary URL.
 */
const ID_LENGTH = 64;

const ID_PATTERN = /^[0-9a-f]{64}$/;

/** Immutable content, so the answer is good until the heat death of the CDN. */
const FOREVER = "public, max-age=31536000, immutable";

const USAGE = `box2d-py scenario store

  POST /s          the source as the body, returns {"id", "bytes", "url"}
  GET  /s/<id>     that source back, as text/x-python

Ids are all ${ID_LENGTH} hex characters of the SHA-256 of the source's
UTF-8 bytes, so posting the same scenario twice gives the same link. Nothing
here is private and nothing can be deleted.
`;

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // The browser build fetches this from another origin, and there is nothing
    // to protect: everything here is public and unauthenticated by design.
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (url.pathname === "/" && request.method === "GET") {
      return text(200, USAGE);
    }

    if (url.pathname === "/s") {
      if (request.method !== "POST") {
        return problem(405, "POST a scenario here, or GET /s/<id> to read one");
      }
      return post(request, env, url);
    }

    const match = url.pathname.match(/^\/s\/(.+)$/);
    if (match) {
      if (request.method !== "GET" && request.method !== "HEAD") {
        return problem(405, "scenarios are immutable; this is a GET");
      }
      return get(match[1], request, env, ctx);
    }

    return problem(404, "no such route");
  },
} satisfies ExportedHandler<Env>;

/** Store a scenario, or recognise one that is already stored. */
async function post(request: Request, env: Env, url: URL): Promise<Response> {
  const body = await readScenario(request);
  if ("response" in body) {
    return body.response;
  }
  const { source, bytes } = body;

  if (!source.trim()) {
    return problem(400, "the body is the scenario's source, and it was empty");
  }

  const id = await scenarioId(bytes);

  // One insert first, rather than a SELECT followed by an INSERT. That makes
  // the first post one D1 query and lets the primary key settle simultaneous
  // posts. A loser reads the winning row below and verifies that it really is
  // the same content; even a concurrent hash collision cannot quietly alias.
  const inserted = await env.DB.prepare(
    "INSERT OR IGNORE INTO scenarios (id, source, bytes, created_at) VALUES (?, ?, ?, ?)",
  )
    .bind(id, source, bytes.length, Date.now())
    .run();

  if (inserted.meta.changes === 1) {
    return linkResponse(201, id, bytes.length, url);
  }

  const existing = await env.DB.prepare("SELECT source FROM scenarios WHERE id = ?")
    .bind(id)
    .first<{ source: string }>();
  if (!existing) {
    return problem(503, "the scenario could not be stored; try again");
  }
  if (existing.source !== source) {
    return problem(409, `${id} is taken by different content`);
  }
  return linkResponse(200, id, bytes.length, url);
}

/** Read at most MAX_BYTES and reject bytes that are not UTF-8 source text. */
async function readScenario(
  request: Request,
): Promise<{ source: string; bytes: Uint8Array } | { response: Response }> {
  const declared = request.headers.get("content-length");
  if (declared && /^\d+$/.test(declared) && Number(declared) > MAX_BYTES) {
    return { response: problem(413, `${declared} bytes; the limit is ${MAX_BYTES}`) };
  }

  const reader = request.body?.getReader();
  if (!reader) {
    return { source: "", bytes: new Uint8Array() };
  }

  const chunks: Uint8Array[] = [];
  let length = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.byteLength;
    if (length > MAX_BYTES) {
      await reader.cancel();
      return {
        response: problem(413, `more than ${MAX_BYTES} bytes; the limit is ${MAX_BYTES}`),
      };
    }
    chunks.push(value);
  }

  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }

  try {
    return {
      // Keep a UTF-8 BOM as U+FEFF. TextDecoder strips it by default, which
      // would make GET return different bytes from the ones the id hashes.
      source: new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes),
      bytes,
    };
  } catch {
    return { response: problem(400, "the scenario must be UTF-8 text") };
  }
}

/** Hand back a scenario's source. */
async function get(
  id: string,
  request: Request,
  env: Env,
  ctx: ExecutionContext,
): Promise<Response> {
  if (!ID_PATTERN.test(id)) {
    return problem(400, `${id} is not a scenario id`);
  }

  // An id cannot change what it points at, so a hit here is always right and,
  // where Cloudflare's Cache API is active, avoids a D1 read entirely.
  const cache = caches.default;
  const cacheUrl = new URL(request.url);
  cacheUrl.search = "";
  const cacheKey = new Request(cacheUrl, { method: "GET" });
  const hit = await cache.match(cacheKey);
  if (hit) {
    return request.method === "HEAD" ? withoutBody(hit) : hit;
  }

  const row = await env.DB.prepare("SELECT source, bytes FROM scenarios WHERE id = ?")
    .bind(id)
    .first<{ source: string; bytes: number }>();
  if (!row) {
    return problem(404, `no scenario ${id}`);
  }

  const response = new Response(row.source, {
    headers: {
      ...corsHeaders(),
      "content-type": "text/x-python; charset=utf-8",
      "content-length": String(row.bytes),
      "cache-control": FOREVER,
      "x-content-type-options": "nosniff",
    },
  });
  ctx.waitUntil(cache.put(cacheKey, response.clone()));
  return request.method === "HEAD" ? withoutBody(response) : response;
}

/** The ID_LENGTH hex characters of the SHA-256 of the source's bytes. */
export async function scenarioId(source: string | Uint8Array): Promise<string> {
  const bytes = typeof source === "string" ? new TextEncoder().encode(source) : source;
  const digest = await crypto.subtle.digest(
    "SHA-256",
    bytes,
  );
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, ID_LENGTH);
}

/** What a caller gets back: the id, and the link to give someone else. */
function link(id: string, bytes: number, url: URL) {
  return { id, bytes, url: `${url.origin}/s/${id}` };
}

function linkResponse(status: number, id: string, bytes: number, url: URL): Response {
  const body = link(id, bytes, url);
  return json(status, body, { location: body.url });
}

/** HEAD carries the same status and headers as GET, but never its source. */
function withoutBody(response: Response): Response {
  return new Response(null, { status: response.status, headers: response.headers });
}

function corsHeaders(): Record<string, string> {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, HEAD, POST, OPTIONS",
    "access-control-allow-headers": "content-type",
    "access-control-max-age": "86400",
  };
}

function json(
  status: number,
  body: unknown,
  extraHeaders: Record<string, string> = {},
): Response {
  return Response.json(body, {
    status,
    headers: { ...corsHeaders(), "cache-control": "no-store", ...extraHeaders },
  });
}

function text(status: number, body: string): Response {
  return new Response(body, {
    status,
    headers: {
      ...corsHeaders(),
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

/** An error a person can read, since a person is who pastes these URLs. */
function problem(status: number, detail: string): Response {
  return text(status, `${status}: ${detail}\n`);
}
