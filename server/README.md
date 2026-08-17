# The scenario store

A Cloudflare Worker that serves the WASM testbed as static assets and keeps
shared scenarios in D1. The page and API use one origin, so the browser build
needs no server URL or CORS setup.

There are no accounts. A link is the only handle on a scenario, everyone who has
it can read it, and nothing can be deleted.

## What it does

| | |
|---|---|
| `POST /s` | the source as the body, returns `{"id", "bytes", "url"}` |
| `GET /s/<id>` | that source back, as `text/x-python` |
| `GET /` | the WASM testbed |

```console
$ curl -X POST --data-binary @my_scenario.py https://…/s
{"id":"cc079dc74034f6c1585e1b4a5e9d19d1398203bebfaf570ac067779c518f8d01","bytes":248,"url":"https://…/s/cc079dc74034f6c1585e1b4a5e9d19d1398203bebfaf570ac067779c518f8d01"}

$ curl https://…/s/cc079dc74034f6c1585e1b4a5e9d19d1398203bebfaf570ac067779c518f8d01
from box2d_testbed.base_test import BaseTest, UI
…
```

## Why it is shaped like this

**An id is the hash of the source** -- all 64 hex characters of the SHA-256 of
its UTF-8 bytes. Both ends can work one out without asking the other, which is
worth more than it sounds: the testbed knows a scenario's link before it uploads
it, and can tell whether the store already has one.

```python
>>> hashlib.sha256(source.encode()).hexdigest()
'cc079dc74034f6c1585e1b4a5e9d19d1398203bebfaf570ac067779c518f8d01'
```

The complete digest is longer than a truncated id, but this is an anonymous
public store and 64 hex characters are still an ordinary URL. **SHA-256 rather
than MD5** for two reasons -- `crypto.subtle` has no MD5, so it would mean
shipping a JS implementation, and cheap collisions are exactly the wrong trade
for public content addressing. Content that somehow arrives for an occupied id
but does not match what is stored gets a `409` rather than being papered over.

**Nothing is mutable**, which follows from the above and buys a lot: posting the
same source twice is one row and one link, and every read can be cached forever.
The `GET` path answers out of the data center's Cache API before it reaches the
database, so a popular scenario does not repeatedly read D1. There is no `PUT`
and no `DELETE`.

**D1 rather than KV.** Scenarios are a few KB of Python, so one table holds them,
and D1 can answer "the most recent" -- which KV cannot without an index
maintained by hand. Immutability plus the cache means the database is not in the
hot path anyway.

**It is a pastebin that accepts Python**, and will be used as one. What stands
against that here is a 64 KiB cap and the absence of any way to delete or
overwrite. Rate limiting belongs in front of `POST` before this is public; see
below.

## Running it

Needs **Node 22 or newer**. If the only node on your `PATH` is older, emsdk
ships one, the same trick `src/tools/build_wasm.sh` uses:

```bash
EMSDK_NODE="$(find "$HOME/.cache/pyodide-build" -maxdepth 5 -type d -path '*/emsdk/node/*/bin' | head -1)"
export PATH="$EMSDK_NODE:$PATH"
```

```bash
npm install
npm test           # runs in workerd against a real local D1
npm run typecheck  # regenerates the runtime types, then tsc
```

The tests run inside the Workers runtime rather than against a mock of D1, and
they apply the migrations from `migrations/` rather than stating the schema
themselves -- so a mistake in a migration fails here rather than on the way to
production.

Build the current WASM wheel once, then run the complete site locally:

```bash
cd ..
pyodide build
cd server
npm run migrate:local
npm run dev          # http://localhost:8787
```

`npm run dev` runs `web/prepare.py` first. Static assets bypass the Worker;
`/s` and `/s/<hash>` invoke it and use local D1.

## Deploying

For a new deployment, create the database once and put the id it prints in
`wrangler.jsonc`:

```bash
npx wrangler d1 create box2d-py # paste the id into wrangler.jsonc
npm run migrate:remote
npm run deploy
```

The returned `*.workers.dev` URL is already a usable sharing endpoint. Attach a
custom domain or route before relying on the Cache API: Cloudflare deliberately
makes programmatic cache operations on `*.workers.dev` deployments no-ops. The
immutable response headers are still correct there, but reads continue to reach
D1 until the Worker has a custom-domain cache.

## Still to do

- **Rate limiting on `POST`**, before the URL is public. A Cloudflare rate
  limiting rule is the least code; a Durable Object counter is the alternative
  if the limit needs to be per-something-else.
- **`GET /recent`**, which the `created_at` index is already there for. Left out
  while ids are the only names a scenario has -- a list of hashes is not a
  gallery.
- **Nothing fetched executes on arrival.** The web testbed opens imported source
  read-only and unrun. Run is explicit; Fork first makes an editable copy.
